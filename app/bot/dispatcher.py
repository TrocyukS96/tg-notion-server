from aiogram import Bot, Dispatcher

from app.core.config import settings

bot: Bot | None = None
if settings.telegram_bot_token:
    bot = Bot(token=settings.telegram_bot_token)

dp = Dispatcher()

from app.bot.handlers import auth, start

dp.include_router(start.router)
dp.include_router(auth.router)
