from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.core.config import settings
from app.services.user_service import get_user
from app.core.database import AsyncSessionLocal

router = Router()


@router.message(Command("connect"))
async def cmd_connect(message: types.Message):
    """Отправляет ссылку для авторизации в Notion"""
    telegram_id = message.from_user.id
    
    # Проверяем, может пользователь уже авторизован
    async with AsyncSessionLocal() as db:
        user = await get_user(db, telegram_id)
        
        if user and user.notion_access_token:
            await message.answer(
                "✅ Вы уже авторизованы в Notion!\n"
                f"📊 Выбранная база: {user.selected_database_id or 'не выбрана'}\n"
                "Используйте /select_db для выбора базы."
            )
            return
    
    # Формируем ссылку для авторизации
    auth_url = f"{settings.BASE_URL}/notion/login?telegram_id={telegram_id}"
    
    # Создаём кнопку-ссылку
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔑 Авторизоваться в Notion",
                url=auth_url
            )]
        ]
    )
    
    await message.answer(
        "🔐 Для работы с Notion необходимо авторизоваться.\n\n"
        "Нажмите на кнопку ниже, чтобы перейти к авторизации:\n"
        "После авторизации вернитесь в бот и нажмите /status",
        reply_markup=keyboard
    )


@router.message(Command("status"))
async def cmd_status(message: types.Message):
    """Проверяет статус авторизации в Notion"""
    telegram_id = message.from_user.id
    
    async with AsyncSessionLocal() as db:
        user = await get_user(db, telegram_id)
        
        if not user:
            await message.answer(
                "❌ Вы не зарегистрированы.\n"
                "Используйте /start для регистрации."
            )
            return
        
        if user.notion_access_token:
            status = "✅ Авторизован"
            db_status = f"📊 Выбранная база: {user.selected_database_id or 'не выбрана'}"
        else:
            status = "❌ Не авторизован"
            db_status = "Используйте /connect для авторизации"
        
        await message.answer(
            f"📋 Статус Notion:\n"
            f"• {status}\n"
            f"• {db_status}\n\n"
            f"👤 Ваш ID в Telegram: {telegram_id}"
        )
