from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.core.database import AsyncSessionLocal
from app.services.user_service import get_user, update_selected_database
from app.services.notion_service import search_databases

router = Router()


class SelectDBStates(StatesGroup):
    waiting_for_query = State()  # Ждем ввода названия базы


@router.message(Command("select_db"))
async def cmd_select_db(message: types.Message, state: FSMContext):
    """Начинает процесс выбора базы данных"""
    telegram_id = message.from_user.id
    
    # Проверяем авторизацию
    async with AsyncSessionLocal() as db:
        user = await get_user(db, telegram_id)
        
        if not user or not user.notion_access_token:
            await message.answer(
                "❌ Сначала авторизуйтесь в Notion через /connect"
            )
            return
    
    await message.answer(
        "🔍 Введите название базы данных (или часть названия), которую хотите использовать:"
    )
    await state.set_state(SelectDBStates.waiting_for_query)


@router.message(SelectDBStates.waiting_for_query)
async def process_db_search(message: types.Message, state: FSMContext):
    """Обрабатывает поиск базы данных по названию"""
    query = message.text.strip()
    telegram_id = message.from_user.id
    
    if not query:
        await message.answer("❌ Введите название базы данных")
        return
    
    await message.answer("🔍 Ищу базы данных...")
    
    async with AsyncSessionLocal() as db:
        user = await get_user(db, telegram_id)
        
        if not user or not user.notion_access_token:
            await message.answer("❌ Сначала авторизуйтесь через /connect")
            await state.clear()
            return
        
        # Ищем базы данных через Notion API
        try:
            databases = await search_databases(query, user.notion_access_token)
        except Exception as e:
            await message.answer(f"❌ Ошибка при поиске: {e}")
            await state.clear()
            return
    
    if not databases:
        await message.answer(
            "❌ Базы данных не найдены.\n"
            "Попробуйте другое название или создайте базу вручную в Notion."
        )
        await state.clear()
        return
    
    # Создаем кнопки для каждой найденной базы
    keyboard_buttons = []
    for db_item in databases[:10]:  # Ограничиваем 10 базами
        db_id = db_item.get("id")
        db_title = db_item.get("title", "Без названия")
        keyboard_buttons.append(
            [InlineKeyboardButton(
                text=f"📊 {db_title}",
                callback_data=f"select_db_{db_id}"
            )]
        )
    
    # Добавляем кнопку отмены
    keyboard_buttons.append(
        [InlineKeyboardButton(text="❌ Отмена", callback_data="select_db_cancel")]
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.answer(
        f"🔍 Найдено баз: {len(databases)}\n\n"
        "Выберите базу данных для работы:",
        reply_markup=keyboard
    )
    await state.clear()


@router.callback_query(lambda c: c.data and c.data.startswith("select_db_"))
async def process_db_selection(callback: types.CallbackQuery):
    """Обрабатывает выбор базы данных по кнопке"""
    telegram_id = callback.from_user.id
    db_id = callback.data.replace("select_db_", "")
    
    if db_id == "cancel":
        await callback.message.edit_text("❌ Выбор базы отменен")
        await callback.answer()
        return
    
    # Сохраняем выбранную базу в БД
    async with AsyncSessionLocal() as db:
        user = await update_selected_database(db, telegram_id, db_id)
        
        if not user:
            await callback.message.edit_text("❌ Пользователь не найден. Используйте /start")
            await callback.answer()
            return
    
    await callback.message.edit_text(
        f"✅ База данных выбрана!\n"
        f"ID: {db_id}\n\n"
        "Используйте /tasks для просмотра задач."
    )
    await callback.answer()
