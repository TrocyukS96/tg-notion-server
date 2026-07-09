from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault


async def set_main_menu(bot: Bot) -> None:
    """Устанавливает команды для кнопки меню (☰)"""
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="board", description="📊 Открыть доску"),
        BotCommand(command="connect", description="🔑 Подключить Notion"),
        BotCommand(command="select_db", description="📂 Выбрать базу данных"),
        BotCommand(command="tasks", description="📋 Мои задачи"),
        BotCommand(command="add", description="➕ Добавить задачу"),
        BotCommand(command="help", description="ℹ️ Помощь"),
    ]

    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
