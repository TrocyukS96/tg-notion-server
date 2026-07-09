from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import settings

bot: Bot | None = None
if settings.telegram_bot_token:
    bot = Bot(token=settings.telegram_bot_token)

dp = Dispatcher(storage=MemoryStorage())

from app.bot.handlers import add, auth, databases, start, tasks

dp.include_router(start.router)
dp.include_router(auth.router)
dp.include_router(databases.router)
dp.include_router(tasks.router)
dp.include_router(add.router)