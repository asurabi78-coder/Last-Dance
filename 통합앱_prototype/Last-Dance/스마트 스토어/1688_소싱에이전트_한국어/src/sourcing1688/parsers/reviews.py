from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sourcing1688 import __version__


REVIEW_TAG_TERMS = (
    "质量",
    "包装",
    "发货",
    "做工",
    "好评",
    "有内容",
    "物流",
    "服务",
    "颜色",
    "尺寸",
    "材质",
    "态度",
    "回购",
)

REVIEW_UI_MARKERS = (
    "采购商评价",
    "买家评价",
    "综合评价",
    "全部评价",
    "好评率",
    "有内容",
    "暂无更多评价",
    "暂无评价",
    "暂无有效评价",
    "还没有评价",
    "暂无相关评价",
    "未找到符合您筛选的记录",
)

EMPTY_REVIEW_MARKERS = ("暂无更多评价", "暂无评价", "暂无有效评价", "还没有评价", "暂无相关评价", "未找到符合您筛选的记录")


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _loads(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return None


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _extract_summary_tags(text: str) -> list[dict[str, Any]]:
    tags: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if not clean or len(clean) > 50:
            continue
        match = re.search(r"([\u4e00-\u9fffA-Za-z0-9]{2,24})\s+(\d{1,6})$", clean)
        if not match:
            continue
        label = match.group(1).strip()
        if not label or label in seen:
            continue
        if not any(term in label for term in REVIEW_TAG_TERMS):
            continue
        seen.add(label)
        tags.append({"label_zh": label, "count": int(match.group(2))})
    return tags


def _extract_review_texts(text: str) -> list[str]:
    reviews: list[str] = []
    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if len(clean) < 12 or len(clean) > 240:
            continue
        if any(marker in clean for marker in REVIEW_UI_MARKERS):
            continue
        if re.search(r"[\u4e00-\u9fff]", clean):
            reviews.append(clean)
    return list(dict.fromkeys(reviews))[:20]


def _extract_review_summary(text: str) -> dict[str, Any]:
    normalized = re.sub(r"\s+", " ", text)
    score = None
    review_count_text = None
    positive_rate = None
    content_review_count_text = None
    if match := re.search(r"(?:综合评价|综合评分|评分)\s*([0-9](?:\.[0-9])?)", normalized):
        score = float(match.group(1))
    elif match := re.search(r"\b([0-5](?:\.[0-9])?)\s+(?:[0-9]+\+?条评价|好评率)", normalized):
        score = float(match.group(1))
    if match := re.search(r"([0-9]+(?:\.[0-9]+)?万?\+?)\s*条评价", normalized):
        review_count_text = match.group(1)
    if match := re.search(r"好评率\s*([0-9]+(?:\.[0-9]+)?)\s*%", normalized):
        positive_rate = float(match.group(1)) / 100
    if match := re.search(r"有内容\s*([0-9]+(?:\.[0-9]+)?万?\+?)", normalized):
        content_review_count_text = match.group(1)
    return {
        "score": score,
        "review_count_text": review_count_text,
        "positive_rate": positive_rate,
        "content_review_count_text": content_review_count_text,
    }


def _payload_signal(payload: str) -> dict[str, Any]:
    signal: dict[str, Any] = {
        "service": None,
        "status": None,
        "message": None,
        "review_count": None,
        "video_id_seen": False,
    }
    raw = payload[:4000]
    lowered = raw.lower()
    if "queryitemratedlist" in lowered:
        signal["service"] = "queryItemRatedList"
    elif "querydsrratedata" in lowered:
        signal["service"] = "queryDsrRateData"
    elif "offerdetail" in lowered or "offerwarnservice" in lowered:
        signal["service"] = "offerDetail"
    if "system_error" in lowered:
        signal["status"] = "system_error"
    elif '"success"' in lowered or '"ok"' in lowered or "resultcode" in lowered:
        signal["status"] = "ok_or_success"
    if "videoid" in lowered:
        signal["video_id_seen"] = True

    data = _loads(payload)
    if data is not None:
        for node in _walk(data):
            if signal["message"] is None:
                msg = node.get("message") or node.get("msg") or node.get("errorMessage")
                if msg:
                    signal["message"] = str(msg)
            if signal["review_count"] is None:
                for key in ("total", "totalCount", "rateCount", "count"):
                    value = node.get(key)
                    if isinstance(value, int):
                        signal["review_count"] = value
                        break
    return signal


def _is_1688_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return host == "1688.com" or host.endswith(".1688.com")


def parse_review_snapshot(
    *,
    source_url: str,
    body_text: str = "",
    network_payloads: list[str] | None = None,
) -> dict[str, Any]:
    text = _as_text(body_text)
    review_summary = _extract_review_summary(text)
    summary_tags = _extract_summary_tags(text)
    review_texts = _extract_review_texts(text)
    empty_markers = [marker for marker in EMPTY_REVIEW_MARKERS if marker in text]
    signals = [_payload_signal(payload) for payload in network_payloads or [] if _as_text(payload)]
    warnings: list[str] = []
    if empty_markers and summary_tags:
        warnings.append("리뷰 태그는 보이지만 개별 리뷰 목록은 현재 화면 또는 네트워크 응답에서 비어 있습니다.")
    elif empty_markers:
        warnings.append("현재 화면에서 개별 리뷰 목록이 비어 있습니다.")
    if any(signal.get("status") == "system_error" for signal in signals):
        warnings.append("리뷰 목록 API 응답 중 system_error가 있어 Chrome 화면의 리뷰 요약과 다른 네트워크 응답을 함께 확인해야 합니다.")
    is_1688_source = _is_1688_url(source_url)
    if not is_1688_source:
        warnings.append("Source URL is not a 1688 host, so this parser output is not marked as live 1688 data.")

    summary_has_data = any(value is not None for value in review_summary.values())
    status = "ok" if summary_has_data or summary_tags or review_texts else "partial_data"
    review_list_status = "available" if review_texts else ("empty" if empty_markers else "unknown")
    return {
        "status": status,
        "provider": "chrome_devtools",
        "provider_version": __version__,
        "source_type": "browser",
        "live_verified": is_1688_source,
        "capture_status": "browser_capture_1688_url" if is_1688_source else "unverified_source_url",
        "source_url": source_url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "review_summary": review_summary,
        "summary_tags": summary_tags,
        "review_texts": review_texts,
        "review_list_status": review_list_status,
        "empty_markers": empty_markers,
        "network_signals": signals,
        "warnings": warnings,
        "seller_notes": [
            "리뷰 태그는 상품 반응의 방향성을 보는 참고 자료로 사용하세요.",
            "개별 리뷰 목록이 비어 있으면 옵션, 필터, 로그인 상태, Chrome 네트워크 응답을 다시 확인하세요.",
        ],
    }
