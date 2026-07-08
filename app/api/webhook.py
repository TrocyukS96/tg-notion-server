from aiogram.types import Update
from fastapi import APIRouter, HTTPException, Request

from app.bot.dispatcher import bot, dp
from app.core.config import settings

router = APIRouter(tags=["webhook"])


@router.post("/webhook")
async def telegram_webhook(request: Request) -> dict[str, bool]:
    if not settings.telegram_bot_token or bot is None:
        raise HTTPException(status_code=500, detail="Telegram bot token is not configured")

    update = Update.model_validate(
        await request.json(),
        context={"bot": bot},
    )
    await dp.feed_update(bot, update)
    return {"ok": True}
