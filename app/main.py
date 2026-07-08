from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import router as auth_router
from app.core.database import check_db_connection, close_db, get_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_db_connection()
    await init_db()
    yield
    await close_db()


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)



