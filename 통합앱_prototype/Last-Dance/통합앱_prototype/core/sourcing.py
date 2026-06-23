# -*- coding: utf-8 -*-
"""소싱 — 도매꾹 오픈API getItemList + 모의 폴백. 썸네일 URL 정규화 포함."""
import random
import re
import requests

from . import config

TIMEOUT = 12
API_URL = "https://domeggook.com/ssl/api/"
MARKUP = 2.6


def available() -> bool:
    return config.present("DOMEGGOOK_API_KEY")


def normalize_thumb(u, base="https://"):
    """썸네일 URL 정규화: '//' 겹침 제거, 스킴 보정."""
    if not u:
        return ""
    u = str(u).strip()
    if u.startswith("//"):
        u = "https:" + u
    if not re.match(r"^https?://", u):
        u = base + u.lstrip("/")
    m = re.match(r"^(https?://)(.*)$", u)
    if m:
        u = m.group(1) + re.sub(r"/{2,}", "/", m.group(2))
    return u


def _mock(keyword):
    random.seed("src" + keyword)
    suppliers = ["도매꾹", "도매매", "1688", "알리바바"]
    rows = []
    for i in range(6):
        cost = random.randint(1000, 9000)
        price = int(cost * random.uniform(2.2, 3.5) // 100 * 100)
        fee = int(price * 0.12) + 2500
        margin = price - cost - fee
        rows.append({"상품후보": keyword + " 후보 " + str(i + 1),
                     "공급처": random.choice(suppliers),
                     "사입원가": cost, "예상판매가": price, "부대비용": fee,
                     "예상마진": margin,
                     "점수": round(min(100, margin / price * 180), 1),
                     "출처": "모의", "링크": "", "썸네일": ""})
    return rows


def _to_int(v):
    try:
        return int(str(v).replace(",", "").strip() or 0)
    except Exception:
        return 0


def _pick(d, *names):
    for n in names:
        if isinstance(d, dict) and d.get(n) not in (None, ""):
            return d.get(n)
    return ""


def search(keyword):
    if not available():
        return _mock(keyword), False
    try:
        params = {"ver": "4.1", "mode": "getItemList",
                  "aid": config.get("DOMEGGOOK_API_KEY"), "market": "dome",
                  "om": "json", "kw": keyword, "sz": 20, "pg": 1, "so": "rd"}
        r = requests.get(API_URL, params=params, timeout=TIMEOUT)
        if r.status_code != 200:
            return _mock(keyword), False
        data = r.json()
        lst = ((data.get("domeggook") or {}).get("list") or {}).get("item", [])
        if isinstance(lst, dict):
            lst = [lst]
        if not isinstance(lst, list) or not lst:
            return _mock(keyword), False
        rows = []
        for it in lst[:20]:
            cost = _to_int(_pick(it, "price", "supplyPrice", "lowestPrice"))
            if cost <= 0:
                continue
            price = int(cost * MARKUP)
            fee = int(price * 0.12) + 2500
            margin = price - cost - fee
            rows.append({
                "상품후보": _pick(it, "title", "name") or keyword,
                "공급처": "도매꾹",
                "사입원가": cost, "예상판매가": price, "부대비용": fee,
                "예상마진": margin,
                "점수": round(min(100, (margin / price) * 180), 1) if price else 0.0,
                "출처": "도매꾹API",
                "링크": _pick(it, "url", "link"),
                "썸네일": normalize_thumb(_pick(it, "thumb", "thumbnail", "img")),
            })
        if not rows:
            return _mock(keyword), False
        rows.sort(key=lambda x: x["점수"], reverse=True)
        return rows, True
    except Exception:
        return _mock(keyword), False
