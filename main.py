#!/usr/bin/env python


import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.utils.markdown import hbold


TOKEN = '6870699781:AAHLu0HKhuIw3-HAuq-zTcX9N6zXmz0UerY'

dp = Dispatcher()


@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
    """
*НЕГРЫ!*, ПИДОРЫ!Привет! Я бот для голосования за фильмы.

Доступные команды:
/help - получить справку
    """
    )

@dp.message(Command("help"))
async def help(message: types.Message):
    await message.answer(
    """
*Доступные команды:*
/add - добавить два фильма для голосования (разделите названия запятой)
/vote - проголосовать за или против фильма (используйте формат: `/vote [название фильма] [голос]`)
/show - вывести список фильмов
    """
    )

@dp.message(Command("add"))
async def add(message: types.Message):
    username = message.from_user.username or message.from_user.full_name
    await message.answer('')

@dp.message(Command("vote"))
async def vode(message: types.Message):
    await message.answer('')

@dp.message(Command("list"))
async def list(message: types.Message):
    await message.answer('')

async def main():
    bot = Bot(TOKEN, parse_mode=ParseMode.MARKDOWN)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

