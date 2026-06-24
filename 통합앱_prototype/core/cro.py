# -*- coding: utf-8 -*-
"""상세페이지 전환율(CRO) 점검 — 생성된 카피(13섹션/단순)를 일반 CRO 기준으로 점검.
순수 로직(UI/네트워크 비의존). 점수·등급·항목별 결과·개선제안 반환.
주의: 일반 전환율 기준이며 네이버 검색노출(SEO)과는 별개."""

# 과장·허위·금지 소지 표현(자체 작성, copy_gpt와 동일 취지)
BANNED_WORDS = [
    "최저가", "최고", "최상", "1위", "넘버원", "no.1", "유일", "절대", "100%", "무조건",
    "완벽", "완치", "특효", "부작용없", "의학적", "치료", "효능", "공식인증", "정품보장",
    "당일완판", "품절임박", "마지막기회", "평생", "영구",
]
# 전환에 도움되는 긴급성 표현(금지어와 겹치지 않는 안전 표현)
URGENCY_HINTS = ["지금", "오늘", "한정", "마감", "바로", "조기", "선착순", "재입고"]


def _item_text(it):
    """items가 dict로 와도 안전하게 문자열로 변환."""
    if isinstance(it, dict):
        for _k in ("title", "name", "text", "headline", "label", "prompt", "content", "value"):
            _v = it.get(_k)
            if _v:
                return str(_v)
        for _v in it.values():
            if isinstance(_v, str) and _v.strip():
                return _v
        return ""
    return "" if it is None else str(it)


def _norm_items(items):
    return [t for t in (_item_text(i) for i in (items or [])) if t]


def _sec_map(cr):
    return {s.get("key"): s for s in (cr.get("sections") or []) if isinstance(s, dict)}


def _all_text(cr):
    parts = [str(cr.get("title", "")), str(cr.get("tagline", ""))]
    for s in (cr.get("sections") or []):
        parts += [str(s.get("headline", "")), str(s.get("sub", "")), str(s.get("note", ""))]
        parts += _norm_items(s.get("items"))
    parts += [str(x) for x in (cr.get("bullets") or [])]
    parts.append(str(cr.get("body", "")))
    return " ".join(parts)


def find_banned(cr):
    """본문 전체에서 발견된 금지/과장 표현 리스트(중복 제거)."""
    low = _all_text(cr).replace(" ", "").lower()
    hits = []
    for w in BANNED_WORDS:
        if w.replace(" ", "").lower() in low and w not in hits:
            hits.append(w)
    return hits


def _check(name, ok, weight, ok_msg, bad_msg, warn=False):
    level = "ok" if ok else ("warn" if warn else "fail")
    return {"name": name, "ok": bool(ok), "level": level, "weight": weight,
            "msg": ok_msg if ok else bad_msg}


def audit(cr):
    """카피 CRO 점검. 반환: {score, grade, checks[], suggestions[], mode}."""
    cr = cr or {}
    checks = []
    if cr.get("sections"):
        m = _sec_map(cr)
        hero = m.get("hero", {})
        pain = m.get("pain", {})
        solution = m.get("solution", {})
        proof = m.get("proof", {})
        authority = m.get("authority", {})
        benefits = m.get("benefits", {})
        risk = m.get("risk", {})
        cta = m.get("cta", {})

        hl = str(hero.get("headline", "")).strip()
        checks.append(_check("Hero 헤드라인", len(hl) >= 6, 3,
                             "핵심 가치를 담은 헤드라인이 있습니다.",
                             "Hero 헤드라인이 비었거나 너무 짧습니다(5초 내 가치 전달 필요)."))
        checks.append(_check("Hero 서브/CTA 문구", bool(str(hero.get("sub", "")).strip()), 2,
                             "서브카피/행동유도 문구가 있습니다.",
                             "Hero에 서브카피·CTA 문구가 없습니다.", warn=True))
        checks.append(_check("Pain 고통점", len(pain.get("items") or []) >= 2, 2,
                             "고객 고통점이 구체적으로 제시됐습니다.",
                             "고통점(공감 포인트)이 2개 미만입니다.", warn=True))
        checks.append(_check("Solution 명확성", bool(str(solution.get("headline", "")).strip()), 2,
                             "해결책 한 줄이 명확합니다.",
                             "Solution 헤드라인이 비어 있습니다."))
        checks.append(_check("Proof(후기/통계)", (len(proof.get("items") or []) >= 1) or bool(str(proof.get("headline", "")).strip()), 3,
                             "사회적 증거(후기/통계)가 있습니다.",
                             "Proof(후기·통계 등 사회적 증거)가 비어 있습니다 — 전환에 큰 영향."))
        checks.append(_check("Authority 신뢰", bool(str(authority.get("headline", "")).strip()) or bool(authority.get("items")), 1,
                             "전문성/신뢰 근거가 있습니다.",
                             "Authority(신뢰 근거)가 비어 있습니다.", warn=True))
        checks.append(_check("Benefits 혜택", len(benefits.get("items") or []) >= 3, 2,
                             "혜택이 3개 이상 제시됐습니다.",
                             "혜택(Benefits)이 3개 미만입니다.", warn=True))
        checks.append(_check("Risk/FAQ 안심", len(risk.get("items") or []) >= 1, 2,
                             "보증/FAQ로 구매 불안을 낮춥니다.",
                             "Risk(보증·FAQ) 항목이 없습니다.", warn=True))
        checks.append(_check("최종 CTA", bool(str(cta.get("headline", "")).strip()), 3,
                             "마무리 CTA가 있습니다.",
                             "최종 CTA 헤드라인이 비어 있습니다."))
        cta_text = (str(cta.get("headline", "")) + str(cta.get("sub", "")) + " ".join(_norm_items(cta.get("items")))).replace(" ", "")
        checks.append(_check("긴급성 문구", any(u in cta_text for u in URGENCY_HINTS), 2,
                             "행동을 앞당기는 긴급성 표현이 있습니다.",
                             "CTA에 긴급성(지금/오늘/한정 등) 표현이 약합니다.", warn=True))
    else:
        # 단순 카피 모드
        checks.append(_check("제목", len(str(cr.get("title", "")).strip()) >= 6, 3,
                             "제목이 있습니다.", "제목이 비었거나 너무 짧습니다."))
        checks.append(_check("셀링포인트", len(cr.get("bullets") or []) >= 3, 3,
                             "셀링포인트가 3개 이상입니다.", "셀링포인트가 3개 미만입니다.", warn=True))
        checks.append(_check("본문 분량", len(str(cr.get("body", "")).strip()) >= 80, 2,
                             "본문 분량이 충분합니다.", "본문이 너무 짧습니다(80자 미만).", warn=True))

    # 공통: 금지어 / 태그
    banned = find_banned(cr)
    checks.append(_check("과장·금지어 없음", len(banned) == 0, 3,
                         "과장·금지 표현이 없습니다.",
                         "과장/금지 소지 표현 발견: " + ", ".join(banned)))
    checks.append(_check("검색 태그", len(cr.get("tags") or []) >= 5, 1,
                         "검색 태그가 5개 이상입니다.", "검색 태그가 5개 미만입니다.", warn=True))

    total_w = sum(c["weight"] for c in checks) or 1
    got_w = sum(c["weight"] for c in checks if c["ok"])
    score = round(got_w / total_w * 100)
    grade = "A" if score >= 80 else ("B" if score >= 60 else "C")
    suggestions = [c["msg"] for c in checks if not c["ok"]]
    return {"score": score, "grade": grade, "checks": checks,
            "suggestions": suggestions, "mode": "13섹션" if cr.get("sections") else "단순"}
