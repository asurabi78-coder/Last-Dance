from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from sourcing1688.models import AssetDownloadResponse, DetailResponse, HotKeywordsResponse, ImageSearchResponse, ProviderCapability, RankingsResponse, SearchResponse


class Base1688Provider(ABC):
    name: str = "base"
    provider_version: str = "0.1.0"
    source_type: str = "base"

    def capabilities(self) -> ProviderCapability:
        return ProviderCapability(provider=self.name, provider_version=self.provider_version, source_type=self.source_type)  # type: ignore[arg-type]

    @abstractmethod
    async def search_products(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 30,
        sort: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> SearchResponse:
        raise NotImplementedError

    @abstractmethod
    async def get_product_detail(self, offer_id_or_url: str) -> DetailResponse:
        raise NotImplementedError

    @abstractmethod
    async def download_product_assets(
        self,
        offer_id_or_url: str,
        output_dir: str | Path,
        include: str | set[str] | list[str] | None = None,
        dry_run: bool = False,
    ) -> AssetDownloadResponse:
        raise NotImplementedError

    @abstractmethod
    async def get_hot_keywords(self, category_id: str | None = None, limit: int = 20) -> HotKeywordsResponse:
        raise NotImplementedError

    @abstractmethod
    async def get_rankings(
        self,
        category_id: str | None = None,
        rank_type: str = "hot",
        limit: int = 20,
    ) -> RankingsResponse:
        raise NotImplementedError

    async def image_search(self, image_url: str | None = None, image_path: str | None = None, page: int = 1, page_size: int = 20) -> ImageSearchResponse:
        return ImageSearchResponse(
            status="provider_unavailable",
            message=f"{self.name} provider does not implement image search.",
            provider=self.name,
            provider_version=self.provider_version,
            source_type=self.source_type,  # type: ignore[arg-type]
        )
