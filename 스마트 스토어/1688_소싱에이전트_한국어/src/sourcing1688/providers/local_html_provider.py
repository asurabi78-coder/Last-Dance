from __future__ import annotations

from pathlib import Path
from typing import Any

from sourcing1688.assets.downloader import download_assets
from sourcing1688.models import (
    AssetDownloadResponse,
    DetailResponse,
    HotKeywordsResponse,
    ProviderCapability,
    RankingsResponse,
    SearchResponse,
)
from sourcing1688.parsers.rendered_html import PARSER_VERSION, parse_rendered_html_file
from sourcing1688.providers.base import Base1688Provider
from sourcing1688.utils import structured_error


class LocalHtml1688Provider(Base1688Provider):
    name = "local_html"
    provider_version = PARSER_VERSION
    source_type = "local_html"

    def capabilities(self) -> ProviderCapability:
        return ProviderCapability(
            provider=self.name,
            provider_version=self.provider_version,
            source_type="local_html",
            live_verified=False,
            detail=True,
            download_assets=True,
            parse_rendered_html=True,
            notes=["Parses local rendered or SingleFile-style 1688 detail HTML. It does not perform live network search."],
        )

    async def search_products(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 30,
        sort: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> SearchResponse:
        message = "local_html provider only parses local rendered product detail HTML files."
        return SearchResponse(status="provider_unavailable", message=message, error=structured_error("provider_unavailable", message), provider=self.name, provider_version=self.provider_version, source_type="local_html", live_verified=False)

    async def get_product_detail(self, offer_id_or_url: str) -> DetailResponse:
        path = Path(offer_id_or_url)
        if not path.exists():
            message = "local_html provider expects a path to a rendered HTML file."
            return DetailResponse(status="provider_unavailable", message=message, error=structured_error("provider_unavailable", message), provider=self.name, provider_version=self.provider_version, source_type="local_html", live_verified=False)
        return parse_rendered_html_file(path)

    async def download_product_assets(
        self,
        offer_id_or_url: str,
        output_dir: str | Path,
        include: str | set[str] | list[str] | None = None,
        dry_run: bool = False,
    ) -> AssetDownloadResponse:
        detail_response = await self.get_product_detail(offer_id_or_url)
        if detail_response.item is None:
            return AssetDownloadResponse(status=detail_response.status, message=detail_response.message, error=detail_response.error, provider=self.name, provider_version=self.provider_version, source_type="local_html", live_verified=False)
        html_path = Path(offer_id_or_url)
        manifest = await download_assets(
            detail_response.item,
            output_dir,
            include=include,
            html=html_path.read_text(encoding="utf-8"),
            source_url=detail_response.item.url,
            raw_html_path=str(html_path),
            parser_version=PARSER_VERSION,
            dry_run=dry_run,
        )
        return AssetDownloadResponse(status=manifest.status, manifest=manifest, manifest_path=str(Path(manifest.saved_dir) / "manifest.json"), provider=self.name, provider_version=self.provider_version, source_type="local_html", live_verified=False)

    async def get_hot_keywords(self, category_id: str | None = None, limit: int = 20) -> HotKeywordsResponse:
        message = "local_html provider does not provide hot keyword data."
        return HotKeywordsResponse(status="provider_unavailable", message=message, error=structured_error("provider_unavailable", message), provider=self.name, provider_version=self.provider_version, source_type="local_html", live_verified=False)

    async def get_rankings(self, category_id: str | None = None, rank_type: str = "hot", limit: int = 20) -> RankingsResponse:
        message = "local_html provider does not provide ranking data."
        return RankingsResponse(status="provider_unavailable", message=message, error=structured_error("provider_unavailable", message), provider=self.name, provider_version=self.provider_version, source_type="local_html", live_verified=False)
