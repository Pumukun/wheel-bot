# handlers/admin.py
import logging
from aiogram import Bot, Router, types
from aiogram.filters import Command, BaseFilter

import state
from config import ADMIN_USER_ID, USERS_TO_NOTIFY, GIF_URL
from services.logic import calculate_and_format_results

# TODO [DX]: Создание фильтра — хорошая практика, чтобы не проверять ID админа в каждом хэндлере.
class IsAdmin(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id == ADMIN_USER_ID

router = Router()

@router.message(Command("votestart"), IsAdmin())
async def start_voting_admin(message: types.Message):
    # TODO [UX]: После старта голосования стоит отправить уведомление всем участникам,
    # которые добавляли фильмы, чтобы они знали о начале.
    state.is_voting = True
    await message.reply("Голосование начато!")

@router.message(Command("end"), IsAdmin())
async def end_voting_admin(message: types.Message):
    if state.final_results_calculated:
        await message.reply(f"Голосование уже было завершено.\n{state.cached_results_string}")
        return

    if not state.film_ratings:
        await message.reply("Нет фильмов для голосования. Нечего завершать.")
        return

    logging.info(f"Admin (ID: {message.from_user.id}) initiated /end command.")
    state.cached_results_string = calculate_and_format_results()
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
