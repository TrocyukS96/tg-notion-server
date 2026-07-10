from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.services.user_service import create_user, get_user, update_notion_tokens

NOTION_AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"
NOTION_OAUTH_TIMEOUT = 10.0

OAUTH_USER_ERROR_MESSAGES = {
    "access_denied": "User denied Notion access",
    "invalid_request": "Invalid OAuth request",
}

router = APIRouter(prefix="/notion", tags=["auth"])

STATE_PREFIX = "tg_"


def build_oauth_state(telegram_id: int) -> str:
    return f"{STATE_PREFIX}{telegram_id}"


def parse_oauth_state(state: str) -> int:
    if not state.startswith(STATE_PREFIX):
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    try:
        return int(state.removeprefix(STATE_PREFIX))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid state parameter") from exc


def build_notion_oauth_url(telegram_id: int) -> str:
    params = {
        "client_id": settings.notion_client_id,
        "redirect_uri": settings.notion_redirect_uri,
        "response_type": "code",
        "state": build_oauth_state(telegram_id),
        "owner": "user",
    }
    return f"{NOTION_AUTHORIZE_URL}?{urlencode(params)}"


def build_oauth_return_url(
    *,
    success: bool,
    telegram_id: int,
    error: str | None = None,
) -> str:
    if success and settings.telegram_mini_app_link:
        return f"{settings.telegram_mini_app_link.rstrip('/')}?startapp=notion_auth_ok"

    base = settings.WEBAPP_URL.rstrip("/")
    params: dict[str, str] = {
        "notion_auth": "success" if success else "error",
        "telegram_id": str(telegram_id),
    }

    if error:
        params["error"] = error[:200]

    return f"{base}?{urlencode(params)}"


@router.get("/login")
async def notion_login(telegram_id: int = Query(...)) -> RedirectResponse:
    if not settings.notion_client_id or not settings.notion_redirect_uri:
        raise HTTPException(status_code=500, detail="Notion OAuth is not configured")

    return RedirectResponse(url=build_notion_oauth_url(telegram_id))


async def exchange_notion_code(code: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=NOTION_OAUTH_TIMEOUT) as client:
            response = await client.post(
                NOTION_TOKEN_URL,
                auth=(settings.notion_client_id, settings.notion_client_secret),
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.notion_redirect_uri,
                },
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Notion OAuth request timed out",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Failed to connect to Notion OAuth service",
        ) from exc

    if response.status_code == 200:
        data = response.json()
        if "access_token" not in data:
            raise HTTPException(
                status_code=502,
                detail="Notion returned an invalid token response",
            )
        return data

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    error_code = payload.get("code")
    message = payload.get("message", "Failed to exchange authorization code")

    if error_code == "invalid_grant" or response.status_code == 400:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid authorization code: {message}",
        )

    raise HTTPException(status_code=502, detail=message)


@router.get("/callback")
async def notion_callback(
    state: str = Query(...),
    code: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    if (
        not settings.notion_client_id
        or not settings.notion_client_secret
        or not settings.notion_redirect_uri
    ):
        raise HTTPException(status_code=500, detail="Notion OAuth is not configured")

    telegram_id = parse_oauth_state(state)

    if error:
        detail = OAUTH_USER_ERROR_MESSAGES.get(
            error,
            error_description or "OAuth authorization failed",
        )
        return RedirectResponse(
            url=build_oauth_return_url(
                success=False,
                telegram_id=telegram_id,
                error=detail,
            ),
            status_code=302,
        )

    if not code:
        return RedirectResponse(
            url=build_oauth_return_url(
                success=False,
                telegram_id=telegram_id,
                error="Authorization code is missing",
            ),
            status_code=302,
        )

    try:
        token_data = await exchange_notion_code(code)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "OAuth authorization failed"
        return RedirectResponse(
            url=build_oauth_return_url(
                success=False,
                telegram_id=telegram_id,
                error=detail,
            ),
            status_code=302,
        )

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token") or ""

    if await get_user(db, telegram_id) is None:
        await create_user(db, telegram_id)

    user = await update_notion_tokens(db, telegram_id, access_token, refresh_token)
    if user is None:
        return RedirectResponse(
            url=build_oauth_return_url(
                success=False,
                telegram_id=telegram_id,
                error="User not found",
            ),
            status_code=302,
        )

    return RedirectResponse(
        url=build_oauth_return_url(success=True, telegram_id=telegram_id),
        status_code=302,
    )


@router.get("/status")
async def notion_status(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: AsyncSession = Depends(get_db),
):
    """Проверяет, авторизован ли пользователь в Notion"""
    user = await get_user(db, telegram_id)
    if not user:
        return {"authorized": False, "message": "Пользователь не найден"}

    if user.notion_access_token:
        return {
            "authorized": True,
            "has_refresh_token": bool(user.notion_refresh_token),
            "notion_workspace_id": user.notion_workspace_id,
            "selected_database_id": user.selected_database_id,
        }

    return {"authorized": False, "message": "Notion не подключён"}
