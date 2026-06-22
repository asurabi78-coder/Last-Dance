# -*- coding: utf-8 -*-
"""배치 연속 생성 — 여러 (키워드,상품) 항목의 상세페이지를 일괄 생성하고 store에 저장.
순수 파이썬(Streamlit 호출 없음). bounded 동시 실행으로 API rate limit/쿼터 보호."""
from concurrent.futures import ThreadPoolExecutor

from . import copy_gpt, image_gen, detail_template, store


def _val(item, *keys):
    for k in keys:
        v = item.get(k)
        if v:
            return str(v).strip()
    return ""


def _gen_one(item, opts):
    """단일 항목: 카피→(이미지)→HTML→저장. 결과 dict 반환. st.* 호출 금지(스레드)."""
    keyword = _val(item, "키워드", "keyword")
    product = _val(item, "상품명", "product")
    features = _val(item, "특징", "features")
    thumb = _val(item, "썸네일", "thumb")
    provider = opts.get("provider", "openai")
    res = {"keyword": keyword, "product": product, "status": "ok",
           "id": None, "error": None, "title": "", "engine": ""}

    # 1) 카피
    cr = None
    try:
        if opts.get("mode_13", True):
            cr = copy_gpt.generate_13(product or "상품", keyword or "키워드",
                                      features=features, provider=provider)
        else:
            cr = copy_gpt.generate(product or "상품", keyword or "키워드",
                                   features=features, provider=provider)
        if opts.get("do_human", False):
            cr = copy_gpt.humanize(cr, provider=provider)
    except Exception as e:
        res["status"] = "fail"
        res["error"] = f"카피 실패: {str(e)[:160]}"
        return res

    cr["hero"] = ""
    # 2) 대표이미지(옵션) — 실패해도 전체는 진행
    if opts.get("include_img", False) and (image_gen.available_gemini() or image_gen.available_openai()):
        imgs, eng = None, None
        if opts.get("use_thumb_img", True) and thumb:
            try:
                ref = image_gen.fetch_image_bytes(thumb)
                imgs, _e = image_gen.edit_image(ref, image_gen.SCENE_PROMPTS["흰배경 메인컷"])
                eng = "도매꾹기반·" + _e
            except Exception:
                imgs, eng = None, None
        if not imgs:
            try:
                ip = f"Studio e-commerce hero shot of {product or keyword}, clean white background, photorealistic, 1:1"
                imgs, eng = image_gen.generate_image(ip)
            except Exception:
                imgs = None
        if imgs:
            cr["hero"] = "data:image/png;base64," + imgs[0]
            cr["hero_engine"] = eng
            res["engine"] = eng

    # 3) HTML 렌더
    meta = {"상품명": product or cr.get("title", "")}
    html = ""
    try:
        if cr.get("sections"):
            html = detail_template.build_detail_html_13(cr, hero_img=cr.get("hero", ""), meta=meta)
        else:
            html = detail_template.build_detail_html(cr, hero_img=cr.get("hero", ""), meta=meta)
    except Exception:
        html = ""
    res["title"] = cr.get("title", "") or product or keyword

    # 4) 저장
    if opts.get("save", True):
        try:
            res["id"] = store.save_detail(
                cr, html=html,
                meta={"상품명": product or cr.get("title", ""), "키워드": keyword},
                hero=cr.get("hero"))
        except Exception as e:
            res["status"] = "fail"
            res["error"] = f"저장 실패: {str(e)[:160]}"
    return res


def parse_manual(text):
    """수동 입력 텍스트 → 항목 리스트. 한 줄당 '키워드 | 상품명 | 특징'(| 구분, 뒤 2개 생략 가능)."""
    items = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        kw = parts[0] if len(parts) >= 1 else ""
        pr = parts[1] if len(parts) >= 2 else ""
        ft = parts[2] if len(parts) >= 3 else ""
        if kw or pr:
            items.append({"키워드": kw, "상품명": pr, "특징": ft})
    return items


def run_batch(items, opts=None, max_workers=2):
    """여러 항목 일괄 생성+저장. 입력 순서대로 결과 리스트 반환(동시 실행하되 순서 보존)."""
    opts = dict(opts or {})
    items = [it for it in (items or [])
             if _val(it, "키워드", "keyword") or _val(it, "상품명", "product")]
    if not items:
        return []
    mw = max(1, min(int(max_workers or 2), 4))
    with ThreadPoolExecutor(max_workers=mw) as ex:
        return list(ex.map(lambda it: _gen_one(it, opts), items))
