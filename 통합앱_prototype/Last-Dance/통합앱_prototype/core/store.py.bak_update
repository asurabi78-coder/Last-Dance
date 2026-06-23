# -*- coding: utf-8 -*-
"""생성 결과 저장/불러오기 — 상세페이지 카피(JSON)·HTML·대표이미지를 saved/ 폴더에 보관.
개인용 로컬 저장(외부 통신 불필요). 항목 1개 = saved/{id}/ 폴더 (copy.json, page.html, hero.png?)."""
import os
import re
import json
import time
import base64
import shutil

# 프로젝트 루트의 saved/ (core/../saved)
SAVE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "saved"))


def _ensure_dir():
    os.makedirs(SAVE_DIR, exist_ok=True)
    return SAVE_DIR


def _slug(text, maxlen=30):
    """파일명 안전 슬러그(한글 유지, 공백·특수문자는 _)."""
    s = str(text or "").strip()
    s = re.sub(r"[\\/:*?\"<>|\s]+", "_", s)      # 파일명 금지문자/공백 → _
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:maxlen] or "item"


def _hero_to_png(hero) -> bytes:
    """hero가 data:image/...;base64,xxx 또는 순수 base64면 PNG 바이트로. 아니면 None."""
    if not hero or not isinstance(hero, str):
        return None
    b64 = hero
    if hero.startswith("data:"):
        comma = hero.find(",")
        if comma == -1:
            return None
        b64 = hero[comma + 1:]
    try:
        return base64.b64decode(b64)
    except Exception:
        return None


def save_detail(cr, html="", meta=None, hero=None):
    """상세페이지 결과 저장. 반환: 저장 id(폴더명).
    cr: 카피 dict / html: 렌더된 HTML 문자열 / meta: {상품명,키워드 등} / hero: data-url 또는 base64."""
    _ensure_dir()
    meta = dict(meta or {})
    title = meta.get("상품명") or (cr or {}).get("title") or meta.get("키워드") or "상세페이지"
    keyword = meta.get("키워드") or (cr or {}).get("keyword") or ""
    ts = time.strftime("%Y%m%d_%H%M%S")
    item_id = f"{ts}_{_slug(title)}"
    folder = os.path.join(SAVE_DIR, item_id)
    # 동일 초 충돌 방지
    n = 1
    while os.path.exists(folder):
        folder = os.path.join(SAVE_DIR, f"{item_id}_{n}")
        n += 1
    item_id = os.path.basename(folder)
    os.makedirs(folder)

    hero_bytes = _hero_to_png(hero if hero is not None else (cr or {}).get("hero"))
    has_image = False
    if hero_bytes:
        with open(os.path.join(folder, "hero.png"), "wb") as f:
            f.write(hero_bytes)
        has_image = True

    record = {
        "id": item_id,
        "title": title,
        "keyword": keyword,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "created_ts": time.time(),
        "has_image": has_image,
        "meta": meta,
        "copy": cr or {},
    }
    with open(os.path.join(folder, "copy.json"), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    if html:
        with open(os.path.join(folder, "page.html"), "w", encoding="utf-8") as f:
            f.write(html)
    return item_id


def list_saved():
    """저장된 항목 메타 목록(최신순). [{id,title,keyword,created,created_ts,has_image}]"""
    if not os.path.isdir(SAVE_DIR):
        return []
    items = []
    for name in os.listdir(SAVE_DIR):
        meta_path = os.path.join(SAVE_DIR, name, "copy.json")
        if not os.path.isfile(meta_path):
            continue
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                rec = json.load(f)
            items.append({
                "id": rec.get("id", name),
                "title": rec.get("title", name),
                "keyword": rec.get("keyword", ""),
                "created": rec.get("created", ""),
                "created_ts": rec.get("created_ts", 0),
                "has_image": rec.get("has_image", False),
            })
        except Exception:
            continue
    items.sort(key=lambda x: x.get("created_ts", 0), reverse=True)
    return items


def load_detail(item_id):
    """저장 항목 전체 로드. 반환: {record..., 'html': str, 'hero_path': str|None} 또는 None."""
    folder = os.path.join(SAVE_DIR, item_id)
    meta_path = os.path.join(folder, "copy.json")
    if not os.path.isfile(meta_path):
        return None
    with open(meta_path, "r", encoding="utf-8") as f:
        rec = json.load(f)
    html_path = os.path.join(folder, "page.html")
    rec["html"] = ""
    if os.path.isfile(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            rec["html"] = f.read()
    hero_path = os.path.join(folder, "hero.png")
    rec["hero_path"] = hero_path if os.path.isfile(hero_path) else None
    return rec


def delete_detail(item_id):
    """저장 항목 폴더 삭제. 반환: 성공 여부."""
    folder = os.path.join(SAVE_DIR, item_id)
    # SAVE_DIR 밖 경로 방지
    if os.path.abspath(folder).startswith(SAVE_DIR + os.sep) and os.path.isdir(folder):
        shutil.rmtree(folder, ignore_errors=True)
        return not os.path.exists(folder)
    return False
