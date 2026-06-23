import pytest

from sourcing1688.utils import encode_1688_search_keyword, extract_offer_id


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://detail.1688.com/offer/123456789.html", "123456789"),
        ("https://detail.1688.com:443/offer/123456789.html", "123456789"),
        ("http://detail.1688.com/offer/123456789.html", "123456789"),
        ("detail.1688.com/offer/123456789.html", "123456789"),
        ("123456789", "123456789"),
        ("https://m.1688.com/offer/123456789.html?spm=a2615", "123456789"),
        ("http://detail.m.1688.com/page/index.html?offerId=812305105474&skuId=5505516668292", "812305105474"),
        ("https://s.1688.com/selloffer/similar_search.html?offerIds=843851306548", "843851306548"),
    ],
)
def test_extract_offer_id(value, expected):
    assert extract_offer_id(value) == expected


def test_extract_offer_id_rejects_invalid_input():
    with pytest.raises(ValueError):
        extract_offer_id("https://example.com/no-offer")


@pytest.mark.parametrize(
    "value",
    [
        "https://fake1688.com/offer/123456789.html",
        "https://detail.1688.com.evil.test/offer/123456789.html",
        "https://example.com/item?offerId=123456789",
        "https://example.com/item?skuId=999888777666",
    ],
)
def test_extract_offer_id_rejects_lookalike_or_external_urls(value):
    with pytest.raises(ValueError):
        extract_offer_id(value)


def test_encode_1688_search_keyword_uses_gbk_for_chinese_search_page():
    assert encode_1688_search_keyword("\u624b\u673a\u652f\u67b6") == "%CA%D6%BB%FA%D6%A7%BC%DC"
