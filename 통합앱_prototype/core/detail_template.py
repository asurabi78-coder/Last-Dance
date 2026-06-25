# -*- coding: utf-8 -*-
"""상세페이지 HTML 템플릿 빌더. GPT 카피 + (옵션)히어로 이미지 data URI를 받아 완성 HTML 반환.
이 모듈은 단독으로 동작하며 외부 통신/키가 필요 없다(순수 문자열 조립)."""
import html as _html


def _e(s):
    return _html.escape(str(s or ""))


# 디자인 조정 기본값 — app.py 패널과 동일하게 유지
DESIGN_DEFAULTS = {
    "title_size": 40,
    "sub_size": 16,
    "sec_size": 28,
    "body_size": 16,
    "line_height": 1.2,
    "letter_spacing": 0.0,
    "word_keep": True,
    "title_gap": 12,
    "align": "center",
    "hero_bg": "#111418",
    "hero_fg": "#ffffff",
    "accent": "#c8a04b",
}


def _design_css(design: dict) -> str:
    """디자인 조정 dict → 기존 스타일 뒤에 덧붙일 override CSS 문자열."""
    if not design:
        return ""
    d = dict(DESIGN_DEFAULTS)
    d.update({k: v for k, v in design.items() if v is not None})
    rules = []
    if d.get("accent"):
        rules.append(":root{--gold:%s;}" % d["accent"])
    hero = []
    if d.get("hero_bg"):
        hero.append("background:%s" % d["hero_bg"])
    if d.get("hero_fg"):
        hero.append("color:%s" % d["hero_fg"])
    if d.get("align"):
        hero.append("text-align:%s" % d["align"])
    if hero:
        rules.append(".hero{%s}" % ";".join(hero))
    h1 = []
    if d.get("title_size"):
        h1.append("font-size:%dpx" % int(d["title_size"]))
    if d.get("line_height"):
        h1.append("line-height:%s" % float(d["line_height"]))
    if d.get("letter_spacing") is not None:
        h1.append("letter-spacing:%sem" % float(d["letter_spacing"]))
    if d.get("word_keep", True):
        h1.append("word-break:keep-all")
        h1.append("overflow-wrap:break-word")
    if d.get("align"):
        h1.append("text-align:%s" % d["align"])
    if d.get("hero_fg"):
        h1.append("color:%s" % d["hero_fg"])
    if d.get("title_gap") is not None:
        h1.append("margin-bottom:%dpx" % int(d["title_gap"]))
    if h1:
        rules.append(".hero h1{%s}" % ";".join(h1))
    if d.get("sub_size"):
        rules.append(".hero p.tag{font-size:%dpx;word-break:keep-all;}" % int(d["sub_size"]))
    if d.get("sec_size"):
        rules.append("h2.sec{font-size:%dpx;word-break:keep-all;}" % int(d["sec_size"]))
    if d.get("body_size"):
        bs = int(d["body_size"])
        rules.append(".lead{font-size:%dpx;word-break:keep-all;}" % bs)
        rules.append(".dlist{font-size:%dpx;word-break:keep-all;}" % bs)
    return "".join(rules)


def _item_text(it):
    """섹션 items가 dict로 와도 안전하게 문자열로 변환."""
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


def _gallery_section(section_images) -> str:
    """간단 모드용: 생성 이미지들을 '상세 이미지' 갤러리로 렌더(없으면 빈 문자열)."""
    imgs = [v for v in (section_images or {}).values() if v]
    if not imgs:
        return ""
    cards = "".join(
        "<img src='" + _e(u) + "' alt='detail' "
        "style='width:100%;border-radius:14px;margin-top:14px'/>" for u in imgs)
    return ("<section class='pad center'><div class='kicker'>Detail</div>"
            "<h2 class='sec'>상세 이미지</h2><div class='rule'></div>"
            "<div style='max-width:680px;margin:0 auto'>" + cards + "</div></section>")


def _extra_gallery(images) -> str:
    """④에서 '상세페이지에 추가'한 이미지 리스트를 갤러리 섹션으로 렌더(없으면 빈 문자열)."""
    imgs = [u for u in (images or []) if u]
    if not imgs:
        return ""
    cards = "".join(
        "<img src='" + _e(u) + "' alt='detail' "
        "style='width:100%;border-radius:14px;margin-top:14px'/>" for u in imgs)
    return ("<section class='pad center'><div class='kicker'>Gallery</div>"
            "<h2 class='sec'>추가 이미지</h2><div class='rule'></div>"
            "<div style='max-width:680px;margin:0 auto'>" + cards + "</div></section>")


def _video_section(video_url: str) -> str:
    """영상 URL이 있으면 상세페이지에 <video> 섹션을 렌더(없으면 빈 문자열)."""
    if not video_url:
        return ""
    u = _e(video_url)
    return ("<section class='pad center'><div class='kicker'>Video</div>"
            "<h2 class='sec'>영상으로 보기</h2><div class='rule'></div>"
            "<video controls preload='metadata' playsinline "
            "style='width:100%;max-width:680px;border-radius:14px;margin-top:18px' "
            "src='" + u + "'></video></section>")


def _editable_block() -> str:
    """직접편집용: 텍스트 클릭 편집 + 'HTML 저장' + '이미지로 저장'(스마트스토어용) 버튼."""
    return (
        "<div id='__editbar' style='position:fixed;top:0;left:0;right:0;z-index:9999;"
        "background:#111418;color:#fff;padding:8px 14px;font-size:13px;text-align:center;"
        "font-family:sans-serif'>\u270f\ufe0f \uae00\uc790 \ud074\ub9ad\ud574 \uc218\uc815 \u00b7 \uc6b0\uce21 \uc544\ub798 "
        "<b>\U0001f4f7 \uc774\ubbf8\uc9c0\ub85c \uc800\uc7a5</b>(\uc2a4\ub9c8\ud2b8\uc2a4\ud1a0\uc5b4\uc6a9) \ub610\ub294 <b>\U0001f4be HTML \uc800\uc7a5</b></div>"
        "<button id='__imgbtn' style='position:fixed;bottom:20px;right:20px;z-index:9999;"
        "background:#03c75a;color:#fff;font-weight:800;border:none;padding:14px 20px;border-radius:999px;"
        "box-shadow:0 4px 14px rgba(0,0,0,.3);cursor:pointer;font-size:15px;font-family:sans-serif'>"
        "\U0001f4f7 \uc774\ubbf8\uc9c0\ub85c \uc800\uc7a5</button>"
        "<button id='__savebtn' style='position:fixed;bottom:20px;right:185px;z-index:9999;"
        "background:#c8a04b;color:#1a1a1a;font-weight:800;border:none;padding:14px 20px;border-radius:999px;"
        "box-shadow:0 4px 14px rgba(0,0,0,.3);cursor:pointer;font-size:15px;font-family:sans-serif'>"
        "\U0001f4be HTML \uc800\uc7a5</button>"
        "<script src='https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js'></script>"
        "<script>(function(){"
        "document.body.style.paddingTop='40px';"
        "document.querySelectorAll('.wrap h1,.wrap h2,.wrap h3,.wrap h4,.wrap p,.wrap li,.wrap td,.wrap th,.wrap span')"
        ".forEach(function(el){el.setAttribute('contenteditable','true');});"
        "document.getElementById('__savebtn').addEventListener('click',function(){"
        "var c=document.documentElement.cloneNode(true);"
        "['#__editbar','#__savebtn','#__imgbtn'].forEach(function(q){var n=c.querySelector(q);if(n)n.remove();});"
        "c.querySelectorAll('[contenteditable]').forEach(function(el){el.removeAttribute('contenteditable');});"
        "c.querySelectorAll('script').forEach(function(el){el.remove();});"
        "var bd=c.querySelector('body');if(bd)bd.style.paddingTop='';"
        "var a=document.createElement('a');"
        "a.href=URL.createObjectURL(new Blob(['<!DOCTYPE html>'+c.outerHTML],{type:'text/html'}));"
        "a.download='\uc0c1\uc138\ud398\uc774\uc9c0_\ud3b8\uc9d1\ubcf8.html';a.click();});"
        "document.getElementById('__imgbtn').addEventListener('click',function(){"
        "var btn=this;btn.textContent='\u2026 \uc0dd\uc131\uc911';"
        "if(typeof html2canvas==='undefined'){alert('\uc774\ubbf8\uc9c0 \ub77c\uc774\ube0c\ub7ec\ub9ac \ub85c\ub529 \uc911 \u2014 \uc7a0\uc2dc \ud6c4 \ub2e4\uc2dc');btn.textContent='\U0001f4f7 \uc774\ubbf8\uc9c0\ub85c \uc800\uc7a5';return;}"
        "html2canvas(document.querySelector('.wrap'),{useCORS:true,scale:2,backgroundColor:'#ffffff'}).then(function(cv){"
        "var a=document.createElement('a');a.href=cv.toDataURL('image/png');a.download='\uc0c1\uc138\ud398\uc774\uc9c0.png';a.click();"
        "btn.textContent='\U0001f4f7 \uc774\ubbf8\uc9c0\ub85c \uc800\uc7a5';"
        "}).catch(function(e){alert('\uc774\ubbf8\uc9c0 \uc0dd\uc131 \uc2e4\ud328(\uc678\ubd80 \uc774\ubbf8\uc9c0\uac00 \uc788\uc73c\uba74 \ub9c9\ud790 \uc218 \uc788\uc74c): '+e);"
        "btn.textContent='\U0001f4f7 \uc774\ubbf8\uc9c0\ub85c \uc800\uc7a5';});});"
        "})();</script>"
    )


def _video_section(video_url: str) -> str:
    """영상 URL이 있으면 상세페이지에 <video> 섹션을 렌더(없으면 빈 문자열)."""
    if not video_url:
        return ""
    u = _e(video_url)
    return ("<section class='pad center'><div class='kicker'>Video</div>"
            "<h2 class='sec'>영상으로 보기</h2><div class='rule'></div>"
            "<video controls preload='metadata' playsinline "
            "style='width:100%;max-width:680px;border-radius:14px;margin-top:18px' "
            "src='" + u + "'></video></section>")


def build_detail_html(copy: dict, hero_img: str = "", meta: dict = None, design: dict = None, video_url: str = "", section_images: dict = None, extra_images: list = None, editable: bool = False) -> str:
    """copy: {title,bullets,body,tags,image_brief,...}, hero_img: data URI 또는 URL, meta: 사양 dict"""
    copy = copy or {}
    meta = meta or {}
    _raw_title = str(copy.get("title", "상품 상세페이지") or "")
    title = _e(_raw_title).replace("\r\n", "\n").replace("\n", " ")          # 한 줄용(타이틀/섹션/CTA)
    title_html = _e(_raw_title).replace("\r\n", "\n").replace("\n", "<br>")  # 히어로 제목용(직접 줄바꿈 반영)
    body = _e(copy.get("body", ""))
    bullets = [b for b in (copy.get("bullets") or []) if b][:4]
    feats = [f for f in (copy.get("image_brief") or copy.get("bullets") or []) if f][:3]
    tags = [t for t in (copy.get("tags") or []) if t]

    badges = "".join(f"<span class='badge'>{_e(b)}</span>" for b in (tags[:4] or bullets[:4]))
    points = "".join(
        f"<div class='pt'><div class='n'>POINT 0{i+1}</div><div class='ph'>{_e(b)}</div></div>"
        for i, b in enumerate(bullets)) or "<div class='pt'><div class='ph'>핵심 포인트</div></div>"
    fcards = "".join(
        f"<div class='fcard'><h4>{_e(f)}</h4></div>" for f in feats) or "<div class='fcard'><h4>특징</h4></div>"
    tagline = " · ".join(_e(t) for t in tags[:3]) if tags else "데일리부터 실사용까지"

    if hero_img:
        hero_visual = f"<img src='{hero_img}' alt='product' style='max-width:100%;border-radius:14px;margin-top:24px'/>"
        main_slot = f"<img src='{hero_img}' alt='product' style='width:100%;border-radius:14px'/>"
    else:
        hero_visual = ""
        main_slot = "<div class='slot'>［ 메인 대표컷 영역 ］<div class='small'>여기에 제품 사진을 넣으세요</div></div>"

    spec_rows = ""
    spec_fields = [("상품명", meta.get("상품명", copy.get("title", ""))),
                   ("소재", meta.get("소재", "※ 공급사 확인 후 입력")),
                   ("사이즈", meta.get("사이즈", "※ 공급사 사이즈표 입력")),
                   ("제조국", meta.get("제조국", "※ 확인 후 입력")),
                   ("세탁", meta.get("세탁", "제품 라벨 표기 기준"))]
    for k, v in spec_fields:
        cls = " class='fill'" if str(v).startswith("※") else ""
        spec_rows += f"<tr><th>{_e(k)}</th><td><span{cls}>{_e(v)}</span></td></tr>"

    tag_line = " ".join("#" + _e(t) for t in tags)
    design_css = _design_css(design)
    video_html = _video_section(video_url)
    gallery_html = _gallery_section(section_images)
    extra_html = _extra_gallery(extra_images)
    editable_block = _editable_block() if editable else ""

    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{title}</title>
<style>
:root{{--ink:#111418;--paper:#fff;--mut:#6b7280;--line:#e5e7eb;--gold:#c8a04b;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",sans-serif;color:var(--ink);background:#f3f4f2;line-height:1.6;}}
.wrap{{max-width:760px;margin:0 auto;background:var(--paper);}}
.pad{{padding:52px 32px;}} .center{{text-align:center;}}
.kicker{{font-size:13px;letter-spacing:.25em;font-weight:700;color:var(--gold);text-transform:uppercase;}}
h2.sec{{font-size:28px;font-weight:800;margin-top:10px;line-height:1.25;}}
.lead{{font-size:16px;color:#4b5563;margin-top:14px;}}
.rule{{width:44px;height:3px;background:var(--gold);margin:18px auto 0;border-radius:2px;}}
.hero{{background:var(--ink);color:#fff;padding:60px 32px;text-align:center;}}
.hero h1{{font-size:clamp(28px,6vw,46px);font-weight:900;letter-spacing:.01em;}}
.hero p.tag{{margin-top:18px;font-size:16px;color:#e5e7eb;}}
.badges{{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:22px;}}
.badge{{border:1px solid #3a4250;color:#e5e7eb;font-size:12px;font-weight:600;padding:7px 13px;border-radius:999px;}}
.slot{{background:#eef0ee;border:1px dashed #c3c9c0;border-radius:14px;padding:40px 20px;text-align:center;color:#8a9183;font-weight:700;}}
.slot .small{{font-size:12px;font-weight:400;margin-top:6px;}}
.points{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:28px;}}
.pt{{border:1px solid var(--line);border-radius:14px;padding:20px;}}
.pt .n{{font-size:12px;font-weight:800;color:var(--gold);letter-spacing:.1em;}}
.pt .ph{{font-size:16px;font-weight:700;margin-top:8px;}}
.stripe{{background:#2f3b2f;color:#eef2ec;}} .stripe .kicker{{color:var(--gold);}} .stripe h2.sec{{color:#fff;}}
.frow{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:28px;}}
.fcard{{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:20px;text-align:center;}}
.fcard h4{{font-size:15px;font-weight:700;}}
table{{width:100%;border-collapse:collapse;margin-top:22px;font-size:14px;}}
th,td{{border:1px solid var(--line);padding:12px 14px;text-align:left;}} th{{background:#f7f8f7;width:32%;font-weight:700;}}
td .fill{{color:#cd2e3a;font-weight:600;}}
.cta{{background:var(--ink);color:#fff;text-align:center;padding:50px 32px;}}
.cta h2{{font-size:24px;font-weight:900;}} .cta .btn{{display:inline-block;margin-top:22px;background:var(--gold);color:#1a1a1a;font-weight:800;padding:14px 38px;border-radius:999px;}}
.foot{{padding:24px;font-size:12px;color:#9aa3af;text-align:center;background:#f3f4f2;}}
@media(max-width:560px){{.points,.frow{{grid-template-columns:1fr;}}}}
{design_css}
</style></head><body><div class="wrap">
<header class="hero"><h1>{title_html}</h1><p class="tag">{tagline}</p>
<div class="badges">{badges}</div>{hero_visual}</header>
<section class="pad center"><div class="kicker">Product</div><h2 class="sec">{title}</h2><div class="rule"></div>
<p class="lead">{body}</p></section>
<section class="pad" style="padding-top:0;">{main_slot}</section>
{gallery_html}
{extra_html}
{video_html}
<section class="pad" style="padding-top:0;"><div class="center"><div class="kicker">Key Point</div><h2 class="sec">핵심 포인트</h2><div class="rule"></div></div>
<div class="points">{points}</div></section>
<section class="pad stripe"><div class="center"><div class="kicker">Highlight</div><h2 class="sec">이런 점이 좋아요</h2><div class="rule"></div></div>
<div class="frow">{fcards}</div></section>
<section class="pad"><div class="center"><div class="kicker">Information</div><h2 class="sec">상품 정보</h2><div class="rule"></div></div>
<table>{spec_rows}</table></section>
<section class="pad center" style="padding-top:0;"><p style="color:#888;font-size:13px;">{tag_line}</p></section>
<section class="cta"><h2>{title}</h2><p style="color:#9aa3af;margin-top:8px;">지금 만나보세요</p><span class="btn">구매하기</span></section>
<div class="foot">상세페이지 초안 (Cowork 통합앱 생성) · 사양·이미지는 공급사 자료로 교체하세요</div>
</div>{editable_block}</body></html>"""


def build_detail_html_13(copy: dict, hero_img: str = "", meta: dict = None, section_images: dict = None, design: dict = None, video_url: str = "", extra_images: list = None, editable: bool = False) -> str:
    """13섹션 감정여정 카피(dict with 'sections')를 프리미엄 HTML로 렌더."""
    copy = copy or {}
    meta = meta or {}
    section_images = section_images or {}
    _raw_title = str(copy.get("title", "상품 상세페이지") or "")
    title = _e(_raw_title).replace("\r\n", "\n").replace("\n", " ")
    title_html = _e(_raw_title).replace("\r\n", "\n").replace("\n", "<br>")
    tagline = _e(copy.get("tagline", ""))
    tags = [t for t in (copy.get("tags") or []) if t]
    badges = "".join(f"<span class='badge'>{_e(t)}</span>" for t in tags[:5])
    hero_visual = (f"<img src='{hero_img}' alt='product' style='max-width:100%;border-radius:14px;margin-top:24px'/>"
                   if hero_img else "")
    dark_keys = {"hero", "story", "proof", "cta"}
    blocks = ""
    for sec in copy.get("sections", []):
        k = sec.get("key", "")
        if k == "hero":
            continue
        hl = _e(sec.get("headline", ""))
        sub = _e(sec.get("sub", ""))
        items = [t for t in (_item_text(i) for i in (sec.get("items") or [])) if t]
        note = _e(sec.get("note", ""))
        if not (hl or sub or items or note or section_images.get(k)):
            continue
        lis = "".join(f"<li>{_e(i)}</li>" for i in items)
        items_html = f"<ul class='dlist'>{lis}</ul>" if lis else ""
        note_html = f"<p class='note'>{note}</p>" if note else ""
        sub_html = f"<p class='lead'>{sub}</p>" if sub else ""
        cls = "pad stripe" if k in dark_keys else "pad"
        if k == "cta":
            blocks += (f"<section class='cta'><h2>{hl or title}</h2>"
                       f"{('<p>'+sub+'</p>') if sub else ''}"
                       f"{items_html}<span class='btn'>구매하기</span></section>")
        else:
            simg = section_images.get(k, "")
            img_html = (f"<div style='max-width:680px;margin:20px auto 0'><img src='{simg}' "
                        f"alt='{_e(sec.get('label',''))}' style='width:100%;border-radius:14px'/></div>") if simg else ""
            blocks += (f"<section class='{cls}'><div class='center'>"
                       f"<div class='kicker'>{_e(sec.get('label',''))}</div>"
                       f"<h2 class='sec'>{hl}</h2><div class='rule'></div></div>"
                       f"{sub_html}{items_html}{note_html}{img_html}</section>")
    spec_rows = ""
    for kk, vv in [("상품명", meta.get("상품명", copy.get("title", ""))),
                   ("소재", meta.get("소재", "※ 공급사 확인 후 입력")),
                   ("사이즈", meta.get("사이즈", "※ 공급사 사이즈표 입력")),
                   ("제조국", meta.get("제조국", "※ 확인 후 입력"))]:
        cls = " class='fill'" if str(vv).startswith("※") else ""
        spec_rows += f"<tr><th>{_e(kk)}</th><td><span{cls}>{_e(vv)}</span></td></tr>"
    tag_line = " ".join("#" + _e(t) for t in tags)
    css = build_detail_html({}, "", {}).split("<style>")[1].split("</style>")[0]
    css += " .dlist{max-width:620px;margin:14px auto 0;padding-left:18px;text-align:left;font-size:15px;color:#374151;line-height:1.9} .stripe .dlist{color:#dfe6da} .note{max-width:620px;margin:12px auto 0;color:#888;font-size:13px} .stripe .note{color:#aebaa6}"
    css += _design_css(design)
    video_html = _video_section(video_url)
    extra_html = _extra_gallery(extra_images)
    editable_block = _editable_block() if editable else ""
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{title}</title>
<style>{css}</style></head><body><div class="wrap">
<header class="hero"><h1>{title_html}</h1>{('<p class=tag>'+tagline+'</p>') if tagline else ''}
<div class="badges">{badges}</div>{hero_visual}</header>
{blocks}
{extra_html}
{video_html}
<section class="pad"><div class="center"><div class="kicker">Information</div><h2 class="sec">상품 정보</h2><div class="rule"></div></div>
<table>{spec_rows}</table></section>
<section class="pad center" style="padding-top:0;"><p style="color:#888;font-size:13px;">{tag_line}</p></section>
<div class="foot">상세페이지 (13섹션 감정여정) · Cowork 통합앱 생성 · 사양·이미지는 공급사 자료로 교체하세요</div>
</div>{editable_block}</body></html>"""


def build_smartstore_html(copy: dict, meta: dict = None, section_images: dict = None, extra_images: list = None) -> str:
    """스마트스토어 HTML 직접입력용: 인라인 스타일 프래그먼트.
    <style>/<script>/<head>/<body>/<table>/<a>/<video> 미사용 — 인라인 style만."""
    copy = copy or {}
    meta = meta or {}
    section_images = section_images or {}
    title = _e(str(copy.get("title", "상품 상세페이지") or "")).replace("\r\n", " ").replace("\n", " ")
    tags = [t for t in (copy.get("tags") or []) if t]
    o = ["<div style='max-width:760px;margin:0 auto;font-family:sans-serif;color:#111418;line-height:1.7'>"]
    o.append("<div style='background:#111418;color:#fff;padding:40px 24px;text-align:center'>")
    o.append("<div style='font-size:30px;font-weight:900;word-break:keep-all'>" + title + "</div>")
    if copy.get("tagline"):
        o.append("<div style='margin-top:12px;font-size:15px;color:#e5e7eb'>" + _e(copy.get("tagline")) + "</div>")
    o.append("</div>")
    has_sections = bool(copy.get("sections"))
    for sec in (copy.get("sections") or []):
        if sec.get("key") == "hero":
            continue
        hl = _e(sec.get("headline", ""))
        sub = _e(sec.get("sub", ""))
        items = [_item_text(i) for i in (sec.get("items") or []) if _item_text(i)]
        note = _e(sec.get("note", ""))
        simg = section_images.get(sec.get("key", ""), "")
        if not (hl or sub or items or note or simg):
            continue
        o.append("<div style='padding:36px 24px;text-align:center;border-top:1px solid #eee'>")
        if sec.get("label"):
            o.append("<div style='font-size:12px;letter-spacing:2px;color:#c8a04b;font-weight:700'>" + _e(sec.get("label")) + "</div>")
        if hl:
            o.append("<div style='font-size:24px;font-weight:800;margin-top:8px;word-break:keep-all'>" + hl + "</div>")
        if sub:
            o.append("<div style='font-size:16px;color:#555;margin-top:12px;word-break:keep-all'>" + sub + "</div>")
        for it in items:
            o.append("<div style='font-size:15px;color:#374151;margin-top:8px;word-break:keep-all'>\u2022 " + _e(it) + "</div>")
        if note:
            o.append("<div style='font-size:13px;color:#888;margin-top:10px'>" + note + "</div>")
        if simg:
            o.append("<div style='margin-top:16px'><img src='" + _e(simg) + "' style='max-width:100%;border-radius:12px' alt='detail'/></div>")
        o.append("</div>")
    if not has_sections:
        for b in [x for x in (copy.get("bullets") or []) if x]:
            o.append("<div style='padding:6px 24px;text-align:center;font-size:15px;color:#374151'>\u2022 " + _e(b) + "</div>")
        if copy.get("body"):
            o.append("<div style='padding:12px 24px 24px;text-align:center;font-size:16px;color:#4b5563'>" + _e(copy.get("body")) + "</div>")
    for u in (extra_images or []):
        if u:
            o.append("<div style='padding:0 24px 16px;text-align:center'><img src='" + _e(u) + "' style='max-width:100%;border-radius:12px' alt='detail'/></div>")
    o.append("<div style='padding:36px 24px;border-top:1px solid #eee'>")
    o.append("<div style='font-size:20px;font-weight:800;text-align:center;margin-bottom:16px'>상품 정보</div>")
    for kk, vv in [("상품명", meta.get("상품명", copy.get("title", ""))),
                   ("소재", meta.get("소재", "※ 공급사 확인 후 입력")),
                   ("사이즈", meta.get("사이즈", "※ 공급사 사이즈표")),
                   ("제조국", meta.get("제조국", "※ 확인 후 입력"))]:
        o.append("<div style='display:flex;border-bottom:1px solid #eee;padding:10px 0'>"
                 "<div style='width:30%;font-weight:700;color:#555'>" + _e(kk) + "</div>"
                 "<div style='width:70%'>" + _e(vv) + "</div></div>")
    o.append("</div>")
    if tags:
        o.append("<div style='padding:16px 24px;text-align:center;color:#888;font-size:13px'>" + _e(" ".join("#" + t for t in tags)) + "</div>")
    o.append("</div>")
    return "".join(o)
