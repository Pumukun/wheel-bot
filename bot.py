# bot.py
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from config import TOKEN
from handlers import common, voting, admin
from handlers.admin import send_startup_gif_and_message

async def main():
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    bot = Bot(token=TOKEN, parse_mode=None)
    dp = Dispatcher()

    dp.include_router(admin.router)
    dp.include_router(voting.router)
    dp.include_router(common.router) # Этот роутер должен быть последним, т.к. в нем есть хэндлер без фильтров

    await bot.delete_webhook(drop_pending_updates=True)

    await send_startup_gif_and_message(bot)

    logging.info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
