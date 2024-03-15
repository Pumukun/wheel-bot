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

user_films = {}
film_ratings = {}

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
/list - вывести список фильмов
    """
    )

@dp.message(Command("add"))
async def add(message: types.Message):
    if len(message.text.split(',')) != 2:
        await message.reply("Пожалуйста, введите два названия фильмов, разделенных запятой.")
        return

    user_name = message.from_user.username or message.from_user.first_name

    film1, film2 = map(str.strip, message.text.replace('/add ', '').split(','))

    if user_name in user_films:
        await message.reply("У вас уже есть фильмы в списке!")
        return
    
    if film1 in film_ratings.keys():
        await message.reply(f'{film1}- повтор')
        return
    if film2 in film_ratings.keys():
        await message.reply(f'{film2}- повтор')
        return 

    user_films[user_name] = [film1, film2]
    await message.reply(f"Фильмы {film1} и {film2} добавлены для пользователя {user_name}.")
    film_ratings.update({film1: 0, film2: 0})

@dp.message(Command("vote"))
async def vode(message: types.Message):
    await message.answer('')

@dp.message(Command("list"))
async def list(message: types.Message):
    films_list = "\n".join(film_ratings.keys())
    await message.answer(f'список добавленх фильмов:\n{films_list}')

async def main():
    bot = Bot(TOKEN, parse_mode=ParseMode.MARKDOWN)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

