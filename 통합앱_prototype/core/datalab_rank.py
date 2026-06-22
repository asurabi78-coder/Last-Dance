# -*- coding: utf-8 -*-
"""네이버 데이터랩 쇼핑인사이트 — 분야별 인기검색어 TOP.
A) 비공식 엔드포인트(getCategoryKeywordRank): 화면의 TOP 리스트를 그대로 가져옴(약관 리스크·깨질 수 있음)
B) 공식 DataLab 폴백: 분야 트렌드(검색 키 기반) — TOP 리스트는 아니지만 안정적
※ 비공식 호출 실패 시 자동으로 폴백 메시지/모의로 떨어진다.
"""
import datetime as _dt
import requests

from . import config

RANK_URL = "https://datalab.naver.com/shoppingInsight/getCategoryKeywordRank.naver"

# 네이버 쇼핑 대분류 카테고리 cid (공개적으로 알려진 표준 분류)
CATEGORY_CID = {
    "패션의류": "50000000", "패션잡화": "50000001", "화장품/미용": "50000002",
    "디지털/가전": "50000003", "가구/인테리어": "50000004", "출산/육아": "50000005",
    "식품": "50000006", "스포츠/레저": "50000007", "생활/건강": "50000008",
    "여가/생활편의": "50000009",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://datalab.naver.com/shoppingInsight/sCategory.naver",
    "X-Requested-With": "XMLHttpRequest",
}


def categories():
    return list(CATEGORY_CID.keys())


def _parse_ranks(data):
    """엔드포인트 JSON → [{'순위':int,'키워드':str}]. 응답 구조 변화에 방어적."""
    ranks = []
    if isinstance(data, dict):
        ranks = data.get("ranks") or (data.get("data") or [{}])[0].get("ranks", []) \
            if isinstance(data.get("data"), list) else data.get("ranks", [])
    rows = []
    for it in (ranks or []):
        kw = str(it.get("keyword", "")).strip()
        if not kw:
            continue
        rows.append({"순위": int(it.get("rank", len(rows) + 1)), "키워드": kw})
    return rows


def popular_keywords(category_name, count=20, days=30):
    """비공식 엔드포인트로 분야별 인기검색어 TOP 조회. 실패 시 예외."""
    cid = CATEGORY_CID.get(category_name)
    if not cid:
        raise ValueError("알 수 없는 분야: " + str(category_name))
    end = _dt.date.today()
    start = end - _dt.timedelta(days=days)
    params = {"cid": cid, "timeUnit": "date",
              "startDate": start.isoformat(), "endDate": end.isoformat(),
              "age": "", "gender": "", "device": "", "page": "1", "count": str(count)}
    r = requests.post(RANK_URL, headers=HEADERS, data=params, timeout=12)
    if r.status_code != 200:
        raise RuntimeError(f"데이터랩 {r.status_code}: {r.text[:120]}")
    rows = _parse_ranks(r.json())
    if not rows:
        raise RuntimeError("인기검색어 응답이 비어있음(구조 변경 가능)")
    return rows


def get_top(category_name, count=20):
    """(rows, source). 비공식 성공 시 source='데이터랩 인기검색어', 실패 시 ([], 사유)."""
    try:
        return popular_keywords(category_name, count=count), "데이터랩 인기검색어"
    except Exception as e:
        return [], f"가져오기 실패({str(e)[:60]}) — ①에서 키워드를 직접 입력해 분석하세요"
