from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault


async def set_main_menu(bot: Bot) -> None:
    """Устанавливает команды для кнопки меню (☰)"""
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
    ]

    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
