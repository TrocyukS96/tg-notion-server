#!/usr/bin/env python3
"""
Скрипт для установки вебхука Telegram бота.
Запускать после деплоя бэкенда на Render.
"""

import argparse
import asyncio
import sys
from pathlib import Path

import httpx
from aiogram import Bot

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings


async def set_webhook() -> None:
    """Устанавливает вебхук для бота."""
    if not settings.telegram_bot_token:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не задан в .env")
        return

    if not settings.telegram_webhook_url:
        print("❌ Ошибка: TELEGRAM_WEBHOOK_URL не задан в .env")
        print("   Пример: https://ваш-домен.onrender.com/webhook")
        return

    bot = Bot(token=settings.telegram_bot_token)

    try:
        print("📋 Проверяем текущий вебхук...")
        current_webhook = await bot.get_webhook_info()
        print(f"   Текущий URL: {current_webhook.url or 'не установлен'}")
        print(f"   Пендинг обновлений: {current_webhook.pending_update_count}")

        print(f"\n🔄 Устанавливаем вебхук: {settings.telegram_webhook_url}")

        webhook_params = {
            "url": settings.telegram_webhook_url,
            "drop_pending_updates": True,
            "max_connections": 40,
        }

        if settings.telegram_webhook_secret:
            webhook_params["secret_token"] = settings.telegram_webhook_secret
            print(f"   🔐 Секретный токен: {settings.telegram_webhook_secret[:8]}...")

        result = await bot.set_webhook(**webhook_params)

        if result:
            print("✅ Вебхук успешно установлен!")
        else:
            print("❌ Ошибка при установке вебхука (вернул False)")
            return

        print("\n📋 Проверяем новый вебхук...")
        new_webhook = await bot.get_webhook_info()
        print(f"   URL: {new_webhook.url}")
        secret_status = (
            f"{settings.telegram_webhook_secret[:8]}... (установлен)"
            if settings.telegram_webhook_secret
            else "не установлен"
        )
        print(f"   Секретный токен: {secret_status}")
        print(f"   Пендинг обновлений: {new_webhook.pending_update_count}")

        print(f"\n🔍 Проверяем доступность эндпоинта {settings.telegram_webhook_url}...")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    settings.telegram_webhook_url,
                    json={"update_id": 123456789},
                )
                if response.status_code == 200:
                    print(f"   ✅ Эндпоинт доступен (HTTP {response.status_code})")
                else:
                    print(f"   ⚠️ Эндпоинт ответил с кодом {response.status_code}")
        except Exception as e:
            print(f"   ❌ Не удалось проверить эндпоинт: {e}")

        print("\n🎉 Готово! Бот теперь будет получать обновления через вебхук.")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    finally:
        await bot.session.close()


async def delete_webhook() -> None:
    """Удаляет вебхук (переводит бота в polling-режим)."""
    if not settings.telegram_bot_token:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не задан")
        return

    bot = Bot(token=settings.telegram_bot_token)

    try:
        print("🔄 Удаляем вебхук...")
        result = await bot.delete_webhook(drop_pending_updates=True)

        if result:
            print("✅ Вебхук удалён. Бот переведён в polling-режим.")
        else:
            print("❌ Ошибка при удалении вебхука")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Управление вебхуком Telegram бота")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Удалить вебхук (перевести бота в polling-режим)",
    )

    args = parser.parse_args()

    if args.delete:
        asyncio.run(delete_webhook())
    else:
        asyncio.run(set_webhook())
