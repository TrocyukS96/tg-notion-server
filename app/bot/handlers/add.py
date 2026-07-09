import re

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from app.core.database import AsyncSessionLocal
from app.services.user_service import get_user
from app.services.notion_service import create_task, get_database_columns

router = Router()


class AddTaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_status = State()
    waiting_for_due_date = State()
    waiting_for_confirmation = State()


@router.message(Command("add"))
async def cmd_add_task(message: types.Message, state: FSMContext):
    """Начинает процесс добавления задачи"""
    telegram_id = message.from_user.id

    async with AsyncSessionLocal() as db:
        user = await get_user(db, telegram_id)

        if not user or not user.notion_access_token:
            await message.answer("❌ Сначала авторизуйтесь в Notion через /connect")
            return

        if not user.selected_database_id:
            await message.answer("❌ Сначала выберите базу данных через /select_db")
            return

        database_id = user.selected_database_id
        access_token = user.notion_access_token

    await state.update_data(database_id=database_id)

    try:
        columns = await get_database_columns(database_id, access_token)
        await state.update_data(columns=columns)
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении колонок: {e}")
        return

    await message.answer(
        "📝 Введите **название** задачи:",
        parse_mode="Markdown",
    )
    await state.set_state(AddTaskStates.waiting_for_title)


@router.message(AddTaskStates.waiting_for_title)
async def process_task_title(message: types.Message, state: FSMContext):
    """Обрабатывает ввод названия задачи"""
    title = message.text.strip()

    if not title:
        await message.answer("❌ Название не может быть пустым. Введите название:")
        return

    await state.update_data(title=title)

    await message.answer(
        "📝 Введите **описание** задачи (или отправьте 'пропустить'):",
        parse_mode="Markdown",
    )
    await state.set_state(AddTaskStates.waiting_for_description)


@router.message(AddTaskStates.waiting_for_description)
async def process_task_description(message: types.Message, state: FSMContext):
    """Обрабатывает ввод описания задачи"""
    description = message.text.strip()

    if description.lower() == "пропустить":
        description = ""

    await state.update_data(description=description)

    data = await state.get_data()
    columns = data.get("columns", [])

    if not columns:
        await message.answer(
            "❌ Не найдены колонки в базе данных. Создайте их вручную в Notion."
        )
        await state.clear()
        return

    keyboard_buttons = []
    for column in columns[:20]:
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text=f"📌 {column}",
                    callback_data=f"status_{column}",
                )
            ]
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer(
        "📂 Выберите **колонку** (статус) для задачи:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(AddTaskStates.waiting_for_status)


@router.callback_query(AddTaskStates.waiting_for_status)
async def process_task_status(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор колонки"""
    if not callback.data or not callback.data.startswith("status_"):
        await callback.answer()
        return

    status = callback.data.removeprefix("status_")
    await state.update_data(status=status)

    await callback.message.delete()
    await callback.message.answer(
        f"✅ Выбрана колонка: {status}\n\n"
        "📅 Введите **дату дедлайна** в формате ГГГГ-ММ-ДД (или отправьте 'пропустить'):",
        parse_mode="Markdown",
    )
    await state.set_state(AddTaskStates.waiting_for_due_date)
    await callback.answer()


@router.message(AddTaskStates.waiting_for_due_date)
async def process_task_due_date(message: types.Message, state: FSMContext):
    """Обрабатывает ввод даты дедлайна"""
    due_date = message.text.strip()

    if due_date.lower() == "пропустить":
        due_date = None
    elif not re.match(r"^\d{4}-\d{2}-\d{2}$", due_date):
        await message.answer(
            "❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД (например, 2025-12-31)\n"
            "Или отправьте 'пропустить'"
        )
        return

    await state.update_data(due_date=due_date)

    data = await state.get_data()
    title = data.get("title")
    description = data.get("description") or "—"
    status = data.get("status")
    due = due_date or "—"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Создать задачу", callback_data="confirm_add")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_add")],
        ]
    )

    await message.answer(
        f"📋 **Проверьте задачу:**\n\n"
        f"📌 **Название:** {title}\n"
        f"📝 **Описание:** {description}\n"
        f"📂 **Колонка:** {status}\n"
        f"📅 **Дедлайн:** {due}\n\n"
        f"Все верно?",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(AddTaskStates.waiting_for_confirmation)


@router.callback_query(AddTaskStates.waiting_for_confirmation)
async def process_task_confirmation(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает подтверждение создания задачи"""
    if callback.data == "cancel_add":
        await callback.message.edit_text("❌ Создание задачи отменено")
        await state.clear()
        await callback.answer()
        return

    if callback.data != "confirm_add":
        await callback.answer()
        return

    data = await state.get_data()
    telegram_id = callback.from_user.id

    async with AsyncSessionLocal() as db:
        user = await get_user(db, telegram_id)

        if not user or not user.notion_access_token:
            await callback.message.edit_text("❌ Ошибка авторизации. Используйте /connect")
            await state.clear()
            await callback.answer()
            return

        access_token = user.notion_access_token
        database_id = user.selected_database_id

    try:
        await create_task(
            database_id=database_id,
            title=data.get("title"),
            description=data.get("description", ""),
            status=data.get("status"),
            due_date=data.get("due_date"),
            access_token=access_token,
        )

        await callback.message.edit_text(
            f"✅ **Задача создана!**\n\n"
            f"📌 **Название:** {data.get('title')}\n"
            f"📂 **Колонка:** {data.get('status')}\n\n"
            f"Используйте /tasks для просмотра всех задач.",
            parse_mode="Markdown",
        )
        await state.clear()
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка при создании задачи: {e}")
        await state.clear()

    await callback.answer()
