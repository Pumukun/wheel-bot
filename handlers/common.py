# handlers/common.py
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from keyboards.reply import start_markup
from .voting import filmlist
import state
from config import save_subscribers
import logging

router = Router()


@router.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        """Привет! Я бот для голосования за фильмы.
Доступные команды:
/help - получить справку
/add фильм1, фильм2 - добавить два фильма для голосования
/vote ID:голос - проголосовать
/filmlist - вывести список фильмов
/results - показать итоги голосования
/reset - сбросить свои голоса
/subscribe - подписаться на уведомления о голосовании
/end - (админ) завершить голосование""",
        reply_markup=start_markup()
    )


@router.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        """Доступные команды:
/add фильм1, фильм2 - добавить пару фильмов.
/vote фильм_ID:голос, ... - проголосовать. ID из /filmlist. голос: +/-. Пример: /vote 1:+, 3:-
Ограничения: 2 'за', 2 'против'. Нельзя за свои фильмы.
/filmlist - список всех фильмов.
/results - итоги голосования.
/subscribe - подписаться на уведомления о голосовании.
/unsubscribe - отписаться от уведомлений.
/end - (админ) завершает голосование."""
    )


@router.message(Command("subscribe"))
async def subscribe_notifications(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name

    if user_id in state.subscribed_users:
        await message.reply("Вы уже подписаны на уведомления о голосовании.")
        return

    state.subscribed_users.add(user_id)
    save_subscribers(state.subscribed_users)
    logging.info(f"User {user_name} (ID: {user_id}) subscribed to notifications.")
    await message.reply("✅ Вы подписались на уведомления о начале голосования!")


@router.message(Command("unsubscribe"))
async def unsubscribe_notifications(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name

    if user_id not in state.subscribed_users:
        await message.reply("Вы не подписаны на уведомления.")
        return

    state.subscribed_users.remove(user_id)
    save_subscribers(state.subscribed_users)
    logging.info(f"User {user_name} (ID: {user_id}) unsubscribed from notifications.")
    await message.reply("❌ Вы отписались от уведомлений о голосовании.")


# TODO [DX]: Этот хэндлер зависит от хэндлеров в других файлах. Это может привести к путанице.
# Лучше отправлять информационные сообщения напрямую, а не вызывать другие хэндлеры.
@router.message()
async def handle_text_buttons(message: types.Message):
    if message.text == 'Инфо' or message.text == 'HEГP':
        await help_command(message)
    elif message.text == 'Голосование':
        await message.reply("Для голосования используйте команду /vote, например: /vote 1:+, 2:-\n"
                            "Список фильмов и их ID можно посмотреть командой /filmlist.")
    elif message.text == 'Список':
        await filmlist(message)