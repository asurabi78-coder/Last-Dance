from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sourcing1688 import __version__
from sourcing1688.assets.downloader import download_assets
from sourcing1688.config import Settings, get_settings
from sourcing1688.models import (
    AssetDownloadResponse,
    DetailResponse,
    HotKeywordsResponse,
    ImageSearchResponse,
    ProductSearchResult,
    ProviderCapability,
    RankingsResponse,
    SearchResponse,
)
from sourcing1688.parsers.rendered_html import PARSER_VERSION, parse_rendered_html
from sourcing1688.providers.base import Base1688Provider
from sourcing1688.providers.selectors import BROWSER_SELECTORS
from sourcing1688.state import runtime_paths
from sourcing1688.utils import encode_1688_search_keyword, extract_offer_id, structured_error


PROVIDER_VERSION = __version__


class Browser1688Provider(Base1688Provider):
    """Playwright persistent-profile provider with no verification bypass."""

    name = "browser"
    provider_version = PROVIDER_VERSION
    source_type = "browser"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def capabilities(self) -> ProviderCapability:
        return ProviderCapability(
            provider=self.name,
            provider_version=self.provider_version,
            source_type="browser",
            live_verified=False,
            search=True,
            detail=True,
            download_assets=True,
            hot_keywords=True,
            rankings=True,
            image_search=False,
            required_env=["SOURCING1688_BROWSER_PROFILE optional; defaults to SOURCING1688_HOME/browser-profile"],
            notes=["Uses a human-managed Playwright persistent profile. If the profile is missing, open it with `sourcing1688 browser-profile open --json` and log in manually."],
        )

    def detect_block_state_from_text(self, url: str, title: str, html: str) -> tuple[str | None, str | None]:
        combined = f"{url}\n{title}\n{html}"
        lowered = combined.lower()
        if any(marker.lower() in lowered for marker in BROWSER_SELECTORS["verification_markers"]):
            return "blocked_by_verification", "1688 verification page detected"
        if any(marker.lower() in lowered for marker in BROWSER_SELECTORS["login_markers"]):
            return "needs_human_login", "1688 login page detected"
        return None, None

    async def _detect_block_state(self, page) -> tuple[str | None, str | None]:
        return self.detect_block_state_from_text(page.url, await page.title(), (await page.content())[:20000])

    def _profile_missing(self, response_type):
        if self.settings.browser_profile:
            message = "Browser profile path does not exist yet."
        else:
            message = "Browser profile path is not configured."
        suggested_action = "Run `sourcing1688 browser-profile open --json`, log in to 1688 manually in the opened browser, close the browser, then retry."
        return response_type(
            status="needs_human_login",
            message=message,
            needs_human_action=True,
            suggested_action=suggested_action,
            error=structured_error("needs_human_login", message, needs_human_action=True, suggested_action=suggested_action),
            provider=self.name,
            provider_version=self.provider_version,
            source_type="browser",
            live_verified=False,
            fetched_at=datetime.now(timezone.utc),
        )

    async def check_profile(self, live: bool = False) -> dict[str, Any]:
        if not self.settings.browser_profile:
            response = self._profile_missing(SearchResponse)
            payload = response.model_dump(mode="json")
            payload["ready"] = False
            return payload
        path = Path(self.settings.browser_profile)
        has_files = path.exists() and any(path.iterdir()) if path.exists() else False
        if not path.exists():
            response = self._profile_missing(SearchResponse)
            payload = response.model_dump(mode="json")
            payload.update({"ready": False, "profile_path": str(path), "exists": False, "profile_has_files": False})
            return payload
        if not live:
            return {
                "status": "live_not_verified",
                "provider": self.name,
                "provider_version": self.provider_version,
                "source_type": "browser",
                "live_verified": False,
                "ready": False,
                "profile_path": str(path),
                "exists": True,
                "profile_has_files": has_files,
                "headless": self.settings.browser_headless,
                "message": "Profile exists, but login/verification state has not been checked live.",
            }
        browser_state, error = await self._with_page("https://www.1688.com")
        if error:
            payload = error.model_dump(mode="json")
            payload["ready"] = False
            return payload
        playwright, context, page_obj, url = browser_state
        try:
            await page_obj.goto(url, wait_until="domcontentloaded", timeout=45000)
            status, message = await self._detect_block_state(page_obj)
            if status:
                return {"status": status, "provider": self.name, "provider_version": self.provider_version, "source_type": "browser", "live_verified": False, "ready": False, "profile_path": str(path), "exists": True, "profile_has_files": has_files, "message": message, "error": structured_error(status, message or status, needs_human_action=True).model_dump(mode="json")}
            return {"status": "live_not_verified", "provider": self.name, "provider_version": self.provider_version, "source_type": "browser", "live_verified": False, "ready": False, "profile_path": str(path), "exists": True, "profile_has_files": has_files, "message": "Browser opened 1688, but this check does not prove product pages/API are live verified."}
        finally:
            await context.close()
            await playwright.stop()

    async def _with_page(self, url: str):
        from playwright.async_api import async_playwright

        if not self.settings.browser_profile:
            return None, self._profile_missing(DetailResponse)
        profile = Path(self.settings.browser_profile)
        if not profile.exists():
            return None, self._profile_missing(DetailResponse)
        playwright = await async_playwright().start()
        context = await playwright.chromium.launch_persistent_context(
            str(profile),
            headless=self.settings.browser_headless,
            viewport={"width": 1365, "height": 900},
        )
        page = context.pages[0] if context.pages else await context.new_page()
        return (playwright, context, page, url), None

    def _raw_snapshot_path(self, prefix: str) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        raw_dir = runtime_paths(self.settings)["raw"] / stamp
        raw_dir.mkdir(parents=True, exist_ok=True)
        return raw_dir / f"{prefix}.html"

    async def search_products(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 30,
        sort: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> SearchResponse:
        if not self.settings.browser_profile:
            return self._profile_missing(SearchResponse)
        encoded_keyword = encode_1688_search_keyword(keyword)
        browser_state, error = await self._with_page(f"https://s.1688.com/selloffer/offer_search.htm?keywords={encoded_keyword}&beginPage={page}")
        if error:
            return self._profile_missing(SearchResponse)
        playwright, context, page_obj, url = browser_state
        try:
            await asyncio.sleep(self.settings.rate_limit_seconds)
            await page_obj.goto(url, wait_until="domcontentloaded", timeout=45000)
            status, message = await self._detect_block_state(page_obj)
            html = await page_obj.content()
            snapshot_path = self._raw_snapshot_path("search")
            snapshot_path.write_text(html, encoding="utf-8")
            if status:
                suggested_action = "Complete the login or verification manually in the browser profile, then retry. No bypass is attempted."
                return SearchResponse(status=status, message=message, needs_human_action=status != "provider_unavailable", suggested_action=suggested_action, error=structured_error(status, message or status, needs_human_action=status != "provider_unavailable", suggested_action=suggested_action), provider=self.name, provider_version=self.provider_version, source_type="browser", live_verified=False, raw_reference_path=str(snapshot_path), keyword=keyword)
            items = self._parse_search_dom(html, keyword, page_size)
            message = None if items else "Browser opened 1688, but no product cards were parsed. Login may be incomplete, verification may be required, or the 1688 page structure may have changed."
            return SearchResponse(status="ok" if items else "partial_data", message=message, items=items, keyword=keyword, provider=self.name, provider_version=self.provider_version, source_type="browser", live_verified=False, raw_reference_path=str(snapshot_path), warnings=["Browser search parser is implemented but live result structure is not verified in this environment."])
        finally:
            await context.close()
            await playwright.stop()

    def _parse_search_dom(self, html: str, keyword: str, limit: int) -> list[ProductSearchResult]:
        import re
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        items: list[ProductSearchResult] = []
        seen_offer_ids: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            href = str(anchor["href"])
            if "offer" not in href.lower():
                continue
            try:
                offer_id = extract_offer_id(href)
            except ValueError:
                continue
            if offer_id in seen_offer_ids:
                continue
            seen_offer_ids.add(offer_id)
            title = anchor.get_text(" ", strip=True) or anchor.get("title") or f"1688 offer {offer_id}"
            image = None
            parent = anchor.parent
            if parent:
                img = parent.find("img")
                if img:
                    image = img.get("src") or img.get("data-src")
                    if image and str(image).startswith("//"):
                        image = f"https:{image}"
            items.append(ProductSearchResult(offer_id=offer_id, url=f"https://detail.1688.com/offer/{offer_id}.html", title_zh=title, image_url=image, source_keyword=keyword, provider=self.name, provider_version=self.provider_version, source_type="browser", live_verified=False, warnings=["DOM parsed; fields may be partial."]))
            if len(items) >= limit:
                break
        return items

    async def get_product_detail(self, offer_id_or_url: str) -> DetailResponse:
        if not self.settings.browser_profile:
            return self._profile_missing(DetailResponse)
        try:
            offer_id = extract_offer_id(offer_id_or_url)
        except ValueError as exc:
            return DetailResponse(status="error", message=str(exc), error=structured_error("invalid_offer_id", str(exc)), provider=self.name)
        url = f"https://detail.1688.com/offer/{offer_id}.html"
        browser_state, error = await self._with_page(url)
        if error:
            return self._profile_missing(DetailResponse)
        playwright, context, page_obj, _ = browser_state
        try:
            await asyncio.sleep(self.settings.rate_limit_seconds)
            await page_obj.goto(url, wait_until="domcontentloaded", timeout=45000)
            status, message = await self._detect_block_state(page_obj)
            html = await page_obj.content()
            snapshot_path = self._raw_snapshot_path(f"detail-{offer_id}")
            snapshot_path.write_text(html, encoding="utf-8")
            if status:
                suggested_action = "Complete the login or verification manually in the browser profile, then retry. No bypass is attempted."
                return DetailResponse(status=status, message=message, needs_human_action=True, suggested_action=suggested_action, error=structured_error(status, message or status, needs_human_action=True, suggested_action=suggested_action), provider=self.name, provider_version=self.provider_version, source_type="browser", live_verified=False, raw_reference_path=str(snapshot_path))
            try:
                parsed = parse_rendered_html(html, source_path=snapshot_path)
            except Exception as exc:  # noqa: BLE001
                message = "Rendered HTML parser failed while extracting product detail."
                return DetailResponse(
                    status="partial_data",
                    message=message,
                    needs_human_action=False,
                    suggested_action="Use the saved raw_reference_path HTML for parser debugging, then retry after updating the parser.",
                    error=structured_error(
                        "parser_error",
                        f"{message} {exc}",
                        details={"raw_reference_path": str(snapshot_path), "exception_type": type(exc).__name__},
                    ),
                    provider=self.name,
                    provider_version=self.provider_version,
                    source_type="browser",
                    live_verified=False,
                    raw_reference_path=str(snapshot_path),
                    warnings=["Browser detail HTML was saved, but parser extraction failed."],
                )
            if parsed.item:
                parsed.item.provider = self.name
                parsed.item.provider_version = self.provider_version
                parsed.item.source_type = "browser"
                parsed.item.live_verified = False
            parsed.provider = self.name
            parsed.provider_version = self.provider_version
            parsed.source_type = "browser"
            parsed.live_verified = False
            parsed.raw_reference_path = str(snapshot_path)
            parsed.warnings.append("Browser detail parser is implemented but live 1688 rendering was not verified in this environment.")
            return parsed
        finally:
            await context.close()
            await playwright.stop()

    async def download_product_assets(
        self,
        offer_id_or_url: str,
        output_dir: str | Path,
        include: str | set[str] | list[str] | None = None,
        dry_run: bool = False,
    ) -> AssetDownloadResponse:
        detail_response = await self.get_product_detail(offer_id_or_url)
        if detail_response.item is None:
            return AssetDownloadResponse(status=detail_response.status, message=detail_response.message, error=detail_response.error, provider=self.name, provider_version=self.provider_version, source_type="browser", live_verified=False)
        html = Path(detail_response.raw_reference_path).read_text(encoding="utf-8") if detail_response.raw_reference_path else None
        manifest = await download_assets(detail_response.item, output_dir, include=include, html=html, source_url=detail_response.item.url, raw_html_path=detail_response.raw_reference_path, parser_version=PARSER_VERSION, dry_run=dry_run)
        return AssetDownloadResponse(status=manifest.status, manifest=manifest, manifest_path=str(Path(manifest.saved_dir) / "manifest.json"), provider=self.name, provider_version=self.provider_version, source_type="browser", live_verified=False)

    async def get_hot_keywords(self, category_id: str | None = None, limit: int = 20) -> HotKeywordsResponse:
        message = "Browser hot keyword extraction is live-capable only when a reachable ranking page/XHR is identified; this environment has not verified it."
        return HotKeywordsResponse(status="live_not_verified", message=message, error=structured_error("live_not_verified", message), provider=self.name, provider_version=self.provider_version, source_type="browser", live_verified=False)

    async def get_rankings(self, category_id: str | None = None, rank_type: str = "hot", limit: int = 20) -> RankingsResponse:
        message = "Browser ranking extraction is live-capable only when a reachable ranking page/XHR is identified; this environment has not verified it."
        return RankingsResponse(status="live_not_verified", message=message, error=structured_error("live_not_verified", message), provider=self.name, provider_version=self.provider_version, source_type="browser", live_verified=False)

    async def image_search(self, image_url: str | None = None, image_path: str | None = None, page: int = 1, page_size: int = 20) -> ImageSearchResponse:
        message = "Browser image search is not implemented because the live workflow is uncertain and must not bypass upload/verification controls."
        return ImageSearchResponse(status="provider_unavailable", message=message, error=structured_error("provider_unavailable", message), provider=self.name, provider_version=self.provider_version, source_type="browser", live_verified=False)
