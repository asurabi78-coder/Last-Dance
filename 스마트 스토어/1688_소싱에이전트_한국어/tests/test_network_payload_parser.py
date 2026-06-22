import json

from sourcing1688.mcp_server import mcp
from sourcing1688.parsers.rendered_html import parse_network_payload


def test_parse_1688_network_payload_detail_model():
    payload = {
        "result": {
            "global": {
                "globalData": {
                    "model": {
                        "offerModel": {
                            "offerId": "1018990720574",
                            "subject": "宠物胸背带牵引绳",
                            "imageList": [
                                {"fullPathImageURI": "https://cbu01.alicdn.com/img/ibank/O1CN01-main.jpg"}
                            ],
                            "detailImageList": [
                                {"fullPathImageURI": "https://cbu01.alicdn.com/img/ibank/O1CN01-detail.jpg"}
                            ],
                        },
                        "tradeModel": {
                            "saleCount": "1728",
                            "offerPriceModel": {"currentPrices": [{"beginAmount": 2, "price": "11.50"}]},
                        },
                        "sellerModel": {
                            "companyName": "广州宠物用品厂",
                            "score": "4.5",
                            "sellerWinportUrlMap": {"indexUrl": "https://example.1688.com"},
                        },
                        "wirelessVideo": {
                            "videoUrl": "https://video.alicdn.com/example/product.mp4",
                            "videoId": "123",
                        },
                    }
                }
            }
        }
    }

    response = parse_network_payload(json.dumps(payload), source_url="https://detail.1688.com/offer/1018990720574.html")

    assert response.status == "partial_data"
    assert response.item is not None
    assert response.item.offer_id == "1018990720574"
    assert response.item.title_zh == "宠物胸背带牵引绳"
    assert response.item.trade_volume == 1728
    assert response.item.price_tiers[0].price == 11.5
    assert response.item.seller and response.item.seller.name == "广州宠物用品厂"
    assert response.item.main_image_urls == ["https://cbu01.alicdn.com/img/ibank/O1CN01-main.jpg"]
    assert response.item.detail_image_urls == ["https://cbu01.alicdn.com/img/ibank/O1CN01-detail.jpg"]
    assert response.item.video_urls == ["https://video.alicdn.com/example/product.mp4"]


def test_parse_1688_network_payload_reports_video_metadata_without_url():
    payload = {"offerModel": {"offerId": "856551681324", "subject": "测试商品"}, "wirelessVideo": {"videoId": "0", "videoUrl": ""}}

    response = parse_network_payload(payload, source_url="https://detail.1688.com/offer/856551681324.html")

    assert response.item is not None
    assert response.item.offer_id == "856551681324"
    assert response.warnings
    assert "network data" in response.warnings[0]


def test_network_payload_parser_accepts_jsonp_wrapper():
    response = parse_network_payload(
        'mtopjsonp1({"data":{"offerId":"999888777","subject":"测试商品","priceInfo":{"price":"12.5"}}})',
        source_url="https://detail.1688.com/offer/999888777.html",
    )

    assert response.status == "partial_data"
    assert response.provider_version == "0.5.30"
    assert response.live_verified is True
    assert response.item.offer_id == "999888777"
    assert response.item.price_tiers[0].price == 12.5


def test_network_payload_failure_does_not_claim_live_for_non_1688_source():
    response = parse_network_payload("not-json", source_url="https://example.com/page")

    assert response.status == "partial_data"
    assert response.live_verified is False


def test_network_payload_failure_does_not_verify_lookalike_domain():
    response = parse_network_payload("not-json", source_url="https://fake1688.com/page")

    assert response.status == "partial_data"
    assert response.live_verified is False


def test_mcp_tool_list_includes_network_payload_parser():
    tool_names = {tool.name for tool in mcp._tool_manager.list_tools()}

    assert "parse_1688_network_payload_content" in tool_names
    assert "open_chrome_devtools_setup" in tool_names
