# -*- coding: utf-8 -*-
"""상품 영상 생성 — fal.ai Kling 이미지→영상.
키(FAL_KEY)가 있어야만 동작하며, 모의 폴백은 없다(영상은 실제 호출만)."""
import os
from . import config

# 모델 엔드포인트 (품질/비용 균형)
MODELS = {
    "Kling 2.1 standard (저렴·기본)": "fal-ai/kling-video/v2.1/standard/image-to-video",
    "Kling 2.1 pro (고품질·비쌈)": "fal-ai/kling-video/v2.1/pro/image-to-video",
}
DEFAULT_MODEL = "fal-ai/kling-video/v2.1/standard/image-to-video"

# 영어 프롬프트 권장(Kling)
DEFAULT_PROMPT = ("A person gently holds and uses the product, soft natural studio "
                  "lighting, slow smooth camera movement, realistic e-commerce lifestyle shot")


def available() -> bool:
    return config.present("FAL_KEY")


def _ensure_key():
    k = config.get("FAL_KEY")
    if k:
        os.environ["FAL_KEY"] = k


def generate_video(image_bytes: bytes = None, image_url: str = "", prompt: str = "",
                   duration: str = "5", model: str = DEFAULT_MODEL, on_log=None):
    """이미지→영상 생성. (video_url, engine, warn) 반환. 실패 시 ('', '', warn)."""
    if not available():
        return "", "", "FAL_KEY 없음 (.env에 키를 넣어주세요)"
    _ensure_key()
    try:
        import fal_client
    except Exception:
        return "", "", "fal-client 미설치 → '.venv\\Scripts\\python.exe -m pip install fal-client'"
    try:
        url = image_url or ""
        if image_bytes:
            # fal 저장소 업로드(403 우회): 이미지를 data URI로 직접 전달
            import base64 as _b64
            mime = "image/png"
            if image_bytes[:3] == b"\xff\xd8\xff":
                mime = "image/jpeg"
            elif image_bytes[:4] == b"RIFF":
                mime = "image/webp"
            try:
                url = "data:" + mime + ";base64," + _b64.b64encode(image_bytes).decode()
            except Exception:
                url = fal_client.upload(image_bytes, "image/png")  # 폴백
        if not url:
            return "", "", "기준 이미지가 없습니다"
        args = {"image_url": url, "prompt": (prompt or DEFAULT_PROMPT), "duration": str(duration)}

        def _cb(update):
            if on_log is not None and hasattr(update, "logs"):
                for lg in (getattr(update, "logs", None) or []):
                    try:
                        on_log(lg.get("message", ""))
                    except Exception:
                        pass

        result = fal_client.subscribe(model, arguments=args, with_logs=True, on_queue_update=_cb)
        vurl = ((result or {}).get("video") or {}).get("url", "")
        if not vurl:
            return "", "", "영상 URL을 받지 못했습니다: " + str(result)[:200]
        parts = model.split("/")
        eng = "fal/kling-" + (parts[-3] if len(parts) >= 3 else "?")
        return vurl, eng, None
    except Exception as e:
        return "", "", "영상 생성 실패: " + str(e)
