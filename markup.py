from aiogram.types import ReplyKeyboardMarkup, KeyboardButton



def start_markup():
    btn1 = KeyboardButton(text='HEГP')
    btn2 = KeyboardButton(text='Голосование')
    btn3 = KeyboardButton(text='Список')

    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [btn2, btn3],
        [btn1]
    ])

