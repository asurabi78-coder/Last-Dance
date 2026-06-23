# -*- coding: utf-8 -*-
"""환경설정: 상위 폴더 .env 로드. 키 값은 절대 외부로 출력하지 않는다."""
import os

try:
    from dotenv import load_dotenv, find_dotenv
    _p = find_dotenv(usecwd=True)
    if not _p:
        _p = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    load_dotenv(_p)
except Exception:
    pass


def get(name: str, default: str = "") -> str:
    # .env에 'set DOMEGGOOK_API_KEY=' 처럼 'set ' 접두가 붙은 경우 방어
    return (os.environ.get(name) or os.environ.get("set " + name) or default).strip()


def present(name: str) -> bool:
    return bool(get(name))


# 카피 LLM 기본 모델 (필요시 .env로 override)
OPENAI_MODEL = get("OPENAI_MODEL", "gpt-4o-mini")
# Gemini 이미지 모델
GEMINI_IMAGE_MODEL = get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
# 도매꾹 오픈API 베이스(스펙 확인 후 .env로 조정 가능)
DOMEGGOOK_API_BASE = get("DOMEGGOOK_API_BASE", "https://domeggook.com/ssl/api/")
