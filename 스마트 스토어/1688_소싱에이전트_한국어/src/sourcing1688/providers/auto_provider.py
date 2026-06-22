from __future__ import annotations

from pathlib import Path
from typing import Any

from sourcing1688.config import Settings, get_settings
from sourcing1688 import __version__
from sourcing1688.models import (
    AssetDownloadResponse,
    DetailResponse,
    HotKeywordsResponse,
    ImageSearchResponse,
    ProviderCapability,
    RankingsResponse,
    SearchResponse,
)
from sourcing1688.providers.api_auth import ApiAuthManager
from sourcing1688.providers.api_provider import Api1688Provider
from sourcing1688.providers.base import Base1688Provider
from sourcing1688.utils import structured_error


PROVIDER_VERSION = __version__


class Auto1688Provider(Base1688Provider):
    """Resolve to API when available; never launch a managed browser implicitly."""

    name = "auto"
    provider_version = PROVIDER_VERSION
    source_type = "auto"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def capabilities(self) -> ProviderCapability:
        return ProviderCapability(
            provider=self.name,
            provider_version=self.provider_version,
            source_type="auto",
            live_verified=False,
            search=True,
            detail=True,
            download_assets=True,
            hot_keywords=True,
            rankings=True,
            image_search=True,
            required_env=["Chrome DevTools MCP connection"],
            notes=[
                "Use Chrome DevTools page/network capture for non-API live 1688 pages.",
                "Does not launch the managed browser provider implicitly.",
            ],
        )

    def resolve(self) -> Base1688Provider | None:
        if ApiAuthManager(self.settings).has_any_credentials():
            return Api1688Provider(settings=self.settings)
        return None

    def _missing_live_provider(self, response_type):
        message = "Auto search needs a live 1688 data source from Chrome DevTools page/network capture."
        suggested_action = "Use Chrome DevTools to open the 1688 page, capture rendered HTML/network JSON, then parse it with sourcing1688 tools. If Chrome DevTools cannot connect, call open_chrome_devtools_setup."
        return response_type(
            status="provider_unavailable",
            message=message,
            suggested_action=suggested_action,
            error=structured_error("chrome_devtools_required", message, suggested_action=suggested_action),
            provider=self.name,
            provider_version=self.provider_version,
            source_type="auto",
            live_verified=False,
        )

    async def search_products(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 30,
        sort: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> SearchResponse:
        provider = self.resolve()
        if provider is None:
            response = self._missing_live_provider(SearchResponse)
            response.keyword = keyword
            return response
        return await provider.search_products(keyword, page=page, page_size=page_size, sort=sort, filters=filters)

    async def get_product_detail(self, offer_id_or_url: str) -> DetailResponse:
        provider = self.resolve()
        if provider is None:
            return self._missing_live_provider(DetailResponse)
        return await provider.get_product_detail(offer_id_or_url)

    async def download_product_assets(
        self,
        offer_id_or_url: str,
        output_dir: str | Path,
        include: str | set[str] | list[str] | None = None,
        dry_run: bool = False,
    ) -> AssetDownloadResponse:
        provider = self.resolve()
        if provider is None:
            return self._missing_live_provider(AssetDownloadResponse)
        return await provider.download_product_assets(offer_id_or_url, output_dir, include=include, dry_run=dry_run)

    async def get_hot_keywords(self, category_id: str | None = None, limit: int = 20) -> HotKeywordsResponse:
        provider = self.resolve()
        if provider is None:
            return self._missing_live_provider(HotKeywordsResponse)
        return await provider.get_hot_keywords(category_id=category_id, limit=limit)

    async def get_rankings(self, category_id: str | None = None, rank_type: str = "hot", limit: int = 20) -> RankingsResponse:
        provider = self.resolve()
        if provider is None:
            return self._missing_live_provider(RankingsResponse)
        return await provider.get_rankings(category_id=category_id, rank_type=rank_type, limit=limit)

    async def image_search(
        self,
        image_url: str | None = None,
        image_path: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ImageSearchResponse:
        provider = self.resolve()
        if provider is None:
            return self._missing_live_provider(ImageSearchResponse)
        return await provider.image_search(image_url=image_url, image_path=image_path, page=page, page_size=page_size)


class ChromeDevtools1688Provider(Auto1688Provider):
    """Explicit Chrome DevTools route. It never falls back to API credentials."""

    name = "chrome-devtools"
    source_type = "browser"

    def capabilities(self) -> ProviderCapability:
        capability = super().capabilities()
        capability.provider = self.name
        capability.source_type = "browser"
        capability.notes = ["Use Chrome DevTools page/network capture from the user's existing Chrome tabs."]
        return capability

    def resolve(self) -> Base1688Provider | None:
        return None
