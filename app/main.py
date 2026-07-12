from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import router as auth_router
from app.api.databases import router as databases_router
from app.api.tasks import columns_router, router as tasks_router
from app.api.webhook import router as webhook_router
from app.bot.commands import set_main_menu
from app.bot.dispatcher import bot
from app.core.database import check_db_connection, close_db, get_db, init_db
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_db_connection()
    await init_db()
    if bot is not None:
        await set_main_menu(bot)
    yield
    if bot is not None:
        await bot.session.close()
    await close_db()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://notion-webapp-six.vercel.app",
        "https://*.vercel.app",          
    ],
    allow_credentials=True,
    allow_methods=["*"],               
    allow_headers=["*"],            
)

app.include_router(auth_router)
app.include_router(databases_router)
app.include_router(tasks_router)
app.include_router(columns_router)
app.include_router(webhook_router)



