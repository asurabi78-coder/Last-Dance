# -*- coding: utf-8 -*-
"""네이버 검색광고 keywordstool(검색량·경쟁도) + 쇼핑 상품수/경쟁률 + 상품화 점수/등급."""
import base64
import hashlib
import hmac
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

from . import config

SEARCHAD_BASE = "https://api.searchad.naver.com"
SHOP_URL = "https://openapi.naver.com/v1/search/shop.json"
TIMEOUT = 10
SHOP_MAX_WORKERS = 4     # 쇼핑 상품수 동시 조회 수(rate limit 보호)

# 점수 가중치(조정 가능)
W_VOL, W_COMP, W_RATIO = 0.40, 0.30, 0.30
VOL_CAP = 30000          # 월검색량 만점 기준
COMP_MAP = {"낮음": 0.2, "중간": 0.5, "높음": 0.85}


def _clean(kw):
    return re.sub(r"\s+", "", str(kw)).strip()


def _num(v):
    try:
        if v in ("", "< 10", None):
            return 0
        return int(str(v).replace(",", "").replace("<", "").strip())
    except Exception:
        return 0


def _signature(ts, method, uri, secret):
    msg = f"{ts}.{method}.{uri}"
    return base64.b64encode(hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest()).decode()


def _headers(method, uri):
    ts = str(round(time.time() * 1000))
    return {"Content-Type": "application/json; charset=UTF-8", "X-Timestamp": ts,
            "X-API-KEY": config.get("NAVER_AD_ACCESS_LICENSE"),
            "X-Customer": config.get("NAVER_AD_CUSTOMER_ID"),
            "X-Signature": _signature(ts, method, uri, config.get("NAVER_AD_SECRET_KEY"))}


def available():
    return all(config.present(k) for k in
               ["NAVER_AD_ACCESS_LICENSE", "NAVER_AD_SECRET_KEY", "NAVER_AD_CUSTOMER_ID"])


def shopping_available():
    return config.present("NAVER_CLIENT_ID") and config.present("NAVER_CLIENT_SECRET")


def _grade(score):
    return "A" if score >= 70 else ("B" if score >= 45 else "C")


def _base_score(total, comp_label):
    vol = min(1.0, total / VOL_CAP)
    comp = 1 - COMP_MAP.get(comp_label, 0.5)
    # 상품수 없을 때: 검색량/경쟁도만 (비중 재배분)
    return round(100 * (0.55 * vol + 0.45 * comp), 1)


def _full_score(total, comp_label, product_cnt):
    vol = min(1.0, total / VOL_CAP)
    comp = 1 - COMP_MAP.get(comp_label, 0.5)
    ratio = (product_cnt / total) if total else 999      # 경쟁률(낮을수록 좋음)
    ratio_score = max(0.0, min(1.0, 1 - ratio / 3))      # ratio 0→1, 3이상→0
    return round(100 * (W_VOL * vol + W_COMP * comp + W_RATIO * ratio_score), 1)


def related_keywords(keyword):
    uri = "/keywordstool"
    params = {"hintKeywords": _clean(keyword), "showDetail": "1"}
    r = requests.get(SEARCHAD_BASE + uri, headers=_headers("GET", uri), params=params, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"검색광고 API {r.status_code}: {r.text[:160]}")
    rows = []
    for it in r.json().get("keywordList", []):
        kw = str(it.get("relKeyword", "")).strip()
        if not kw:
            continue
        total = _num(it.get("monthlyPcQcCnt")) + _num(it.get("monthlyMobileQcCnt"))
        comp = it.get("compIdx", "")
        rows.append({"키워드": kw, "월검색량": total, "경쟁도": comp,
                     "상품수": None, "경쟁률": None,
                     "상품화점수": _base_score(total, comp), "등급": ""})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.drop_duplicates("키워드").sort_values("월검색량", ascending=False).reset_index(drop=True)
    df["등급"] = df["상품화점수"].map(_grade)
    return df


def shopping_total(keyword):
    """키워드의 네이버 쇼핑 등록상품수(total)."""
    r = requests.get(SHOP_URL, params={"query": keyword, "display": 1},
                     headers={"X-Naver-Client-Id": config.get("NAVER_CLIENT_ID"),
                              "X-Naver-Client-Secret": config.get("NAVER_CLIENT_SECRET")},
                     timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"쇼핑 API {r.status_code}: {r.text[:120]}")
    return int(r.json().get("total", 0))


def enrich_with_shopping(df, top_n=15):
    """상위 top_n 키워드에 상품수·경쟁률·고도화 점수/등급 채움(호출량 제한)."""
    if df is None or df.empty or not shopping_available():
        return df
    df = df.copy()
    idxs = list(df.head(top_n).index)
    # 네트워크 호출(shopping_total)만 동시 처리. DataFrame 갱신은 메인 스레드에서 수행.
    counts = {}
    with ThreadPoolExecutor(max_workers=SHOP_MAX_WORKERS) as ex:
        fut_to_idx = {ex.submit(shopping_total, df.at[i, "키워드"]): i for i in idxs}
        for fut in as_completed(fut_to_idx):
            i = fut_to_idx[fut]
            try:
                counts[i] = fut.result()
            except Exception:
                continue   # 실패 키워드는 건너뜀(기존 동작과 동일)
    for i in idxs:
        if i not in counts:
            continue
        cnt = counts[i]
        total = df.at[i, "월검색량"] or 0
        df.at[i, "상품수"] = cnt
        df.at[i, "경쟁률"] = round(cnt / total, 2) if total else None
        df.at[i, "상품화점수"] = _full_score(total, df.at[i, "경쟁도"], cnt)
        df.at[i, "등급"] = _grade(df.at[i, "상품화점수"])
    return df.sort_values("상품화점수", ascending=False).reset_index(drop=True)
