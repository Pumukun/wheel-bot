# keyboards/reply.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# TODO: лучше переделать под Inline-кнопки, да и для всего остального их надо сделать

def start_markup():
    btn1 = KeyboardButton(text='HEГP')
    btn2 = KeyboardButton(text='Голосование')
    btn3 = KeyboardButton(text='Список')
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [btn2, btn3],
        [btn1]
    ])
