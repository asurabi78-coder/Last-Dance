from pathlib import Path

from sourcing1688.parsers.rendered_html import parse_rendered_html, parse_rendered_html_file, parse_visible_page_snapshot


FIXTURES = Path(__file__).parent / "fixtures"


def test_rendered_html_parser_extracts_detail_assets_and_fields():
    result = parse_rendered_html_file(FIXTURES / "singlefile_detail_sample.html")

    assert result.status == "partial_data"
    detail = result.item
    assert detail.offer_id == "123456789"
    assert detail.title_zh
    assert "https://cbu01.alicdn.com/img/ibank/O1CN-main-1.jpg" in detail.main_image_urls
    assert "https://cbu01.alicdn.com/img/ibank/O1CN-detail-1.jpg" in detail.detail_image_urls
    assert "https://cbu01.alicdn.com/img/ibank/O1CN-option-black.jpg" in detail.option_image_urls
    assert detail.video_urls == ["https://cloud.video.taobao.com/play/u/1/p/1/e/6/t/1/123.mp4"]
    assert detail.main_image_urls.count("https://cbu01.alicdn.com/img/ibank/O1CN-main-1.jpg") == 1
    assert not any("lazyload" in url for url in detail.main_image_urls)
    assert detail.attributes


def test_existing_product_detail_fixture_is_parseable():
    result = parse_rendered_html_file(FIXTURES / "product_detail_sample.html")

    assert result.item.offer_id == "123456789"
    assert result.item.title_zh


def test_rendered_html_parser_accepts_source_url_for_chrome_captured_html():
    html = """
    <html>
      <head><title>Chrome captured product</title></head>
      <body>
        <h1>Chrome captured product</h1>
        <img src="//cbu01.alicdn.com/img/ibank/O1CN-chrome-main.jpg">
      </body>
    </html>
    """

    result = parse_rendered_html(html, source_url="https://detail.1688.com/offer/1018990720574.html")

    assert result.item.offer_id == "1018990720574"
    assert result.item.url == "https://detail.1688.com/offer/1018990720574.html"
    assert result.item.main_image_urls == ["https://cbu01.alicdn.com/img/ibank/O1CN-chrome-main.jpg"]
    assert result.live_verified is False
    assert result.item.live_verified is False


def test_rendered_html_parser_extracts_1688_model_trade_and_seller_fields():
    html = """
    <html>
      <head><title>Fallback title</title></head>
      <body>
        <script>
        window.__DATA__ = {
          "global": {
            "globalData": {
              "model": {
                "offerModel": {
                  "offerId": 1018990720574,
                  "subject": "宠物硅胶梳通用梳子",
                  "leafCategoryName": "宠物梳子"
                },
                "sellerModel": {
                  "companyName": "义乌市捷煜日用百货有限公司",
                  "sellerIdentity": "tp",
                  "winportUrl": "https://shop.example.1688.com",
                  "sellerSign": {"signs": {"isTp": true, "isFactoryDealer": false}}
                },
                "tradeModel": {
                  "beginAmount": 1,
                  "canBookedAmount": 35282,
                  "priceDisplay": "3.74",
                  "saleCount": 210,
                  "offerPriceModel": {
                    "currentPrices": [{"beginAmount": 1, "price": "3.74"}]
                  }
                },
                "skuModel": {
                  "skuProps": [
                    {
                      "prop": "颜色",
                      "value": [
                        {
                          "name": "粉色小号",
                          "imageUrl": "https://cbu01.alicdn.com/img/ibank/O1CN-option.jpg"
                        }
                      ]
                    }
                  ]
                }
              }
            }
          }
        };
        </script>
      </body>
    </html>
    """

    result = parse_rendered_html(html)
    detail = result.item

    assert detail.offer_id == "1018990720574"
    assert detail.title_zh == "宠物硅胶梳通用梳子"
    assert detail.category == "宠物梳子"
    assert detail.price_tiers[0].price == 3.74
    assert detail.price_tiers[0].min_quantity == 1
    assert detail.stock == 35282
    assert detail.trade_volume == 210
    assert detail.seller.name == "义乌市捷煜日用百货有限公司"
    assert detail.seller.url == "https://shop.example.1688.com"
    assert detail.sku_options[0].name == "颜色"
    assert detail.sku_options[0].values == ["粉色小号"]
    assert detail.option_image_urls == ["https://cbu01.alicdn.com/img/ibank/O1CN-option.jpg"]


def test_rendered_html_parser_warns_when_video_metadata_is_hidden():
    html = """
    <html>
      <body>
        <script>
        window.__DATA__ = {
          "offerModel": {"offerId": 775988776405, "subject": "宠物用品", "leafCategoryName": "宠物牵引绳"},
          "tradeModel": {"beginAmount": 1, "canBookedAmount": 10, "priceDisplay": "11.50", "saleCount": 1728},
          "sellerModel": {"companyName": "测试卖家"},
          "wirelessVideo": {"videoId": 0, "videoUrl": ""}
        };
        </script>
      </body>
    </html>
    """

    result = parse_rendered_html(html)

    assert result.item.video_urls == []
    assert result.warnings
    assert "no downloadable video url" in result.warnings[0].lower()


def test_rendered_html_parser_uses_visible_1688_text_when_json_is_sparse():
    html = """
    <html>
      <head>
        <title>杜老汉兔子趴趴垫保暖冬天兔子垫子夹夹垫侏儒垂耳兔荷兰猪兔子窝</title>
      </head>
      <body>
        <script>window.__DATA__ = {"offerModel": {"offerId": 856551681324}};</script>
        <div>杜老汉（山东）生物科技有限公司</div>
        <h1>杜老汉兔子趴趴垫保暖冬天兔子垫子夹夹垫侏儒垂耳兔荷兰猪兔子窝</h1>
        <div>一年内</div>
        <div>100+</div>
        <div>个成交</div>
        <div>价格</div>
        <div>¥</div>
        <div>25.00</div>
        <div>~</div>
        <div>¥</div>
        <div>39.00</div>
        <div>1个起批</div>
        <div>商品属性</div>
        <div>材质</div>
        <div>布类</div>
        <div>品牌</div>
        <div>杜老汉</div>
        <div>是否跨境出口专供货源</div>
        <div>是</div>
        <div>商品描述</div>
        <script>
          window.assetHints = [
            "https://cbu01.alicdn.com/img/ibank/O1CN01rejsj61Bs2sgIAIpZ_!!0-0-cib.jpg",
            "https://cbu01.alicdn.com/img/ibank/O1CN01ORwIZS1s7oW8LiPmR_!!2216180205720-0-cib.jpg",
            "https://cloud.video.taobao.com/play/u/2216180205720/p/2/e/6/t/1/494830060237.mp4"
          ];
        </script>
      </body>
    </html>
    """

    result = parse_rendered_html(html, source_url="https://detail.1688.com/offer/856551681324.html")
    detail = result.item

    assert detail.offer_id == "856551681324"
    assert detail.price_tiers[0].min_quantity == 1
    assert detail.price_tiers[0].price == 25.0
    assert detail.trade_volume == 100
    assert detail.seller.name == "杜老汉（山东）生物科技有限公司"
    assert detail.attributes["材质"] == "布类"
    assert detail.attributes["品牌"] == "杜老汉"
    assert detail.main_image_urls
    assert detail.video_urls == ["https://cloud.video.taobao.com/play/u/2216180205720/p/2/e/6/t/1/494830060237.mp4"]


def test_visible_page_snapshot_prefers_company_name_over_supplier_highlights():
    body_text = "\n".join(
        [
            "供应商亮点",
            "源头工厂20年|支持OEM/ODM|专利设计防泼水",
            "跨境专供欧美|月产7万件起",
            "加厚涤纶布旅游衣服收纳袋旅行用品套装束口鞋套整理六件套收纳包",
            "¥41.00",
            "2件起批",
            "已售4600+件",
            "浙江华彩箱包有限公司",
            "店铺回头率62%",
        ]
    )

    result = parse_visible_page_snapshot(
        source_url="https://detail.1688.com/offer/755178864684.html",
        title="加厚涤纶布旅游衣服收纳袋旅行用品套装束口鞋套整理六件套收纳包 - 阿里巴巴",
        body_text=body_text,
        media_urls=["https://cloud.video.taobao.com/play/u/2684580704/p/2/e/6/t/1/442197115990.mp4"],
    )

    assert result.provider == "chrome_devtools"
    assert result.provider_version == "0.5.30"
    assert result.live_verified is True
    assert result.item.seller.name == "浙江华彩箱包有限公司"
    assert result.item.video_urls == ["https://cloud.video.taobao.com/play/u/2684580704/p/2/e/6/t/1/442197115990.mp4"]


def test_visible_page_snapshot_does_not_verify_lookalike_domain():
    result = parse_visible_page_snapshot(
        source_url="https://fake1688.com/offer/755178864684.html",
        title="旅行收纳袋 - 阿里巴巴",
        body_text="\n".join(
            [
                "旅行收纳袋",
                "浙江华彩箱包有限公司",
                "¥41.00",
                "2件起批",
                "已售4600+件",
            ]
        ),
        media_urls=[],
    )

    assert result.live_verified is False
    assert result.item is None
    assert result.message.startswith("Current page is not a 1688 offer page")


def test_visible_page_snapshot_extracts_tiers_seller_attributes_and_filters_external_media():
    result = parse_visible_page_snapshot(
        source_url="https://detail.1688.com/offer/812345678901.html",
        title="手机防水袋 户外漂流潜水防水包 - 阿里巴巴",
        body_text="\n".join(
            [
                "手机防水袋 户外漂流潜水防水包",
                "店铺 深圳市蓝海户外用品有限公司",
                "100-999 个 ¥4.50",
                "1000-4999 个 ¥3.60",
                "≥5000 个 ¥2.80",
                "30天成交 1.2万件",
                "复购率 28%",
                "诚信通 8年",
                "实力商家",
                "发货地 广东 深圳",
                "材质 PVC+ABS",
                "适用型号 6.8英寸以内手机",
                "颜色 透明黑边, 透明白边, 荧光绿",
                "支持定制 logo定制 包装定制",
            ]
        ),
        media_urls=[
            "https://cbu01.alicdn.com/img/ibank/waterproof.jpg",
            "https://example.com/not-1688-cdn.jpg",
        ],
    )

    assert result.item is not None
    detail = result.item
    assert [(tier.min_quantity, tier.price) for tier in detail.price_tiers] == [(100, 4.5), (1000, 3.6), (5000, 2.8)]
    assert detail.month_sold == 12000
    assert detail.trade_volume == 12000
    assert detail.repurchase_rate == 0.28
    assert detail.seller.name == "深圳市蓝海户外用品有限公司"
    assert detail.seller.location == "广东 深圳"
    assert detail.seller.years_active == 8
    assert "实力商家" in detail.seller.badges
    assert detail.attributes["材质"] == "PVC+ABS"
    assert detail.attributes["适用型号"] == "6.8英寸以内手机"
    assert detail.main_image_urls == ["https://cbu01.alicdn.com/img/ibank/waterproof.jpg"]
    assert result.warnings


def test_visible_page_snapshot_extracts_price_first_tiers_and_seller_year_suffix():
    result = parse_visible_page_snapshot(
        source_url="https://detail.1688.com:443/offer/812345678902.html",
        title="便携旅行收纳包 - 阿里巴巴",
        body_text="\n".join(
            [
                "便携旅行收纳包",
                "深圳市某某科技有限公司 5年",
                "¥3.80 / 2-99个",
                "¥3.45 / 100-999个",
                "¥2.98 / ≥1000个",
                "30天成交 520件",
            ]
        ),
        media_urls=[],
    )

    detail = result.item
    assert result.live_verified is True
    assert [(tier.min_quantity, tier.price) for tier in detail.price_tiers] == [(2, 3.8), (100, 3.45), (1000, 2.98)]
    assert detail.seller.name == "深圳市某某科技有限公司"
    assert detail.seller.years_active == 5


def test_visible_page_snapshot_extracts_rmb_price_first_tiers():
    result = parse_visible_page_snapshot(
        source_url="https://detail.1688.com/offer/812345678903.html",
        title="旅行配件 - 阿里巴巴",
        body_text="\n".join(
            [
                "旅行配件",
                "义乌市出行用品有限公司",
                "￥22.50 1-49件",
                "￥19.80 50-499件",
                "￥16.90 ≥500件",
            ]
        ),
        media_urls=[],
    )

    assert [(tier.min_quantity, tier.price) for tier in result.item.price_tiers] == [(1, 22.5), (50, 19.8), (500, 16.9)]


def test_visible_page_snapshot_extracts_split_rmb_symbol_price_and_moq():
    result = parse_visible_page_snapshot(
        source_url="https://detail.1688.com/offer/812345678904.html",
        title="旅行配件 - 阿里巴巴",
        body_text="\n".join(["旅行配件", "义乌市出行用品有限公司", "￥22.50 起", "2件起批"]),
        media_urls=[],
    )

    assert [(tier.min_quantity, tier.price) for tier in result.item.price_tiers] == [(2, 22.5)]


def test_visible_page_snapshot_extracts_yuan_price_ranges_without_symbol():
    result = parse_visible_page_snapshot(
        source_url="https://detail.1688.com/offer/812345678905.html",
        title="旅行配件 - 阿里巴巴",
        body_text="\n".join(["旅行配件", "义乌市出行用品有限公司", "22.50-49.90元", "3件起批"]),
        media_urls=[],
    )

    assert [(tier.min_quantity, tier.price) for tier in result.item.price_tiers] == [(3, 22.5)]


def test_visible_page_snapshot_extracts_yuan_tier_rows():
    result = parse_visible_page_snapshot(
        source_url="https://detail.1688.com/offer/812345678906.html",
        title="旅行配件 - 阿里巴巴",
        body_text="\n".join(["旅行配件", "义乌市出行用品有限公司", "2件 22.50元", "50件 19.80元"]),
        media_urls=[],
    )

    assert [(tier.min_quantity, tier.price) for tier in result.item.price_tiers] == [(2, 22.5), (50, 19.8)]


def test_visible_page_snapshot_parser_keeps_live_dom_fields_compactly():
    body_text = "\n".join(
        [
            "杜老汉（山东）生物科技有限公司",
            "杜老汉兔子趴趴垫保暖冬天兔子垫子夹夹垫侏儒垂耳兔荷兰猪兔子窝",
            "一年内",
            "100+",
            "个成交",
            "价格",
            "¥",
            "25.00",
            "~",
            "¥",
            "39.00",
            "1个起批",
            "商品属性",
            "材质",
            "布类",
            "品牌",
            "杜老汉",
            "商品描述",
        ]
    )

    result = parse_visible_page_snapshot(
        source_url="https://detail.1688.com/offer/856551681324.html",
        title="杜老汉兔子趴趴垫保暖冬天兔子垫子夹夹垫侏儒垂耳兔荷兰猪兔子窝",
        body_text=body_text,
        media_urls=[
            "https://cbu01.alicdn.com/img/ibank/O1CN01rejsj61Bs2sgIAIpZ_!!0-0-cib.jpg",
            "https://img.alicdn.com/imgextra/i1/6000000001270/O1CN01BnFLqn1LFi16CptNf_!!6000000001270-0-tbvideo.jpg",
            "https://cloud.video.taobao.com/play/u/2216180205720/p/2/e/6/t/1/494830060237.mp4",
        ],
    )
    detail = result.item

    assert result.provider == "chrome_devtools"
    assert detail.source_type == "browser"
    assert result.provider_version == "0.5.30"
    assert detail.price_tiers[0].price == 25.0
    assert detail.trade_volume == 100
    assert detail.seller.name == "杜老汉（山东）生物科技有限公司"
    assert detail.main_image_urls == [
        "https://cbu01.alicdn.com/img/ibank/O1CN01rejsj61Bs2sgIAIpZ_!!0-0-cib.jpg",
        "https://img.alicdn.com/imgextra/i1/6000000001270/O1CN01BnFLqn1LFi16CptNf_!!6000000001270-0-tbvideo.jpg",
    ]
    assert detail.video_urls == ["https://cloud.video.taobao.com/play/u/2216180205720/p/2/e/6/t/1/494830060237.mp4"]


def test_visible_page_snapshot_promotes_category_stock_and_detail_media():
    body_text = "\n".join(
        [
            "测试旅行收纳袋",
            "义乌市出行用品有限公司",
            "¥",
            "19.90",
            "2件起批",
            "库存",
            "35282件",
            "商品属性",
            "产品类别",
            "旅行袋",
            "材质",
            "涤纶",
            "商品描述",
        ]
    )

    result = parse_visible_page_snapshot(
        source_url="https://detail.1688.com/offer/812345678907.html",
        title="测试旅行收纳袋 - 阿里巴巴",
        body_text=body_text,
        media_urls=[
            "https://cbu01.alicdn.com/img/ibank/O1CN-main-1.jpg",
            "https://cbu01.alicdn.com/img/ibank/O1CN-main-2.jpg",
            "https://cbu01.alicdn.com/img/ibank/O1CN-main-3.jpg",
            "https://cbu01.alicdn.com/img/ibank/O1CN-main-4.jpg",
            "https://cbu01.alicdn.com/img/ibank/O1CN-main-5.jpg",
            "https://cbu01.alicdn.com/img/ibank/O1CN-main-6.jpg",
            "https://cbu01.alicdn.com/img/ibank/O1CN-detail-1.jpg",
            "https://cbu01.alicdn.com/img/ibank/O1CN-option_sum.jpg",
        ],
    )
    detail = result.item

    assert detail.category == "旅行袋"
    assert detail.stock == 35282
    assert len(detail.main_image_urls) == 6
    assert detail.detail_image_urls == ["https://cbu01.alicdn.com/img/ibank/O1CN-detail-1.jpg"]
    assert detail.option_image_urls == ["https://cbu01.alicdn.com/img/ibank/O1CN-option_sum.jpg"]


def test_rendered_html_parser_merges_extra_json_seller_and_images():
    html = """
    <html>
      <body>
        <script>
        window.__DATA__ = {
          "offerId": "888888888",
          "subject": "测试商品",
          "priceInfo": {"price": "19.90", "beginAmount": 2},
          "sellerDataInfo": {"companyName": "测试源头工厂", "compositeServiceScore": "4.7"},
          "imageList": [{"imageUrl": "https://cbu01.alicdn.com/img/ibank/O1CN-json-main.jpg"}]
        };
        </script>
      </body>
    </html>
    """

    detail = parse_rendered_html(html).item

    assert detail.price_tiers[0].min_quantity == 2
    assert detail.price_tiers[0].price == 19.9
    assert detail.seller.name == "测试源头工厂"
    assert detail.seller.score == 4.7
    assert detail.main_image_urls == ["https://cbu01.alicdn.com/img/ibank/O1CN-json-main.jpg"]
