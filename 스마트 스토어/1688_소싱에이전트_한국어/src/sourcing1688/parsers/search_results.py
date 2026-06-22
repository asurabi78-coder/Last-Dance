from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sourcing1688 import __version__
from sourcing1688.utils import extract_offer_id


DEFAULT_CNY_KRW_RATE = 190.0

COMMON_BADGES = (
    "源头工厂",
    "实力商家",
    "超级工厂",
    "诚信通",
    "跨境专供",
    "支持OEM",
    "支持ODM",
    "一件代发",
    "48小时发货",
    "24小时发货",
    "现货",
    "工厂直供",
)


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for item in items:
        key = item.get("offer_id") or item.get("url") or item.get("title_zh")
        if not key or key in seen:
            continue
        seen.add(str(key))
        output.append(item)
    return output


def _raw_get(raw: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in raw and raw.get(key) not in {None, ""}:
            return raw.get(key)
    return None


def parse_chinese_count(value: str) -> int | None:
    text = value.replace(",", "").replace("＋", "+").strip()
    has_sales_signal = bool(re.search(r"成交|已售|销量|售出|卖出|全网", text))
    has_rate_signal = bool(re.search(r"复购|回头|回购|重复购买", text))
    if has_rate_signal and not has_sales_signal:
        return None
    patterns = [
        r"(?:成交|已售|销量|售出|卖出|全网)\D{0,12}?([0-9]+(?:\.[0-9]+)?)(万|千)?\+?\s*件?",
        r"([0-9]+(?:\.[0-9]+)?)(万|千)\+?\s*(?:件|单|人)?",
        r"(\d+(?:\.\d+)?)\+?\s*(?:件|单|人|个)",
    ]
    match = None
    unit = ""
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            unit = match.group(2) if len(match.groups()) >= 2 and match.group(2) else ""
            break
    if not match:
        return None
    number = float(match.group(1))
    if unit == "万":
        number *= 10000
    elif unit == "千":
        number *= 1000
    return int(number)


def _extract_price_range(*values: Any) -> tuple[float | None, float | None]:
    text = " ".join(_as_text(value) for value in values if value is not None)
    currency_numbers: list[str] = []
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*[-~—]\s*(\d+(?:\.\d+)?)\s*(?:元|块|CNY|RMB)", text, flags=re.IGNORECASE):
        currency_numbers.append(match.group(1))
        currency_numbers.append(match.group(2))
    for match in re.finditer(r"(?:¥|￥|CNY|RMB)\s*(\d+(?:\.\d+)?)(?:\s*[-~—]\s*(?:¥|￥)?\s*(\d+(?:\.\d+)?))?", text, flags=re.IGNORECASE):
        currency_numbers.append(match.group(1))
        if match.group(2):
            currency_numbers.append(match.group(2))
    currency_numbers.extend(re.findall(r"(\d+(?:\.\d+)?)\s*元", text))
    if not currency_numbers:
        before_moq = re.split(r"\d+\s*(?:件|个|只|套|箱|包)\s*(?:起批|起订|起购)", text, maxsplit=1)[0]
        currency_numbers = re.findall(r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)", before_moq)
        if not currency_numbers and re.search(r"起批|起订|起购", text):
            return None, None
    source_numbers = currency_numbers or re.findall(r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)", text)
    numbers = [float(item) for item in source_numbers]
    useful = [number for number in numbers if number >= 0.01]
    if not useful:
        return None, None
    if len(useful) == 1:
        return useful[0], useful[0]
    return min(useful[:4]), max(useful[:4])


def _extract_offer_id(url: str) -> str | None:
    if not url:
        return None
    try:
        return extract_offer_id(url)
    except ValueError:
        return None
    return None


def _canonical_url(url: str, offer_id: str | None) -> str | None:
    if offer_id:
        return f"https://detail.1688.com/offer/{offer_id}.html"
    return url or None


def _is_1688_url(url: str) -> bool:
    try:
        candidate = url
        if url and not re.match(r"^[a-z][a-z0-9+.-]*://", url, flags=re.IGNORECASE) and re.match(r"^[^/\s]+\.[^/\s]+/", url):
            candidate = f"https://{url}"
        host = (urlparse(candidate).hostname or "").lower()
    except ValueError:
        return False
    return host == "1688.com" or host.endswith(".1688.com")


def _extract_repurchase_rate(*values: Any) -> float | None:
    text = " ".join(_as_text(value) for value in values if value is not None)
    match = re.search(r"(?:回头率|复购率|回购率)\s*([0-9]+(?:\.[0-9]+)?)\s*%", text)
    if not match:
        return None
    return float(match.group(1)) / 100


def _extract_badges(*values: Any) -> list[str]:
    text = " ".join(_as_text(value) for value in values if value is not None)
    badges: list[str] = []
    for badge in COMMON_BADGES:
        if badge in text:
            badges.append(badge)
    badges.extend(re.findall(r"(?:回头率|复购率|回购率)\s*[0-9]+(?:\.[0-9]+)?%", text))
    badges.extend(re.findall(r"(?:已售|全网|成交)\s*[0-9]+(?:\.[0-9]+)?[万千]?\+?件?", text))
    return list(dict.fromkeys(badges))


def _krw(value: float | None, rate: float) -> int | None:
    return int(round(value * rate)) if value is not None else None


def _category_hint(title: str, keyword: str) -> str | None:
    source = f"{keyword} {title}"
    hints = [
        (("防水袋", "防水包", "手机防水袋", "手机防水包", "防水套"), "방수 파우치/방수팩 후보"),
        (("旅行", "旅游", "收纳", "洗漱", "行李", "护照", "分装瓶"), "여행/수납 관련 후보"),
        (("手机", "支架", "车载", "桌面", "懒人支架"), "스마트폰 거치/차량용 액세서리 후보"),
        (("伞", "防晒", "遮阳", "晴雨", "黑胶"), "우산/자외선 차단 관련 후보"),
        (("宠物", "猫", "狗", "牵引", "胸背", "猫咪"), "반려동물 용품 후보"),
        (("运动", "跑步", "健身", "户外", "露营"), "스포츠/아웃도어 관련 후보"),
        (("包装", "纸袋", "食品袋", "手提袋"), "포장/소모품 관련 후보"),
    ]
    for terms, summary in hints:
        if any(term in source for term in terms):
            return summary
    return None


def _why_candidate(sold_count: int | None, price_min: float | None, seller: str, badges: list[str]) -> list[str]:
    notes: list[str] = []
    if sold_count and sold_count >= 10000:
        notes.append("판매 신호가 매우 높아 수요 검증용 후보로 볼 수 있습니다.")
    elif sold_count and sold_count >= 1000:
        notes.append("판매량이 확인되어 테스트 후보로 검토할 수 있습니다.")
    if price_min is not None and price_min <= 10:
        notes.append("표시 단가가 낮아 샘플 테스트와 마진 검토가 쉽습니다.")
    elif price_min is not None:
        notes.append("표시 가격 기준으로 국내 판매가와 마진을 바로 비교할 수 있습니다.")
    if seller:
        notes.append("판매자명이 확인되어 상점 상세 검증으로 이어갈 수 있습니다.")
    if badges:
        notes.append("검색 카드에서 판매/배송/상점 관련 신호가 일부 확인됩니다.")
    if not notes:
        notes.append("검색 결과에서 노출된 후보입니다. 상세페이지에서 MOQ, 옵션, 판매자 신뢰도를 확인해야 합니다.")
    return notes


def _normalize_item(raw: dict[str, Any], *, rank: int, keyword: str, rate: float) -> dict[str, Any] | None:
    title = _as_text(_raw_get(raw, "title", "title_zh", "titleZh", "name", "标题", "商品标题", "商品名", "名称"))
    url = _as_text(_raw_get(raw, "url", "href", "product_url", "productUrl", "链接", "商品链接", "详情链接"))
    if not title and not url:
        return None
    raw_offer_id = _as_text(_raw_get(raw, "offer_id", "offerId"))
    if raw_offer_id and (not url or _is_1688_url(url)):
        try:
            offer_id = extract_offer_id(raw_offer_id)
        except ValueError:
            offer_id = raw_offer_id if re.fullmatch(r"\d{6,}", raw_offer_id) else None
    else:
        offer_id = _extract_offer_id(url)
    price_text = _as_text(_raw_get(raw, "price_text", "priceText", "price", "price_cny", "priceCny", "价格", "价格范围", "价格区间", "价格文本", "单价"))
    sold_text = _as_text(_raw_get(raw, "sold_text", "soldText", "sales_text", "salesText", "month_sold_text", "monthSoldText", "trade_text", "tradeText", "成交", "销量", "已售", "月销量"))
    seller = _as_text(_raw_get(raw, "seller_name", "sellerName", "seller", "shop_name", "shopName", "店铺", "店铺名", "卖家", "商家", "供应商"))
    image_url = _as_text(_raw_get(raw, "image_url", "imageUrl", "image", "img", "图片", "图片链接", "主图"))
    raw_text = _as_text(raw.get("raw_text") or raw.get("text") or " ".join(str(value) for value in raw.values() if not isinstance(value, (dict, list))))
    badges = raw.get("badges") if isinstance(raw.get("badges"), list) else []
    badges = [_as_text(badge) for badge in badges if _as_text(badge)]
    badges = list(dict.fromkeys(badges + _extract_badges(raw_text, title)))
    price_min, price_max = _extract_price_range(raw.get("price_cny_min"), raw.get("price_cny_max"), price_text)
    sold_count = parse_chinese_count(sold_text)
    repurchase_rate = raw.get("repurchase_rate")
    if repurchase_rate is None:
        repurchase_rate = _extract_repurchase_rate(raw_text, " ".join(badges))
    return {
        "rank": rank,
        "offer_id": offer_id or None,
        "url": _canonical_url(url, offer_id),
        "raw_url": url or None,
        "title_zh": title or None,
        "title_ko_summary": _category_hint(title, keyword),
        "agent_description_instruction": "Translate the Chinese title and visible card context into a Korean seller-facing product description before presenting it.",
        "image_url": image_url or None,
        "price_text": price_text or None,
        "price_cny_min": price_min,
        "price_cny_max": price_max,
        "price_krw_min": _krw(price_min, rate),
        "price_krw_max": _krw(price_max, rate),
        "sold_text": sold_text or None,
        "sold_count": sold_count,
        "seller_name": seller or None,
        "repurchase_rate": repurchase_rate,
        "badges": badges,
        "why_candidate": _why_candidate(sold_count, price_min, seller, badges),
        "next_check": [
            "상세페이지에서 MOQ, 옵션, 재고, 배송 가능 수량을 확인하세요.",
            "리뷰, 재구매율, 상점 점수, 실제 이미지/영상 품질을 확인한 뒤 샘플 발주 여부를 판단하세요.",
        ],
    }


def _rate_from_env() -> tuple[float, str]:
    raw = os.environ.get("SOURCING1688_CNY_KRW_RATE")
    if raw:
        try:
            return float(raw), "env:SOURCING1688_CNY_KRW_RATE"
        except ValueError:
            pass
    return DEFAULT_CNY_KRW_RATE, "default_estimate"


def parse_search_results_snapshot(
    *,
    keyword: str,
    source_url: str,
    items: list[dict[str, Any]],
    cny_krw_rate: float | None = None,
    min_items: int = 10,
) -> dict[str, Any]:
    rate, rate_source = (float(cny_krw_rate), "provided") if cny_krw_rate is not None else _rate_from_env()
    normalized: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        if item := _normalize_item(raw, rank=len(normalized) + 1, keyword=keyword, rate=rate):
            normalized.append(item)
    normalized = _dedupe(normalized)
    for index, item in enumerate(normalized, start=1):
        item["rank"] = index
    warnings: list[str] = []
    if len(normalized) < min_items:
        warnings.append(f"Visible search snapshot contained {len(normalized)} candidates; expected at least {min_items}. Scroll/load more results and capture again.")
    is_1688_source = _is_1688_url(source_url)
    if not is_1688_source:
        warnings.append("Source URL is not a 1688 host, so this parser output is not marked as live 1688 data.")
    return {
        "status": "ok" if normalized else "partial_data",
        "provider": "chrome_devtools",
        "provider_version": __version__,
        "source_type": "browser",
        "live_verified": is_1688_source,
        "capture_status": "browser_capture_1688_url" if is_1688_source else "unverified_source_url",
        "keyword": keyword,
        "source_url": source_url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(normalized),
        "minimum_expected": min_items,
        "cny_krw_rate": rate,
        "rate_source": rate_source,
        "currency_note": "KRW prices are estimates from the supplied or configured CNY/KRW rate.",
        "items": normalized,
        "warnings": warnings,
    }
