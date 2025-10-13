# tests/test_full_workflow.py
import pytest
import main
import logging  # <-- Импортируем logging
from main import add, vote, reset_votes, start_voting_admin
from user import User
from tests.helpers import MockUser, MockMessage

# Сообщаем pytest, что все тесты в этом файле асинхронные
pytestmark = pytest.mark.asyncio

# Настраиваем логгер специально для этого тестового файла
logger = logging.getLogger("TEST_WORKFLOW")

@pytest.fixture(autouse=True)
def reset_state_before_each_test():
    """
    Эта фикстура автоматически очищает состояние бота перед
    каждым запуском теста. Это гарантирует, что тесты не влияют друг на друга.
    """
    main.users.clear()
    main.film_ratings.clear()
    main.final_results_calculated = False
    main.is_voting = False

async def test_complete_user_workflow():
    """
    Тестирует полный и корректный рабочий процесс с подробным логированием.
    """
    # <-- ЛОГ
    logger.info("================== НАЧАЛО ТЕСТА: test_complete_user_workflow ==================")

    # --- 1. АРРАНЖИРОВКА: Настраиваем пользователей и начальное состояние ---
    admin_user = MockUser(id=main.ADMIN_USER_ID, username="Admin", first_name="Admin")
    user_a = MockUser(id=100, username="UserA", first_name="UserA")
    user_b = MockUser(id=200, username="UserB", first_name="UserB")
    # <-- ЛОГ
    logger.info(f"ЭТАП 1: Пользователи созданы (Admin: {admin_user.id}, UserA: {user_a.id}, UserB: {user_b.id})")


    # --- 2. ЭТАП ДОБАВЛЕНИЯ ФИЛЬМОВ ---
    # <-- ЛОГ
    logger.info("ЭТАП 2: Пользователи добавляют фильмы...")
    msg_add_a = MockMessage(from_user=user_a, text="/add Фильм-1, Фильм-2")
    await add(msg_add_a)
    assert "Фильмы \"Фильм-1\" и \"Фильм-2\" добавлены" in msg_add_a.reply_text
    assert "Фильм-1" in main.film_ratings

    msg_add_b = MockMessage(from_user=user_b, text="/add Фильм-3, Фильм-4")
    await add(msg_add_b)
    assert len(main.film_ratings) == 4
    # <-- ЛОГ
    logger.info(f"Фильмы успешно добавлены. Текущий рейтинг: {main.film_ratings}")


    # --- 3. ПРОВЕРКА БЛОКИРОВКИ ГОЛОСОВАНИЯ ---
    # <-- ЛОГ
    logger.info("ЭТАП 3: Проверка блокировки голосования (is_voting=False)...")
    vote_fail_msg = MockMessage(from_user=user_a, text="/vote 1:+")
    await vote(vote_fail_msg)
    assert "Голосование ещё не началось." in vote_fail_msg.reply_text
    assert main.film_ratings["Фильм-3"] == 0
    # <-- ЛОГ
    logger.info("Проверка успешна: голосование заблокировано, рейтинг не изменился.")


    # --- 4. АДМИН ЗАПУСКАЕТ ГОЛОСОВАНИЕ ---
    # <-- ЛОГ
    logger.info("ЭТАП 4: Админ запускает голосование командой /votestart...")
    start_msg = MockMessage(from_user=admin_user, text="/votestart")
    await start_voting_admin(start_msg)
    assert main.is_voting is True
    # <-- ЛОГ
    logger.info(f"Голосование успешно запущено. main.is_voting = {main.is_voting}")


    # --- 5. ЭТАП КОРРЕКТНОГО ГОЛОСОВАНИЯ ---
    # <-- ЛОГ
    logger.info("ЭТАП 5: Проверка успешного голосования...")
    user_a_instance = main.users[user_a.id]
    user_a_instance.ensure_shuffled_list_exists(list(main.film_ratings.keys()))
    shuffled_list_a = user_a_instance.get_shuffled_films()
    
    vote_for_film_id = next(id for id, name in shuffled_list_a.items() if name == "Фильм-3")
    # <-- ЛОГ
    logger.info(f"UserA голосует за 'Фильм-3' (его ID для этого фильма: {vote_for_film_id}).")
    
    vote_success_msg = MockMessage(from_user=user_a, text=f"/vote {vote_for_film_id}:+")
    await vote(vote_success_msg)
    assert 'Ваш голос \'ЗА\' "Фильм-3" принят' in vote_success_msg.reply_text
    assert main.film_ratings["Фильм-3"] == 1
    assert user_a_instance.get_votes_for() == 1
    # <-- ЛОГ
    logger.info(f"Голосование успешно. Рейтинг 'Фильм-3' стал {main.film_ratings['Фильм-3']}. Голосов у UserA: {user_a_instance.get_votes_for()}")


    # --- 6. ПРОВЕРКА ЗАПРЕТА ГОЛОСОВАНИЯ ЗА СВОЙ ФИЛЬМ ---
    # <-- ЛОГ
    logger.info("ЭТАП 6: Проверка запрета голосования за свой фильм...")
    own_film_id = next(id for id, name in shuffled_list_a.items() if name == "Фильм-1")
    
    vote_own_film_msg = MockMessage(from_user=user_a, text=f"/vote {own_film_id}:-")
    await vote(vote_own_film_msg)
    assert "За свой фильм ('Фильм-1') голосовать нельзя" in vote_own_film_msg.reply_text
    assert main.film_ratings["Фильм-1"] == 0
    # <-- ЛОГ
    logger.info("Проверка успешна: голос за свой фильм отклонен, рейтинг не изменился.")


    # --- 7. ЭТАП СБРОСА ГОЛОСОВ ---
    # <-- ЛОГ
    logger.info(f"ЭТАП 7: UserA сбрасывает свои голоса. Рейтинг 'Фильм-3' до сброса: {main.film_ratings['Фильм-3']}")
    reset_msg = MockMessage(from_user=user_a, text="/reset")
    await reset_votes(reset_msg)
    
    assert "Ваши голоса были сброшены" in reset_msg.reply_text
    assert main.film_ratings["Фильм-3"] == 0
    assert user_a_instance.get_votes_for() == 0
    assert not user_a_instance.get_voted_on()
    # <-- ЛОГ
    logger.info(f"Сброс успешен. Рейтинг 'Фильм-3' после сброса: {main.film_ratings['Фильм-3']}. Голоса UserA очищены.")


    # --- 8. ПРОВЕРКА СБРОСА ДЛЯ НЕ ГОЛОСОВАВШЕГО ---
    # <-- ЛОГ
    logger.info("ЭТАП 8: Проверка сброса для пользователя, который не голосовал (UserB)...")
    reset_fail_msg = MockMessage(from_user=user_b, text="/reset")
    await reset_votes(reset_fail_msg)
    assert "Вы ещё не голосовали, сбрасывать нечего" in reset_fail_msg.reply_text
    # <-- ЛОГ
    logger.info("Проверка успешна: получен корректный ответ для не голосовавшего пользователя.")
    logger.info("================== ТЕСТ УСПЕШНО ЗАВЕРШЕН ==================")
