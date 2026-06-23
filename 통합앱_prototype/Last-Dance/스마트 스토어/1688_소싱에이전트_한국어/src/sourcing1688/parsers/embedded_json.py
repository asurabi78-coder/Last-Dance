from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup


INTERESTING_KEYS = {
    "offerId",
    "offer_id",
    "subject",
    "price",
    "priceInfo",
    "priceRange",
    "priceRanges",
    "skuOptions",
    "monthSold",
    "saleCount",
    "beginAmount",
    "offerModel",
    "sellerDataInfo",
    "shopInfo",
    "companyInfo",
    "memberModel",
    "sellerModel",
    "skuModel",
    "tradeModel",
    "imageList",
    "images",
}

BALANCED_VALUE_KEYS = [
    "globalData",
    "offerModel",
    "sellerDataInfo",
    "shopInfo",
    "companyInfo",
    "memberModel",
    "sellerModel",
    "skuModel",
    "tradeModel",
    "imageList",
    "images",
]


def _walk_json(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if any(key in value for key in INTERESTING_KEYS):
            found.append(value)
        for child in value.values():
            found.extend(_walk_json(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_json(child))
    return found


def walk_json_candidates(value: Any) -> list[dict[str, Any]]:
    return _walk_json(value)


def _balanced_json_slice(text: str, start: int) -> str | None:
    opener = text[start]
    closer = "}" if opener == "{" else "]" if opener == "[" else None
    if closer is None:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _extract_balanced_key_values(text: str, key: str) -> list[Any]:
    values: list[Any] = []
    pattern = f'"{key}"'
    cursor = 0
    while True:
        key_index = text.find(pattern, cursor)
        if key_index == -1:
            break
        cursor = key_index + len(pattern)
        colon_index = text.find(":", cursor)
        if colon_index == -1:
            continue
        value_index = colon_index + 1
        while value_index < len(text) and text[value_index].isspace():
            value_index += 1
        if value_index >= len(text) or text[value_index] not in "{[":
            continue
        raw = _balanced_json_slice(text, value_index)
        if not raw:
            continue
        try:
            values.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return values


def extract_embedded_json_candidates(soup: BeautifulSoup, html: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for script in soup.find_all("script"):
        text = script.string or script.get_text() or ""
        text = text.strip()
        if not text:
            continue
        if script.get("type") == "application/json":
            try:
                candidates.extend(_walk_json(json.loads(text)))
                continue
            except json.JSONDecodeError:
                pass
        for match in re.finditer(r"(?:window\.)?[A-Za-z0-9_$]+\s*=\s*[\{\[]", text):
            value_start = text.find(match.group(0).rstrip()[-1], match.start())
            raw = _balanced_json_slice(text, value_start)
            if not raw:
                continue
            try:
                candidates.extend(_walk_json(json.loads(raw)))
            except json.JSONDecodeError:
                continue
        interesting_pattern = "|".join(re.escape(key) for key in INTERESTING_KEYS)
        for match in re.finditer(r"\{[^{}]*(?:" + interesting_pattern + r")[\s\S]*?\}", text):
            raw = match.group(0)
            try:
                candidates.extend(_walk_json(json.loads(raw)))
            except json.JSONDecodeError:
                continue
        for key in BALANCED_VALUE_KEYS:
            for value in _extract_balanced_key_values(text, key):
                candidates.append({key: value})
                candidates.extend(_walk_json(value))
    return candidates


def merge_candidates(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for candidate in candidates:
        for key, value in candidate.items():
            if value not in (None, "", [], {}) and key not in merged:
                merged[key] = value
    return merged
