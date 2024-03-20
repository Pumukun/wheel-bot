#!/usr/bin/env python

import random
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
gif_file: str = r'https://i.postimg.cc/kgppKXB3/sex-alarm.gif'
users_to_notify = ['383688364']
#, '726099628', '405212645', '897485892', '653482793', '527456671', '801068651']

TOKEN: str | None = getenv('BOT_TOKEN')
bot = Bot(TOKEN, parse_mode=ParseMode.MARKDOWN)
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
/vote - проголосовать за или против фильма (используйте формат: `/vote [название фильма],[за/против]`)
/filmlist - вывести список фильмов
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
    user_name: str = message.from_user.username or message.from_user.first_name
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

'''
@dp.message(Command("list"))
async def list(message: types.Message):
    films_list: str = "\n".join(film_ratings.keys())
    await message.answer(f'список добавленых фильмов:\n{films_list}')
'''

@dp.message(Command("filmlist"))
async def filmlist(message: types.Message):
    films: List[str] = list(film_ratings.keys())

    random.shuffle(films)
    films_str: str = "\n".join(films)
    await message.answer(f'Список добавленных фильмов в случайном порядке:\n{films_str}')

@dp.message()
async def reply(message: types.Message):
    if message.text == 'HEГP':
        await help(message)
    elif message.text == 'Голосование':
        await vote(message)
    elif message.text == 'Список':
        await filmlist(message)

async def send_message_to_users():
    for user_id in users_to_notify:
        message: str = 'alarm! Да начнётся Колесо!'
        try:
            await bot.send_animation(user_id, gif_file)
            await bot.send_message(user_id, message)
            print(f"Сообщение отправлено пользователю с ID {user_id}")
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю с ID {user_id}: {e}")


async def main():
    await send_message_to_users()
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
