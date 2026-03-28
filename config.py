# config.py
import os
import sys
import logging
import json
from pathlib import Path
from dotenv import load_dotenv
from typing import List

load_dotenv()

TOKEN: str | None = os.getenv("MY_TOKEN")
ADMIN_USER_ID_STR: str | None = os.getenv("ADMIN_USER_ID")
USERS_TO_NOTIFY_STR: str | None = os.getenv("USERS_TO_NOTIFY")

if TOKEN is None:
    logging.critical("MY_TOKEN не найден в переменных окружения или .env файле. Завершение работы.")
    sys.exit(1)

if ADMIN_USER_ID_STR is None or not ADMIN_USER_ID_STR.isdigit():
    logging.critical("ADMIN_USER_ID не найден или имеет неверный формат. Завершение работы.")
    sys.exit(1)

ADMIN_USER_ID: int = int(ADMIN_USER_ID_STR)
USERS_TO_NOTIFY: List[str] = USERS_TO_NOTIFY_STR.split(',') if USERS_TO_NOTIFY_STR else []

GIF_URL: str = r'https://i.postimg.cc/kgppKXB3/sex-alarm.gif'

SUBSCRIBERS_FILE = Path("subscribers.json")

def load_subscribers() -> set:
    if SUBSCRIBERS_FILE.exists():
        try:
            with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('subscribers', []))
        except Exception as e:
            logging.error(f"Ошибка при загрузке подписчиков: {e}")
            return set()
    return set()

def save_subscribers(subscribers: set):
    try:
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({'subscribers': list(subscribers)}, f, ensure_ascii=False, indent=2)
        logging.info(f"Список подписчиков сохранён ({len(subscribers)} чел.)")
    except Exception as e:
        logging.error(f"Ошибка при сохранении подписчиков: {e}")