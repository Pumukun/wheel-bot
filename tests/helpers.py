# tests/helpers.py
import logging
from dataclasses import dataclass, field
from typing import Optional

# --- Эмуляция объектов aiogram ---

logger = logging.getLogger("MOCK_OBJECTS")

class MockBot:
    """Эмулирует объект Bot для вызова его методов."""
    async def send_message(self, chat_id: int, text: str, **kwargs):
        logger.info(f"MOCK BOT: send_message called for chat_id={chat_id} with text='{text[:50]}...'")
        # В реальных тестах здесь можно было бы сохранять вызовы для проверок
        pass
    
    async def send_animation(self, chat_id: int, animation: str, **kwargs):
        logger.info(f"MOCK BOT: send_animation called for chat_id={chat_id} with animation='{animation}'")
        pass


@dataclass
class MockUser:
    """Упрощенная версия пользователя Telegram"""
    id: int
    username: str
    first_name: str

@dataclass
class MockMessage:
    """Упрощенная версия сообщения Telegram с эмуляцией bot"""
    from_user: MockUser
    text: str
    reply_text: Optional[str] = None
    bot: MockBot = field(default_factory=MockBot) # <-- ДОБАВЛЕНО: теперь у сообщения есть бот

    async def reply(self, text: str):
        """Сохраняем ответ бота, чтобы проверить его в тесте"""
        self.reply_text = text
        logger.info(f"BOT REPLIED: {text}")

    async def answer(self, text: str, **kwargs):
        """Аналогично reply"""
        self.reply_text = text
        logger.info(f"BOT ANSWERED: {text}")
