from aiogram import Router, types
from aiogram.filters import Command

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для работы с Notion.\n\n"
        "📌 Команды:\n"
        "/connect - Подключить Notion\n"
        "/select_db - Выбрать базу данных\n"
        "/tasks - Показать задачи\n"
        "/status - Статус подключения\n"
        "/help - Помощь"
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🤖 Что я умею:\n\n"
        "1. Подключаться к вашему Notion через OAuth\n"
        "2. Создавать базы данных\n"
        "3. Управлять задачами через канбан-доску\n"
        "4. Добавлять задачи голосом\n\n"
        "🚀 Начните с команды /connect"
    )
