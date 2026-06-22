from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_from_bytes, quote_plus, urlparse

from pydantic import BaseModel

from sourcing1688.models import StructuredError


OFFER_ID_PATTERN = re.compile(r"(?:offer/)?(?P<offer_id>\d{6,})(?:\.html)?")

PINYIN_HINTS = {
    "黑": "hei",
    "胶": "jiao",
    "防": "fang",
    "晒": "shai",
    "晴": "qing",
    "雨": "yu",
    "伞": "san",
    "三": "san",
    "折": "zhe",
    "遮": "zhe",
    "阳": "yang",
    "紫": "zi",
    "外": "wai",
    "线": "xian",
    "厨": "chu",
    "房": "fang",
    "收": "shou",
    "纳": "na",
    "盒": "he",
    "风": "feng",
    "扇": "shan",
    "灯": "deng",
    "硅": "gui",
    "餐": "can",
}


def extract_offer_id(value: str) -> str:
    value = value.strip()
    if re.fullmatch(r"\d{6,}", value):
        return value

    candidates = [value]
    if not re.match(r"^[a-z][a-z0-9+.-]*://", value, flags=re.IGNORECASE) and re.match(r"^[^/\s]+\.[^/\s]+/", value):
        candidates.insert(0, f"https://{value}")

    for candidate in candidates:
        try:
            parsed = urlparse(candidate)
        except ValueError:
            continue
        host = (parsed.hostname or "").lower()
        if host and not (host == "1688.com" or host.endswith(".1688.com")):
            continue
        if match := re.search(r"(?:^|/)offer/(?P<offer_id>\d{6,})(?:\.html)?(?:$|[/?#])", parsed.path):
            return match.group("offer_id")
        if host:
            query = parse_qs(parsed.query)
            for key in ("offerId", "offerIds", "offer_id"):
                for item in query.get(key, []) + query.get(key.lower(), []):
                    if re.fullmatch(r"\d{6,}", item):
                        return item

    if not re.search(r"://|^[^/\s]+\.[^/\s]+", value):
        query_match = re.search(r"(?:offerId|offerIds|offer_id)=(?P<offer_id>\d{6,})", value, flags=re.IGNORECASE)
        if query_match:
            return query_match.group("offer_id")

    raise ValueError(f"Could not extract 1688 offer_id from: {value}")


def encode_1688_search_keyword(keyword: str) -> str:
    """Encode search keywords the way the 1688 search page expects."""
    normalized = keyword.strip()
    try:
        return quote_from_bytes(normalized.encode("gbk"))
    except UnicodeEncodeError:
        return quote_plus(normalized)


def sanitize_filename(value: str, max_length: int = 120) -> str:
    value = value.strip().replace("\\", "-").replace("/", "-")
    value = re.sub(r"[\r\n\t]+", " ", value)
    value = re.sub(r'[<>:"|?*]+', "-", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" .-_")
    if not value:
        return "asset"
    return value[:max_length].strip(" .-_")


def slugify(value: str, fallback: str = "item", max_length: int = 80) -> str:
    tokens: list[str] = []
    current: list[str] = []
    for char in value:
        if char in PINYIN_HINTS:
            if current:
                tokens.append("".join(current))
                current = []
            tokens.append(PINYIN_HINTS[char])
        else:
            normalized = unicodedata.normalize("NFKD", char)
            ascii_part = normalized.encode("ascii", "ignore").decode("ascii").lower()
            if ascii_part and re.match(r"[a-z0-9]", ascii_part):
                current.append(ascii_part)
            else:
                if current:
                    tokens.append("".join(current))
                    current = []
    if current:
        tokens.append("".join(current))
    slug = "-".join(tokens)
    slug = re.sub(r"[^a-z0-9-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        slug = fallback
    return slug[:max_length].strip("-") or fallback


def jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value


def dumps_json(value: Any) -> str:
    return json.dumps(jsonable(value), ensure_ascii=False, indent=2)


def structured_error(
    code: str,
    message: str,
    *,
    needs_human_action: bool = False,
    suggested_action: str | None = None,
    details: dict[str, Any] | None = None,
) -> StructuredError:
    return StructuredError(
        code=code,
        message=message,
        needs_human_action=needs_human_action,
        suggested_action=suggested_action,
        details=details or {},
    )


def error_payload(
    code: str,
    message: str,
    *,
    status: str = "error",
    needs_human_action: bool = False,
    suggested_action: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "needs_human_action": needs_human_action,
        "suggested_action": suggested_action,
        "error": structured_error(
            code=code,
            message=message,
            needs_human_action=needs_human_action,
            suggested_action=suggested_action,
            details=details or {},
        ).model_dump(mode="json"),
    }
