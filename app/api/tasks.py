from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.notion_service import (
    add_column_to_database,
    create_task,
    get_tasks,
    update_task_status,
    _parse_task,
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
    status: str


class CreateColumnBody(BaseModel):
    title: str


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


@router.patch("/{task_id}")
async def update_user_task(
    task_id: str,
    body: UpdateTaskBody,
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user = await _require_user_with_database(db, telegram_id)

    try:
        updated = await update_task_status(
            task_id,
            body.status,
            user.notion_access_token,
        )
        return _parse_task(updated)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
