# handlers/voting.py
import logging
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery

from user import User
import state
from services.logic import parse_votes, get_or_create_fallback_shuffled_list, calculate_and_format_results
from config import ADMIN_USER_ID
from keyboards.inline import (
    create_pagination_keyboard,
    VotePagingCallback,
    NavigatePagingCallback,
    DUMMY_CALLBACK
)

router = Router()

# TODO [UX]: Весь процесс голосования (/filmlist -> /vote) можно объединить в одно интерактивное сообщение
# с Inline-кнопками "За" и "Против" под каждым фильмом. Это устранит необходимость ручного ввода команд.

@router.message(Command("add"))
async def add(message: types.Message):
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
    if user_id not in state.users:
        state.users[user_id] = User(user_name, [], user_id)
    
    user_instance = state.users[user_id]
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

    if film1 in state.film_ratings:
        await message.reply(f"Фильм \"{film1}\" уже был добавлен ранее.")
        return

    if film2 in state.film_ratings:
        await message.reply(f"Фильм \"{film2}\" уже был добавлен ранее.")
        return

    user_instance.films.extend([film1, film2])
    state.film_ratings[film1] = 0
    state.film_ratings[film2] = 0
    state.fallback_cache_is_fresh = False
    
    await message.reply(f"Фильмы \"{film1}\" и \"{film2}\" добавлены вами, {user_name}.")
    logging.info(f"User {user_name} (ID: {user_id}) added films: {film1}, {film2}. Fallback cache invalidated.")
    logging.info(f"Текущее состояние film_ratings после добавления: {state.film_ratings}")


@router.message(Command("filmlist"))
async def filmlist(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name
    display_list: Dict[int, str]
    list_type_msg: str
    all_current_film_names = list(state.film_ratings.keys())
    
    if not all_current_film_names:
        await message.answer("Список фильмов пока пуст. Добавьте фильмы командой /add.")
        return

    user_has_personally_added_films = False
    if user_id in state.users and state.users[user_id].get_films():
        user_has_personally_added_films = True

    if user_has_personally_added_films:
        user_instance = state.users[user_id]
        user_instance.ensure_shuffled_list_exists(all_current_film_names)
        display_list = user_instance.get_shuffled_films()
        list_type_msg = f"Список фильмов:"
    else:
        display_list = get_or_create_fallback_shuffled_list()
        if user_id in state.users:
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


@router.message(Command("reset"))
async def reset_votes(message: types.Message):
    user_id = message.from_user.id
    if not state.users.get(user_id) or not state.users[user_id].get_voted_on():
        await message.answer("Вы ещё не голосовали, сбрасывать нечего")
        return
    
    user_instance = state.users[user_id]
    for film_name, vote_type in user_instance.get_voted_on().items():
        if film_name in state.film_ratings:
            if vote_type == 'за':
                state.film_ratings[film_name] -= 1
            elif vote_type == 'против':
                state.film_ratings[film_name] += 1
    
    user_instance.reset_votes()
    logging.info(f"User {message.from_user.username} (ID: {user_id}) has reset their votes.")
    await message.reply("Ваши голоса были сброшены. Теперь вы можете проголосовать заново.")

@router.message(Command("vote"))
async def vote(message: types.Message):
    """
    Обрабатывает голоса пользователей с подробным логированием для отладки.
    """
    if state.current_status == state.VotingStatus.FINISHED:
        await message.reply("Голосование уже завершено. Для просмотра итогов используйте /results.")
        return
    if state.current_status == state.VotingStatus.NOT_STARTED:
        await message.reply("Голосование ещё не началось.")
        return

    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name

    # [VOTE_DEBUG] Логируем начало обработки
    logging.info(f"[VOTE_DEBUG] User '{user_name}' ({user_id}) sent vote: {message.text}")

    if user_id not in state.users:
        state.users[user_id] = User(user_name, [], user_id)
        logging.info(f"New user {user_name} (ID: {user_id}) created on first vote.")
    
    user_instance = state.users[user_id]
    parsed_votes = parse_votes(message.text)

    if not parsed_votes:
        await message.reply("Некорректный формат голосования. Используйте: /vote ID:голос. Пример: /vote 1:+.")
        return

    all_current_film_names = list(state.film_ratings.keys())
    if not all_current_film_names:
        await message.reply("Нет фильмов для голосования. Дождитесь, пока кто-нибудь добавит их.")
        return

    user_instance.ensure_shuffled_list_exists(all_current_film_names)
    film_map_for_voting = user_instance.get_shuffled_films()

    if not film_map_for_voting and all_current_film_names:
        logging.error(f"Film map for voting for user {user_id} is empty, but global films exist.")
        await message.reply("Ошибка: не удалось получить список фильмов для голосования. Попробуйте /filmlist, затем /vote.")
        return

    reply_buffer = ""
    successful_votes_in_this_message = 0
    log_film_scores_changed = False

    for film_identifier, vote_action_str in parsed_votes.items():
        actual_film_name = film_map_for_voting.get(int(film_identifier)) if film_identifier.isdigit() else None
        
        # [VOTE_DEBUG] Логируем каждую попытку голосования
        logging.info(f"[VOTE_DEBUG] User '{user_name}': Processing vote for Film ID '{film_identifier}' ('{actual_film_name}') with action '{vote_action_str}'")

        if not actual_film_name:
            logging.warning(f"[VOTE_DEBUG] User '{user_name}': VOTE BLOCKED -> Film with ID {film_identifier} not found in personal list.")
            reply_buffer += f"⚠️ Фильм с ID {film_identifier} не найден в вашем списке.\n"
            continue
        
        # Проверка №1: Голосование за свой фильм
        if actual_film_name in user_instance.get_films():
            logging.warning(f"[VOTE_DEBUG] User '{user_name}': VOTE BLOCKED for '{actual_film_name}' -> User is voting for their own film.")
            reply_buffer += f"🚫 За свой фильм ('{actual_film_name}') голосовать нельзя.\n"
            continue

        vote_action_str_lower = vote_action_str.lower()
        if vote_action_str_lower in ['за', '+']:
            # Проверка №2: Конфликт голосов (уже голосовал 'против')
            if user_instance.has_voted_against(actual_film_name):
                logging.warning(f"[VOTE_DEBUG] User '{user_name}': VOTE BLOCKED for '{actual_film_name}' -> User has already voted 'against'.")
                reply_buffer += f"🚫 Вы уже голосовали 'против' \"{actual_film_name}\".\n"
                continue
            
            # Проверка №3: Повторный голос
            if user_instance.has_voted_for(actual_film_name):
                logging.info(f"[VOTE_DEBUG] User '{user_name}': VOTE IGNORED for '{actual_film_name}' -> User has already voted 'for'.")
                reply_buffer += f"ℹ️ Вы уже голосовали 'за' \"{actual_film_name}\".\n"
                continue

            # Проверка №4: Лимит голосов 'за'
            if user_instance.get_votes_for() >= 2:
                logging.warning(f"[VOTE_DEBUG] User '{user_name}': VOTE BLOCKED for '{actual_film_name}' -> 'For' vote limit (2) reached.")
                reply_buffer += f"✋ Достигнут лимит голосов 'за' (2).\n"
                continue
            
            # [VOTE_DEBUG] Если все проверки пройдены
            logging.info(f"[VOTE_DEBUG] User '{user_name}': VOTE SUCCESS for '{actual_film_name}' -> +1")
            initial_score = state.film_ratings.get(actual_film_name, 0)
            state.film_ratings[actual_film_name] += 1
            user_instance.add_vote_for(actual_film_name)
            successful_votes_in_this_message += 1
            log_film_scores_changed = True
            reply_buffer += f"👍 Ваш голос 'ЗА' \"{actual_film_name}\" принят.\n"
        
        elif vote_action_str_lower in ['против', '-']:
            # Проверки для голоса 'против'
            if user_instance.has_voted_for(actual_film_name):
                logging.warning(f"[VOTE_DEBUG] User '{user_name}': VOTE BLOCKED for '{actual_film_name}' -> User has already voted 'for'.")
                reply_buffer += f"🚫 Вы уже голосовали 'за' \"{actual_film_name}\".\n"
                continue

            if user_instance.has_voted_against(actual_film_name):
                logging.info(f"[VOTE_DEBUG] User '{user_name}': VOTE IGNORED for '{actual_film_name}' -> User has already voted 'against'.")
                reply_buffer += f"ℹ️ Вы уже голосовали 'против' \"{actual_film_name}\".\n"
                continue

            if user_instance.get_votes_against() >= 2:
                logging.warning(f"[VOTE_DEBUG] User '{user_name}': VOTE BLOCKED for '{actual_film_name}' -> 'Against' vote limit (2) reached.")
                reply_buffer += f"✋ Достигнут лимит голосов 'против' (2).\n"
                continue
            
            logging.info(f"[VOTE_DEBUG] User '{user_name}': VOTE SUCCESS for '{actual_film_name}' -> -1")
            initial_score = state.film_ratings.get(actual_film_name, 0)
            state.film_ratings[actual_film_name] -= 1
            user_instance.add_vote_against(actual_film_name)
            successful_votes_in_this_message += 1
            log_film_scores_changed = True
            reply_buffer += f"👎 Ваш голос 'ПРОТИВ' \"{actual_film_name}\" принят.\n"
        else:
            reply_buffer += f"⚠️ Для \"{actual_film_name}\": неизвестный голос '{vote_action_str}'.\n"

    if reply_buffer:
        await message.reply(reply_buffer)
    elif not parsed_votes:
        await message.reply("Не удалось обработать ваш запрос на голосование. Проверьте формат.")
        return

    if log_film_scores_changed:
        logging.info(f"Current film_ratings state after votes by {user_name} (ID: {user_id}): {state.film_ratings}")

    if successful_votes_in_this_message > 0 and not state.final_results_calculated:
        current_total_user_vote_actions = sum(u.get_votes_for() + u.get_votes_against() for u in state.users.values())
        num_films = len(state.film_ratings)
        
        if num_films > 0 and current_total_user_vote_actions >= 2 * num_films and not state.final_results_calculated:
            logging.info("Vote tally condition met. Calculating final results FOR ADMIN ONLY.")
            state.cached_results_string = calculate_and_format_results()
            state.final_results_calculated = True
            state.current_status = state.VotingStatus.FINISHED
            results_message_for_admin = f"ГОЛОСОВАНИЕ ЗАВЕРШЕНО!\n\n{state.cached_results_string}"
            try:
                await message.bot.send_message(ADMIN_USER_ID, results_message_for_admin)
                logging.info(f"Automatic voting ended. Results sent to ADMIN_USER_ID {ADMIN_USER_ID}.")
                if user_id != ADMIN_USER_ID:
                    await message.answer("Ваш голос был решающим! Голосование завершено. Итоги объявлены администратором.")
            except Exception as e:
                logging.error(f"Error sending results to ADMIN_USER_ID {ADMIN_USER_ID} after automatic end: {e}")

@router.message(Command("results"))
async def display_results(message: types.Message):
    num_films = len(state.film_ratings)
    if num_films == 0:
        await message.answer("Нет фильмов для подсчета результатов. Голосование не начато.")
        return

    current_results_display_string = calculate_and_format_results()

    if state.current_status == state.VotingStatus.FINISHED:
        await message.answer(f"Итоги Голосования (завершено):\n{state.cached_results_string}")
    else:
        current_total_user_vote_actions = sum(u.get_votes_for() + u.get_votes_against() for u in state.users.values())
        if num_films > 0 and current_total_user_vote_actions >= 2 * num_films:
            logging.info("Results condition met on /results command. Finalizing results.")
            state.cached_results_string = current_results_display_string
            state.current_status = state.VotingStatus.FINISHED
            await message.answer(f"ГОЛОСОВАНИЕ ЗАВЕРШЕНО (по итогам /results)!\n\n{state.cached_results_string}")
            if message.from_user.id != ADMIN_USER_ID:
                try:
                    await message.bot.send_message(ADMIN_USER_ID, f"Голосование было завершено через команду /results.\n\n{state.cached_results_string}")
                    logging.info(f"Results (finalized by /results) also sent to ADMIN_USER_ID {ADMIN_USER_ID}.")
                except Exception as e:
                    logging.error(f"Error sending results (finalized by /results) to ADMIN_USER_ID: {e}")
        else:
            await message.answer(
                f"Голосование еще не завершено. (Всего голосов: {current_total_user_vote_actions}, Нужно: {2 * num_films} для завершения).\n\n"
                f"Предварительные результаты:\n{current_results_display_string}")

@router.message(Command("pagelist"))
async def pagelist(message: types.Message):
    """
    Отправляет первую страницу списка голосования с пагинацией.
    """
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name
    
    if user_id not in state.users:
        state.users[user_id] = User(user_name, [], user_id)
    
    user_instance = state.users[user_id]
    all_current_film_names = list(state.film_ratings.keys())

    if not all_current_film_names:
        await message.answer("Список фильмов пока пуст. Добавьте фильмы командой /add.")
        return

    message_text, keyboard = create_pagination_keyboard(
        user_instance, all_current_film_names, page=0
    )
    
    if keyboard:
        await message.answer(message_text, reply_markup=keyboard)
    else:
        await message.answer(message_text)

@router.callback_query(NavigatePagingCallback.filter())
async def handle_page_navigation(query: CallbackQuery, callback_data: NavigatePagingCallback):
    """
    (НОВЫЙ ХЭНДЛЕР)
    Обрабатывает нажатия кнопок "Назад" и "Вперед".
    """
    page = callback_data.page
    
    user_id = query.from_user.id
    if user_id not in state.users:
        await query.answer("Произошла ошибка. Пожалуйста, введите /pagelist заново.", show_alert=True)
        return

    user_instance = state.users[user_id]
    all_current_film_names = list(state.film_ratings.keys())

    message_text, keyboard = create_pagination_keyboard(
        user_instance, all_current_film_names, page=page
    )

    try:
        await query.message.edit_text(message_text, reply_markup=keyboard)
        await query.answer(f"Переход на страницу {page + 1}")
    except Exception as e:
        logging.warning(f"Ошибка при обновлении пагинации: {e}")
        await query.answer("Не удалось обновить список.")


@router.callback_query(VotePagingCallback.filter())
async def handle_page_vote(query: CallbackQuery, callback_data: VotePagingCallback, bot: Bot):
    if state.current_status == state.VotingStatus.FINISHED:
        await query.answer("Голосование уже завершено.", show_alert=True)
        return
    if state.current_status == state.VotingStatus.NOT_STARTED:
        await query.answer("Голосование ещё не началось.", show_alert=True)
        return

    user_id = query.from_user.id
    user_name = query.from_user.username or query.from_user.first_name

    film_id = callback_data.film_id
    action = callback_data.action

    if user_id not in state.users:
        state.users[user_id] = User(user_name, [], user_id)

    user_instance = state.users[user_id]

    user_instance.ensure_shuffled_list_exists(list(state.film_ratings.keys()))
    film_name = user_instance.get_shuffled_films().get(film_id)

    if not film_name:
        await query.answer("Ошибка: фильм не найден. Попробуйте обновить /pagelist", show_alert=True)
        return

    logging.info(
        f"[VOTE_PAGING] User '{user_name}' ({user_id}) processing vote: '{action}' for film_id {film_id} ('{film_name}')")

    response_text = ""
    log_film_scores_changed = False

    if film_name in user_instance.get_films():
        response_text = "🚫 За свой фильм голосовать нельзя."
        await query.answer(response_text, show_alert=True)
        return

    if action == 'for':
        if user_instance.has_voted_against(film_name):
            response_text = f"🚫 Вы уже голосовали 'против' \"{film_name}\"."
        elif user_instance.has_voted_for(film_name):
            response_text = f"ℹ️ Вы уже голосовали 'за' \"{film_name}\"."
        elif user_instance.get_votes_for() >= 2:
            response_text = "✋ Достигнут лимит голосов 'за' (2)."
        else:
            state.film_ratings[film_name] += 1
            user_instance.add_vote_for(film_name)
            log_film_scores_changed = True
            response_text = f"👍 Ваш голос 'ЗА' \"{film_name}\" принят."

    elif action == 'against':
        if user_instance.has_voted_for(film_name):
            response_text = f"🚫 Вы уже голосовали 'за' \"{film_name}\"."
        elif user_instance.has_voted_against(film_name):
            response_text = f"ℹ️ Вы уже голосовали 'против' \"{film_name}\"."
        elif user_instance.get_votes_against() >= 2:
            response_text = "✋ Достигнут лимит голосов 'против' (2)."
        else:
            state.film_ratings[film_name] -= 1
            user_instance.add_vote_against(film_name)
            log_film_scores_changed = True
            response_text = f"👎 Ваш голос 'ПРОТИВ' \"{film_name}\" принят."

    await query.answer(response_text, show_alert=("🚫" in response_text or "✋" in response_text))

    if log_film_scores_changed:
        logging.info(f"Current film_ratings state after votes by {user_name} (ID: {user_id}): {state.film_ratings}")

        current_total_user_vote_actions = sum(u.get_votes_for() + u.get_votes_against() for u in state.users.values())
        num_films = len(state.film_ratings)

        if num_films > 0 and current_total_user_vote_actions >= 2 * num_films and not state.final_results_calculated:
            logging.info("Vote tally condition met (via pagination). Calculating final results.")
            state.cached_results_string = calculate_and_format_results()
            state.final_results_calculated = True
            state.current_status = state.VotingStatus.FINISHED
            results_message_for_admin = f"ГОЛОСОВАНИЕ ЗАВЕРШЕНО!\n\n{state.cached_results_string}"
            try:
                await bot.send_message(ADMIN_USER_ID, results_message_for_admin)
                logging.info(f"Automatic voting ended (via pagination). Results sent to ADMIN_USER_ID {ADMIN_USER_ID}.")
                if user_id != ADMIN_USER_ID:
                    await query.message.answer("Ваш голос был решающим! Голосование завершено.")
            except Exception as e:
                logging.error(f"Error sending results to ADMIN_USER_ID {ADMIN_USER_ID} after automatic end: {e}")

    try:
        all_current_film_names = list(state.film_ratings.keys())
        updated_text, updated_keyboard = create_pagination_keyboard(
            user_instance,
            all_current_film_names,
            page=callback_data.page
        )
        if updated_keyboard:
            await query.message.edit_text(updated_text, reply_markup=updated_keyboard)
    except Exception as e:
        logging.warning(f"Не удалось обновить клавиатуру после голосования: {e}")

@router.callback_query(F.data == DUMMY_CALLBACK)
async def handle_dummy_button(query: CallbackQuery):
    """
    (НОВЫЙ ХЭНДЛЕР)
    Обрабатывает нажатие на "пустую" кнопку с названием фильма.
    """
    await query.answer("Это просто название фильма :) Нажимайте 👍 или 👎.")
