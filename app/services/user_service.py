from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_user(db: AsyncSession, telegram_id: int) -> User | None:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, telegram_id: int) -> User:
    user = User(telegram_id=telegram_id)
    db.add(user)
    await db.commit()
    return user


async def update_notion_tokens(
    db: AsyncSession,
    telegram_id: int,
    access_token: str,
    refresh_token: str,
) -> User | None:
    user = await get_user(db, telegram_id)
    if user is None:
        return None

    user.notion_access_token = access_token
    user.notion_refresh_token = refresh_token
    await db.commit()
    await db.refresh(user)
    return user


async def update_selected_database(
    db: AsyncSession,
    telegram_id: int,
    database_id: str,
) -> User | None:
    user = await get_user(db, telegram_id)
    if user is None:
        return None

    user.selected_database_id = database_id
    await db.commit()
    await db.refresh(user)
    return user


async def get_selected_database(db: AsyncSession, telegram_id: int) -> str | None:
    user = await get_user(db, telegram_id)
    if user is None:
        return None
    return user.selected_database_id
