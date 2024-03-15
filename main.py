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
from typing import List, Dict

from markup import start_markup

user_films: Dict[str, List[str]] = {}
film_ratings: Dict[str, int] = {}
user_votes: Dict[str, Dict[str, Dict[str, int]]] = {}

TOKEN = '6870699781:AAHLu0HKhuIw3-HAuq-zTcX9N6zXmz0UerY'

dp = Dispatcher()


@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
    """
*НЕГРЫ!*, ПИДОРЫ!Привет! Я бот для голосования за фильмы.

Доступные команды:
/help - получить справку
    """,
    reply_markup=start_markup()
    )

@dp.message(Command("help"))
async def help(message: types.Message):
    await message.answer(
    """
*Доступные команды:*
/add - добавить два фильма для голосования (разделите названия запятой)
/vote - проголосовать за или против фильма (используйте формат: `/vote [название фильма][за/против]`)
/list - вывести список фильмов
    """
    )

@dp.message(Command("add"))
async def add(message: types.Message):
    if len(message.text.split(',')) != 2:
        await message.reply("Пожалуйста, введите два названия фильмов, разделенных запятой.")
        return
 
    user_name: str = message.from_user.username or message.from_user.first_name
    
    film1, film2 = map(str.strip, message.text.replace('/add ', '').split(','))
    if film1 == film2:
        await message.reply("Фильмы должны быть разные")
        return
    
    if user_name in user_films and len(user_films[user_name]) >= 2:
        await message.reply("Больше добавлять нельзя")
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
async def vote(message: types.Message):
    if len(message.text.split(',')) != 2:
        await message.reply("Формат : /vote <название фильма>,<за/против>")
    user_name = message.from_user.username or message.from_user.first_name
    film_name, vote = map(str.strip, message.text.replace('/vote ', '').split(','))
    if film_name not in film_ratings:
        await message.reply("Фильма нет или я гей и хуёво закодил")
        return
    if vote.lower() not in ['за','против']:
        await message.reply("Голос должен быть 'за' или 'против' ")
        return
    if film_name in user_films.get(user_name, []):
        await message.reply("За своё не голосуем")
        return
    if user_name not in user_votes:
        user_votes[user_name] = {}
    if film_name in user_votes[user_name]:
        await message.reply('Уже голосовал за это')
        return
    if len(user_votes[user_name]) >= 4:
        await message.reply("Голоса кончились")
        return
    
    #TODO нужно чтобы голосов "за" и "против" было не больше двух             
    if vote.lower() == 'за':
        user_votes[user_name][film_name] = {'за': 1, 'против': 0}
    else:
        user_votes[user_name][film_name] = {'за':0, 'против': 1}
    
    current_score: int = film_ratings.get(film_name, 0)
    if vote.lower() == 'за':
        current_score += 1
    else:
        current_score -= 1

    film_ratings[film_name] = current_score
    
    for film_name, score in film_ratings.items():
        print(f"{film_name}: {score}")

@dp.message(Command("list"))
async def list(message: types.Message):
    films_list: str = "\n".join(film_ratings.keys())
    await message.answer(f'список добавленых фильмов:\n{films_list}')

@dp.message()
async def reply(message: types.Message):
    if message.text == 'HEГP':
        await help(message)
    elif message.text == 'Голосование':
        await vote(message)
    elif message.text == 'Список':
        await list(message)

async def main():
    bot = Bot(TOKEN, parse_mode=ParseMode.MARKDOWN)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

