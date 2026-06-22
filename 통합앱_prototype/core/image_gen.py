# -*- coding: utf-8 -*-
"""이미지 생성 — Gemini(나노바나나) 우선, 실패 시 OpenAI(gpt-image-1) 폴백 + remove.bg."""
import base64
import requests

from . import config

TIMEOUT = 120


def available_gemini() -> bool:
    return config.present("GEMINI_API_KEY")


def available_openai() -> bool:
    return config.present("OPENAI_API_KEY")


def available_removebg() -> bool:
    return config.present("REMOVE_BG_API_KEY")


def _gemini(prompt):
    model = config.GEMINI_IMAGE_MODEL
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={config.get('GEMINI_API_KEY')}")
    r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini {r.status_code}: {r.text[:160]}")
    out = []
    for cand in r.json().get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                out.append(inline["data"])
    if not out:
        raise RuntimeError("Gemini 응답에 이미지 없음")
    return out


def _openai(prompt, size="1024x1024"):
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {config.get('OPENAI_API_KEY')}",
                 "Content-Type": "application/json"},
        json={"model": config.get("OPENAI_IMAGE_MODEL", "gpt-image-1"),
              "prompt": prompt, "size": size, "n": 1},
        timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI 이미지 {r.status_code}: {r.text[:160]}")
    data = r.json().get("data", [])
    out = [d["b64_json"] for d in data if d.get("b64_json")]
    if not out:
        # 일부 응답은 url로 옴
        out = [requests.get(d["url"], timeout=TIMEOUT).content for d in data if d.get("url")]
        out = [base64.b64encode(b).decode() for b in out]
    if not out:
        raise RuntimeError("OpenAI 응답에 이미지 없음")
    return out


def generate_image(prompt, provider="auto"):
    """이미지(base64 PNG 리스트). provider: auto|gemini|openai. auto는 Gemini→OpenAI 폴백."""
    errors = []
    order = {"gemini": ["gemini"], "openai": ["openai"]}.get(provider, ["gemini", "openai"])
    for p in order:
        try:
            if p == "gemini" and available_gemini():
                return _gemini(prompt), "Gemini"
            if p == "openai" and available_openai():
                return _openai(prompt), "OpenAI(gpt-image-1)"
        except Exception as e:
            errors.append(str(e)[:120])
    raise RuntimeError(" / ".join(errors) or "사용 가능한 이미지 엔진 없음")


def remove_background(image_bytes: bytes) -> bytes:
    r = requests.post(
        "https://api.remove.bg/v1.0/removebg",
        headers={"X-Api-Key": config.get("REMOVE_BG_API_KEY")},
        files={"image_file": ("image.png", image_bytes)},
        data={"size": "auto"}, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"remove.bg {r.status_code}: {r.text[:160]}")
    return r.content


def b64_to_bytes(b64: str) -> bytes:
    return base64.b64decode(b64)


def fetch_image_bytes(url: str) -> bytes:
    """원격 이미지 URL(도매꾹 대표이미지 등) → PNG 표준화 바이트. 편집 API 호환용."""
    if not url:
        raise RuntimeError("이미지 URL이 비어있음")
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code != 200:
        raise RuntimeError(f"이미지 다운로드 {r.status_code}")
    raw = r.content
    if not raw:
        raise RuntimeError("이미지 응답이 비어있음")
    try:
        from io import BytesIO
        from PIL import Image
        im = Image.open(BytesIO(raw)).convert("RGBA")
        out = BytesIO()
        im.save(out, format="PNG")
        return out.getvalue()
    except Exception:
        return raw  # 변환 실패 시 원본 바이트 그대로


def composite_on_white(image_bytes: bytes) -> bytes:
    """투명/일반 이미지를 흰 배경 위에 합성한 PNG 바이트 반환(네트워크 불필요)."""
    from io import BytesIO
    from PIL import Image
    im = Image.open(BytesIO(image_bytes)).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    out = BytesIO()
    bg.convert("RGB").save(out, format="PNG")
    return out.getvalue()


def to_white_bg(image_bytes: bytes) -> bytes:
    """업로드 이미지 → 배경 제거(remove.bg) → 흰배경 합성 PNG."""
    cut = remove_background(image_bytes)   # 투명 PNG
    return composite_on_white(cut)


# ---------- 참조 이미지 편집(업로드 사진 → 장면 변형) ----------
SCENE_PROMPTS = {
    "흰배경 메인컷": "Place this exact product on a clean pure white studio background (#ffffff), soft even studio lighting, professional e-commerce hero shot. Keep the product identical (same shape, color, text, logo). 1:1.",
    "사용 연출컷": "Photorealistic lifestyle scene of this exact product being used in a real everyday setting, natural daylight, tasteful composition with empty space for text. Keep the product identical. 4:3.",
    "배경 교체": "Keep this exact product unchanged and replace only the background with a premium studio/outdoor/desk scene that fits the product. Photorealistic, soft shadows. Keep product identical.",
    "디테일 클로즈업": "Extreme close-up / alternative angle of this exact product highlighting material and texture. Keep the product identical (do not alter text or logo). Macro, sharp focus. 1:1.",
}


def _gemini_edit(image_bytes, prompt, mime="image/png"):
    model = config.GEMINI_IMAGE_MODEL
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={config.get('GEMINI_API_KEY')}")
    body = {"contents": [{"parts": [
        {"text": prompt},
        {"inline_data": {"mime_type": mime, "data": base64.b64encode(image_bytes).decode()}},
    ]}]}
    r = requests.post(url, json=body, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini edit {r.status_code}: {r.text[:160]}")
    out = []
    for cand in r.json().get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                out.append(inline["data"])
    if not out:
        raise RuntimeError("Gemini edit 응답에 이미지 없음")
    return out


def _openai_edit(image_bytes, prompt, size="1024x1024"):
    r = requests.post(
        "https://api.openai.com/v1/images/edits",
        headers={"Authorization": f"Bearer {config.get('OPENAI_API_KEY')}"},
        data={"model": config.get("OPENAI_IMAGE_MODEL", "gpt-image-1"), "prompt": prompt, "size": size, "n": 1},
        files={"image": ("ref.png", image_bytes, "image/png")},
        timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI edit {r.status_code}: {r.text[:160]}")
    data = r.json().get("data", [])
    out = [d["b64_json"] for d in data if d.get("b64_json")]
    if not out:
        raise RuntimeError("OpenAI edit 응답에 이미지 없음")
    return out


def edit_image(image_bytes, prompt, provider="auto"):
    """참조 이미지 + 프롬프트 → 변형 이미지(base64 리스트), 엔진명. Gemini→OpenAI 폴백."""
    errors = []
    order = {"gemini": ["gemini"], "openai": ["openai"]}.get(provider, ["gemini", "openai"])
    for pv in order:
        try:
            if pv == "gemini" and available_gemini():
                return _gemini_edit(image_bytes, prompt), "Gemini"
            if pv == "openai" and available_openai():
                return _openai_edit(image_bytes, prompt), "OpenAI(gpt-image-1)"
        except Exception as e:
            errors.append(str(e)[:120])
    raise RuntimeError(" / ".join(errors) or "사용 가능한 편집 엔진 없음")


def expand_from_reference(image_bytes, scenes, provider="auto"):
    """선택한 장면들에 대해 변형 이미지 생성. [(scene, b64, engine|None, err|None)] 반환."""
    results = []
    for scene in scenes:
        prompt = SCENE_PROMPTS.get(scene, scene)
        try:
            imgs, eng = edit_image(image_bytes, prompt, provider=provider)
            results.append((scene, imgs[0], eng, None))
        except Exception as e:
            results.append((scene, None, None, str(e)[:120]))
    return results
