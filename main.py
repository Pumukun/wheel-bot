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

from user import User

# Dict["id", User]
users: Dict[int, User] = {}
film_ratings: Dict[str, int] = {}
user_votes: Dict[str, Dict[str, Dict[str, int]]] = {}
gif_file: str = r'https://i.postimg.cc/kgppKXB3/sex-alarm.gif'
users_to_notify = ['383688364']
#, '726099628', '405212645', '897485892', '653482793', '527456671', '801068651']

TOKEN: str | None = getenv('TG_BOT_TOKEN')
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
/vote - проголосовать за или против фильма (используйте формат: `/vote [название_фильма/id_фильма]: [за/против]/[+/-], ...`)
/filmlist - вывести список фильмов
    """
    )

@dp.message(Command("add"))
async def add(message: types.Message):
    if len(message.text.split(',')) != 2:
        await message.reply("Пожалуйста, введите два названия фильмов, разделенных запятой.")
        return

    user_id: int = message.from_user.id
    user_name: str = message.from_user.username or message.from_user.first_name

    if user_id not in users:
        users[user_id] = User(user_name, [], user_id)

    film1, film2 = map(str.strip, message.text.replace('/add ', '').split(','))
    if film1 == film2:
        await message.reply("Фильмы должны быть разные")
        return

    if user_id in users and len(users[user_id].get_films()) >= 2:
        await message.reply("Больше добавлять нельзя")
        return

    if film1 in film_ratings.keys():
        await message.reply(f'{film1}- повтор')
        return
    if film2 in film_ratings.keys():
        await message.reply(f'{film2}- повтор')
        return

    users[user_id].films = [film1, film2]
    await message.reply(f"Фильмы {film1} и {film2} добавлены для пользователя {user_name}.")
    film_ratings.update({
        film1: 0,
        film2: 0
    })

def print_films_score(film_ratings):
    for film_name, score in film_ratings.items():
        print(f"{film_name}: {score}")


def parse_votes(msg: str) -> Dict[str, str]:
    msg = msg.text
    msg = msg.replace('/vote ', '')
    # f1: +, f2: за, f4: -
    msg = msg.replace(' ', '')
    print(msg)
    return dict(map(lambda x: x.split(':'), msg.split(',')))


def shuffle_list(user_id: int) -> Dict[int, str]:
    ind: int = 1
    for f in film_ratings:
        users[user_id].shuffled_films[ind] = f
        ind += 1
    sh_list = list(users[user_id].get_shuffled_films().items())
    random.shuffle(sh_list)
    users[user_id].shuffled_films = dict(sorted(sh_list, key=lambda x: x[0]))
    return dict(sorted(sh_list, key=lambda x: x[0]))


@dp.message(Command("vote"))
async def vote(message: types.Message):
    #if len(message.text.split(':')) != 2:
    #    await message.reply("Формат : /vote <название фильма>: <за/против>, <название фильма>: <за/против>, ...")
    
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Вы ещё не добавляли ни одного фильма")
        return

    parsed_votes: Dict[str, str] = parse_votes(message)
    
    user_sh_films: Dict[int, str] = users[user_id].get_shuffled_films()
    if user_sh_films == {}:
        user_sh_films = shuffle_list(user_id)
        users[user_id].shuffled_films = user_sh_films

    
    buffer: str = ""
    for film_name, vote in parsed_votes.items():
        if film_name.isdigit():
            film_name = user_sh_films[int(film_name)]
            print(film_name)
        
        if film_name not in film_ratings and int(film_name) not in user_sh_films:
            await message.reply("Фильма нет или я гей и хуёво закодил")
            return
        if vote.lower() not in ['за','против', '+', '-']:
            print(vote.lower(), film_name)
            await message.reply("Голос должен быть 'за' / 'против' или '+' / '-'")
            return
        if film_name in users[user_id].get_films():
            await message.reply("За своё не голосуем")
            return

        if vote.lower() in ['за', '+']:
            if (users[user_id].get_votes_for() >= 2):
                await message.reply("Нельзя больше 2 голосов 'за'")
                return
            film_ratings[film_name] += 1
            users[user_id].votes_for += 1
        else:
            if (users[user_id].get_votes_against() >= 2):
                await message.reply("Нельзя больше 2 голосов 'против'")
                return
            film_ratings[film_name] -= 1
            users[user_id].votes_against += 1

        buffer += f"Ваш голос '{vote}' для фильма '{film_name}' принят\n"

        print(film_ratings.items())

    await message.reply(buffer)


@dp.message(Command("filmlist"))
async def filmlist(message: types.Message):
    user_id: int = message.from_user.id

    if user_id not in users:
        await message.reply("Вы ещё не добавляли ни одного фильма")
        return
        
    sh_list: Dict[int, str] = shuffle_list(user_id)
    print(sh_list)
    
    buffer: str = ""
    for index, film in users[user_id].get_shuffled_films().items():
        buffer += f"{index}. {film}\n"
    await message.answer(f'Список добавленных фильмов в случайном порядке:\n{buffer}')

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
