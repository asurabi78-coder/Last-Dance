# -*- coding: utf-8 -*-
"""네이버 스마트스토어 상품명 SEO 점검 — 공개 가이드 기반 자체 구현(휴리스틱, UI/네트워크 비의존).
검사: 길이 / 핵심키워드 앞배치 / 단어 중복 / 특수문자 절제 / 과장·금지어 / 어절 수.
주의: 네이버 알고리즘은 비공개 → 일반 권고 기준의 휴리스틱 점검입니다."""
import re

from .cro import BANNED_WORDS  # 과장·금지어 재사용

_SPECIAL_RE = re.compile(r"[^0-9A-Za-z가-힣\s]")


def _tokens(name):
    return [t for t in re.split(r"\s+", str(name or "").strip()) if t]


def _chk(name, ok, weight, ok_msg, bad_msg, warn=False):
    return {"name": name, "ok": bool(ok),
            "level": "ok" if ok else ("warn" if warn else "fail"),
            "weight": weight, "msg": ok_msg if ok else bad_msg}


def check_name_seo(name, keyword=""):
    """상품명 SEO 점검. 반환: {score, grade, checks[], suggestions[]}."""
    name = str(name or "").strip()
    kw = str(keyword or "").strip()
    checks = []

    # 1) 길이
    L = len(name)
    checks.append(_chk("길이(8~50자)", 8 <= L <= 50, 3,
                       f"적정 길이({L}자).",
                       f"길이 {L}자 — " + ("너무 김(검색결과 잘림 위험)." if L > 50 else "너무 짧음(키워드 부족)."),
                       warn=True))

    # 2) 핵심키워드 앞배치
    if kw:
        nm_ns = name.replace(" ", "")
        kw_ns = kw.replace(" ", "")
        idx = nm_ns.find(kw_ns)
        if idx == -1:
            checks.append(_chk("핵심키워드 포함", False, 3, "",
                               f"핵심키워드 '{kw}'가 상품명에 없습니다."))
        else:
            front = idx <= max(1, int(len(nm_ns) * 0.5))
            checks.append(_chk("핵심키워드 앞배치", front, 3,
                               "핵심키워드가 앞쪽에 배치됐습니다.",
                               f"핵심키워드 '{kw}'가 뒤쪽에 있습니다 — 앞으로 이동 권장.", warn=True))
    else:
        checks.append({"name": "핵심키워드", "ok": True, "level": "ok",
                       "weight": 3, "msg": "키워드 미입력 — 점검 생략."})

    # 3) 단어 중복(어뷰징 위험)
    toks = [t for t in _tokens(name) if len(t) >= 2]
    dup = sorted({t for t in toks if toks.count(t) >= 2})
    checks.append(_chk("단어 중복 없음", len(dup) == 0, 2,
                       "중복 단어가 없습니다.",
                       "중복 단어: " + ", ".join(dup) + " (키워드 반복 어뷰징 위험).", warn=True))

    # 4) 특수문자 절제
    sp = _SPECIAL_RE.findall(name)
    checks.append(_chk("특수문자 절제", len(sp) <= 3, 1,
                       "특수문자 사용이 적정합니다.",
                       f"특수문자 과다({len(sp)}개) — 네이버 비권장.", warn=True))

    # 5) 과장·금지어
    low = name.replace(" ", "").lower()
    hits = [w for w in BANNED_WORDS if w.replace(" ", "").lower() in low]
    checks.append(_chk("과장·금지어 없음", len(hits) == 0, 3,
                       "과장·금지 표현이 없습니다.",
                       "금지/과장 표현: " + ", ".join(hits)))

    # 6) 어절 수(키워드 노출 기회 vs 스터핑)
    nt = len(_tokens(name))
    checks.append(_chk("어절 수(3~15)", 3 <= nt <= 15, 2,
                       f"적정 어절 수({nt}개).",
                       f"어절 {nt}개 — " + ("너무 적어 노출 기회 부족." if nt < 3 else "너무 많아 키워드 스터핑 위험."),
                       warn=True))

    total = sum(c["weight"] for c in checks) or 1
    got = sum(c["weight"] for c in checks if c["ok"])
    score = round(got / total * 100)
    grade = "A" if score >= 80 else ("B" if score >= 60 else "C")
    return {"score": score, "grade": grade, "checks": checks,
            "suggestions": [c["msg"] for c in checks if not c["ok"]]}
