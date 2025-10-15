# handlers/common.py
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from keyboards.reply import start_markup
from .voting import filmlist

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
/end - (админ) завершает голосование."""
    )

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
