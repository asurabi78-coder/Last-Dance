# -*- coding: utf-8 -*-
"""네이버 커머스API — 스마트스토어 상품 '판매대기(WAIT)' 등록(임시저장).
인증: OAuth2 client_credentials + bcrypt 전자서명. 등록: v2/products.
※ 외부통신 차단 환경에선 토큰/업로드/등록(실전송)은 검증 불가 → PC에서 최종 확인.
   검증 가능한 부분: 전자서명 생성, 페이로드 조립(build_payload), 필수값 점검(validate_inputs)."""
import time
import base64

import requests

from . import config

API_BASE = "https://api.commerce.naver.com/external"
TIMEOUT = 30


def available():
    return config.present("NAVER_COMMERCE_CLIENT_ID") and config.present("NAVER_COMMERCE_CLIENT_SECRET")


def _signature(client_id, client_secret, ts_ms):
    """커머스API 전자서명: bcrypt.hashpw(f'{id}_{ts}', client_secret) → base64.
    client_secret 자체가 bcrypt salt 문자열($2a$...)이어야 함."""
    import bcrypt
    pwd = f"{client_id}_{ts_ms}".encode("utf-8")
    hashed = bcrypt.hashpw(pwd, client_secret.encode("utf-8"))
    return base64.standard_b64encode(hashed).decode("utf-8")


def get_token():
    """액세스 토큰 발급(실전송)."""
    cid = config.get("NAVER_COMMERCE_CLIENT_ID")
    csec = config.get("NAVER_COMMERCE_CLIENT_SECRET")
    ts = int(time.time() * 1000)
    sign = _signature(cid, csec, ts)
    data = {"client_id": cid, "timestamp": ts, "client_secret_sign": sign,
            "grant_type": "client_credentials", "type": "SELF"}
    r = requests.post(f"{API_BASE}/v1/oauth2/token", data=data, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"토큰 발급 실패 {r.status_code}: {r.text[:200]}")
    tok = r.json().get("access_token")
    if not tok:
        raise RuntimeError("토큰 응답에 access_token 없음")
    return tok


def upload_image(image_bytes, token):
    """대표이미지를 네이버 이미지서버에 업로드(실전송) → URL 리스트."""
    r = requests.post(f"{API_BASE}/v1/product-images/upload",
                      headers={"Authorization": f"Bearer {token}"},
                      files={"imageFiles": ("hero.png", image_bytes, "image/png")},
                      timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"이미지 업로드 실패 {r.status_code}: {r.text[:200]}")
    images = r.json().get("images", [])
    urls = [im.get("url") for im in images if im.get("url")]
    if not urls:
        raise RuntimeError("이미지 업로드 응답에 url 없음")
    return urls


def validate_inputs(inp):
    """업로드 전 필수값 점검. 누락 항목명 리스트 반환(빈 리스트면 통과)."""
    missing = []
    if not str(inp.get("leafCategoryId") or "").strip():
        missing.append("카테고리코드(leafCategoryId)")
    if not str(inp.get("name") or "").strip():
        missing.append("상품명")
    try:
        if int(inp.get("salePrice") or 0) <= 0:
            missing.append("판매가(>0)")
    except Exception:
        missing.append("판매가(숫자)")
    try:
        if int(inp.get("stockQuantity") or 0) < 0:
            missing.append("재고(0 이상)")
    except Exception:
        missing.append("재고(숫자)")
    if not str(inp.get("representativeImageUrl") or "").strip():
        missing.append("대표이미지")
    return missing


def build_payload(inp, status_type="WAIT"):
    """상품 등록 페이로드(dict) 조립. 순수 함수(네트워크 불필요).
    status_type: 'WAIT'(판매대기=임시저장, 기본) / 'SALE'(판매중).
    ※ 커머스API v2 스키마 기준 골격. 실제 등록 시 일부 필수항목은 계정/카테고리별로 조정 필요(PC 확인)."""
    name = str(inp.get("name") or "").strip()
    detail = inp.get("detailContent") or f"<div>{name}</div>"
    rep = str(inp.get("representativeImageUrl") or "").strip()
    optional_imgs = [u for u in (inp.get("optionalImageUrls") or []) if u]
    payload = {
        "originProduct": {
            "statusType": status_type,          # WAIT = 판매대기(임시저장)
            "saleType": "NEW",
            "leafCategoryId": str(inp.get("leafCategoryId") or "").strip(),
            "name": name,
            "detailContent": detail,
            "images": {
                "representativeImage": {"url": rep},
                "optionalImages": [{"url": u} for u in optional_imgs],
            },
            "salePrice": int(inp.get("salePrice") or 0),
            "stockQuantity": int(inp.get("stockQuantity") or 0),
            "deliveryInfo": {
                "deliveryType": "DELIVERY",
                "deliveryAttributeType": "NORMAL",
                "deliveryCompany": inp.get("deliveryCompany") or "CJGLS",
                "deliveryFee": {
                    "deliveryFeeType": inp.get("deliveryFeeType") or "FREE",
                    "baseFee": int(inp.get("baseFee") or 0),
                },
            },
            "detailAttribute": {
                "afterServiceInfo": {
                    "afterServiceTelephoneNumber": inp.get("asPhone") or "",
                    "afterServiceGuideContent": inp.get("asGuide") or "판매자 문의 바랍니다.",
                },
                "originAreaInfo": {
                    "originAreaCode": inp.get("originAreaCode") or "0200037",  # 기타(국내/수입)
                    "content": inp.get("originContent") or "",
                },
            },
        },
        "smartstoreChannelProduct": {
            "channelProductName": name,
            "naverShoppingRegistration": True,
            "channelProductDisplayStatusType": "ON",
        },
    }
    return payload


def register_product(payload, token):
    """상품 등록(실전송). 성공 시 응답 JSON 반환."""
    r = requests.post(f"{API_BASE}/v2/products",
                      headers={"Authorization": f"Bearer {token}",
                               "Content-Type": "application/json"},
                      json=payload, timeout=TIMEOUT)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"상품 등록 실패 {r.status_code}: {r.text[:300]}")
    return r.json()
