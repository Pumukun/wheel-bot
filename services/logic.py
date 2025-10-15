# services/logic.py
import random
import logging
from typing import List, Dict

# TODO: Функции в этом файле должны быть "чистыми" — получать все необходимые данные
# через аргументы, а не импортировать из `state`.

from state import film_ratings, fallback_shuffled_films_cache, fallback_cache_is_fresh

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

def calculate_and_format_results() -> str:
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

