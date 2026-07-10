from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

from app.core.config import settings

router = Router()

START_TEXT = (
    "👋 <b>Добро пожаловать в TG Notion!</b>\n\n"
    "Это приложение связывает Telegram с вашими задачами в Notion. "
    "Все управление задачами — в удобной канбан-доске прямо в Telegram.\n\n"
    "🚀 <b>С чего начать:</b>\n"
    "1. Нажмите «📊 Открыть доску» или отправьте /board\n"
    "2. Подключите аккаунт Notion\n"
    "3. Выберите базу данных с задачами\n\n"
    "📌 <b>Команды:</b>\n"
    "/board — открыть канбан-доску\n"
    "/help — подробная инструкция\n\n"
    "🔜 <b>Скоро:</b> голосовой ввод задач с помощью ИИ — просто надиктуйте задачу, "
    "а бот сам создаст её в Notion."
)

HELP_TEXT = (
    "📖 <b>Как пользоваться TG Notion</b>\n\n"
    "🔹 <b>Что это?</b>\n"
    "TG Notion — Telegram-бот с канбан-доской для работы с задачами из Notion. "
    "Все изменения синхронизируются с выбранной базой данных в вашем workspace.\n\n"
    "🔹 <b>Первый запуск</b>\n"
    "1. Откройте web app — /board или кнопка «📊 Открыть доску»\n"
    "2. Авторизуйтесь в Notion и разрешите доступ к workspace\n"
    "3. Выберите базу данных — оттуда будут подгружаться задачи\n\n"
    "🔹 <b>Что можно делать в web app</b>\n"
    "• Просматривать задачи на канбан-доске\n"
    "• Перетаскивать задачи между колонками\n"
    "• Создавать и редактировать задачи\n"
    "• Добавлять новые колонки\n\n"
    "🔹 <b>Скоро</b>\n"
    "• Голосовой ввод задач с помощью ИИ — отправьте голосовое сообщение, "
    "и бот распознает текст, определит название, описание и дедлайн, "
    "а затем создаст задачу в Notion\n\n"
    "🔹 <b>Команды бота</b>\n"
    "/start — главное меню\n"
    "/board — открыть доску\n"
    "/help — эта справка"
)


def _main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📊 Открыть доску",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL),
                )
            ],
            [
                KeyboardButton(text="ℹ️ Помощь"),
            ],
        ],
        resize_keyboard=True,
    )


def _board_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
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


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start с кнопкой WebApp"""
    await message.answer(
        START_TEXT,
        reply_markup=_main_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("board"))
async def cmd_board(message: types.Message):
    """Команда для открытия доски"""
    await message.answer(
        "📊 <b>Канбан-доска</b>\n\n"
        "Нажмите кнопку ниже, чтобы открыть web app. "
        "Там вы подключите Notion, выберете базу и сможете управлять задачами.",
        reply_markup=_board_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(F.text == "ℹ️ Помощь")
async def btn_help(message: types.Message):
    await cmd_help(message)
