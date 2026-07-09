from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    notion_client_id: str = ""
    notion_client_secret: str = ""
    notion_redirect_uri: str = ""
    database_url: str = ""
    openai_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""
    telegram_webhook_secret: str = ""
    BASE_URL: str = ""
    WEBAPP_URL: str = "https://ваш-проект.vercel.app"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
