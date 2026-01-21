# handlers/admin.py
import logging
from aiogram import Bot, Router, types
from aiogram.filters import Command, BaseFilter

import state
from config import ADMIN_USER_ID, USERS_TO_NOTIFY, GIF_URL
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
                users_notified_count +=1
                logging.info(f"Pagelist sent to user {user_id} by /votestart")
            except Exception as e:
                # Если пользователь заблокировал бота
                logging.error(f"Не удалось отправить список голосования пользователю {user_id}: {e}")
                # (Опционально) Сообщаем админу о проблеме
                await message.answer(f"⚠️ Не удалось отправить сообщение пользователю {user_obj.get_name()} (ID: {user_id}). Возможно, бот заблокирован.")

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


async def send_startup_gif_and_message(bot: Bot):
    if not USERS_TO_NOTIFY:
        logging.info("Список USERS_TO_NOTIFY пуст, стартовые уведомления не отправляются.")
        return
    
    original_message_text: str = 'alarm! Да начнётся Колесо!'
    for user_id_str in USERS_TO_NOTIFY:
        try:
            if GIF_URL:
                await bot.send_animation(chat_id=user_id_str, animation=GIF_URL)
            await bot.send_message(chat_id=user_id_str, text=original_message_text)
            logging.info(f"Стартовое уведомление отправлено пользователю с ID {user_id_str}")
        except Exception as e:
            logging.error(f"Ошибка при отправке стартового уведомления пользователю с ID {user_id_str}: {e}")
