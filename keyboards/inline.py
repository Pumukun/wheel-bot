# keyboards/inline.py
import math
import logging
from typing import List, Tuple, Optional
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from user import User 

class VotePagingCallback(CallbackData, prefix="page_vote"):
    """
    action: 'for' или 'against'
    film_id: ID фильма из *персонального* списка (1, 2, 3...)
    """
    action: str
    film_id: int

class NavigatePagingCallback(CallbackData, prefix="page_nav"):
    """
    action: 'prev' или 'next'
    page: номер страницы (начиная с 0)
    """
    action: str
    page: int

DUMMY_CALLBACK = "dummy_pagination_button"
PAGE_SIZE = 6

def create_pagination_keyboard(
    user: User, 
    all_film_names: List[str], 
    page: int = 0
) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    """
    Создает текст сообщения и клавиатуру с пагинацией.
    """
    
    user.ensure_shuffled_list_exists(all_film_names)
    shuffled_list = user.get_shuffled_films()
    user_own_films = user.get_films()

    films_to_display = []
    for film_id, film_name in shuffled_list.items():
        if film_name not in user_own_films:
            films_to_display.append((film_id, film_name))

    if not films_to_display:
        if user_own_films:
            return "В списке пока нет фильмов, добавленных другими участниками.", None
        return "Список фильмов для голосования пуст.", None

    total_films = len(films_to_display)
    total_pages = math.ceil(total_films / PAGE_SIZE)
    page = max(0, min(page, total_pages - 1)) 

    start_index = page * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    current_page_films = films_to_display[start_index:end_index]

    builder = InlineKeyboardBuilder()

    for film_id, film_name in current_page_films:
        display_name = (film_name[:25] + '...') if len(film_name) > 28 else film_name
        
        builder.row(
            InlineKeyboardButton(
                text="👎",
                callback_data=VotePagingCallback(action="against", film_id=film_id).pack()
            ),
            InlineKeyboardButton(
                text=display_name,
                callback_data=DUMMY_CALLBACK 
            ),
            InlineKeyboardButton(
                text="👍",
                callback_data=VotePagingCallback(action="for", film_id=film_id).pack()
            )
        )

    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=NavigatePagingCallback(action="prev", page=page - 1).pack()
            )
        )
    if end_index < total_films:
        nav_row.append(
            InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=NavigatePagingCallback(action="next", page=page + 1).pack()
            )
        )
    
    if nav_row:
        builder.row(*nav_row)

    message_text = f"Голосование (Страница {page + 1} / {total_pages})"
    
    return message_text, builder.as_markup()
