from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode

import httpx

from sourcing1688.config import Settings, get_settings
from sourcing1688.providers.api_auth import ApiTokenCache
from sourcing1688.utils import structured_error


AUTH_BASE_URL = "https://auth.1688.com/oauth/authorize"


def auth_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    cache = ApiTokenCache(settings.ali1688_token_cache_path).read()
    has_cache_access = bool(cache.get("access_token"))
    has_cache_refresh = bool(cache.get("refresh_token"))
    return {
        "status": "ok",
        "provider": "api",
        "ready": bool(
            settings.ali1688_app_key
            and settings.ali1688_app_secret
            and (settings.ali1688_refresh_token or settings.ali1688_access_token or has_cache_refresh or has_cache_access)
        ),
        "has_app_key": bool(settings.ali1688_app_key),
        "has_app_secret": bool(settings.ali1688_app_secret),
        "has_refresh_token_env": bool(settings.ali1688_refresh_token),
        "has_access_token_env": bool(settings.ali1688_access_token),
        "token_cache_exists": settings.ali1688_token_cache_path.exists(),
        "token_cache_path": str(settings.ali1688_token_cache_path),
        "token_cache_has_access_token": has_cache_access,
        "token_cache_has_refresh_token": has_cache_refresh,
    }


def build_authorization_url(redirect_uri: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    if not settings.ali1688_app_key:
        message = "ALI1688_APP_KEY is required to build an authorization URL."
        return {
            "status": "missing_credentials",
            "ready": False,
            "error": structured_error("missing_credentials", message, suggested_action="Set ALI1688_APP_KEY, then retry.").model_dump(mode="json"),
            "suggested_action": "Set ALI1688_APP_KEY, then retry.",
        }
    query = urlencode({"client_id": settings.ali1688_app_key, "redirect_uri": redirect_uri, "response_type": "code", "site": "1688"})
    return {
        "status": "ok",
        "authorization_url": f"{AUTH_BASE_URL}?{query}",
        "redirect_uri": redirect_uri,
        "next_step": "Open authorization_url, approve the app, copy the returned code, then run `sourcing1688 auth exchange --code CODE --redirect-uri ...`.",
    }


async def exchange_code_for_token(code: str, redirect_uri: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    missing = []
    if not settings.ali1688_app_key:
        missing.append("ALI1688_APP_KEY")
    if not settings.ali1688_app_secret:
        missing.append("ALI1688_APP_SECRET")
    if missing:
        message = "ALI1688_APP_KEY and ALI1688_APP_SECRET are required to exchange an OAuth code."
        return {
            "status": "missing_credentials",
            "ready": False,
            "missing_env": missing,
            "error": structured_error("missing_credentials", message, suggested_action="Set AppKey/AppSecret, then retry.").model_dump(mode="json"),
            "suggested_action": "Set AppKey/AppSecret, then retry.",
        }
    url = f"{settings.ali1688_api_base}/system.oauth2/getToken/{settings.ali1688_app_key}"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            url,
            data={
                "grant_type": "authorization_code",
                "client_id": settings.ali1688_app_key,
                "client_secret": settings.ali1688_app_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result") if isinstance(payload.get("result"), dict) else payload
    access_token = result.get("access_token")
    refresh_token = result.get("refresh_token")
    expires_in = int(result.get("expires_in") or 36000)
    cache_payload = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": time.time() + expires_in,
    }
    cache = ApiTokenCache(settings.ali1688_token_cache_path)
    cache.write({key: value for key, value in cache_payload.items() if value})
    return {
        "status": "ok",
        "token_saved": True,
        "token_cache_path": str(settings.ali1688_token_cache_path),
        "has_access_token": bool(access_token),
        "has_refresh_token": bool(refresh_token),
        "next_step": "Run `sourcing1688 auth status --json` and `sourcing1688 provider-check --provider api --json`.",
    }


def clear_token_cache(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    existed = settings.ali1688_token_cache_path.exists()
    if existed:
        settings.ali1688_token_cache_path.unlink()
    return {
        "status": "ok",
        "token_cache_path": str(settings.ali1688_token_cache_path),
        "deleted": existed,
        "message": "Environment variables such as ALI1688_APP_KEY and ALI1688_APP_SECRET cannot be cleared by this command.",
    }
