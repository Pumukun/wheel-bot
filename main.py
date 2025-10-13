#!/usr/bin/env python
import os
import random
import asyncio
import logging
import sys
from os import getenv
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from typing import List, Dict, Tuple

from markup import start_markup
from user import User

# --- Глобальные переменные ---
users: Dict[int, User] = {}
film_ratings: Dict[str, int] = {}

gif_file: str = r'https://i.postimg.cc/kgppKXB3/sex-alarm.gif'  # URL вашей GIF
users_to_notify = ['383688364', '726099628', '405212645', '897485892', '653482793', '527456671',
                   '801068651', '1996813077']
ADMIN_USER_ID = 383688364

fallback_shuffled_films_cache: Dict[int, str] = {}
fallback_cache_is_fresh: bool = False

final_results_calculated: bool = False
is_voting: bool = False
cached_results_string: str = ""

load_dotenv()
TOKEN: str | None = os.getenv("MY_TOKEN")
if TOKEN is None:
    logging.critical("MY_TOKEN не найден в переменных окружения или .env файле. Завершение работы.")
    sys.exit(1)

bot = Bot(TOKEN, parse_mode=None)
dp = Dispatcher()


# --- Вспомогательные функции ---

def _generate_fibonacci_up_to(limit_count: int) -> List[int]:
    fibs = []
    if limit_count <= 0: return []
    a, b = 1, 2
    fibs.append(a)
    if limit_count == 1: return fibs
    fibs.append(b)
    if limit_count == 2: return fibs
    current_a, current_b = a, b
    while len(fibs) < limit_count:
        next_fib = current_a + current_b
        fibs.append(next_fib)
        current_a, current_b = current_b, next_fib
    return fibs

def _calculate_and_format_results_logic() -> str:
    if not film_ratings:
        return "Нет фильмов для подсчета."

    sorted_films_by_score_display = sorted(film_ratings.items(), key=lambda item: item[1], reverse=True)
    if not sorted_films_by_score_display:
        return "Нет фильмов после сортировки."

    all_scores = list(film_ratings.values())
    if not all_scores:
        return "Нет данных для подсчета."

    min_score = min(all_scores)
    max_score = max(all_scores)

    if min_score == max_score:
        score_to_assigned_points = {min_score: 1}
    else:
        points_count = max_score - min_score + 1
        
        fib_points_sequence = _generate_fibonacci_up_to(points_count)

        score_to_assigned_points = {}
        current_score_tier = min_score
        for i in range(points_count):
            point_value = fib_points_sequence[i] if i < len(fib_points_sequence) else (fib_points_sequence[-1] if fib_points_sequence else 1)
            score_to_assigned_points[current_score_tier] = point_value
            current_score_tier += 1

    result_lines = ["Итоги Голосования:"]
    for film_name, score in sorted_films_by_score_display:
        assigned_points = score_to_assigned_points.get(score, 1)  # Используем 1 как запасной вариант
        result_lines.append(f"• \"{film_name}\": Голоса: {score}, Очки: {assigned_points}")

    return "\n".join(result_lines) if len(result_lines) > 1 else "Не удалось сформировать результаты."

def get_or_create_fallback_shuffled_list() -> Dict[int, str]:
    global fallback_shuffled_films_cache, fallback_cache_is_fresh
    if not fallback_cache_is_fresh or not fallback_shuffled_films_cache:
        if not film_ratings:
            fallback_shuffled_films_cache.clear()
            fallback_cache_is_fresh = True
            return {}
        temp_film_list = list(film_ratings.keys())
        random.shuffle(temp_film_list)
        fallback_shuffled_films_cache.clear()
        for i, film_name in enumerate(temp_film_list):
            fallback_shuffled_films_cache[i + 1] = film_name
        fallback_cache_is_fresh = True
        logging.info("Fallback shuffled film list (re)generated and cached.")
    return fallback_shuffled_films_cache


def parse_votes(message_text: str) -> Dict[str, str]:
    if message_text.lower().startswith('/vote '):
        processed_text = message_text[len('/vote '):]
    else:
        processed_text = message_text
    processed_text = processed_text.replace(' ', '')
    votes_dict = {}
    if not processed_text: return votes_dict
    pairs = processed_text.split(',')
    for pair in pairs:
        if ':' in pair:
            parts = pair.split(':', 1)
            if len(parts) == 2:
                film_identifier, vote_action = parts[0].strip(), parts[1].strip()
                if film_identifier and vote_action: votes_dict[film_identifier] = vote_action
            else:
                logging.warning(f"Invalid vote pair format (missing action after colon?): {pair}")
        else:
            logging.warning(f"Invalid vote pair format (missing colon?): {pair}")
    return votes_dict


async def send_startup_gif_and_message():
    if not users_to_notify:
        logging.info("Список users_to_notify пуст, стартовые уведомления не отправляются.")
        return
    original_message_text: str = 'alarm! Да начнётся Колесо!'
    for user_id_str in users_to_notify:
        try:
            if gif_file:
                await bot.send_animation(chat_id=user_id_str, animation=gif_file)
            await bot.send_message(chat_id=user_id_str, text=original_message_text)
            logging.info(f"Стартовое уведомление (GIF и текст) отправлено пользователю с ID {user_id_str}")
        except Exception as e:
            logging.error(f"Ошибка при отправке стартового уведомления пользователю с ID {user_id_str}: {e}")


# --- Обработчики команд ---

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        """Привет! Я бот для голосования за фильмы.
Доступные команды:
/help - получить справку
/add фильм1, фильм2 - добавить два фильма для голосования (разделите названия запятой)
/vote фильм_ID_или_название: +/- - проголосовать (можно несколько через запятую)
/filmlist - вывести список фильмов для голосования
/results - показать итоги голосования
/reset - сбросить свои голоса
/end - (только для администратора) завершить голосование и подвести итоги
        """,
        reply_markup=start_markup()
    )


@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        """Доступные команды:
/add фильм1, фильм2 - добавить два фильма для голосования. Вы можете добавить только одну пару фильмов.
/vote фильм_ID:голос, ... - проголосовать. фильм_ID из /filmlist. голос: за/против/+/-. Пример: /vote 1:+, 3:-
  Ограничения: 2 'за', 2 'против'. Нельзя за свои фильмы.
/filmlist - список всех фильмов. Если вы добавляли фильмы, список будет персонально перемешан для вас.
/results - итоги голосования (доступны всем).
/end - (только для администратора) принудительно завершает голосование и подводит итоги (результаты видит только администратор).
        """
    )


@dp.message(Command("add"))
async def add(message: types.Message):
    global fallback_cache_is_fresh
    payload = message.text[len("/add "):].strip()
    if not payload:
        await message.reply("Пожалуйста, укажите два названия фильмов через запятую после команды /add.")
        return
    film_parts = [f.strip() for f in payload.split(',')]
    if len(film_parts) != 2:
        await message.reply("Пожалуйста, введите ровно два названия фильмов, разделенных запятой.")
        return

    user_id: int = message.from_user.id
    user_name: str = message.from_user.username or message.from_user.first_name

    if user_id not in users:
        users[user_id] = User(user_name, [], user_id)
    user_instance = users[user_id]

    film1, film2 = film_parts[0], film_parts[1]
    if not film1 or not film2:
        await message.reply("Названия фильмов не могут быть пустыми.")
        return
    if film1 == film2:
        await message.reply("Фильмы должны быть разные.")
        return
    if len(user_instance.get_films()) >= 2:
        await message.reply(f"{user_name}, вы уже добавили максимальное количество фильмов (2).")
        return
    if film1 in film_ratings:
        await message.reply(f"Фильм \"{film1}\" уже был добавлен ранее.")
        return
    if film2 in film_ratings:
        await message.reply(f"Фильм \"{film2}\" уже был добавлен ранее.")
        return

    user_instance.films.extend([film1, film2])
    film_ratings[film1] = 0
    film_ratings[film2] = 0
    fallback_cache_is_fresh = False
    await message.reply(f"Фильмы \"{film1}\" и \"{film2}\" добавлены вами, {user_name}.")
    logging.info(f"User {user_name} (ID: {user_id}) added films: {film1}, {film2}. Fallback cache invalidated.")
    logging.info(f"Текущее состояние film_ratings после добавления: {film_ratings}")


@dp.message(Command("filmlist"))
async def filmlist(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name
    display_list: Dict[int, str]
    list_type_msg: str
    all_current_film_names = list(film_ratings.keys())

    if not all_current_film_names:
        await message.answer("Список фильмов пока пуст. Добавьте фильмы командой /add.")
        return

    user_has_personally_added_films = False
    if user_id in users and users[user_id].get_films():
        user_has_personally_added_films = True

    if user_has_personally_added_films:
        user_instance = users[user_id]
        user_instance.ensure_shuffled_list_exists(all_current_film_names)
        display_list = user_instance.get_shuffled_films()
        list_type_msg = f"Список фильмов:"
    else:
        display_list = get_or_create_fallback_shuffled_list()
        if user_id in users:
            list_type_msg = f"Общий список фильмов ({user_name}), вы еще не добавляли свои фильмы:"
        else:
            list_type_msg = "Общий список фильмов для голосования:"

    if not display_list:
        await message.answer("Не удалось сформировать список фильмов. Попробуйте еще раз.")
        logging.warning(f"Filmlist display_list is empty for user {user_id} even though global films might exist.")
        return

    buffer: str = f"{list_type_msg} (ID. Название)\n"
    for index, film_name in display_list.items():
        buffer += f"{index}. {film_name}\n"
    await message.answer(buffer)

@dp.message(Command("reset"))
async def reset_votes(message: types.Message):
    user_id = message.from_user.id

    if user_id not in users[user_id].get_voted_on():
        await.message.reply("Вы ещё не голосовали, сбрасывать нечего")
        return

    user_instance = users[user_id]

    for film_name, vote_type in user_instance.get_voted_on().items():
        if film_name in film_ratings:
            if vote_type == 'за':
                film_ratings[film_name] -= 1
            elif vote_type == 'против':
                film_ratings[film_name] += 1

    user_instance.reset_votes()
    logging.info(f"User {message.from_user.username} (ID: {user_id}) has reset their votes.")
    await message.reply("Ваши голоса были сброшены. Теперь вы можете проголосовать заново.")

@dp.message(Command("vote"))
async def vote(message: types.Message):
    global final_results_calculated, cached_results_string
    if final_results_calculated:
        await message.reply("Голосование уже завершено. Для просмотра итогов используйте /results.")
        return
    
    if not is_voting:
        await message.reply("Голосование ещё не началось.")
        return

    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name

    if user_id not in users:
        users[user_id] = User(user_name, [], user_id)
        logging.info(f"New user {user_name} (ID: {user_id}) created on first vote.")
    user_instance = users[user_id]

    parsed_votes = parse_votes(message.text)
    if not parsed_votes:
        await message.reply("Некорректный формат голосования. Используйте: /vote ID:голос. Пример: /vote 1:+.")
        return

    all_current_film_names = list(film_ratings.keys())
    if not all_current_film_names:
        await message.reply("Нет фильмов для голосования. Дождитесь, пока кто-нибудь добавит их.")
        return

    user_instance.ensure_shuffled_list_exists(all_current_film_names)
    film_map_for_voting = user_instance.get_shuffled_films()

    if not film_map_for_voting and all_current_film_names:
        logging.error(f"Film map for voting for user {user_id} is empty, but global films exist.")
        await message.reply(
            "Ошибка: не удалось получить список фильмов для голосования. Попробуйте /filmlist, затем /vote.")
        return

    reply_buffer = ""
    successful_votes_in_this_message = 0
    log_film_scores_changed = False

    for film_identifier, vote_action_str in parsed_votes.items():
        actual_film_name = film_map_for_voting.get(int(film_identifier)) if film_identifier.isdigit() else None
        
        if not actual_film_name:
            reply_buffer += f"⚠️ Фильм с ID {film_identifier} не найден в вашем списке.\n"
            continue

        if actual_film_name in user_instance.get_films():
            reply_buffer += f"🚫 За свой фильм ('{actual_film_name}') голосовать нельзя.\n"
            continue

        vote_action_str_lower = vote_action_str.lower()
        if vote_action_str_lower in ['за', '+']:
            if user_instance.has_voted_against(actual_film_name):
                reply_buffer += f"🚫 Вы уже голосовали 'против' \"{actual_film_name}\".\n"
                continue
            if user_instance.has_voted_for(actual_film_name):
                 reply_buffer += f"ℹ️ Вы уже голосовали 'за' \"{actual_film_name}\".\n"
                 continue
            if user_instance.get_votes_for() >= 2:
                reply_buffer += f"✋ Достигнут лимит голосов 'за' (2).\n"
                continue
            
            initial_score = film_ratings.get(actual_film_name, 0)
            film_ratings[actual_film_name] += 1
            user_instance.add_vote_for(actual_film_name)
            
            successful_votes_in_this_message += 1
            log_film_scores_changed = True
            reply_buffer += f"👍 Ваш голос 'ЗА' \"{actual_film_name}\" принят.\n"
            logging.info(
                f"VOTE UP: User {user_name} (ID: {user_id}) voted FOR '{actual_film_name}'. "
                f"Score change: {initial_score} -> {film_ratings[actual_film_name]}."
            )

        elif vote_action_str_lower in ['против', '-']:
            if user_instance.has_voted_for(actual_film_name):
                reply_buffer += f"🚫 Вы уже голосовали 'за' \"{actual_film_name}\".\n"
                continue
            if user_instance.has_voted_against(actual_film_name):
                 reply_buffer += f"ℹ️ Вы уже голосовали 'против' \"{actual_film_name}\".\n"
                 continue
            if user_instance.get_votes_against() >= 2:
                reply_buffer += f"✋ Достигнут лимит голосов 'против' (2).\n"
                continue

            initial_score = film_ratings.get(actual_film_name, 0)
            film_ratings[actual_film_name] -= 1
            user_instance.add_vote_against(actual_film_name)

            successful_votes_in_this_message += 1
            log_film_scores_changed = True
            reply_buffer += f"👎 Ваш голос 'ПРОТИВ' \"{actual_film_name}\" принят.\n"
            logging.info(
                f"VOTE DOWN: User {user_name} (ID: {user_id}) voted AGAINST '{actual_film_name}'. "
                f"Score change: {initial_score} -> {film_ratings[actual_film_name]}."
            )
        
        else:
             reply_buffer += f"⚠️ Для \"{actual_film_name}\": неизвестный голос '{vote_action_str}'.\n"

    if reply_buffer:
        await message.reply(reply_buffer)
    elif not parsed_votes:
        await message.reply("Не удалось обработать ваш запрос на голосование. Проверьте формат.")
        return

    if log_film_scores_changed:
        logging.info(f"Current film_ratings state after votes by {user_name} (ID: {user_id}): {film_ratings}")

    if successful_votes_in_this_message > 0 and not final_results_calculated:
        current_total_user_vote_actions = sum(u.get_votes_for() + u.get_votes_against() for u in users.values())
        num_films = len(film_ratings)
        logging.info(
            f"Total votes cast: {current_total_user_vote_actions}, "
            f"Num films: {num_films}. Votes needed: {2 * num_films if num_films > 0 else 'N/A'}"
        )

        if num_films > 0 and current_total_user_vote_actions >= 2 * num_films:
            logging.info("Vote tally condition met. Calculating final results FOR ADMIN ONLY.")
            cached_results_string = _calculate_and_format_results_logic()
            final_results_calculated = True
            results_message_for_admin = f"ГОЛОСОВАНИЕ ЗАВЕРШЕНО!\n\n{cached_results_string}"

            try:
                await bot.send_message(ADMIN_USER_ID, results_message_for_admin)
                logging.info(f"Automatic voting ended. Results sent to ADMIN_USER_ID {ADMIN_USER_ID}.")
                
                if user_id != ADMIN_USER_ID:
                    await message.answer(
                        "Ваш голос был решающим! Голосование завершено. Итоги объявлены администратором."
                    )
            except Exception as e:
                logging.error(f"Error sending results to ADMIN_USER_ID {ADMIN_USER_ID} after automatic end: {e}")


@dp.message(Command("results"))
async def display_results(message: types.Message):
    global final_results_calculated, cached_results_string

    # Теперь любой пользователь может запросить /results
    num_films = len(film_ratings)
    if num_films == 0:
        await message.answer("Нет фильмов для подсчета результатов. Голосование не начато.")
        return

    # Всегда рассчитываем текущие результаты для отображения
    current_results_display_string = _calculate_and_format_results_logic()

    if final_results_calculated:
        # Если голосование уже завершено (неважно кем и как), показываем кешированные результаты.
        # cached_results_string должен быть актуальным.
        await message.answer(f"Итоги Голосования (завершено):\n{cached_results_string}")
    else:
        # Голосование еще не завершено. Проверяем, не выполнено ли условие завершения прямо сейчас.
        current_total_user_vote_actions = sum(u.get_votes_for() + u.get_votes_against() for u in users.values())

        if num_films > 0 and current_total_user_vote_actions >= 2 * num_films:
            # Условие выполнено, финализируем результаты
            logging.info("Results condition met on /results command. Finalizing results.")
            cached_results_string = current_results_display_string  # Он уже посчитан
            final_results_calculated = True

            # Сообщаем запросившему пользователю
            await message.answer(f"ГОЛОСОВАНИЕ ЗАВЕРШЕНО (по итогам /results)!\n\n{cached_results_string}")

            # Также отправляем сообщение администратору, если это не он запросил /results
            if message.from_user.id != ADMIN_USER_ID:
                try:
                    await bot.send_message(ADMIN_USER_ID,
                                           f"Голосование было завершено через команду /results.\n\n{cached_results_string}")
                    logging.info(f"Results (finalized by /results) also sent to ADMIN_USER_ID {ADMIN_USER_ID}.")
                except Exception as e:
                    logging.error(f"Error sending results (finalized by /results) to ADMIN_USER_ID: {e}")
        else:
            # Условие не выполнено, показываем предварительные результаты
            await message.answer(
                f"Голосование еще не завершено. (Всего голосов: {current_total_user_vote_actions}, Нужно: {2 * num_films} для завершения).\n\nПредварительные результаты:\n{current_results_display_string}")

@dp.message(Command("vote_start"))
aysnc def start_voting_admin(message.types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_USER_ID:
        await message.reply("У вас нет прав, да и откуда ты знаешь команду")
        return
    is_voting = True

@dp.message(Command("end"))
async def end_voting_admin(message: types.Message):
    global final_results_calculated, cached_results_string
    user_id = message.from_user.id

    if user_id != ADMIN_USER_ID:
        await message.reply("У вас нет прав для использования этой команды.")
        logging.warning(f"User {user_id} ({message.from_user.username or message.from_user.first_name}) "
                        f"attempted to use /end command without permission.")
        return

    if final_results_calculated:
        # Показываем уже сохраненные результаты, если админ снова вызовет /end
        await message.reply(f"Голосование уже было завершено.\n{cached_results_string}")
        return

    if not film_ratings:
        await message.reply("Нет фильмов для голосования. Нечего завершать.")
        logging.info(f"Admin (ID: {user_id}) tried to /end voting, but no films exist.")
        return

    logging.info(f"Admin (ID: {user_id}) initiated /end command. Calculating final results FOR ADMIN ONLY.")
    cached_results_string = _calculate_and_format_results_logic()
    final_results_calculated = True
    results_broadcast_message = f"ГОЛОСОВАНИЕ ПРИНУДИТЕЛЬНО ЗАВЕРШЕНО АДМИНИСТРАТОРОМ!\n\n{cached_results_string}"

    await message.answer(results_broadcast_message)
    logging.info(f"Final film_ratings state at forced end by admin: {film_ratings}")


@dp.message()
async def handle_text_buttons(message: types.Message):
    if message.text == 'Инфо':
        await help_command(message)
    elif message.text == 'Голосование':
        await message.reply(
            "Для голосования используйте команду /vote, например: /vote 1:+, 2:-\nСписок фильмов и их ID можно посмотреть командой /filmlist.")
    elif message.text == 'Список':
        await filmlist(message)


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await send_startup_gif_and_message()
    logging.info("Starting polling...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(main())
