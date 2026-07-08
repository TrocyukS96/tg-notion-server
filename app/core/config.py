import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


class Settings:
    def __init__(self) -> None:
        self.notion_client_id = os.getenv("NOTION_CLIENT_ID", "")
        self.notion_client_secret = os.getenv("NOTION_CLIENT_SECRET", "")
        self.notion_redirect_uri = os.getenv("NOTION_REDIRECT_URI", "")
        self.database_url = os.getenv("DATABASE_URL", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL", "")
        self.telegram_webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
