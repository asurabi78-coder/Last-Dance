from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from sourcing1688.config import get_settings
from sourcing1688.keyword_expander import expand_keywords
from sourcing1688.models import (
    AssetDownloadResponse,
    DetailResponse,
    ImageSearchResponse,
    ProductSearchResult,
    ProviderCapabilitiesResponse,
    Recommendation,
    RecommendationResponse,
    SearchResponse,
)
from sourcing1688.providers.api_provider import Api1688Provider
from sourcing1688.providers.auto_provider import Auto1688Provider, ChromeDevtools1688Provider
from sourcing1688.providers.base import Base1688Provider
from sourcing1688.providers.browser_provider import Browser1688Provider
from sourcing1688.providers.local_html_provider import LocalHtml1688Provider
from sourcing1688.scoring import score_product
from sourcing1688.storage import SourcingStorage
from sourcing1688.utils import extract_offer_id, structured_error


CHROME_DEVTOOLS_ALIASES = {"1688", "sourcing1688", "sourcing-agent-1688", "chrome", "chrome-devtools", "chrome_devtools", "devtools"}


def normalize_provider_name(provider_name: str | None = None) -> str:
    selected = (provider_name or get_settings().provider or "auto").lower()
    if selected in CHROME_DEVTOOLS_ALIASES:
        return "chrome-devtools"
    return selected


def get_provider(provider_name: str | None = None) -> Base1688Provider:
    settings = get_settings()
    selected = normalize_provider_name(provider_name)
    if selected == "auto":
        return Auto1688Provider(settings=settings)
    if selected == "chrome-devtools":
        return ChromeDevtools1688Provider(settings=settings)
    if selected == "api":
        return Api1688Provider(settings=settings)
    if selected == "browser":
        return Browser1688Provider(settings=settings)
    if selected in {"local_html", "local-html", "html"}:
        return LocalHtml1688Provider()
    raise ValueError(f"Unknown provider: {selected}")


def provider_names() -> list[str]:
    return ["auto", "api", "browser", "local_html"]


def get_all_provider_capabilities() -> ProviderCapabilitiesResponse:
    providers = {name: get_provider(name).capabilities() for name in provider_names()}
    return ProviderCapabilitiesResponse(status="ok", providers=providers)


def _missing_api_env(settings) -> list[str]:
    missing = []
    if not settings.ali1688_app_key:
        missing.append("ALI1688_APP_KEY")
    if not settings.ali1688_app_secret:
        missing.append("ALI1688_APP_SECRET")
    if not (settings.ali1688_refresh_token or settings.ali1688_access_token):
        missing.append("ALI1688_REFRESH_TOKEN or ALI1688_ACCESS_TOKEN")
    return missing


def check_provider(provider_name: str) -> dict[str, Any]:
    requested = provider_name.lower()
    selected = normalize_provider_name(requested)
    provider = get_provider(selected)
    capability = provider.capabilities()
    payload = capability.model_dump(mode="json")
    payload.update({"status": "ok", "ready": True, "capabilities": capability.model_dump(mode="json")})
    settings = get_settings()

    if selected == "api":
        missing_env = _missing_api_env(settings)
        if missing_env:
            message = "1688 API credentials are not configured."
            payload.update(
                {
                    "status": "missing_credentials",
                    "ready": False,
                    "missing_env": missing_env,
                    "suggested_action": "Set API credentials, use provider=browser with a logged-in browser profile, or use provider=local_html for saved product pages.",
                    "error": structured_error("missing_credentials", message, suggested_action="Set API credentials, use provider=browser, or use provider=local_html.").model_dump(mode="json"),
                }
            )
        else:
            payload.update({"status": "live_not_verified", "ready": True, "missing_env": [], "suggested_action": "Run an opt-in live smoke test before treating results as verified."})
    elif selected == "browser":
        profile = settings.browser_profile
        if not profile:
            message = "SOURCING1688_BROWSER_PROFILE is not configured."
            payload.update(
                {
                    "status": "needs_human_login",
                    "ready": False,
                    "missing_env": ["SOURCING1688_BROWSER_PROFILE"],
                    "suggested_action": "Run `sourcing1688 browser-profile open --json`, log in to 1688 manually, close the browser, then retry.",
                    "error": structured_error("needs_human_login", message, needs_human_action=True, suggested_action="Open and log in with a human-managed browser profile.").model_dump(mode="json"),
                }
            )
        elif not Path(profile).exists():
            message = "Configured browser profile path does not exist."
            payload.update(
                {
                    "status": "needs_human_login",
                    "ready": False,
                    "profile_path": profile,
                    "suggested_action": "Run `sourcing1688 browser-profile open --json`, log in to 1688 manually, close the browser, then retry.",
                    "error": structured_error("needs_human_login", message, needs_human_action=True, suggested_action="Open and log in with a human-managed browser profile.").model_dump(mode="json"),
                }
            )
        else:
            payload.update(
                {
                    "status": "live_not_verified",
                    "ready": False,
                    "profile_path": profile,
                    "suggested_action": "Run an opt-in browser profile check or live smoke test; do not assume login is valid yet.",
                    "error": structured_error("live_not_verified", "Browser profile exists, but login/verification state was not checked.").model_dump(mode="json"),
                }
            )
    elif selected in {"auto", "chrome-devtools"}:
        missing_env = _missing_api_env(settings)
        if selected == "auto" and not missing_env:
            payload.update({"status": "live_not_verified", "ready": True, "selected_provider": "api", "suggested_action": "Run an opt-in live smoke test before treating API results as verified."})
        else:
            message = "Chrome DevTools provider needs page/network capture for live 1688 data." if selected == "chrome-devtools" else "Auto provider needs Chrome DevTools page/network capture for live 1688 data."
            payload.update(
                {
                    "status": "provider_unavailable",
                    "ready": False,
                    "selected_provider": "chrome-devtools",
                    "missing_env": [],
                    "suggested_action": "Use Chrome DevTools to open the 1688 page and capture rendered HTML/network JSON. If Chrome DevTools reports DevToolsActivePort, call open_chrome_devtools_setup first.",
                    "error": structured_error(
                        "chrome_devtools_required",
                        message,
                        suggested_action="Use Chrome DevTools page/network capture, or call open_chrome_devtools_setup for first-run setup.",
                    ).model_dump(mode="json"),
                }
            )
        if selected == "chrome-devtools":
            payload.update({"provider": "chrome-devtools", "selected_provider": "chrome-devtools", "requested_provider": requested, "capabilities": payload["capabilities"] | {"provider": "chrome-devtools", "source_type": "browser"}})
    return payload


def _provider_metadata(provider: Base1688Provider) -> dict[str, Any]:
    capability = provider.capabilities()
    return {
        "provider": provider.name,
        "provider_version": provider.provider_version,
        "source_type": provider.source_type,
        "live_verified": capability.live_verified,
    }


def has_hangul(value: str) -> bool:
    return bool(re.search(r"[\uac00-\ud7a3]", value))


def _dedupe_results(items: list[ProductSearchResult]) -> list[ProductSearchResult]:
    deduped: dict[str, ProductSearchResult] = {}
    for item in items:
        deduped.setdefault(item.offer_id, item)
    return list(deduped.values())


async def search_sourcing_products(
    keyword: str,
    *,
    top: int = 30,
    page: int = 1,
    provider_name: str | None = None,
    page_size: int | None = None,
    sort: str | None = None,
    filters: dict[str, Any] | None = None,
) -> SearchResponse:
    provider = get_provider(provider_name)
    expansion = expand_keywords(keyword) if has_hangul(keyword) else None
    if expansion and not expansion.keywords:
        return SearchResponse(
            status="partial_data",
            message="No built-in Chinese seed terms matched this Korean keyword. A Codex agent should generate Chinese 1688 sourcing terms from the user intent and then search live Chrome results.",
            suggested_action=expansion.agent_instruction,
            keyword=keyword,
            expanded_keywords=expansion.keywords,
            keyword_expansion=expansion,
            warnings=expansion.warnings,
            **_provider_metadata(provider),
        )
    keywords = expansion.keywords if expansion and expansion.keywords else [keyword]
    all_items: list[ProductSearchResult] = []
    first_blocked: SearchResponse | None = None
    first_empty_partial: SearchResponse | None = None
    for source_keyword in keywords:
        response = await provider.search_products(
            source_keyword,
            page=page,
            page_size=page_size or top,
            sort=sort,
            filters=filters,
        )
        if response.status not in {"ok", "partial_data"}:
            first_blocked = first_blocked or response
            continue
        if not response.items:
            first_empty_partial = first_empty_partial or response
            continue
        all_items.extend(response.items)
        if len(_dedupe_results(all_items)) >= top:
            break
    if not all_items and first_blocked:
        first_blocked.keyword = keyword
        if expansion:
            first_blocked.expanded_keywords = expansion.keywords
            first_blocked.keyword_expansion = expansion
        return first_blocked
    if not all_items and first_empty_partial:
        first_empty_partial.keyword = keyword
        if expansion:
            first_empty_partial.expanded_keywords = expansion.keywords
            first_empty_partial.keyword_expansion = expansion
        return first_empty_partial
    return SearchResponse(
        status="ok",
        items=_dedupe_results(all_items)[:top],
        keyword=keyword,
        expanded_keywords=expansion.keywords if expansion else [],
        keyword_expansion=expansion,
        **_provider_metadata(provider),
    )


async def analyze_product_url(url: str, *, provider_name: str | None = None) -> dict[str, Any]:
    offer_id = extract_offer_id(url)
    provider = get_provider(provider_name)
    detail_response = await provider.get_product_detail(offer_id)
    if detail_response.item is None:
        return detail_response.model_dump(mode="json")
    score = score_product(detail_response.item)
    return {
        "status": detail_response.status,
        "offer_id": offer_id,
        "provider": provider.name,
        "provider_version": provider.provider_version,
        "source_type": provider.source_type,
        "live_verified": provider.capabilities().live_verified,
        "detail": detail_response.item.model_dump(mode="json"),
        "score": score.model_dump(mode="json"),
    }


async def get_product_detail(offer_id_or_url: str, *, provider_name: str | None = None) -> DetailResponse:
    provider = get_provider(provider_name)
    return await provider.get_product_detail(offer_id_or_url)


async def download_product_assets(
    offer_id_or_url: str,
    output_dir: str | Path,
    *,
    include: str | set[str] | list[str] | None = None,
    provider_name: str | None = None,
    dry_run: bool = False,
) -> AssetDownloadResponse:
    provider = get_provider(provider_name)
    return await provider.download_product_assets(offer_id_or_url, output_dir, include=include, dry_run=dry_run)


async def image_search_products(
    *,
    image_url: str | None = None,
    image_path: str | None = None,
    provider_name: str | None = None,
    top: int = 20,
) -> ImageSearchResponse:
    provider = get_provider(provider_name)
    return await provider.image_search(image_url=image_url, image_path=image_path, page_size=top)


async def recommend_products(
    keyword: str,
    *,
    top: int = 10,
    save: bool = False,
    provider_name: str | None = None,
    project: str | None = None,
) -> RecommendationResponse:
    provider = get_provider(provider_name)
    expansion = expand_keywords(keyword)
    search_response = await search_sourcing_products(keyword, top=max(top * 3, top), provider_name=provider.name)
    if search_response.status not in {"ok", "partial_data"}:
        return RecommendationResponse(
            status=search_response.status,
            message=search_response.message,
            needs_human_action=search_response.needs_human_action,
            suggested_action=search_response.suggested_action,
            error=search_response.error,
            keyword=keyword,
            expanded_keywords=expansion.keywords,
            **_provider_metadata(provider),
        )
    if not search_response.items:
        return RecommendationResponse(
            status=search_response.status,
            message=search_response.message,
            suggested_action=search_response.suggested_action,
            keyword=keyword,
            expanded_keywords=expansion.keywords,
            warnings=search_response.warnings,
            **_provider_metadata(provider),
        )

    recommendations = [
        Recommendation(product=item, score=score_product(item))
        for item in search_response.items
    ]
    recommendations.sort(key=lambda item: (item.score.score, item.score.confidence), reverse=True)
    recommendations = recommendations[:top]

    if save:
        storage = SourcingStorage(get_settings().db_path)
        project_name = project or keyword
        storage.save_search_results(project_name, keyword, [item.product for item in recommendations])
        for item in recommendations:
            storage.save_sourcing_score(item.score)
        storage.close()

    return RecommendationResponse(
        status="ok",
        keyword=keyword,
        expanded_keywords=expansion.keywords,
        items=recommendations,
        **_provider_metadata(provider),
        saved=save,
    )
