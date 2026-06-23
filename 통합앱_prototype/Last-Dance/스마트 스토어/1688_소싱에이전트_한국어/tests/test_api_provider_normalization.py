import json
from pathlib import Path

import httpx
import pytest

from sourcing1688.config import Settings
from sourcing1688.providers.api_auth import ApiTokenCache, redact_token_payload
from sourcing1688.providers.api_provider import Api1688Provider, normalize_api_detail, normalize_api_search_items


FIXTURES = Path(__file__).parent / "fixtures"


def test_api_keyword_response_normalizes_product_search_result():
    payload = json.loads((FIXTURES / "api_keyword_response.json").read_text(encoding="utf-8"))

    items = normalize_api_search_items(payload, source_keyword="黑胶伞")

    assert items[0].offer_id == "123456789"
    assert items[0].title_zh == "黑胶防晒晴雨伞 三折遮阳伞"
    assert items[0].title_ko_optional == "Black coating sun umbrella"
    assert items[0].price_min == 12.5
    assert items[0].moq == 2
    assert items[0].repurchase_rate == 0.34
    assert items[0].shipping_badges == ["48小时发货"]
    assert items[0].is_one_piece_dropship_available is True


def test_api_detail_response_normalizes_product_detail():
    payload = json.loads((FIXTURES / "api_detail_response.json").read_text(encoding="utf-8"))

    detail = normalize_api_detail(payload, "123456789")

    assert detail.offer_id == "123456789"
    assert detail.price_tiers[0].min_quantity == 2
    assert detail.attributes["材质"] == "碰击布"
    assert detail.seller.name == "义乌优伞工厂"
    assert detail.main_image_urls
    assert detail.video_urls


@pytest.mark.anyio
async def test_api_error_response_returns_structured_error(monkeypatch):
    monkeypatch.setenv("ALI1688_APP_KEY", "app")
    monkeypatch.setenv("ALI1688_APP_SECRET", "secret")
    monkeypatch.setenv("ALI1688_ACCESS_TOKEN", "token")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=json.loads((FIXTURES / "api_error_response.json").read_text(encoding="utf-8")))

    provider = Api1688Provider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    result = await provider.search_products("黑胶伞")
    await provider.aclose()

    assert result.status == "provider_unavailable"
    assert result.error is not None
    assert result.error.code == "api_error"


def test_token_cache_redaction(tmp_path):
    cache = ApiTokenCache(tmp_path / "token.json")
    cache.write({"access_token": "secret-access", "refresh_token": "secret-refresh", "expires_at": 9999999999})

    redacted = redact_token_payload(cache.read())

    assert redacted["access_token"] == "***REDACTED***"
    assert redacted["refresh_token"] == "***REDACTED***"


def test_api_request_serializes_sort_filter_and_defaults(monkeypatch):
    monkeypatch.setenv("ALI1688_APP_KEY", "app")
    monkeypatch.setenv("ALI1688_APP_SECRET", "secret")
    monkeypatch.setenv("ALI1688_ACCESS_TOKEN", "token")
    provider = Api1688Provider()

    params = provider.build_keyword_search_params(
        "黑胶伞",
        page=2,
        page_size=30,
        sort="monthSold:desc",
        filters={"shipIn48Hours": True, "certifiedFactory": True},
    )

    assert params["country"] == "en"
    assert params["beginPage"] == 2
    assert params["pageSize"] == 30
    assert "shipIn48Hours" in params["filter"]
    assert params["sort"]["monthSold"] == "desc"
