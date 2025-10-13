# tests/helpers.py
from dataclasses import dataclass
from typing import List, Optional

# --- Эмуляция объектов aiogram ---

@dataclass
class MockUser:
    """Упрощенная версия пользователя Telegram"""
    id: int
    username: str
    first_name: str

@dataclass
class MockMessage:
    """Упрощенная версия сообщения Telegram"""
    from_user: MockUser
    text: str
    reply_text: Optional[str] = None

    async def reply(self, text: str):
        """Сохраняем ответ бота, чтобы проверить его в тесте"""
        self.reply_text = text
        print(f"BOT REPLIED: {text}") # Для наглядности при запуске тестов

    async def answer(self, text: str, **kwargs):
        """Аналогично reply"""
        self.reply_text = text
        print(f"BOT ANSWERED: {text}")
