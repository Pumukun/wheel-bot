# tests/test_full_workflow.py
import pytest
import logging

# Импорты из проекта
import state
from handlers.voting import add, vote, reset_votes, filmlist, display_results
from handlers.admin import start_voting_admin, end_voting_admin
from config import ADMIN_USER_ID
from user import User

# Импорты хелперов для теста
from tests.helpers import MockUser, MockMessage

# --- Настройка логгирования ---
logger = logging.getLogger("TEST_WORKFLOW_EXTENDED")

pytestmark = pytest.mark.asyncio

# --- Фикстуры и вспомогательные функции ---

def clear_bot_state():
    """Обычная функция для полной очистки состояния бота."""
    logger.debug("--- [STATE_RESET] Вызвана функция очистки состояния... ---")
    state.users.clear()
    state.film_ratings.clear()
    state.final_results_calculated = False
    state.is_voting = False
    state.cached_results_string = ""
    state.fallback_cache_is_fresh = False
    state.fallback_shuffled_films_cache.clear()
    logger.debug("--- [STATE_RESET] Состояние полностью очищено. ---")

@pytest.fixture(autouse=True)
def reset_state_before_each_test():
    """
    Эта фикстура автоматически вызывает очистку состояния перед каждым тестом.
    """
    logger.info("--- [FIXTURE] Автоматический сброс состояния перед тестом ---")
    clear_bot_state()


def get_film_id_by_name(user_id: int, film_name: str) -> int | None:
    """Вспомогательная функция для получения ID фильма из перемешанного списка пользователя."""
    logger.debug(f"[HELPER] get_film_id_by_name вызван для user_id={user_id}, film_name='{film_name}'")
    user_instance = state.users.get(user_id)
    if not user_instance:
        logger.warning(f"[HELPER] Пользователь {user_id} не найден в state.users. Возвращаем None.")
        return None
    
    user_instance.ensure_shuffled_list_exists(list(state.film_ratings.keys()))
    shuffled_list = user_instance.get_shuffled_films()
    
    for film_id, name in shuffled_list.items():
        if name == film_name:
            logger.debug(f"[HELPER] Найден ID: {film_id} для фильма '{film_name}'.")
            return film_id
            
    logger.warning(f"[HELPER] Фильм '{film_name}' не найден в списке пользователя {user_id}. Возвращаем None.")
    return None

# --- Основной тестовый сценарий ---

async def test_complete_bot_workflow():
    """
    Тестирует полный жизненный цикл бота: от добавления фильмов до просмотра результатов,
    включая все возможные ошибки и ограничения.
    """
    logger.info("================== НАЧАЛО ПОЛНОГО ТЕСТА ЖИЗНЕННОГО ЦИКЛА ==================")

    # --- 1. АРРАНЖИРОВКА: Создаем пользователей ---
    logger.info("--- ЭТАП 1: АРРАНЖИРОВКА ---")
    admin_user = MockUser(id=ADMIN_USER_ID, username="Admin", first_name="Admin")
    user_a = MockUser(id=100, username="UserA", first_name="UserA")
    user_b = MockUser(id=200, username="UserB", first_name="UserB")
    user_c = MockUser(id=300, username="UserC", first_name="UserC")
    logger.debug("Модели пользователей созданы.")
    
    state.users[admin_user.id] = User(name=admin_user.username, films=[], id=admin_user.id)
    logger.debug(f"Объект User для Admin ({admin_user.id}) вручную добавлен в state.")
    logger.info(f"ЭТАП 1 ЗАВЕРШЕН: Пользователи готовы.")

    # --- 2. ЭТАП ДОБАВЛЕНИЯ ФИЛЬМОВ ---
    logger.info("--- ЭТАП 2: ДОБАВЛЕНИЕ ФИЛЬМОВ ---")
    logger.info("--- ЭТАП 2.1: Успешное добавление ---")
    
    logger.debug("Вызов add для UserA...")
    msg_add_a = MockMessage(from_user=user_a, text="/add  Крепкий орешек ,  Терминатор 2 ")
    await add(msg_add_a)
    logger.debug(f"Получен ответ: '{msg_add_a.reply_text}'")
    assert "Фильмы \"Крепкий орешек\" и \"Терминатор 2\" добавлены" in msg_add_a.reply_text
    assert "Крепкий орешек" in state.film_ratings and state.film_ratings["Крепкий орешек"] == 0
    logger.info("ПРОВЕРКА ПРОЙДЕНА: UserA успешно добавил два фильма.")

    logger.debug("Вызов add для UserB...")
    msg_add_b = MockMessage(from_user=user_b, text="/add Матрица, Начало")
    await add(msg_add_b)
    logger.debug(f"Получен ответ: '{msg_add_b.reply_text}'")
    assert len(state.film_ratings) == 4
    logger.info(f"ПРОВЕРКА ПРОЙДЕНА: UserB успешно добавил два фильма. Всего фильмов: {len(state.film_ratings)}")

    logger.info("--- ЭТАП 2.2: Проверка ошибок при добавлении ---")
    
    logger.debug("Проверка лимита фильмов для UserA...")
    msg_add_a_fail = MockMessage(from_user=user_a, text="/add Еще фильм, И еще один")
    await add(msg_add_a_fail)
    assert "вы уже добавили максимальное количество фильмов" in msg_add_a_fail.reply_text
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Нельзя добавить больше двух фильмов.")

    logger.debug("Проверка добавления существующего фильма (UserC)...")
    msg_add_c_fail_exists = MockMessage(from_user=user_c, text="/add Интерстеллар, Матрица")
    await add(msg_add_c_fail_exists)
    assert 'Фильм "Матрица" уже был добавлен ранее' in msg_add_c_fail_exists.reply_text
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Нельзя добавить уже существующий фильм.")
    
    logger.debug("Проверка добавления двух одинаковых фильмов (UserC)...")
    msg_add_c_fail_same = MockMessage(from_user=user_c, text="/add Дюна, Дюна")
    await add(msg_add_c_fail_same)
    assert 'Фильмы должны быть разные' in msg_add_c_fail_same.reply_text
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Нельзя добавить два одинаковых фильма.")
    
    logger.debug("Проверка неверного формата команды add (UserC)...")
    msg_add_c_fail_format = MockMessage(from_user=user_c, text="/add Всего один фильм")
    await add(msg_add_c_fail_format)
    assert 'ровно два названия' in msg_add_c_fail_format.reply_text
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Нельзя добавить один или больше двух фильмов.")
    logger.info("ЭТАП 2 ЗАВЕРШЕН: Все проверки добавления фильмов пройдены.")

    # --- 3. ПРОВЕРКИ ДО НАЧАЛА ГОЛОСОВАНИЯ ---
    logger.info("--- ЭТАП 3: ПРОВЕРКИ ДО СТАРТА ГОЛОСОВАНИЯ ---")
    
    logger.debug("Проверка блокировки /vote до старта...")
    msg_vote_fail = MockMessage(from_user=user_c, text="/vote 1:+")
    await vote(msg_vote_fail)
    assert "Голосование ещё не началось" in msg_vote_fail.reply_text
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Команда /vote не работает до старта.")

    logger.debug("Проверка /filmlist для UserC...")
    msg_filmlist_c = MockMessage(from_user=user_c, text="/filmlist")
    await filmlist(msg_filmlist_c)
    assert "Общий список фильмов" in msg_filmlist_c.reply_text
    assert "1. " in msg_filmlist_c.reply_text and "4. " in msg_filmlist_c.reply_text
    logger.info("ПРОВЕРКА ПРОЙДЕНA: Неучаствовавший пользователь видит общий список фильмов.")
    logger.info("ЭТАП 3 ЗАВЕРШЕН: Проверки до старта пройдены.")

    # --- 4. АДМИН ЗАПУСКАЕТ ГОЛОСОВАНИЕ ---
    logger.info("--- ЭТАП 4: АДМИН ЗАПУСКАЕТ ГОЛОСОВАНИЕ ---")
    
    logger.debug("Вызов start_voting_admin...")
    msg_start_voting = MockMessage(from_user=admin_user, text="/votestart")
    await start_voting_admin(msg_start_voting)
    assert "Голосование начато!" in msg_start_voting.reply_text
    assert state.is_voting is True
    logger.debug(f"Состояние изменено: state.is_voting = {state.is_voting}")
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Голосование успешно запущено.")
    logger.info("ЭТАП 4 ЗАВЕРШЕН.")

    # --- 5. ЭТАП ГОЛОСОВАНИЯ ---
    logger.info("--- ЭТАП 5: ГОЛОСОВАНИЕ ---")
    logger.info("--- ЭТАП 5.1: Успешное голосование ---")
    
    id_for_die_hard = get_film_id_by_name(user_c.id, "Крепкий орешек")
    id_for_matrix = get_film_id_by_name(user_c.id, "Матрица")
    logger.debug(f"UserC голосует: /vote {id_for_die_hard}:+, {id_for_matrix}:-")
    msg_vote_c = MockMessage(from_user=user_c, text=f"/vote {id_for_die_hard}:+, {id_for_matrix}:-")
    await vote(msg_vote_c)
    assert "Ваш голос 'ЗА' \"Крепкий орешек\" принят" in msg_vote_c.reply_text
    assert "Ваш голос 'ПРОТИВ' \"Матрица\" принят" in msg_vote_c.reply_text
    assert state.film_ratings["Крепкий орешек"] == 1
    assert state.film_ratings["Матрица"] == -1
    logger.debug(f"Состояние film_ratings изменено: {state.film_ratings}")
    logger.info("ПРОВЕРКА ПРОЙДЕНА: UserC успешно проголосовал ЗА и ПРОТИВ.")

    logger.info("--- ЭТАП 5.2: Проверки ограничений ---")
    
    id_for_own_film = get_film_id_by_name(user_a.id, "Терминатор 2")
    logger.debug(f"UserA голосует за свой фильм: /vote {id_for_own_film}:+")
    msg_vote_own_fail = MockMessage(from_user=user_a, text=f"/vote {id_for_own_film}:+")
    await vote(msg_vote_own_fail)
    assert "За свой фильм ('Терминатор 2') голосовать нельзя" in msg_vote_own_fail.reply_text
    assert state.film_ratings["Терминатор 2"] == 0
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Нельзя голосовать за свой фильм.")

    logger.debug(f"UserC голосует повторно ЗА: /vote {id_for_die_hard}:+")
    msg_vote_c_again = MockMessage(from_user=user_c, text=f"/vote {id_for_die_hard}:+")
    await vote(msg_vote_c_again)
    assert 'Вы уже голосовали \'за\' "Крепкий орешек"' in msg_vote_c_again.reply_text
    assert state.film_ratings["Крепкий орешек"] == 1
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Нельзя голосовать 'за' дважды за один фильм.")
    
    logger.debug(f"UserC голосует ПРОТИВ после ЗА: /vote {id_for_die_hard}:-")
    msg_vote_c_conflict = MockMessage(from_user=user_c, text=f"/vote {id_for_die_hard}:-")
    await vote(msg_vote_c_conflict)
    assert "Вы уже голосовали 'за' \"Крепкий орешек\"" in msg_vote_c_conflict.reply_text
    assert state.film_ratings["Крепкий орешек"] == 1
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Нельзя голосовать 'против' после 'за'.")
    logger.info("ЭТАП 5 ЗАВЕРШЕН: Все проверки голосования пройдены.")

    # --- 6. ЭТАП СБРОСА ГОЛОСОВ ---
    logger.info("--- ЭТАП 6: СБРОС ГОЛОСОВ ---")
    logger.debug(f"Рейтинги до сброса: {state.film_ratings}")
    
    logger.debug("Вызов reset_votes для UserC...")
    msg_reset_c = MockMessage(from_user=user_c, text="/reset")
    await reset_votes(msg_reset_c)
    assert "Ваши голоса были сброшены" in msg_reset_c.reply_text
    assert state.film_ratings["Крепкий орешек"] == 0
    assert state.film_ratings["Матрица"] == 0
    user_c_instance = state.users[user_c.id]
    assert user_c_instance.get_votes_for() == 0 and user_c_instance.get_votes_against() == 0
    logger.debug(f"Рейтинги после сброса: {state.film_ratings}")
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Голоса UserC успешно сброшены.")
    logger.info("ЭТАП 6 ЗАВЕРШЕН.")

    # --- 7. ЭТАП ПРОМЕЖУТОЧНЫХ РЕЗУЛЬТАТОВ ---
    logger.info("--- ЭТАП 7: ПРОМЕЖУТОЧНЫЕ РЕЗУЛЬТАТЫ ---")
    
    logger.debug("Вызов display_results для UserA...")
    msg_results_interim = MockMessage(from_user=user_a, text="/results")
    await display_results(msg_results_interim)
    assert "Голосование еще не завершено" in msg_results_interim.reply_text
    assert "Крепкий орешек\": Голоса: 0" in msg_results_interim.reply_text
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Промежуточные результаты отображаются корректно.")
    logger.info("ЭТАП 7 ЗАВЕРШЕН.")

    # --- 8. ЭТАП АВТОМАТИЧЕСКОГО ЗАВЕРШЕНИЯ ---
    logger.info("--- ЭТАП 8: АВТОМАТИЧЕСКОЕ ЗАВЕРШЕНИЕ ГОЛОСОВАНИЯ ---")
    
    logger.debug("Начинается серия голосов для завершения...")
    await vote(MockMessage(from_user=user_a, text=f"/vote {get_film_id_by_name(user_a.id, 'Матрица')}:+, {get_film_id_by_name(user_a.id, 'Начало')}:+"))
    logger.debug(f"UserA проголосовал. Рейтинги: {state.film_ratings}")
    await vote(MockMessage(from_user=user_b, text=f"/vote {get_film_id_by_name(user_b.id, 'Крепкий орешек')}:+, {get_film_id_by_name(user_b.id, 'Терминатор 2')}:+"))
    logger.debug(f"UserB проголосовал. Рейтинги: {state.film_ratings}")
    await vote(MockMessage(from_user=user_c, text=f"/vote {get_film_id_by_name(user_c.id, 'Матрица')}:+, {get_film_id_by_name(user_c.id, 'Терминатор 2')}:-"))
    logger.debug(f"UserC проголосовал. Рейтинги: {state.film_ratings}")
    
    logger.debug("Admin делает решающий голос...")
    msg_last_vote = MockMessage(from_user=admin_user, text=f"/vote {get_film_id_by_name(admin_user.id, 'Матрица')}:+, {get_film_id_by_name(admin_user.id, 'Крепкий орешек')}:+")
    await vote(msg_last_vote)
    logger.debug(f"Финальные рейтинги: {state.film_ratings}")

    assert state.film_ratings["Матрица"] == 3
    assert state.film_ratings["Крепкий орешек"] == 2
    assert state.film_ratings["Начало"] == 1
    assert state.film_ratings["Терминатор 2"] == 0
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Финальные голоса подсчитаны верно.")

    assert "Ваш голос 'ЗА' \"Матрица\" принят" in msg_last_vote.reply_text
    assert "Ваш голос 'ЗА' \"Крепкий орешек\" принят" in msg_last_vote.reply_text
    assert state.final_results_calculated is True
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Голосование автоматически завершилось.")
    
    logger.debug("Проверка блокировки голосования после завершения...")
    msg_vote_after_end = MockMessage(from_user=user_a, text=f"/vote {get_film_id_by_name(user_a.id, 'Начало')}:-")
    await vote(msg_vote_after_end)
    assert "Голосование уже завершено" in msg_vote_after_end.reply_text
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Голосование заблокировано после завершения.")

    logger.debug("Проверка финальных результатов для UserB...")
    msg_results_final = MockMessage(from_user=user_b, text="/results")
    await display_results(msg_results_final)
    assert "Итоги Голосования (завершено)" in msg_results_final.reply_text
    assert '• "Матрица": Голоса: 3, Очки: 5' in msg_results_final.reply_text
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Финальные результаты отображаются корректно.")
    logger.info("ЭТАП 8 ЗАВЕРШЕН.")

    # --- 9. ЭТАП ПРИНУДИТЕЛЬНОГО ЗАВЕРШЕНИЯ ---
    logger.info("--- ЭТАП 9: ПРИНУДИТЕЛЬНОЕ ЗАВЕРШЕНИЕ АДМИНОМ ---")
    clear_bot_state()
    
    logger.debug("Пересоздание пользователей для теста /end...")
    state.users[admin_user.id] = User(name=admin_user.username, films=[], id=admin_user.id)
    await add(MockMessage(from_user=user_a, text="/add Фильм X, Фильм Y"))
    state.users[user_b.id] = User(name=user_b.username, films=[], id=user_b.id)
    
    await start_voting_admin(MockMessage(from_user=admin_user, text="/votestart"))
    logger.debug("Голосование для /end запущено.")
    
    await vote(MockMessage(from_user=user_b, text=f"/vote {get_film_id_by_name(user_b.id, 'Фильм X')}:+"))
    logger.debug(f"UserB проголосовал. Рейтинги: {state.film_ratings}")
    assert state.final_results_calculated is False
    
    logger.info("Админ использует /end...")
    msg_end_admin = MockMessage(from_user=admin_user, text="/end")
    await end_voting_admin(msg_end_admin)
    
    assert "ГОЛОСОВАНИЕ ПРИНУДИТЕЛЬНО ЗАВЕРШЕНО" in msg_end_admin.reply_text
    assert state.final_results_calculated is True
    logger.debug(f"Финальный ответ админу: {msg_end_admin.reply_text}")
    assert '• "Фильм X": Голоса: 1, Очки: 2' in msg_end_admin.reply_text
    assert '• "Фильм Y": Голоса: 0, Очки: 1' in msg_end_admin.reply_text
    logger.info("ПРОВЕРКА ПРОЙДЕНА: Админ успешно завершил голосование.")
    logger.info("ЭТАП 9 ЗАВЕРШЕН.")
    
    logger.info("================== ПОЛНЫЙ ТЕСТ ЖИЗНЕННОГО ЦИКЛА УСПЕШНО ЗАВЕРШЕН ==================")
