from __future__ import annotations

import re
import json
from html import escape as html_escape
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from sourcing1688 import __version__
from sourcing1688.models import DetailResponse, PriceTier, ProductDetail, SellerInfo, SkuOption
from sourcing1688.parsers.asset_extractor import VIDEO_EXTENSIONS, dedupe_urls, extract_assets, extract_urls_from_text, safe_urlparse
from sourcing1688.parsers.embedded_json import extract_embedded_json_candidates, merge_candidates, walk_json_candidates
from sourcing1688.utils import extract_offer_id, structured_error


PARSER_VERSION = __version__
ATTRIBUTE_STOP_LINES = {"商品描述", "价格说明", "包装信息", "店铺推荐", "买家评价", "订购说明"}


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace("%", "").replace(",", "").strip())
    except ValueError:
        return None


def _int(value) -> int | None:
    parsed = _float(value)
    return int(parsed) if parsed is not None else None


def _text_lines(soup: BeautifulSoup) -> list[str]:
    return [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]


def _visible_text(soup: BeautifulSoup) -> str:
    return "\n".join(_text_lines(soup))


def _is_1688_source_url(source_url: str | None) -> bool:
    if not source_url:
        return False
    parsed = safe_urlparse(source_url)
    if not parsed:
        return False
    host = (parsed.hostname or "").lower()
    return host == "1688.com" or host.endswith(".1688.com")


def _is_live_browser_capture(provider: str, source_url: str | None) -> bool:
    return provider == "chrome_devtools" and _is_1688_source_url(source_url)


def _is_expected_1688_media_url(url: str) -> bool:
    parsed = safe_urlparse(url)
    if not parsed:
        return False
    host = (parsed.hostname or "").lower()
    return (
        host == "1688.com"
        or host.endswith(".1688.com")
        or host.endswith(".alicdn.com")
        or host.endswith(".aliimg.com")
        or host.endswith(".taobao.com")
    )


def _parse_chinese_count(value: str) -> int | None:
    cleaned = value.replace(",", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if not match:
        return None
    number = float(match.group(1))
    if "万" in cleaned:
        number *= 10000
    return int(number)


def _rate(value) -> float | None:
    parsed = _float(value)
    if parsed is None:
        return None
    return parsed / 100 if parsed > 1 else parsed


def _extract_offer_id(html: str, path: Path | None, source_url: str | None = None) -> str | None:
    if source_url:
        try:
            return extract_offer_id(source_url)
        except ValueError:
            pass
    for pattern in [
        r"detail\.1688\.com/offer/(\d+)\.html",
        r'"offerId"\s*:\s*"?(\d+)"?',
        r'"offer_id"\s*:\s*"?(\d+)"?',
        r"offer/(\d+)\.html",
    ]:
        if match := re.search(pattern, html):
            return match.group(1)
    if path and (match := re.search(r"(\d{6,})", path.name)):
        return match.group(1)
    return None


def _extract_visible_attributes(soup: BeautifulSoup) -> dict[str, object]:
    lines = _text_lines(soup)
    inline_keys = ("材质", "适用型号", "颜色", "支持定制", "品牌", "规格", "产地", "货号", "包装", "尺寸", "重量")
    inline_attrs: dict[str, object] = {}
    for line in lines:
        clean = re.sub(r"\s+", " ", line).strip()
        for key in inline_keys:
            if clean.startswith(f"{key} ") and len(clean) > len(key) + 1:
                inline_attrs.setdefault(key, clean[len(key):].strip())
    if "商品属性" not in lines:
        return inline_attrs
    start = max(index for index, line in enumerate(lines) if line == "商品属性") + 1
    attrs: dict[str, object] = dict(inline_attrs)
    index = start
    while index + 1 < len(lines):
        key = lines[index]
        value = lines[index + 1]
        if key in ATTRIBUTE_STOP_LINES:
            break
        if value in ATTRIBUTE_STOP_LINES:
            break
        if 1 <= len(key) <= 30 and key not in {"商品详情", "商品属性"}:
            attrs.setdefault(key, value)
        index += 2
    return attrs


def _extract_attributes(soup: BeautifulSoup, embedded: dict) -> dict[str, object]:
    attrs: dict[str, object] = {}
    offer_model = _dict(embedded.get("offerModel"))
    raw_attrs = (
        embedded.get("productAttribute")
        or embedded.get("attributes")
        or offer_model.get("productAttribute")
        or offer_model.get("productAttributes")
        or offer_model.get("productFeatureList")
    )
    if isinstance(raw_attrs, dict):
        attrs.update(raw_attrs)
    elif isinstance(raw_attrs, list):
        for item in raw_attrs:
            if isinstance(item, dict):
                key = item.get("attributeName") or item.get("name")
                if key:
                    attrs[str(key)] = item.get("value")
    for row in soup.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if len(cells) >= 2 and cells[0] and len(cells[0]) <= 30:
            attrs.setdefault(cells[0], cells[1])
    attrs.update({key: value for key, value in _extract_visible_attributes(soup).items() if key not in attrs})
    return attrs


def _extract_price_tiers(embedded: dict) -> list[PriceTier]:
    trade_model = _dict(embedded.get("tradeModel"))
    offer_price_model = _dict(trade_model.get("offerPriceModel"))
    price_info = _dict(embedded.get("priceInfo"))
    raw_ranges = embedded.get("priceRange") or embedded.get("priceRanges") or price_info.get("priceRanges") or []
    raw_current_prices = offer_price_model.get("currentPrices") or []
    tiers: list[PriceTier] = []
    for raw_items in [raw_ranges, raw_current_prices]:
        if not isinstance(raw_items, list):
            continue
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            price = _float(item.get("price"))
            if price is None:
                continue
            min_quantity = _int(item.get("startQuantity") or item.get("minQuantity") or item.get("beginAmount")) or 1
            if not any(tier.min_quantity == min_quantity and tier.price == price for tier in tiers):
                tiers.append(PriceTier(min_quantity=min_quantity, price=price))
    if not tiers:
        price = _float(
            embedded.get("price")
            or price_info.get("price")
            or price_info.get("promotionPrice")
            or price_info.get("consignPrice")
            or trade_model.get("priceDisplay")
            or trade_model.get("minPrice")
            or trade_model.get("maxPrice")
        )
        if price is not None:
            tiers.append(PriceTier(min_quantity=_int(embedded.get("beginAmount") or price_info.get("beginAmount") or trade_model.get("beginAmount")) or 1, price=price))
    return tiers


def _extract_visible_price_tiers(soup: BeautifulSoup) -> list[PriceTier]:
    lines = _text_lines(soup)
    tiers: list[PriceTier] = []
    for line in lines:
        clean = re.sub(r"\s+", " ", line)
        qty_first = re.search(r"(?:≥|>=)?\s*(\d+)(?:\s*[-~—]\s*\d+)?\s*(?:个|件|只|套|箱|包)?\s*(?:¥|￥)\s*(\d+(?:\.\d+)?)", clean)
        if not qty_first:
            qty_first = re.search(r"(?:≥|>=)?\s*(\d+)(?:\s*[-~—]\s*\d+)?\s*(?:个|件|只|套|箱|包)\s*(\d+(?:\.\d+)?)\s*(?:元|块)", clean)
        if qty_first:
            tiers.append(PriceTier(min_quantity=int(qty_first.group(1)), price=float(qty_first.group(2))))
            continue
        price_first = re.search(r"(?:¥|￥)\s*(\d+(?:\.\d+)?)\s*(?:/|每|起)?\s*(?:≥|>=)?\s*(\d+)(?:\s*[-~—]\s*\d+)?\s*(?:个|件|只|套|箱|包)", clean)
        if not price_first:
            price_first = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|块)\s*(?:/|每|起)?\s*(?:≥|>=)?\s*(\d+)(?:\s*[-~—]\s*\d+)?\s*(?:个|件|只|套|箱|包)", clean)
        if price_first:
            tiers.append(PriceTier(min_quantity=int(price_first.group(2)), price=float(price_first.group(1))))
    if tiers:
        deduped: dict[int, PriceTier] = {}
        for tier in tiers:
            deduped.setdefault(tier.min_quantity, tier)
        return sorted(deduped.values(), key=lambda tier: tier.min_quantity)
    text = _visible_text(soup)
    if not re.search(r"(?:¥|￥|\d+(?:\.\d+)?\s*(?:元|块))", text):
        return []
    price_match = re.search(r"(?:¥|￥)\s*(\d+(?:\.\d+)?)\s*(?:[-~—]\s*(?:¥|￥)?\s*(\d+(?:\.\d+)?))?", text)
    if not price_match:
        price_match = re.search(r"(\d+(?:\.\d+)?)\s*[-~—]\s*(\d+(?:\.\d+)?)\s*(?:元|块)", text)
    if not price_match:
        price_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|块)", text)
    if not price_match:
        return []
    min_quantity = 1
    if quantity_match := re.search(r"(\d+)\s*(?:个|件|只|套|箱|包)\s*起批", text):
        min_quantity = int(quantity_match.group(1))
    return [PriceTier(min_quantity=min_quantity, price=float(price_match.group(1)))]


def _extract_sku_options(embedded: dict) -> list[SkuOption]:
    sku_model = _dict(embedded.get("skuModel"))
    raw_options = embedded.get("skuOptions") or embedded.get("sku_options") or sku_model.get("skuProps") or embedded.get("skuProps") or []
    options: list[SkuOption] = []
    if isinstance(raw_options, list):
        for item in raw_options:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("prop")
            if not name:
                continue
            raw_values = item.get("values") or item.get("value") or []
            values: list[str] = []
            if isinstance(raw_values, list):
                for value in raw_values:
                    if isinstance(value, dict):
                        option_name = value.get("name") or value.get("value")
                        if option_name:
                            values.append(str(option_name))
                    else:
                        values.append(str(value))
            options.append(SkuOption(name=str(name), values=values))
    return options


def _extract_option_images(embedded: dict) -> list[str]:
    sku_model = _dict(embedded.get("skuModel"))
    raw_options = sku_model.get("skuProps") or embedded.get("skuProps") or []
    urls: list[str] = []
    if isinstance(raw_options, list):
        for item in raw_options:
            if not isinstance(item, dict):
                continue
            raw_values = item.get("value") or item.get("values") or []
            if not isinstance(raw_values, list):
                continue
            for value in raw_values:
                if isinstance(value, dict) and value.get("imageUrl"):
                    urls.append(str(value["imageUrl"]))
    return dedupe_urls(urls)


def _extract_seller(embedded: dict) -> SellerInfo | None:
    seller_raw = (
        _dict(embedded.get("seller"))
        or _dict(embedded.get("sellerModel"))
        or _dict(embedded.get("sellerDataInfo"))
        or _dict(embedded.get("shopInfo"))
        or _dict(embedded.get("companyInfo"))
        or _dict(embedded.get("memberModel"))
    )
    if not seller_raw:
        return None
    winport_urls = _dict(seller_raw.get("sellerWinportUrlMap"))
    signs = _dict(_dict(seller_raw.get("sellerSign")).get("signs"))
    badges = [key for key, enabled in signs.items() if enabled]
    name = seller_raw.get("name") or seller_raw.get("companyName") or seller_raw.get("shopName") or seller_raw.get("loginId") or seller_raw.get("memberName")
    url = seller_raw.get("url") or seller_raw.get("winportUrl") or seller_raw.get("shopUrl") or winport_urls.get("defaultUrl") or winport_urls.get("indexUrl")
    if not (name or url):
        return None
    return SellerInfo(
        name=str(name) if name else None,
        url=str(url) if url else None,
        score=_float(seller_raw.get("score") or seller_raw.get("tradeScore") or seller_raw.get("compositeServiceScore")),
        level=str(seller_raw.get("level") or seller_raw.get("sellerIdentity") or "") or None,
        location=str(seller_raw.get("location") or seller_raw.get("province") or "") or None,
        years_active=_int(seller_raw.get("yearsActive") or seller_raw.get("tpYear") or seller_raw.get("year")),
        badges=badges,
    )


def _extract_visible_seller(soup: BeautifulSoup) -> SellerInfo | None:
    lines = _text_lines(soup)
    text = _visible_text(soup)
    candidates: list[tuple[int, str]] = []
    skip_markers = ("供应商亮点", "功能亮点", "源头工厂", "支持OEM", "支持ODM", "月产", "跨境专供", "共")
    for line in lines[:160]:
        clean = re.sub(r"\s+", " ", line).strip()
        clean = re.sub(r"^(?:店铺|商家|供应商|厂家)\s+", "", clean)
        if not clean or len(clean) > 80:
            continue
        if "|" in clean or any(marker in clean for marker in skip_markers):
            continue
        score = 0
        if "有限公司" in clean:
            score += 100
        elif "公司" in clean:
            score += 80
        elif any(marker in clean for marker in ("工厂", "商行", "店铺", "店", "厂")):
            score += 40
        if score and re.search(r"[\u4e00-\u9fff]", clean):
            candidates.append((score - abs(len(clean) - 12), clean))
    if candidates:
        candidates.sort(reverse=True)
        seller_name = candidates[0][1]
        seller_years = None
        if match := re.search(r"(.+?)\s*(\d+)\s*年$", seller_name):
            seller_name = match.group(1).strip()
            seller_years = int(match.group(2))
        seller = SellerInfo(name=seller_name)
        if match := re.search(r"发货地\s*([^\n]+)", text):
            seller.location = match.group(1).strip()
        if match := re.search(r"(?:诚信通|开店|经营)\s*(\d+)\s*年", text):
            seller.years_active = int(match.group(1))
        elif seller_years is not None:
            seller.years_active = seller_years
        badges = []
        for badge in ("实力商家", "诚信通", "源头工厂", "48小时发货", "24小时发货"):
            if badge in text:
                badges.append(badge)
        seller.badges = badges
        return seller
    return None


def _category_from_attributes(attributes: dict[str, object]) -> str | None:
    for key in ("产品类别", "商品类别", "类目", "叶子类目", "分类"):
        value = attributes.get(key)
        if value:
            return str(value)
    return None


def _extract_category(embedded: dict) -> str | None:
    offer_model = _dict(embedded.get("offerModel"))
    category = embedded.get("category") or embedded.get("leafCategoryName") or offer_model.get("leafCategoryName")
    return str(category) if category else None


def _extract_stock(embedded: dict) -> int | None:
    trade_model = _dict(embedded.get("tradeModel"))
    trade_without_promotion = _dict(trade_model.get("tradeWithoutPromotion"))
    return _int(embedded.get("stock") or trade_model.get("canBookedAmount") or trade_without_promotion.get("canBookedAmountOriginal"))


def _extract_visible_stock(soup: BeautifulSoup) -> int | None:
    text = _visible_text(soup)
    for pattern in [
        r"(?:库存|可售|现货|剩余)\s*([0-9,.]+(?:万)?\+?)\s*(?:件|个|套|只|箱|包)?",
        r"([0-9,.]+(?:万)?\+?)\s*(?:件|个|套|只|箱|包)\s*(?:库存|可售|现货)",
    ]:
        if match := re.search(pattern, text):
            return _parse_chinese_count(match.group(1))
    return None


def _extract_trade_volume(embedded: dict) -> int | None:
    trade_model = _dict(embedded.get("tradeModel"))
    return _int(embedded.get("tradeVolume") or trade_model.get("saleCount"))


def _extract_visible_trade_volume(soup: BeautifulSoup) -> int | None:
    text = _visible_text(soup)
    for pattern in [
        r"一年内\s*([0-9,.]+(?:万)?\+?)\s*个成交",
        r"([0-9,.]+(?:万)?\+?)\s*个成交",
        r"已售\s*([0-9,.]+(?:万)?\+?)\s*(?:件|个)?",
        r"近30天销量\s*([0-9,.]+(?:万)?\+?)\s*(?:件|个)?",
        r"成交\s*([0-9,.]+(?:万)?\+?)\s*(?:件|个|单)?",
    ]:
        if match := re.search(pattern, text):
            return _parse_chinese_count(match.group(1))
    return None


def _extract_visible_month_sold(soup: BeautifulSoup) -> int | None:
    text = _visible_text(soup)
    for pattern in [
        r"30天成交\s*([0-9,.]+(?:万)?\+?)\s*(?:件|个|单)?",
        r"近30天销量\s*([0-9,.]+(?:万)?\+?)\s*(?:件|个|单)?",
        r"月销\s*([0-9,.]+(?:万)?\+?)\s*(?:件|个|单)?",
    ]:
        if match := re.search(pattern, text):
            return _parse_chinese_count(match.group(1))
    return None


def _extract_visible_repurchase_rate(soup: BeautifulSoup) -> float | None:
    text = _visible_text(soup)
    if match := re.search(r"(?:复购率|回头率|重复购买率)\s*([0-9]+(?:\.[0-9]+)?)\s*%", text):
        return float(match.group(1)) / 100
    return None


def _promote_main_images(main: list[str], detail: list[str]) -> tuple[list[str], list[str]]:
    if main:
        return dedupe_urls(main), dedupe_urls(detail)
    product_like: list[str] = []
    for url in detail:
        lowered = url.lower()
        if "/img/ibank/" not in lowered:
            continue
        if any(suffix in lowered for suffix in [".220x220", ".310x310", ".search", ".summ"]):
            continue
        product_like.append(url)
    promoted = dedupe_urls(product_like[:8])
    if not promoted:
        return [], dedupe_urls(detail)
    promoted_set = set(promoted)
    remaining_detail = [url for url in detail if url not in promoted_set]
    return promoted, dedupe_urls(remaining_detail)


def _iter_nested(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_nested(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_nested(child)


def _candidate_image_url(value: Any) -> str | None:
    if isinstance(value, str):
        if "alicdn.com" in value or "aliimg.com" in value:
            return value
        return None
    if not isinstance(value, dict):
        return None
    for key in [
        "url",
        "src",
        "poster",
        "fullPathImageURI",
        "imageUrl",
        "imageURL",
        "imageURI",
        "searchImageURI",
        "summImageURI",
        "size310x310ImageURI",
        "size220x220ImageURI",
        "originalImageURI",
    ]:
        raw = value.get(key)
        if isinstance(raw, str) and raw:
            return raw
    return None


def _extract_model_images(embedded: dict) -> tuple[list[str], list[str], list[str]]:
    main: list[str] = []
    detail: list[str] = []
    option: list[str] = []
    for node in _iter_nested(embedded):
        if not isinstance(node, dict):
            continue
        for key, value in node.items():
            lowered = str(key).lower()
            if not isinstance(value, (list, dict, str)):
                continue
            urls: list[str] = []
            if isinstance(value, list):
                urls = [url for item in value if (url := _candidate_image_url(item))]
            elif isinstance(value, dict) and (url := _candidate_image_url(value)):
                urls = [url]
            elif lowered in {"imageurl", "image_url", "picurl", "pic_url", "mainimageurl", "mainimageuri"} and (url := _candidate_image_url(value)):
                urls = [url]
            if not urls:
                continue
            if "sku" in lowered or "option" in lowered or "prop" in lowered:
                option.extend(urls)
            elif "detail" in lowered or "desc" in lowered:
                detail.extend(urls)
            elif "image" in lowered or "pic" in lowered:
                main.extend(urls)
    return dedupe_urls(main), dedupe_urls(detail), dedupe_urls(option)


def _merge_image_sources(assets: dict[str, list[str]], embedded: dict) -> dict[str, list[str]]:
    model_main, model_detail, model_option = _extract_model_images(embedded)
    return {
        "main_images": dedupe_urls(assets["main_images"] + model_main),
        "detail_images": dedupe_urls(assets["detail_images"] + model_detail),
        "option_images": dedupe_urls(assets["option_images"] + model_option),
        "videos": assets["videos"],
    }


def _extract_model_videos(embedded: dict) -> tuple[list[str], bool]:
    videos: list[str] = []
    metadata_seen = False
    for node in _iter_nested(embedded):
        if not isinstance(node, dict):
            continue
        if any(key in node for key in ["videoId", "videoUrl", "videoURL", "wirelessVideo", "videoUrls", "address"]):
            metadata_seen = True
        for key, value in node.items():
            lowered_key = str(key).lower()
            if "video" not in lowered_key and lowered_key != "address":
                continue
            values = value if isinstance(value, list) else [value]
            for item in values:
                if isinstance(item, str) and item:
                    if item.endswith(".swf"):
                        item = f"{item[:-4]}.mp4"
                    videos.append(item)
                elif isinstance(item, dict):
                    for nested_value in item.values():
                        if isinstance(nested_value, str) and nested_value:
                            if nested_value.endswith(".swf"):
                                nested_value = f"{nested_value[:-4]}.mp4"
                            videos.append(nested_value)
    _, normalized_videos = extract_urls_from_text(" ".join(videos))
    return dedupe_urls(normalized_videos), metadata_seen


def _build_detail_response(
    *,
    embedded: dict,
    soup: BeautifulSoup,
    html: str,
    assets: dict[str, list[str]],
    offer_id: str,
    source_url: str | None,
    source_path: Path | None,
    provider: str,
    source_type: str,
    warnings: list[str],
) -> DetailResponse:
    assets = _merge_image_sources(assets, embedded)
    title = (
        embedded.get("subject")
        or embedded.get("title")
        or _dict(embedded.get("offerModel")).get("subject")
        or (soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else None)
        or (soup.title.string.strip() if soup.title and soup.title.string else None)
        or f"1688 offer {offer_id}"
    )
    price_tiers = _extract_price_tiers(embedded) or _extract_visible_price_tiers(soup)
    seller = _extract_seller(embedded) or _extract_visible_seller(soup)
    main_images, detail_images = _promote_main_images(assets["main_images"], assets["detail_images"])
    option_images = dedupe_urls(assets["option_images"] + _extract_option_images(embedded))
    live_verified = _is_live_browser_capture(provider, source_url)
    attributes = _extract_attributes(soup, embedded)
    category = _extract_category(embedded) or _category_from_attributes(attributes)
    stock = _extract_stock(embedded) or _extract_visible_stock(soup)
    detail = ProductDetail(
        offer_id=offer_id,
        url=source_url or f"https://detail.1688.com/offer/{offer_id}.html",
        title_zh=str(title),
        title_ko_optional=embedded.get("subjectTrans") or embedded.get("titleTrans"),
        price_tiers=price_tiers,
        sku_options=_extract_sku_options(embedded),
        attributes=attributes,
        category=category,
        stock=stock,
        month_sold=_int(embedded.get("monthSold")) or _extract_visible_month_sold(soup),
        trade_volume=_extract_trade_volume(embedded) or _extract_visible_trade_volume(soup),
        repurchase_rate=_rate(embedded.get("repurchaseRate")) or _extract_visible_repurchase_rate(soup),
        seller=seller,
        main_image_urls=main_images,
        detail_image_urls=detail_images,
        option_image_urls=option_images,
        video_urls=assets["videos"],
        raw_source_summary={"provider": provider, "parser_version": PARSER_VERSION, "source_path": str(source_path) if source_path else None, "source_url": source_url},
        provider=provider,
        provider_version=PARSER_VERSION,
        live_verified=live_verified,
        source_type=source_type,  # type: ignore[arg-type]
        fetched_at=datetime.now(timezone.utc),
        raw_reference_path=str(source_path) if source_path else None,
        warnings=warnings,
    )
    missing = []
    for field in ["price_tiers", "main_image_urls", "detail_image_urls", "attributes", "seller", "category", "stock"]:
        value = getattr(detail, field)
        if not value:
            missing.append(field)
    detail.missing_fields = missing
    return DetailResponse(
        status="ok" if not missing else "partial_data",
        item=detail,
        provider=provider,
        provider_version=PARSER_VERSION,
        source_type=source_type,  # type: ignore[arg-type]
        live_verified=live_verified,
        fetched_at=datetime.now(timezone.utc),
        missing_fields=missing,
        raw_reference_path=str(source_path) if source_path else None,
        warnings=warnings,
    )


def parse_rendered_html(html: str, *, source_path: str | Path | None = None, source_url: str | None = None) -> DetailResponse:
    path = Path(source_path) if source_path else None
    soup = BeautifulSoup(html, "html.parser")
    embedded = merge_candidates(extract_embedded_json_candidates(soup, html))
    offer_id = str(embedded.get("offerId") or embedded.get("offer_id") or _extract_offer_id(html, path, source_url) or "")
    if not offer_id:
        message = "Could not extract 1688 offer_id from rendered HTML."
        return DetailResponse(status="partial_data", message=message, error=structured_error("invalid_offer_id", message), provider="local_html", provider_version=PARSER_VERSION, source_type="local_html", live_verified=False)
    assets = extract_assets(soup, html)
    warnings = []
    if not assets["videos"] and re.search(r"(videoId|videoUrl|wirelessVideo|rox-wap-detail-video)", html):
        warnings.append("Video metadata was present, but no downloadable video URL was exposed in this HTML. A logged-in rendered page or captured network response may be needed.")
    return _build_detail_response(
        embedded=embedded,
        soup=soup,
        html=html,
        assets=assets,
        offer_id=offer_id,
        source_url=source_url,
        source_path=path,
        provider="local_html",
        source_type="local_html",
        warnings=warnings,
    )


def parse_rendered_html_file(path: str | Path) -> DetailResponse:
    file_path = Path(path)
    return parse_rendered_html(file_path.read_text(encoding="utf-8"), source_path=file_path)


def parse_visible_page_snapshot(
    *,
    source_url: str,
    title: str | None = None,
    body_text: str = "",
    media_urls: list[str] | None = None,
) -> DetailResponse:
    media_tags: list[str] = []
    media_warnings: list[str] = []
    image_index = 0
    for url in media_urls or []:
        if not _is_expected_1688_media_url(str(url)):
            media_warnings.append(f"Skipped external media URL outside expected 1688/Alibaba hosts: {url}")
            continue
        escaped_url = html_escape(str(url), quote=True)
        lowered = str(url).lower()
        parsed = safe_urlparse(lowered)
        path = lowered.split("?", 1)[0]
        host = parsed.netloc if parsed else ""
        if path.endswith(VIDEO_EXTENSIONS) or "video" in host:
            media_tags.append(f'<video src="{escaped_url}"></video>')
        else:
            asset_type = "option" if "_sum" in lowered else "main" if image_index < 6 else "detail"
            media_tags.append(f'<img data-asset-type="{asset_type}" src="{escaped_url}">')
            image_index += 1
    text_nodes = "\n".join(f"<div>{html_escape(line)}</div>" for line in body_text.splitlines() if line.strip())
    html = "\n".join(
        [
            "<html>",
            "<head>",
            f"<title>{html_escape(title or '')}</title>",
            "</head>",
            "<body>",
            text_nodes,
            *media_tags,
            "</body>",
            "</html>",
        ]
    )
    response = parse_rendered_html(html, source_url=source_url)
    response.warnings.extend(media_warnings)
    response.provider = "chrome_devtools"
    response.source_type = "browser"
    response.live_verified = _is_live_browser_capture("chrome_devtools", source_url)
    if response.item is None and not response.live_verified:
        response.message = "Current page is not a 1688 offer page, or no 1688 offer_id was visible in the captured page."
        response.warnings.append("Open a 1688 detail page in Chrome, then capture the visible page again.")
    if response.item:
        response.item.provider = "chrome_devtools"
        response.item.source_type = "browser"
        response.item.live_verified = response.live_verified
        response.item.raw_source_summary["provider"] = "chrome_devtools"
        response.item.raw_source_summary["source_kind"] = "visible_page_snapshot"
        response.item.warnings.extend(media_warnings)
    return response


def _decode_payload(payload: str) -> Any:
    stripped = payload.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    match = re.match(r"^[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\((.*)\)\s*;?$", stripped, flags=re.DOTALL)
    if match:
        return json.loads(match.group(1))
    raise json.JSONDecodeError("Could not parse JSON or JSONP payload", stripped, 0)


def parse_network_payload(payload: str | dict | list, *, source_url: str | None = None, raw_reference_path: str | None = None) -> DetailResponse:
    live_verified = _is_live_browser_capture("chrome_devtools", source_url)
    try:
        data = _decode_payload(payload) if isinstance(payload, str) else payload
    except json.JSONDecodeError as exc:
        message = f"Could not parse captured 1688 network JSON: {exc}"
        return DetailResponse(status="partial_data", message=message, error=structured_error("parse_network_payload_failed", message), provider="chrome_devtools", provider_version=PARSER_VERSION, source_type="browser", live_verified=live_verified)

    candidates: list[dict[str, Any]] = []
    if isinstance(data, dict):
        candidates.append(data)
    candidates.extend(walk_json_candidates(data))
    embedded = merge_candidates(candidates)
    offer_id = str(embedded.get("offerId") or embedded.get("offer_id") or _dict(embedded.get("offerModel")).get("offerId") or _extract_offer_id("", None, source_url) or "")
    if not offer_id:
        message = "Could not extract 1688 offer_id from captured network payload."
        return DetailResponse(status="partial_data", message=message, error=structured_error("invalid_offer_id", message), provider="chrome_devtools", provider_version=PARSER_VERSION, source_type="browser", live_verified=live_verified)

    main_images, detail_images, option_images = _extract_model_images(embedded)
    videos, video_metadata_seen = _extract_model_videos(embedded)
    warnings: list[str] = []
    if video_metadata_seen and not videos:
        warnings.append("Video metadata was present in captured network data, but no downloadable video URL was exposed. Check offerWarnService/getVideoById responses from the logged-in Chrome tab.")

    assets = {
        "main_images": main_images,
        "detail_images": detail_images,
        "option_images": option_images,
        "videos": videos,
    }
    return _build_detail_response(
        embedded=embedded,
        soup=BeautifulSoup("", "html.parser"),
        html="",
        assets=assets,
        offer_id=offer_id,
        source_url=source_url,
        source_path=Path(raw_reference_path) if raw_reference_path else None,
        provider="chrome_devtools",
        source_type="browser",
        warnings=warnings,
    )
