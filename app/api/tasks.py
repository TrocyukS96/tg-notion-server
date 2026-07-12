from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.notion_service import (
    add_column_to_database,
    create_task,
    delete_column_from_database,
    delete_task,
    get_database_columns,
    get_tasks,
    reorder_tasks,
    update_task,
)
from app.services.user_service import get_user

router = APIRouter(prefix="/tasks", tags=["tasks"])
columns_router = APIRouter(prefix="/columns", tags=["columns"])


class CreateTaskBody(BaseModel):
    title: str
    description: str | None = None
    status: str
    due_date: str | None = None


class UpdateTaskBody(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    due_date: str | None = None


class CreateColumnBody(BaseModel):
    title: str


class DeleteColumnBody(BaseModel):
    title: str


class ReorderTasksBody(BaseModel):
    status: str
    task_ids: list[str]


async def _require_user_with_database(db: AsyncSession, telegram_id: int):
    user = await get_user(db, telegram_id)
    if not user or not user.notion_access_token:
        raise HTTPException(status_code=401, detail="Notion не подключён")

    if not user.selected_database_id:
        raise HTTPException(status_code=400, detail="База данных не выбрана")

    return user


@router.get("")
async def list_tasks(
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user = await _require_user_with_database(db, telegram_id)

    try:
        return await get_tasks(user.selected_database_id, user.notion_access_token)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("")
async def create_user_task(
    body: CreateTaskBody,
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user = await _require_user_with_database(db, telegram_id)

    try:
        task_id = await create_task(
            user.selected_database_id,
            body.title,
            body.description or "",
            body.status,
            body.due_date,
            user.notion_access_token,
        )
        return {
            "id": task_id,
            "title": body.title,
            "description": body.description,
            "status": body.status,
            "due_date": body.due_date,
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.patch("/reorder")
async def reorder_user_tasks(
    body: ReorderTasksBody,
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user = await _require_user_with_database(db, telegram_id)

    if not body.task_ids:
        raise HTTPException(status_code=400, detail="Список задач пуст")

    try:
        await reorder_tasks(
            user.selected_database_id,
            body.status,
            body.task_ids,
            user.notion_access_token,
        )
        return {"status": "ok", "status_column": body.status, "task_ids": body.task_ids}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.patch("/{task_id}")
async def update_user_task(
    task_id: str,
    body: UpdateTaskBody,
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user = await _require_user_with_database(db, telegram_id)

    if not any(
        value is not None
        for value in (body.title, body.description, body.status, body.due_date)
    ):
        raise HTTPException(status_code=400, detail="Нет данных для обновления")

    try:
        clear_due_date = body.due_date == ""
        updated = await update_task(
            task_id,
            user.notion_access_token,
            title=body.title,
            description=body.description,
            status=body.status,
            due_date=body.due_date if body.due_date else None,
            clear_due_date=clear_due_date,
        )
        return updated
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("/{task_id}")
async def delete_user_task(
    task_id: str,
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user = await _require_user_with_database(db, telegram_id)

    try:
        await delete_task(task_id, user.notion_access_token)
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@columns_router.get("")
async def list_columns(
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user = await _require_user_with_database(db, telegram_id)

    try:
        return await get_database_columns(
            user.selected_database_id,
            user.notion_access_token,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@columns_router.post("")
async def create_column(
    body: CreateColumnBody,
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user = await _require_user_with_database(db, telegram_id)

    try:
        await add_column_to_database(
            user.selected_database_id,
            body.title,
            user.notion_access_token,
        )
        return {"status": "ok", "title": body.title}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@columns_router.delete("")
async def remove_column(
    body: DeleteColumnBody,
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user = await _require_user_with_database(db, telegram_id)

    try:
        await delete_column_from_database(
            user.selected_database_id,
            body.title,
            user.notion_access_token,
        )
        return {"status": "ok", "title": body.title}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
