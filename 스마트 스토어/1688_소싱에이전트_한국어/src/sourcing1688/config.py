from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


def default_home() -> Path:
    return Path(os.getenv("SOURCING1688_HOME") or (Path.home() / ".sourcing1688")).expanduser()


def home_path(*parts: str) -> Path:
    return default_home().joinpath(*parts)


class Settings(BaseModel):
    home: Path = Field(default_factory=default_home)
    provider: str = Field(default_factory=lambda: os.getenv("SOURCING1688_PROVIDER", "auto"))
    db_path: Path = Field(default_factory=lambda: Path(os.getenv("SOURCING1688_DB_PATH") or home_path("data", "sourcing1688.duckdb")))
    output_dir: Path = Field(default_factory=lambda: Path(os.getenv("SOURCING1688_OUTPUT_DIR") or home_path("assets")))
    browser_profile: str | None = Field(default_factory=lambda: os.getenv("SOURCING1688_BROWSER_PROFILE") or str(home_path("browser-profile")))
    rate_limit_seconds: float = Field(default_factory=lambda: float(os.getenv("SOURCING1688_RATE_LIMIT_SECONDS", "2")))
    max_pages: int = Field(default_factory=lambda: int(os.getenv("SOURCING1688_MAX_PAGES", "3")))
    ali1688_app_key: str | None = Field(default_factory=lambda: os.getenv("ALI1688_APP_KEY") or None)
    ali1688_app_secret: str | None = Field(default_factory=lambda: os.getenv("ALI1688_APP_SECRET") or None)
    ali1688_refresh_token: str | None = Field(default_factory=lambda: os.getenv("ALI1688_REFRESH_TOKEN") or None)
    ali1688_access_token: str | None = Field(default_factory=lambda: os.getenv("ALI1688_ACCESS_TOKEN") or None)
    ali1688_token_cache_path: Path = Field(default_factory=lambda: Path(os.getenv("ALI1688_TOKEN_CACHE_PATH") or home_path("token-cache", ".1688_token_cache.json")))
    ali1688_api_base: str = Field(default_factory=lambda: os.getenv("ALI1688_API_BASE", "https://gw.open.1688.com/openapi/param2/1"))
    browser_headless: bool = Field(default_factory=lambda: os.getenv("SOURCING1688_BROWSER_HEADLESS", "false").lower() in {"1", "true", "yes"})
    live_smoke: bool = Field(default_factory=lambda: os.getenv("SOURCING1688_LIVE_SMOKE", "false").lower() in {"1", "true", "yes"})


def get_settings() -> Settings:
    return Settings()
