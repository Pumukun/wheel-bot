# handlers/admin.py
import logging
from aiogram import Bot, Router, types
from aiogram.filters import Command, BaseFilter

import state
from config import ADMIN_USER_ID, GIF_URL, save_subscribers
from services.logic import calculate_and_format_results

from keyboards.inline import create_pagination_keyboard


# TODO [DX]: Создание фильтра — хорошая практика, чтобы не проверять ID админа в каждом хэндлере.
class IsAdmin(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id == ADMIN_USER_ID


router = Router()


@router.message(Command("votestart"), IsAdmin())
async def start_voting_admin(message: types.Message):
    if state.current_status == state.VotingStatus.IN_PROGRESS:
        await message.reply("Голосование уже идёт !")
        return

    state.current_status = state.VotingStatus.IN_PROGRESS
    state.final_results_calculated = False
    state.cached_results_string = ""

    await message.reply("Начинаем голосование, рассылаем списки участникам")
    all_film_names = list(state.film_ratings.keys())
    if not all_film_names:
        await message.reply("Ниче нет, никто ничего не вкинул")
        state.current_status = state.VotingStatus.NOT_STARTED
        return
    users_notified_count = 0
    bot_insstance = message.bot

    for user_id, user_obj in state.users.items():
        if user_obj.get_films():
            message_text, keyboard = create_pagination_keyboard(
                user_obj, all_film_names, page=0
            )

            if not keyboard:
                logging.warning(f"User {user_id} added films, but no films to vote on.")
                continue

            try:
                await bot_insstance.send_message(
                    chat_id=user_id,
                    text=message_text,
                    reply_markup=keyboard
                )
                users_notified_count += 1
                logging.info(f"Pagelist sent to user {user_id} by /votestart")
            except Exception as e:
                logging.error(f"Не удалось отправить список голосования пользователю {user_id}: {e}")
                await message.answer(
                    f"⚠️ Не удалось отправить сообщение пользователю {user_obj.get_name()} (ID: {user_id}). Возможно, бот заблокирован.")

    await message.answer(f"Рассылка завершена. Уведомлено: {users_notified_count} чел.")


@router.message(Command("end"), IsAdmin())
async def end_voting_admin(message: types.Message):
    if state.current_status == state.VotingStatus.FINISHED:
        await message.reply(f"Голосование уже было завершено.\n{state.cached_results_string}")
        return

    if not state.film_ratings:
        await message.reply("Нет фильмов для голосования. Нечего завершать.")
        return

    logging.info(f"Admin (ID: {message.from_user.id}) initiated /end command.")
    state.cached_results_string = calculate_and_format_results()
    state.current_status = state.VotingStatus.FINISHED
    state.final_results_calculated = True

    results_broadcast_message = f"ГОЛОСОВАНИЕ ПРИНУДИТЕЛЬНО ЗАВЕРШЕНО АДМИНИСТРАТОРОМ!\n\n{state.cached_results_string}"

    # TODO [UX]: Разослать финальные результаты всем участникам, а не только ответить админу.
    await message.answer(results_broadcast_message)
    logging.info(f"Final film_ratings state at forced end by admin: {state.film_ratings}")


@router.message(Command("adduser"), IsAdmin())
async def add_user_to_notify(message: types.Message):
    payload = message.text[len("/adduser "):].strip()
    if not payload.isdigit():
        await message.reply("Использование: /adduser <user_id>")
        return

    user_id = int(payload)
    state.subscribed_users.add(user_id)
    save_subscribers(state.subscribed_users)
    await message.reply(f"✅ Пользователь {user_id} добавлен в список рассылки.")
    logging.info(f"Admin added user {user_id} to subscribers list.")


@router.message(Command("removeuser"), IsAdmin())
async def remove_user_from_notify(message: types.Message):
    payload = message.text[len("/removeuser "):].strip()
    if not payload.isdigit():
        await message.reply("Использование: /removeuser <user_id>")
        return

    user_id = int(payload)
    if user_id in state.subscribed_users:
        state.subscribed_users.discard(user_id)
        save_subscribers(state.subscribed_users)
        await message.reply(f"❌ Пользователь {user_id} удалён из списка рассылки.")
        logging.info(f"Admin removed user {user_id} from subscribers list.")
    else:
        await message.reply(f"Пользователь {user_id} не найден в списке подписчиков.")


@router.message(Command("subscribers"), IsAdmin())
async def list_subscribers(message: types.Message):
    if not state.subscribed_users:
        await message.reply("📋 Нет подписчиков.\n\nПользователи могут подписаться командой /subscribe")
        return

    subscriber_info = []
    for user_id in state.subscribed_users:
        if user_id in state.users:
            user_name = state.users[user_id].get_name()
            subscriber_info.append(f"• {user_name} (ID: {user_id})")
        else:
            subscriber_info.append(f"• ID: {user_id}")

    subscribers_text = f"📋 Подписчики ({len(state.subscribed_users)}):\n" + "\n".join(subscriber_info)
    await message.reply(subscribers_text)


@router.message(Command("notify"), IsAdmin())
async def manual_notification(message: types.Message):
    if not state.subscribed_users:
        await message.reply("Нет подписчиков для рассылки.")
        return

    payload = message.text[len("/notify "):].strip()
    if not payload:
        await message.reply("Использование: /notify <текст сообщения>")
        return

    sent_count = 0
    for user_id in state.subscribed_users:
        try:
            await message.bot.send_message(chat_id=user_id, text=payload)
            sent_count += 1
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

    await message.reply(f"📢 Рассылка завершена. Отправлено: {sent_count}/{len(state.subscribed_users)}")
    logging.info(f"Admin sent manual notification to {sent_count} subscribers.")


async def send_startup_gif_and_message(bot: Bot):
    if not state.subscribed_users:
        logging.info("Список подписчиков пуст, стартовые уведомления не отправляются.")
        logging.info("Пользователи могут подписаться командой /subscribe")
        return

    original_message_text: str = 'alarm! Да начнётся Колесо!'
    sent_count = 0
    failed_users = []

    for user_id in state.subscribed_users:
        try:
            if GIF_URL:
                await bot.send_animation(chat_id=user_id, animation=GIF_URL)
            await bot.send_message(chat_id=user_id, text=original_message_text)
            sent_count += 1
            logging.info(f"Стартовое уведомление отправлено подписчику с ID {user_id}")
        except Exception as e:
            failed_users.append(user_id)
            logging.error(f"Ошибка при отправке стартового уведомления пользователю с ID {user_id}: {e}")

    logging.info(f"Стартовая рассылка завершена. Отправлено: {sent_count}/{len(state.subscribed_users)}")
    if failed_users:
        logging.warning(f"Не удалось отправить уведомления пользователям: {failed_users}")