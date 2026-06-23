# -*- coding: utf-8 -*-
"""카피 수정/병합 순수 로직 — UI(Streamlit) 비의존. 단위테스트로 100% 검증 가능."""


def merge_hashtags(cr, hashtags):
    """해시태그 리스트를 cr['tags']에 병합(중복 제거, 순서 보존, # 정규화). 새 dict 반환(원본 불변)."""
    cr = dict(cr or {})
    base, seen = [], set()
    for t in (cr.get("tags", []) or []):
        t2 = str(t).strip().lstrip("#")
        if t2 and t2 not in seen:
            base.append(t2)
            seen.add(t2)
    for h in (hashtags or []):
        h2 = str(h).strip().lstrip("#")
        if h2 and h2 not in seen:
            base.append(h2)
            seen.add(h2)
    cr["tags"] = base
    return cr


def _split_lines(text):
    """줄바꿈 입력 → 비어있지 않은 항목 리스트(각 줄 strip)."""
    return [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]


def apply_edits(cr, title=None, tags_text=None, section_edits=None):
    """카피 수정 반영. 새 dict 반환(원본 불변).
    - title: 새 제목(None이면 유지)
    - tags_text: 쉼표구분 문자열(None이면 유지)
    - section_edits: {section_key: {'headline':..,'sub':..,'items_text':..}} (해당 키만 갱신)
    구조(키 순서·개수)는 유지하고 값만 바꾼다."""
    cr = dict(cr or {})
    if title is not None:
        cr["title"] = str(title)
    if tags_text is not None:
        cr["tags"] = [t.strip().lstrip("#") for t in str(tags_text).split(",") if t.strip()]
    if section_edits:
        new_sections = []
        for sec in cr.get("sections", []) or []:
            sec = dict(sec)
            ed = section_edits.get(sec.get("key"))
            if ed:
                if ed.get("headline") is not None:
                    sec["headline"] = str(ed["headline"])
                if ed.get("sub") is not None:
                    sec["sub"] = str(ed["sub"])
                if ed.get("items_text") is not None:
                    sec["items"] = _split_lines(ed["items_text"])
            new_sections.append(sec)
        cr["sections"] = new_sections
    cr["edited"] = True
    return cr


def apply_headline(cr, headline, sub=None):
    """선택한 헤드라인을 카피에 반영. 13섹션이면 hero.headline(+sub), 단순이면 title. 새 dict 반환(원본 불변)."""
    cr = dict(cr or {})
    if cr.get("sections"):
        new = []
        for s in cr["sections"]:
            s = dict(s)
            if s.get("key") == "hero":
                s["headline"] = str(headline)
                if sub is not None:
                    s["sub"] = str(sub)
            new.append(s)
        cr["sections"] = new
    else:
        cr["title"] = str(headline)
    cr["edited"] = True
    return cr
