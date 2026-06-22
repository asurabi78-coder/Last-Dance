from sourcing1688.parsers.reviews import parse_review_snapshot
from sourcing1688.parsers.search_results import parse_search_results_snapshot


def test_search_results_snapshot_normalizes_candidates_and_krw():
    items = [
        {
            "title": f"旅行收纳袋六件套旅游用品衣物整理包{index}",
            "url": f"https://detail.1688.com/offer/{800000000000 + index}.html",
            "price_text": f"¥{5 + index}.8",
            "sold_text": "已售1.2万件",
            "seller_name": f"义乌旅行用品工厂{index}",
            "image_url": "https://cbu01.alicdn.com/img/ibank/test.jpg",
            "raw_text": "源头工厂 48小时发货 回头率59% 已售1.2万件",
        }
        for index in range(10)
    ]

    payload = parse_search_results_snapshot(
        keyword="旅行用品",
        source_url="https://s.1688.com/selloffer/offer_search.htm?keywords=%C2%C3%D0%D0%D3%C3%C6%B7",
        items=items,
        cny_krw_rate=190,
        min_items=10,
    )

    assert payload["status"] == "ok"
    assert payload["count"] == 10
    assert payload["items"][0]["title_ko_summary"] == "여행/수납 관련 후보"
    assert payload["items"][0]["price_krw_min"] == 1102
    assert payload["items"][0]["sold_count"] == 12000
    assert payload["items"][0]["repurchase_rate"] == 0.59
    assert "源头工厂" in payload["items"][0]["badges"]
    assert "48小时发货" in payload["items"][0]["badges"]
    assert payload["warnings"] == []


def test_search_results_snapshot_canonicalizes_mobile_offer_id_links():
    payload = parse_search_results_snapshot(
        keyword="旅行用品",
        source_url="https://s.1688.com/selloffer/offer_search.htm",
        items=[
            {
                "title": "旅行收纳袋可折叠",
                "url": "http://detail.m.1688.com/page/index.html?offerId=787690257525&skuId=123",
                "price_text": "¥6.2",
                "raw_text": "回头率70%",
            }
        ],
        cny_krw_rate=190,
        min_items=1,
    )

    assert payload["items"][0]["offer_id"] == "787690257525"
    assert payload["items"][0]["url"] == "https://detail.1688.com/offer/787690257525.html"
    assert payload["items"][0]["raw_url"].startswith("http://detail.m.1688.com")
    assert payload["items"][0]["repurchase_rate"] == 0.7


def test_search_results_snapshot_warns_when_fewer_than_minimum():
    payload = parse_search_results_snapshot(
        keyword="旅行用品",
        source_url="https://s.1688.com/selloffer/offer_search.htm",
        items=[{"title": "旅行收纳袋", "url": "https://detail.1688.com/offer/800000000001.html", "price_text": "¥2.5"}],
        cny_krw_rate=200,
        min_items=10,
    )

    assert payload["count"] == 1
    assert payload["warnings"]


def test_search_results_prefers_unit_bearing_sales_count_and_currency_price():
    payload = parse_search_results_snapshot(
        keyword="旅行用品",
        source_url="https://s.1688.com/selloffer/offer_search.htm",
        items=[
            {
                "title": "旅行收纳袋",
                "url": "https://detail.1688.com/offer/800000000099.html",
                "price_text": "¥2.50 2件起批",
                "sold_text": "30天成交 1.2万件",
            }
        ],
        cny_krw_rate=200,
        min_items=1,
    )

    item = payload["items"][0]
    assert item["sold_count"] == 12000
    assert item["price_cny_min"] == 2.5
    assert item["price_cny_max"] == 2.5


def test_search_results_uses_number_before_moq_as_price_without_using_moq():
    payload = parse_search_results_snapshot(
        keyword="旅行用品",
        source_url="https://s.1688.com/selloffer/offer_search.htm",
        items=[
            {
                "title": "旅行收纳袋",
                "url": "https://detail.1688.com/offer/800000000100.html",
                "price_text": "5.80 2\u4ef6\u8d77\u6279",
                "sold_text": "已售99件",
            }
        ],
        cny_krw_rate=200,
        min_items=1,
    )

    item = payload["items"][0]
    assert item["price_cny_min"] == 5.8
    assert item["price_cny_max"] == 5.8
    assert item["sold_count"] == 99


def test_search_results_does_not_use_moq_alone_as_price():
    payload = parse_search_results_snapshot(
        keyword="旅行用品",
        source_url="https://s.1688.com/selloffer/offer_search.htm",
        items=[
            {
                "title": "旅行收纳袋",
                "url": "https://detail.1688.com/offer/800000000101.html",
                "price_text": "2\u4ef6\u8d77\u6279",
            }
        ],
        cny_krw_rate=200,
        min_items=1,
    )

    item = payload["items"][0]
    assert item["price_cny_min"] is None
    assert item["price_cny_max"] is None


def test_search_results_marks_non_1688_source_as_unverified():
    payload = parse_search_results_snapshot(
        keyword="旅行用品",
        source_url="https://example.com/search",
        items=[{"title": "旅行收纳袋", "url": "https://detail.1688.com/offer/800000000001.html"}],
        min_items=1,
    )

    assert payload["live_verified"] is False
    assert payload["capture_status"] == "unverified_source_url"


def test_search_results_does_not_verify_lookalike_1688_domain():
    payload = parse_search_results_snapshot(
        keyword="旅行用品",
        source_url="https://fake1688.com/selloffer/offer_search.htm",
        items=[{"title": "旅行收纳袋", "url": "https://detail.1688.com/offer/800000000001.html"}],
        min_items=1,
    )

    assert payload["live_verified"] is False
    assert payload["capture_status"] == "unverified_source_url"


def test_search_results_does_not_turn_external_digits_into_1688_offer_urls():
    payload = parse_search_results_snapshot(
        keyword="旅行用品",
        source_url="https://s.1688.com/selloffer/offer_search.htm",
        items=[
            {"title": "外部候选", "url": "https://example.com/item?skuId=999888777666"},
            {"title": "伪域名候选", "url": "https://detail.1688.com.evil.test/offer/800000000999.html"},
            {"title": "外部显式候选", "url": "https://example.com/item/abc", "offer_id": "999888777667"},
        ],
        min_items=1,
    )

    assert payload["items"][0]["offer_id"] is None
    assert payload["items"][0]["url"] == "https://example.com/item?skuId=999888777666"
    assert payload["items"][1]["offer_id"] is None
    assert payload["items"][1]["url"] == "https://detail.1688.com.evil.test/offer/800000000999.html"
    assert payload["items"][2]["offer_id"] is None
    assert payload["items"][2]["url"] == "https://example.com/item/abc"


def test_search_results_accepts_chinese_keys_and_price_ranges():
    payload = parse_search_results_snapshot(
        keyword="手机防水袋",
        source_url="https://s.1688.com/selloffer/offer_search.htm",
        items=[
            {
                "标题": "手机防水袋 户外漂流潜水防水包",
                "链接": "https://detail.1688.com/offer/800000000102.html",
                "价格": "¥2.80-4.50",
                "成交": "30天成交 1.2万件",
                "店铺": "深圳市蓝海户外用品有限公司",
                "图片": "https://cbu01.alicdn.com/img/ibank/waterproof.jpg",
                "raw_text": "复购率 35% 48小时发货",
            }
        ],
        cny_krw_rate=200,
        min_items=1,
    )

    item = payload["items"][0]
    assert item["title_zh"].startswith("手机防水袋")
    assert item["price_cny_min"] == 2.8
    assert item["price_cny_max"] == 4.5
    assert item["sold_count"] == 12000
    assert item["repurchase_rate"] == 0.35
    assert item["seller_name"] == "深圳市蓝海户外用品有限公司"
    assert item["image_url"].endswith("waterproof.jpg")
    assert item["title_ko_summary"] == "방수 파우치/방수팩 후보"


def test_search_results_accepts_yuan_range_alt_keys_and_does_not_parse_rating_as_sales():
    payload = parse_search_results_snapshot(
        keyword="旅行用品",
        source_url="https://s.1688.com/selloffer/offer_search.htm",
        items=[
            {
                "标题": "旅行收纳袋 出差整理包",
                "链接": "https://detail.1688.com/offer/800000000104.html",
                "价格范围": "2.90-5.90元",
                "soldText": "评价 4.6 / 退货率低",
                "卖家": "义乌市旅行用品有限公司",
            },
            {
                "标题": "户外旅行洗漱包",
                "链接": "https://detail.1688.com/offer/800000000105.html",
                "价格范围": "￥22.5 - ￥49.9",
                "成交": "30天成交 880件",
                "卖家": "深圳出行用品工厂",
            },
        ],
        cny_krw_rate=200,
        min_items=2,
    )

    first, second = payload["items"]
    assert first["price_cny_min"] == 2.9
    assert first["price_cny_max"] == 5.9
    assert first["seller_name"] == "义乌市旅行用品有限公司"
    assert first["sold_count"] is None
    assert second["price_cny_min"] == 22.5
    assert second["price_cny_max"] == 49.9
    assert second["sold_count"] == 880
    assert second["seller_name"] == "深圳出行用品工厂"


def test_search_results_does_not_treat_repurchase_rate_as_sales_count():
    payload = parse_search_results_snapshot(
        keyword="手机防水袋",
        source_url="https://s.1688.com/selloffer/offer_search.htm",
        items=[
            {
                "title": "手机防水袋",
                "url": "https://detail.1688.com/offer/800000000103.html",
                "sold_text": "复购率 35%",
                "raw_text": "复购率 35%",
            }
        ],
        min_items=1,
    )

    item = payload["items"][0]
    assert item["sold_count"] is None
    assert item["repurchase_rate"] == 0.35


def test_review_snapshot_extracts_tags_and_empty_review_state():
    payload = parse_review_snapshot(
        source_url="https://detail.1688.com/offer/755178864684.html",
        body_text="\n".join(
            [
                "采购商评价",
                "质量很好 51",
                "包装严实 45",
                "发货很快 32",
                "做工不错 29",
                "综合评价",
                "5.0",
                "100+条评价",
                "好评率100%",
                "有内容9",
                "暂无更多评价",
            ]
        ),
        network_payloads=['{"resultCode":"SUCCESS","data":{"totalCount":0}}', '{"error":"SYSTEM_ERROR::null"}'],
    )

    assert payload["status"] == "ok"
    assert payload["review_list_status"] == "empty"
    assert payload["review_summary"]["score"] == 5.0
    assert payload["review_summary"]["review_count_text"] == "100+"
    assert payload["review_summary"]["positive_rate"] == 1.0
    assert payload["review_summary"]["content_review_count_text"] == "9"
    assert payload["summary_tags"][0] == {"label_zh": "质量很好", "count": 51}
    assert any(signal["status"] == "system_error" for signal in payload["network_signals"])
    assert payload["warnings"]


def test_review_snapshot_filters_ui_markers_and_unverified_source():
    payload = parse_review_snapshot(
        source_url="https://example.com/offer.html",
        body_text="\n".join(["买家评价", "暂无有效评价", "这家包装很稳，发货也很快，下次还会回购"]),
    )

    assert payload["live_verified"] is False
    assert payload["capture_status"] == "unverified_source_url"
    assert payload["review_list_status"] == "available"
    assert payload["review_texts"] == ["这家包装很稳，发货也很快，下次还会回购"]


def test_review_snapshot_only_verifies_real_1688_hosts():
    lookalike = parse_review_snapshot(
        source_url="https://fake1688.com/offer/755178864684.html",
        body_text="综合评价 4.8 100+条评价",
    )
    with_port = parse_review_snapshot(
        source_url="https://detail.1688.com:443/offer/755178864684.html",
        body_text="综合评价 4.8 100+条评价",
    )

    assert lookalike["live_verified"] is False
    assert lookalike["capture_status"] == "unverified_source_url"
    assert with_port["live_verified"] is True
    assert with_port["capture_status"] == "browser_capture_1688_url"
