from aiogram import Bot, Dispatcher

from app.core.config import settings

dp = Dispatcher()
bot: Bot | None = None

if settings.telegram_bot_token:
    bot = Bot(token=settings.telegram_bot_token)
