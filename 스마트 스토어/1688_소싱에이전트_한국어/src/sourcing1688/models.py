from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


Status = Literal[
    "ok",
    "error",
    "partial_data",
    "partial_success",
    "needs_human_login",
    "blocked_by_verification",
    "provider_unavailable",
    "missing_credentials",
    "live_not_verified",
    "dry_run",
]

SourceType = Literal["api", "browser", "local_html", "auto"]


class JsonModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class StructuredError(JsonModel):
    code: str
    message: str
    needs_human_action: bool = False
    suggested_action: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class StatusResponse(JsonModel):
    status: Status
    message: str | None = None
    needs_human_action: bool = False
    suggested_action: str | None = None
    error: StructuredError | None = None
    provider: str | None = None
    provider_version: str | None = None
    live_verified: bool = False
    source_type: SourceType | None = None
    fetched_at: datetime | None = None
    raw_reference_path: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_serializer("fetched_at")
    def serialize_fetched_at(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class KeywordExpansion(JsonModel):
    status: Status = "ok"
    original_keyword: str
    keywords: list[str]
    source_language: str = "ko"
    target_language: str = "zh"
    needs_review: bool = False
    note: str | None = None
    strategy: str | None = None
    seed_terms: list[str] = Field(default_factory=list)
    agent_instruction: str | None = None
    search_workflow: list[str] = Field(default_factory=list)
    search_urls: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SellerInfo(JsonModel):
    name: str | None = None
    url: str | None = None
    score: float | None = None
    level: str | None = None
    location: str | None = None
    years_active: int | None = None
    badges: list[str] = Field(default_factory=list)


class ProductSearchResult(JsonModel):
    offer_id: str
    url: str
    title_zh: str
    title_ko_optional: str | None = None
    image_url: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    currency: str = "CNY"
    moq: int | None = None
    month_sold: int | None = None
    trade_volume: int | None = None
    repurchase_rate: float | None = None
    seller_name: str | None = None
    seller_url: str | None = None
    seller_score: float | None = None
    seller_level: str | None = None
    badges: list[str] = Field(default_factory=list)
    shipping_badges: list[str] = Field(default_factory=list)
    is_one_piece_dropship_available: bool | None = None
    promotion_price: float | None = None
    consign_price: float | None = None
    buyer_count: int | None = None
    seller_years_active: int | None = None
    source_keyword: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    provider: str | None = None
    provider_version: str | None = None
    live_verified: bool = False
    source_type: SourceType | None = None
    fetched_at: datetime | None = None
    raw_reference_path: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_serializer("fetched_at")
    def serialize_fetched_at(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class PriceTier(JsonModel):
    min_quantity: int
    price: float
    currency: str = "CNY"


class SkuOption(JsonModel):
    name: str
    values: list[str] = Field(default_factory=list)


class ProductDetail(JsonModel):
    offer_id: str
    url: str
    title_zh: str
    title_ko_optional: str | None = None
    price_tiers: list[PriceTier] = Field(default_factory=list)
    sku_options: list[SkuOption] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    category: str | None = None
    stock: int | None = None
    month_sold: int | None = None
    trade_volume: int | None = None
    repurchase_rate: float | None = None
    seller: SellerInfo | None = None
    main_image_urls: list[str] = Field(default_factory=list)
    detail_image_urls: list[str] = Field(default_factory=list)
    option_image_urls: list[str] = Field(default_factory=list)
    video_urls: list[str] = Field(default_factory=list)
    raw_source_summary: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    provider: str | None = None
    provider_version: str | None = None
    live_verified: bool = False
    source_type: SourceType | None = None
    fetched_at: datetime | None = None
    raw_reference_path: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_serializer("fetched_at")
    def serialize_fetched_at(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class FailedAsset(JsonModel):
    url: str
    reason: str
    asset_type: str | None = None


class SavedAsset(JsonModel):
    url: str
    path: str
    skipped_duplicate: bool = False


class PlannedAsset(JsonModel):
    url: str
    asset_type: str


class AssetManifest(JsonModel):
    status: Literal["ok", "partial_success", "dry_run"] = "ok"
    offer_id: str
    saved_dir: str
    html_path: str | None = None
    main_images: list[SavedAsset] = Field(default_factory=list)
    detail_images: list[SavedAsset] = Field(default_factory=list)
    option_images: list[SavedAsset] = Field(default_factory=list)
    videos: list[SavedAsset] = Field(default_factory=list)
    dry_run_assets: list[PlannedAsset] = Field(default_factory=list)
    attributes_json: str | None = None
    failed_assets: list[FailedAsset] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    downloaded_at: datetime | None = None
    source_url: str | None = None
    raw_html_path: str | None = None
    parser_version: str | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    zip_path: str | None = None

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()


class SourcingScore(JsonModel):
    offer_id: str
    score: float
    confidence: float
    why_good: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    suggested_next_action: str
    sourcing_notes: list[str] = Field(default_factory=list)
    data_quality: str = "unknown"
    source_provider: str | None = None
    live_verified: bool = False


class SearchResponse(StatusResponse):
    items: list[ProductSearchResult] = Field(default_factory=list)
    keyword: str | None = None
    expanded_keywords: list[str] = Field(default_factory=list)
    keyword_expansion: KeywordExpansion | None = None


class DetailResponse(StatusResponse):
    item: ProductDetail | None = None


class AssetDownloadResponse(StatusResponse):
    manifest: AssetManifest | None = None
    manifest_path: str | None = None


class HotKeyword(JsonModel):
    keyword: str
    category_id: str | None = None
    rank: int | None = None
    heat: float | None = None


class HotKeywordsResponse(StatusResponse):
    items: list[HotKeyword] = Field(default_factory=list)


class RankingItem(JsonModel):
    rank: int
    keyword: str | None = None
    offer_id: str | None = None
    title_zh: str | None = None
    score: float | None = None
    url: str | None = None


class RankingsResponse(StatusResponse):
    items: list[RankingItem] = Field(default_factory=list)


class Recommendation(JsonModel):
    product: ProductSearchResult
    score: SourcingScore


class RecommendationResponse(StatusResponse):
    keyword: str
    expanded_keywords: list[str] = Field(default_factory=list)
    items: list[Recommendation] = Field(default_factory=list)
    saved: bool = False


class ProviderCapability(JsonModel):
    provider: str
    provider_version: str = "0.1.0"
    source_type: SourceType
    live_verified: bool = False
    search: bool = False
    detail: bool = False
    download_assets: bool = False
    hot_keywords: bool = False
    rankings: bool = False
    image_search: bool = False
    parse_rendered_html: bool = False
    required_env: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ProviderCapabilitiesResponse(StatusResponse):
    providers: dict[str, ProviderCapability] = Field(default_factory=dict)


class ImageSearchResponse(StatusResponse):
    items: list[ProductSearchResult] = Field(default_factory=list)
    image_url: str | None = None
    image_path: str | None = None
