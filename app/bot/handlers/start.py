from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.markdown import hbold, hitalic

from app.core.config import settings

router = Router()

START_TEXT = (
    "👋 <b>Добро пожаловать в TG Notion!</b>\n\n"
    "Это приложение связывает Telegram с вашими задачами в Notion. "
    "Все управление задачами — в удобной канбан-доске прямо в Telegram.\n\n"
    "🚀 <b>С чего начать:</b>\n"
    "1. Нажмите «📊 Открыть доску»\n"
    "2. Подключите аккаунт Notion\n"
    "3. Выберите базу данных с задачами\n\n"
    "📌 <b>Команды:</b>\n"
    "/board — открыть канбан-доску\n"
    "/help — подробная инструкция"
)

HELP_TEXT = (
    "📖 <b>Как пользоваться TG Notion</b>\n\n"
    "🔹 <b>Что это?</b>\n"
    "TG Notion — Telegram-бот с канбан-доской для работы с задачами из Notion. "
    "Все изменения синхронизируются с выбранной базой данных в вашем workspace.\n\n"
    "🔹 <b>Первый запуск</b>\n"
    "1. Откройте web app — кнопка «📊 Открыть доску»\n"
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


def _main_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    """Главная клавиатура с Inline-кнопками (передаёт initData!)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Открыть доску",
                    web_app=WebAppInfo(url=webapp_url)
                )
            ],
            [
                InlineKeyboardButton(
                    text="❓ Помощь",
                    callback_data="help"
                )
            ]
        ]
    )


def _board_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    """Клавиатура для /board с Inline-кнопкой"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Открыть доску",
                    web_app=WebAppInfo(url=webapp_url)
                )
            ]
        ]
    )


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start с Inline-кнопкой WebApp"""
    # Добавляем telegram_id в URL для надёжности
    webapp_url = f"{settings.WEBAPP_URL}?telegram_id={message.from_user.id}"
    
    await message.answer(
        START_TEXT,
        reply_markup=_main_keyboard(webapp_url),
        parse_mode="HTML",
    )


@router.message(Command("board"))
async def cmd_board(message: types.Message):
    """Команда для открытия доски"""
    webapp_url = f"{settings.WEBAPP_URL}?telegram_id={message.from_user.id}"
    
    await message.answer(
        "📊 <b>Канбан-доска</b>\n\n"
        "Нажмите кнопку ниже, чтобы открыть web app. "
        "Там вы подключите Notion, выберете базу и сможете управлять задачами.",
        reply_markup=_board_keyboard(webapp_url),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.callback_query(F.data == "help")
async def callback_help(callback: types.CallbackQuery):
    """Обработчик кнопки 'Помощь'"""
    await callback.message.edit_text(
        HELP_TEXT,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="back_to_start"
                    )
                ]
            ]
        )
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_start")
async def callback_back_to_start(callback: types.CallbackQuery):
    """Возврат на главный экран"""
    webapp_url = f"{settings.WEBAPP_URL}?telegram_id={callback.from_user.id}"
    
    await callback.message.edit_text(
        START_TEXT,
        parse_mode="HTML",
        reply_markup=_main_keyboard(webapp_url)
    )
    await callback.answer()