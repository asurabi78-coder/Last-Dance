from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from sourcing1688.config import Settings, get_settings
from sourcing1688.models import StructuredError


TOKEN_REDACTION = "***REDACTED***"


class ApiTokenCache:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def redact_token_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(payload)
    for key in ["access_token", "refresh_token", "ALI1688_ACCESS_TOKEN", "ALI1688_REFRESH_TOKEN"]:
        if key in redacted and redacted[key]:
            redacted[key] = TOKEN_REDACTION
    return redacted


class ApiAuthManager:
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.cache = ApiTokenCache(self.settings.ali1688_token_cache_path)

    def has_any_credentials(self) -> bool:
        return bool(
            self.settings.ali1688_app_key
            and self.settings.ali1688_app_secret
            and (self.settings.ali1688_access_token or self.settings.ali1688_refresh_token)
        )

    def _cached_access_token(self) -> str | None:
        cached = self.cache.read()
        token = cached.get("access_token")
        expires_at = float(cached.get("expires_at") or 0)
        if token and expires_at > time.time() + 60:
            return str(token)
        return None

    async def get_access_token(self) -> tuple[str | None, StructuredError | None]:
        if self.settings.ali1688_access_token:
            return self.settings.ali1688_access_token, None
        cached = self._cached_access_token()
        if cached:
            return cached, None
        if not (self.settings.ali1688_app_key and self.settings.ali1688_app_secret and self.settings.ali1688_refresh_token):
            return None, StructuredError(
                code="missing_credentials",
                message="ALI1688_APP_KEY, ALI1688_APP_SECRET, and ALI1688_REFRESH_TOKEN or ALI1688_ACCESS_TOKEN are required.",
                suggested_action="Set API credentials or use provider=browser/local_html.",
            )
        return await self.refresh_access_token()

    async def refresh_access_token(self) -> tuple[str | None, StructuredError | None]:
        own_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=20)
        try:
            url = f"{self.settings.ali1688_api_base}/system.oauth2/getToken/{self.settings.ali1688_app_key}"
            response = await client.post(
                url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.settings.ali1688_app_key,
                    "client_secret": self.settings.ali1688_app_secret,
                    "refresh_token": self.settings.ali1688_refresh_token,
                },
            )
            response.raise_for_status()
            payload = response.json()
            token = payload.get("access_token") or payload.get("result", {}).get("access_token")
            if not token:
                return None, StructuredError(
                    code="token_refresh_failed",
                    message="1688 token refresh response did not include access_token.",
                    details={"response": redact_token_payload(payload)},
                )
            expires_in = int(payload.get("expires_in") or payload.get("result", {}).get("expires_in") or 36000)
            cache_payload = {
                "access_token": token,
                "refresh_token": self.settings.ali1688_refresh_token,
                "expires_at": time.time() + expires_in,
            }
            self.cache.write(cache_payload)
            return str(token), None
        except Exception as exc:  # noqa: BLE001 - structured auth failure for agents.
            return None, StructuredError(
                code="token_refresh_failed",
                message=f"1688 token refresh failed: {exc}",
                suggested_action="Re-authorize the 1688 app and refresh ALI1688_REFRESH_TOKEN.",
            )
        finally:
            if own_client:
                await client.aclose()
