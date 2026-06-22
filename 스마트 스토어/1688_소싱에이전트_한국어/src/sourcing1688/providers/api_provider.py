from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from sourcing1688 import __version__
from sourcing1688.assets.downloader import download_assets
from sourcing1688.config import Settings, get_settings
from sourcing1688.models import (
    AssetDownloadResponse,
    DetailResponse,
    HotKeyword,
    HotKeywordsResponse,
    ImageSearchResponse,
    PriceTier,
    ProductDetail,
    ProductSearchResult,
    ProviderCapability,
    RankingItem,
    RankingsResponse,
    SearchResponse,
    SellerInfo,
    SkuOption,
)
from sourcing1688.providers.api_auth import ApiAuthManager
from sourcing1688.providers.base import Base1688Provider
from sourcing1688.utils import extract_offer_id, structured_error


PROVIDER_VERSION = __version__

ENDPOINTS = {
    "keyword_search": "com.alibaba.fenxiao.crossborder/product.search.keywordQuery",
    "image_search": "com.alibaba.fenxiao.crossborder/product.search.imageQuery",
    "detail": "com.alibaba.fenxiao.crossborder/product.search.queryProductDetail",
    "seller_offer_list": "com.alibaba.fenxiao.crossborder/product.search.querySellerOfferList",
    "offer_recommend": "com.alibaba.fenxiao.crossborder/product.search.offerRecommend",
    "related_recommend": "com.alibaba.fenxiao.crossborder/product.related.recommend",
    "ranking": "com.alibaba.fenxiao.crossborder/product.topList.query",
    "hot_keywords": "com.alibaba.fenxiao.crossborder/product.search.topKeyword",
    "category": "com.alibaba.fenxiao.crossborder/category.translation.getById",
}

SUPPORTED_FILTERS = {"shipIn24Hours", "shipIn48Hours", "certifiedFactory", "isOnePsale", "new7", "1688Selection"}
SUPPORTED_SORTS = {"price", "rePurchaseRate", "monthSold"}


def _as_result_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = payload.get("result", payload)
    if isinstance(result, dict):
        nested = result.get("result") or result.get("data") or result.get("items")
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        if isinstance(nested, dict):
            nested_items = nested.get("items") or nested.get("list") or nested.get("result")
            if isinstance(nested_items, list):
                return [item for item in nested_items if isinstance(item, dict)]
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    return []


def _as_result_dict(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result", payload)
    if isinstance(result, dict):
        nested = result.get("result") or result.get("data")
        if isinstance(nested, dict):
            return nested
        return result
    return {}


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value.strip().replace("%", "")
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if isinstance(value, str) and "%" in value:
        return parsed / 100
    return parsed


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _rate(value: Any) -> float | None:
    parsed = _float(value)
    if parsed is None:
        return None
    return parsed / 100 if parsed > 1 else parsed


def _price_info(item: dict[str, Any]) -> dict[str, Any]:
    price_info = item.get("priceInfo") or item.get("price_info") or {}
    return price_info if isinstance(price_info, dict) else {}


def _shipping_badges(item: dict[str, Any]) -> list[str]:
    shipping = item.get("productSimpleShippingInfo") or {}
    badge = shipping.get("shippingTimeGuarantee") if isinstance(shipping, dict) else None
    badges = []
    if badge:
        badges.append(str(badge))
    for service in item.get("serviceList") or []:
        if service == "sendGoods24H":
            badges.append("ship_in_24h")
        elif service == "sendGoods48H":
            badges.append("ship_in_48h")
    return list(dict.fromkeys(badges))


def _seller_info_from_item(item: dict[str, Any]) -> SellerInfo:
    seller = item.get("sellerDataInfo") or item.get("seller") or {}
    seller = seller if isinstance(seller, dict) else {}
    location = " ".join(str(part) for part in [seller.get("province"), seller.get("city")] if part)
    score = _float(seller.get("compositeServiceScore")) or _float(seller.get("score"))
    return SellerInfo(
        name=seller.get("companyName") or seller.get("name") or item.get("sellerName"),
        url=seller.get("shopUrl") or seller.get("url") or item.get("sellerUrl"),
        score=score,
        level=seller.get("tradeMedalLevel") or seller.get("level"),
        location=location or None,
        years_active=_int(seller.get("yearsActive") or seller.get("tpYear")),
        badges=[str(badge) for badge in seller.get("sellerIdentities") or item.get("sellerIdentities") or []],
    )


def normalize_api_search_items(payload: dict[str, Any], source_keyword: str | None = None) -> list[ProductSearchResult]:
    items: list[ProductSearchResult] = []
    fetched_at = datetime.now(timezone.utc)
    for raw in _as_result_list(payload):
        offer_id = str(raw.get("offerId") or raw.get("itemId") or raw.get("offer_id") or "")
        if not offer_id:
            continue
        price_info = _price_info(raw)
        seller = _seller_info_from_item(raw)
        title = str(raw.get("subject") or raw.get("title") or raw.get("name") or "")
        missing = []
        for field, value in {
            "title_zh": title,
            "image_url": raw.get("imageUrl") or raw.get("imgUrl"),
            "price_min": price_info.get("price"),
            "month_sold": raw.get("monthSold") or raw.get("soldOut"),
            "repurchase_rate": raw.get("repurchaseRate"),
        }.items():
            if value in (None, "", []):
                missing.append(field)
        items.append(
            ProductSearchResult(
                offer_id=offer_id,
                url=raw.get("promotionURL") or f"https://detail.1688.com/offer/{offer_id}.html",
                title_zh=title or f"1688 offer {offer_id}",
                title_ko_optional=raw.get("subjectTrans") or raw.get("translateTitle"),
                image_url=raw.get("imageUrl") or raw.get("imgUrl"),
                price_min=_float(price_info.get("price")),
                price_max=_float(price_info.get("price")),
                promotion_price=_float(price_info.get("promotionPrice")),
                consign_price=_float(price_info.get("consignPrice")),
                moq=_int(raw.get("minOrderQuantity")),
                month_sold=_int(raw.get("monthSold") or raw.get("soldOut")),
                trade_volume=_int(raw.get("tradeVolume")),
                buyer_count=_int(raw.get("buyerNum") or raw.get("buyerCount")),
                repurchase_rate=_rate(raw.get("repurchaseRate")),
                seller_name=seller.name,
                seller_url=seller.url,
                seller_score=_float(raw.get("tradeScore")) or seller.score,
                seller_level=seller.level,
                seller_years_active=seller.years_active,
                badges=[str(badge) for badge in raw.get("offerIdentities") or []],
                shipping_badges=_shipping_badges(raw),
                is_one_piece_dropship_available=bool(raw.get("isOnePsale")) if raw.get("isOnePsale") is not None else None,
                source_keyword=source_keyword,
                missing_fields=missing,
                provider="api",
                provider_version=PROVIDER_VERSION,
                live_verified=False,
                source_type="api",
                fetched_at=fetched_at,
                warnings=["API endpoint structure implemented from references; live credentials were not verified in tests."],
            )
        )
    return items


def normalize_api_detail(payload: dict[str, Any], offer_id: str) -> ProductDetail:
    raw = _as_result_dict(payload)
    raw_offer_id = str(raw.get("offerId") or raw.get("itemId") or offer_id)
    price_info = _price_info(raw)
    price_ranges = price_info.get("priceRange") or raw.get("priceRange") or []
    price_tiers = [
        PriceTier(min_quantity=_int(item.get("startQuantity") or item.get("minQuantity")) or 1, price=_float(item.get("price")) or 0)
        for item in price_ranges
        if isinstance(item, dict) and _float(item.get("price")) is not None
    ]
    attributes: dict[str, Any] = {}
    raw_attrs = raw.get("productAttribute") or raw.get("attributes") or []
    if isinstance(raw_attrs, list):
        for attr in raw_attrs:
            if isinstance(attr, dict):
                key = attr.get("attributeName") or attr.get("name")
                value = attr.get("value")
                if key:
                    attributes[str(key)] = value
    elif isinstance(raw_attrs, dict):
        attributes.update(raw_attrs)
    sku_options: list[SkuOption] = []
    if isinstance(raw.get("skuOptions"), list):
        sku_options = [SkuOption.model_validate(item) for item in raw["skuOptions"] if isinstance(item, dict)]
    elif isinstance(raw.get("skuInfos"), list):
        option_values: dict[str, set[str]] = {}
        for sku in raw["skuInfos"]:
            spec = sku.get("specAttrs") if isinstance(sku, dict) else None
            if not spec:
                continue
            for part in str(spec).split(";"):
                if ":" in part:
                    name, value = part.split(":", 1)
                    option_values.setdefault(name.strip(), set()).add(value.strip())
        sku_options = [SkuOption(name=name, values=sorted(values)) for name, values in option_values.items()]
    seller = _seller_info_from_item(raw)
    missing = []
    for field, value in {"price_tiers": price_tiers, "attributes": attributes, "main_image_urls": raw.get("imageList")}.items():
        if not value:
            missing.append(field)
    return ProductDetail(
        offer_id=raw_offer_id,
        url=raw.get("promotionURL") or f"https://detail.1688.com/offer/{raw_offer_id}.html",
        title_zh=raw.get("subject") or raw.get("title") or f"1688 offer {raw_offer_id}",
        title_ko_optional=raw.get("subjectTrans") or raw.get("translateTitle"),
        price_tiers=price_tiers,
        sku_options=sku_options,
        attributes=attributes,
        category=raw.get("categoryName") or raw.get("category"),
        stock=_int(raw.get("stock")),
        month_sold=_int(raw.get("monthSold") or raw.get("soldOut")),
        trade_volume=_int(raw.get("tradeVolume")),
        repurchase_rate=_rate(raw.get("repurchaseRate")),
        seller=seller,
        main_image_urls=[str(url) for url in raw.get("imageList") or raw.get("mainImages") or []],
        detail_image_urls=[str(url) for url in raw.get("descriptionImages") or raw.get("detailImages") or []],
        option_image_urls=[str(url) for url in raw.get("skuImages") or raw.get("optionImages") or []],
        video_urls=[str(url) for url in raw.get("videoList") or raw.get("videos") or []],
        raw_source_summary={"provider": "api", "live_verified": False},
        missing_fields=missing,
        provider="api",
        provider_version=PROVIDER_VERSION,
        live_verified=False,
        source_type="api",
        fetched_at=datetime.now(timezone.utc),
        warnings=["API detail normalizer has not been live verified in this environment."],
    )


class Api1688Provider(Base1688Provider):
    name = "api"
    provider_version = PROVIDER_VERSION
    source_type = "api"

    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.auth = ApiAuthManager(self.settings, client=client)

    def capabilities(self) -> ProviderCapability:
        return ProviderCapability(
            provider=self.name,
            provider_version=self.provider_version,
            source_type="api",
            live_verified=False,
            search=True,
            detail=True,
            download_assets=True,
            hot_keywords=True,
            rankings=True,
            image_search=True,
            required_env=["ALI1688_APP_KEY", "ALI1688_APP_SECRET", "ALI1688_REFRESH_TOKEN or ALI1688_ACCESS_TOKEN"],
            notes=["API endpoints and normalization are implemented from references; live credentials were not available for verification."],
        )

    async def aclose(self) -> None:
        if self.client:
            await self.client.aclose()

    def _missing_credentials_response(self, response_type):
        message = "ALI1688_APP_KEY, ALI1688_APP_SECRET, and ALI1688_REFRESH_TOKEN or ALI1688_ACCESS_TOKEN are required for api provider."
        suggested_action = "Set API credentials or use SOURCING1688_PROVIDER=browser/local_html."
        return response_type(
            status="missing_credentials",
            message=message,
            suggested_action=suggested_action,
            error=structured_error("missing_credentials", message, suggested_action=suggested_action),
            provider=self.name,
            provider_version=self.provider_version,
            source_type="api",
            live_verified=False,
            fetched_at=datetime.now(timezone.utc),
        )

    def _api_error_response(self, response_type, message: str, *, code: str = "api_error"):
        return response_type(
            status="provider_unavailable",
            message=message,
            suggested_action="Check API credentials, solution subscription, endpoint permissions, and signature settings.",
            error=structured_error(code, message),
            provider=self.name,
            provider_version=self.provider_version,
            source_type="api",
            live_verified=False,
            fetched_at=datetime.now(timezone.utc),
            warnings=["Live API request failed or returned an API error."],
        )

    def endpoint_url(self, endpoint_key: str) -> str:
        return f"{self.settings.ali1688_api_base}/{ENDPOINTS[endpoint_key]}/{self.settings.ali1688_app_key}"

    def sign_params(self, path: str, params: dict[str, Any]) -> str:
        # 1688 Open Platform signatures are path + sorted params signed with app secret.
        # This implementation is live-capable but remains live_not_verified until tested with a real app.
        normalized = "".join(f"{key}{params[key]}" for key in sorted(params) if params[key] is not None)
        raw = f"{path}{normalized}".encode("utf-8")
        return hmac.new((self.settings.ali1688_app_secret or "").encode("utf-8"), raw, hashlib.sha1).hexdigest().upper()

    def _serialize_sort(self, sort: str | dict[str, str] | None) -> dict[str, str] | None:
        if sort is None:
            return None
        if isinstance(sort, dict):
            return {key: value for key, value in sort.items() if key in SUPPORTED_SORTS}
        if ":" in sort:
            key, direction = sort.split(":", 1)
            if key in SUPPORTED_SORTS:
                return {key: direction}
        if sort in SUPPORTED_SORTS:
            return {sort: "desc"}
        return None

    def _serialize_filter(self, filters: dict[str, Any] | str | None) -> str | None:
        if filters is None:
            return None
        if isinstance(filters, str):
            selected = [item.strip() for item in filters.split(",") if item.strip() in SUPPORTED_FILTERS]
        else:
            selected = [key for key, enabled in filters.items() if enabled and key in SUPPORTED_FILTERS]
        return ",".join(selected) if selected else None

    def build_keyword_search_params(
        self,
        keyword: str,
        *,
        page: int = 1,
        page_size: int = 20,
        sort: str | dict[str, str] | None = None,
        filters: dict[str, Any] | str | None = None,
        country: str = "en",
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "keyword": keyword,
            "beginPage": page,
            "pageSize": min(page_size, 50),
            "country": country if country != "zh" else "en",
        }
        if serialized_filter := self._serialize_filter(filters):
            params["filter"] = serialized_filter
        if serialized_sort := self._serialize_sort(sort):
            params["sort"] = serialized_sort
        return params

    async def _post_endpoint(self, endpoint_key: str, params: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        token, auth_error = await self.auth.get_access_token()
        if auth_error:
            return None, auth_error.message
        own_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=30)
        try:
            payload = dict(params)
            payload["access_token"] = token
            signature_path = f"param2/1/{ENDPOINTS[endpoint_key]}/{self.settings.ali1688_app_key}"
            payload["_aop_signature"] = self.sign_params(signature_path, payload)
            response = await client.post(self.endpoint_url(endpoint_key), json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get("error_code") or data.get("errorMessage") or data.get("error_message"):
                return data, data.get("error_message") or data.get("errorMessage") or str(data.get("error_code"))
            return data, None
        except Exception as exc:  # noqa: BLE001
            return None, str(exc)
        finally:
            if own_client:
                await client.aclose()

    async def search_products(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 30,
        sort: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> SearchResponse:
        if not self.auth.has_any_credentials():
            return self._missing_credentials_response(SearchResponse)
        data, error = await self._post_endpoint("keyword_search", self.build_keyword_search_params(keyword, page=page, page_size=page_size, sort=sort, filters=filters))
        if error:
            return self._api_error_response(SearchResponse, error)
        items = normalize_api_search_items(data or {}, source_keyword=keyword)
        return SearchResponse(status="ok" if items else "partial_data", items=items, keyword=keyword, provider=self.name, provider_version=self.provider_version, source_type="api", live_verified=False, fetched_at=datetime.now(timezone.utc), warnings=["API response normalized; live verification not performed in this environment."])

    async def image_search(self, image_url: str | None = None, image_path: str | None = None, page: int = 1, page_size: int = 20) -> ImageSearchResponse:
        if not self.auth.has_any_credentials():
            return self._missing_credentials_response(ImageSearchResponse)
        params = {"beginPage": page, "pageSize": min(page_size, 50), "country": "en"}
        if image_url:
            params["imageAddress"] = image_url
        elif image_path:
            return self._api_error_response(ImageSearchResponse, "Local image upload path is implemented as interface only; live upload is not verified.", code="live_not_verified")
        else:
            return self._api_error_response(ImageSearchResponse, "Provide image_url or image_path.", code="invalid_input")
        data, error = await self._post_endpoint("image_search", params)
        if error:
            return self._api_error_response(ImageSearchResponse, error)
        return ImageSearchResponse(status="ok", items=normalize_api_search_items(data or {}, source_keyword="image-search"), image_url=image_url, image_path=image_path, provider=self.name, provider_version=self.provider_version, source_type="api", live_verified=False, fetched_at=datetime.now(timezone.utc), warnings=["1688 image search works best with alicdn image URLs; live verification not performed."])

    async def get_product_detail(self, offer_id_or_url: str) -> DetailResponse:
        try:
            offer_id = extract_offer_id(offer_id_or_url)
        except ValueError as exc:
            return DetailResponse(status="error", message=str(exc), error=structured_error("invalid_offer_id", str(exc)), provider=self.name)
        if not self.auth.has_any_credentials():
            return self._missing_credentials_response(DetailResponse)
        data, error = await self._post_endpoint("detail", {"offerId": offer_id, "country": "en"})
        if error:
            return self._api_error_response(DetailResponse, error)
        detail = normalize_api_detail(data or {}, offer_id)
        return DetailResponse(status="ok" if not detail.missing_fields else "partial_data", item=detail, provider=self.name, provider_version=self.provider_version, source_type="api", live_verified=False, fetched_at=datetime.now(timezone.utc), missing_fields=detail.missing_fields)

    async def download_product_assets(
        self,
        offer_id_or_url: str,
        output_dir: str | Path,
        include: str | set[str] | list[str] | None = None,
        dry_run: bool = False,
    ) -> AssetDownloadResponse:
        detail_response = await self.get_product_detail(offer_id_or_url)
        if detail_response.item is None:
            return AssetDownloadResponse(status=detail_response.status, message=detail_response.message, error=detail_response.error, provider=self.name, provider_version=self.provider_version, source_type="api", live_verified=False)
        manifest = await download_assets(detail_response.item, output_dir, include=include, source_url=detail_response.item.url, dry_run=dry_run)
        return AssetDownloadResponse(status=manifest.status, manifest=manifest, manifest_path=str(Path(manifest.saved_dir) / "manifest.json"), provider=self.name, provider_version=self.provider_version, source_type="api", live_verified=False)

    async def get_hot_keywords(self, category_id: str | None = None, limit: int = 20) -> HotKeywordsResponse:
        if not self.auth.has_any_credentials():
            return self._missing_credentials_response(HotKeywordsResponse)
        data, error = await self._post_endpoint("hot_keywords", {"sourceId": category_id or "0", "type": "cate", "country": "en"})
        if error:
            return self._api_error_response(HotKeywordsResponse, error)
        items = []
        for index, raw in enumerate(_as_result_list(data or {}), start=1):
            keyword = raw.get("seKeyword") or raw.get("keyword")
            if keyword:
                items.append(HotKeyword(keyword=str(keyword), category_id=category_id, rank=index, heat=_float(raw.get("heat"))))
        return HotKeywordsResponse(status="ok" if items else "partial_data", items=items[:limit], provider=self.name, provider_version=self.provider_version, source_type="api", live_verified=False)

    async def get_rankings(self, category_id: str | None = None, rank_type: str = "hot", limit: int = 20) -> RankingsResponse:
        if not self.auth.has_any_credentials():
            return self._missing_credentials_response(RankingsResponse)
        data, error = await self._post_endpoint("ranking", {"rankId": category_id or "0", "rankType": rank_type, "limit": min(limit, 20), "language": "en"})
        if error:
            return self._api_error_response(RankingsResponse, error)
        items = []
        for index, raw in enumerate(_as_result_list(data or {}), start=1):
            offer_id = str(raw.get("itemId") or raw.get("offerId") or "")
            items.append(RankingItem(rank=_int(raw.get("sort")) or index, keyword=raw.get("keyword"), offer_id=offer_id or None, title_zh=raw.get("title"), score=_float(raw.get("goodsScore")), url=f"https://detail.1688.com/offer/{offer_id}.html" if offer_id else None))
        return RankingsResponse(status="ok" if items else "partial_data", items=items[:limit], provider=self.name, provider_version=self.provider_version, source_type="api", live_verified=False)
