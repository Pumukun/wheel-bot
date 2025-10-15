# config.py
import os
import sys
import logging
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
