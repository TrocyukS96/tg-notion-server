from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.notion_service import get_data_source_info, search_databases
from app.services.user_service import get_user, update_selected_database

router = APIRouter(prefix="/notion/databases", tags=["databases"])


class SelectDatabaseBody(BaseModel):
    database_id: str


@router.get("/search")
async def search_user_databases(
    query: str = Query(""),
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user(db, telegram_id)
    if not user or not user.notion_access_token:
        raise HTTPException(status_code=401, detail="Notion не подключён")

    try:
        return await search_databases(query, user.notion_access_token)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/selected")
async def get_selected_database(
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user(db, telegram_id)
    if not user or not user.notion_access_token:
        raise HTTPException(status_code=401, detail="Notion не подключён")

    if not user.selected_database_id:
        raise HTTPException(status_code=404, detail="База данных не выбрана")

    try:
        return await get_data_source_info(
            user.selected_database_id,
            user.notion_access_token,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/select")
async def select_user_database(
    body: SelectDatabaseBody,
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user(db, telegram_id)
    if not user or not user.notion_access_token:
        raise HTTPException(status_code=401, detail="Notion не подключён")

    updated = await update_selected_database(db, telegram_id, body.database_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return {"status": "ok", "selected_database_id": body.database_id}
