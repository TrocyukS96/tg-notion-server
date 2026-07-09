from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

from app.core.config import settings

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start с кнопкой WebApp"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📊 Открыть доску",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL),
                )
            ],
            [
                KeyboardButton(text="🔑 Подключить Notion"),
                KeyboardButton(text="📋 Мои задачи"),
            ],
            [
                KeyboardButton(text="➕ Добавить задачу"),
                KeyboardButton(text="ℹ️ Помощь"),
            ],
        ],
        resize_keyboard=True,
    )

    await message.answer(
        "👋 Привет! Я бот для работы с Notion.\n\n"
        "📌 <b>Команды:</b>\n"
        "/connect - Подключить Notion\n"
        "/select_db - Выбрать базу данных\n"
        "/tasks - Показать задачи\n"
        "/add - Добавить задачу\n"
        "/board - Открыть доску\n"
        "/help - Помощь",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.message(Command("board"))
async def cmd_board(message: types.Message):
    """Команда для открытия доски"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📊 Открыть доску",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL),
                )
            ]
        ],
        resize_keyboard=True,
    )

    await message.answer(
        "📊 Нажмите кнопку, чтобы открыть канбан-доску:",
        reply_markup=keyboard,
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    await message.answer(
        "🤖 <b>Что я умею:</b>\n\n"
        "1️⃣ <b>Подключаться к Notion</b> — /connect\n"
        "2️⃣ <b>Выбирать базу данных</b> — /select_db\n"
        "3️⃣ <b>Просматривать задачи</b> — /tasks\n"
        "4️⃣ <b>Добавлять задачи</b> — /add\n"
        "5️⃣ <b>Открывать доску</b> — /board (или кнопка ниже)\n\n"
        "📊 <b>Канбан-доска</b> позволяет:\n"
        "• Перетаскивать задачи между колонками\n"
        "• Добавлять новые задачи\n"
        "• Добавлять новые колонки\n\n"
        "🔐 <b>Важно:</b> Сначала авторизуйтесь через /connect!",
        parse_mode="HTML",
    )
