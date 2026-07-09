from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.core.database import AsyncSessionLocal
from app.services.user_service import get_user
from app.services.notion_service import get_tasks

router = Router()


@router.message(Command("tasks"))
async def cmd_tasks(message: types.Message):
    """Показывает задачи из выбранной базы данных"""
    telegram_id = message.from_user.id
    
    # Получаем пользователя и выбранную базу
    async with AsyncSessionLocal() as db:
        user = await get_user(db, telegram_id)
        
        if not user or not user.notion_access_token:
            await message.answer(
                "❌ Сначала авторизуйтесь в Notion через /connect"
            )
            return
        
        if not user.selected_database_id:
            await message.answer(
                "❌ Сначала выберите базу данных через /select_db"
            )
            return

        data_source_id = user.selected_database_id
        access_token = user.notion_access_token
    
    await message.answer("📊 Загружаю задачи...")
    
    try:
        # Получаем задачи из Notion
        tasks = await get_tasks(data_source_id, access_token)
    except Exception as e:
        await message.answer(f"❌ Ошибка при загрузке задач: {e}")
        return
    
    if not tasks:
        await message.answer(
            "📭 В этой базе пока нет задач.\n"
            "Используйте /add для создания новой задачи."
        )
        return
    
    # Группируем задачи по статусу (колонкам)
    tasks_by_status = {}
    for task in tasks:
        status = task.get("status", "Без статуса")
        if status not in tasks_by_status:
            tasks_by_status[status] = []
        tasks_by_status[status].append(task)
    
    # Формируем сообщение
    total_tasks = len(tasks)
    message_text = f"📊 Всего задач: {total_tasks}\n\n"
    
    for status, task_list in tasks_by_status.items():
        message_text += f"📌 {status} ({len(task_list)}):\n"
        for i, task in enumerate(task_list[:5], 1):  # Показываем первые 5
            title = task.get("title", "Без названия")
            message_text += f"  {i}. {title}\n"
        if len(task_list) > 5:
            message_text += f"  ... и еще {len(task_list) - 5} задач\n"
        message_text += "\n"
    
    # Добавляем кнопки для управления
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить задачу", callback_data="add_task")],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_tasks")],
        ]
    )
    
    await message.answer(
        message_text[:4000],  # Telegram ограничение на длину сообщения
        reply_markup=keyboard
    )


@router.callback_query(lambda c: c.data == "add_task")
async def callback_add_task(callback: types.CallbackQuery):
    """Кнопка для добавления задачи"""
    await callback.message.answer(
        "Используйте команду /add для создания новой задачи"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "refresh_tasks")
async def callback_refresh_tasks(callback: types.CallbackQuery):
    """Кнопка для обновления списка задач"""
    await callback.message.delete()
    await cmd_tasks(callback.message)
    await callback.answer()
