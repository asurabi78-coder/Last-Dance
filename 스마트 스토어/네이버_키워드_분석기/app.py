import base64
import hashlib
import hmac
import json
import re
import time
import zlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from io import BytesIO

import pandas as pd
import requests
import streamlit as st
from requests.exceptions import Timeout, RequestException

try:
    from streamlit_cookies_manager import EncryptedCookieManager
    COOKIE_MANAGER_AVAILABLE = True
except Exception:
    EncryptedCookieManager = None
    COOKIE_MANAGER_AVAILABLE = False


# =========================================================
# Streamlit 기본 화면 설정
# =========================================================

st.set_page_config(
    page_title="네이버 키워드 & 카테고리 분석기",
    page_icon="🔎",
    layout="wide"
)


# =========================================================
# 기본 설정
# =========================================================

SHOPPING_API_URL = "https://openapi.naver.com/v1/search/shop.json"
DATALAB_SEARCH_API_URL = "https://openapi.naver.com/v1/datalab/search"
SEARCHAD_API_BASE_URL = "https://api.searchad.naver.com"

COOKIE_PREFIX = "naver_keyword_analyzer/"
COOKIE_SETTINGS_KEY = "api_settings_v1"

# 상품 프리셋은 크기가 커질 수 있어 압축 후 여러 쿠키로 나눠 저장합니다.
PRESET_COOKIE_PREFIX = "product_presets_v1"
PRESET_CHUNK_SIZE = 2800
PRESET_MAX_CHUNKS = 20

REQUEST_TIMEOUT = (30, 60)
REQUEST_RETRIES = 3


# =========================================================
# 쿠키 암호 설정
# =========================================================

def get_cookie_password():
    try:
        password = st.secrets.get("COOKIES_PASSWORD", "")
    except Exception:
        password = ""

    if not password:
        password = "local-dev-cookie-password-change-this-value"

    return password


# =========================================================
# 쿠키 매니저 초기화
# =========================================================

cookies = None

if COOKIE_MANAGER_AVAILABLE:
    try:
        cookies = EncryptedCookieManager(
            prefix=COOKIE_PREFIX,
            password=get_cookie_password(),
        )

        if not cookies.ready():
            st.info("브라우저 저장소를 준비 중입니다. 잠시만 기다려주세요.")
            st.stop()

    except Exception as e:
        cookies = None
        st.warning(f"쿠키 저장 기능을 초기화하지 못했습니다: {e}")
else:
    st.warning(
        "streamlit-cookies-manager 패키지를 불러오지 못했습니다. "
        "requirements.txt에 streamlit-cookies-manager가 포함되어 있는지 확인하세요."
    )


# =========================================================
# 기본 API 설정 구조
# =========================================================

def default_settings():
    return {
        "NAVER_CLIENT_ID": "",
        "NAVER_CLIENT_SECRET": "",
        "NAVER_AD_API_KEY": "",
        "NAVER_AD_SECRET_KEY": "",
        "NAVER_AD_CUSTOMER_ID": "",
    }


def normalize_settings(settings):
    base = default_settings()

    if not isinstance(settings, dict):
        return base

    for key in base:
        base[key] = str(settings.get(key, "") or "").strip()

    return base


def has_all_settings(settings):
    settings = normalize_settings(settings)

    required_keys = [
        "NAVER_CLIENT_ID",
        "NAVER_CLIENT_SECRET",
        "NAVER_AD_API_KEY",
        "NAVER_AD_SECRET_KEY",
        "NAVER_AD_CUSTOMER_ID",
    ]

    return all(settings.get(key, "").strip() for key in required_keys)


def has_shopping_settings(settings):
    settings = normalize_settings(settings)
    return bool(settings["NAVER_CLIENT_ID"] and settings["NAVER_CLIENT_SECRET"])


def parse_cookie_settings(raw_value):
    if raw_value is None:
        return default_settings()

    if isinstance(raw_value, dict):
        return normalize_settings(raw_value)

    raw_text = str(raw_value).strip()

    if raw_text in ["", "null", "None", "{}"]:
        return default_settings()

    try:
        parsed = json.loads(raw_text)
        return normalize_settings(parsed)
    except Exception:
        return default_settings()


def sync_form_from_settings(settings):
    settings = normalize_settings(settings)

    st.session_state["form_NAVER_CLIENT_ID"] = settings["NAVER_CLIENT_ID"]
    st.session_state["form_NAVER_CLIENT_SECRET"] = settings["NAVER_CLIENT_SECRET"]
    st.session_state["form_NAVER_AD_API_KEY"] = settings["NAVER_AD_API_KEY"]
    st.session_state["form_NAVER_AD_SECRET_KEY"] = settings["NAVER_AD_SECRET_KEY"]
    st.session_state["form_NAVER_AD_CUSTOMER_ID"] = settings["NAVER_AD_CUSTOMER_ID"]


def load_settings_from_cookie():
    if cookies is None:
        return default_settings()

    try:
        raw_value = cookies.get(COOKIE_SETTINGS_KEY)
        return parse_cookie_settings(raw_value)
    except Exception:
        return default_settings()


def save_settings_to_cookie(settings):
    if cookies is None:
        return False, "쿠키 저장 기능을 사용할 수 없습니다."

    try:
        cookies[COOKIE_SETTINGS_KEY] = json.dumps(
            normalize_settings(settings),
            ensure_ascii=False
        )
        cookies.save()
        return True, "이 브라우저에 API 키를 저장했습니다."
    except Exception as e:
        return False, f"쿠키 저장 중 오류가 발생했습니다: {e}"


def delete_settings_cookie():
    if cookies is None:
        return False, "쿠키 저장 기능을 사용할 수 없습니다."

    try:
        try:
            del cookies[COOKIE_SETTINGS_KEY]
        except Exception:
            cookies[COOKIE_SETTINGS_KEY] = ""

        cookies.save()
        return True, "저장된 API 키를 삭제했습니다."
    except Exception as e:
        return False, f"쿠키 삭제 중 오류가 발생했습니다: {e}"


# =========================================================
# 상품 프리셋 저장/불러오기
# =========================================================

def default_presets_data():
    return {
        "version": 1,
        "products": []
    }


def normalize_presets_data(data):
    base = default_presets_data()

    if not isinstance(data, dict):
        return base

    products = data.get("products", [])
    if not isinstance(products, list):
        products = []

    normalized_products = []

    for product in products:
        if not isinstance(product, dict):
            continue

        preset_id = str(product.get("id", "") or "").strip()
        if not preset_id:
            preset_id = make_preset_id(
                product.get("store_name", ""),
                product.get("product_name", ""),
                product.get("product_url", "")
            )

        keywords_text = str(product.get("keywords_text", "") or "").strip()
        if not keywords_text and isinstance(product.get("keywords"), list):
            keywords_text = "\n".join(str(k).strip() for k in product.get("keywords", []) if str(k).strip())

        normalized_products.append({
            "id": preset_id,
            "store_name": str(product.get("store_name", "") or "").strip(),
            "product_name": str(product.get("product_name", "") or "").strip(),
            "mall_name": str(product.get("mall_name", "") or "").strip(),
            "product_url": str(product.get("product_url", "") or "").strip(),
            "keywords_text": keywords_text,
            "thumbnail_url": str(product.get("thumbnail_url", "") or "").strip(),
            "created_at": str(product.get("created_at", "") or "").strip(),
            "updated_at": str(product.get("updated_at", "") or "").strip(),
            "last_checked_at": str(product.get("last_checked_at", "") or "").strip(),
        })

    base["products"] = normalized_products
    return base


def make_preset_id(store_name, product_name, product_url):
    raw = f"{store_name}|{product_name}|{product_url}|{time.time()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def encode_presets_for_cookie(data):
    json_text = json.dumps(normalize_presets_data(data), ensure_ascii=False)
    compressed = zlib.compress(json_text.encode("utf-8"))
    encoded = base64.urlsafe_b64encode(compressed).decode("utf-8")
    return encoded


def decode_presets_from_cookie(encoded):
    if not encoded:
        return default_presets_data()

    try:
        compressed = base64.urlsafe_b64decode(encoded.encode("utf-8"))
        json_text = zlib.decompress(compressed).decode("utf-8")
        data = json.loads(json_text)
        return normalize_presets_data(data)
    except Exception:
        return default_presets_data()


def load_presets_from_cookie():
    if cookies is None:
        return default_presets_data()

    try:
        count_raw = cookies.get(f"{PRESET_COOKIE_PREFIX}_count")
        count = safe_number(count_raw)

        if count <= 0:
            legacy_raw = cookies.get(PRESET_COOKIE_PREFIX)
            if legacy_raw:
                return decode_presets_from_cookie(legacy_raw)
            return default_presets_data()

        chunks = []
        for index in range(count):
            chunk = cookies.get(f"{PRESET_COOKIE_PREFIX}_{index}")
            if chunk is None:
                return default_presets_data()
            chunks.append(str(chunk))

        return decode_presets_from_cookie("".join(chunks))

    except Exception:
        return default_presets_data()


def save_presets_to_cookie(data):
    if cookies is None:
        return False, "상품 프리셋 저장 기능을 사용할 수 없습니다."

    try:
        encoded = encode_presets_for_cookie(data)
        chunks = [encoded[i:i + PRESET_CHUNK_SIZE] for i in range(0, len(encoded), PRESET_CHUNK_SIZE)]

        if len(chunks) > PRESET_MAX_CHUNKS:
            return False, "저장 데이터가 너무 큽니다. JSON 백업 후 오래된 상품을 일부 삭제해주세요."

        for index in range(PRESET_MAX_CHUNKS):
            key = f"{PRESET_COOKIE_PREFIX}_{index}"
            try:
                del cookies[key]
            except Exception:
                cookies[key] = ""

        cookies[f"{PRESET_COOKIE_PREFIX}_count"] = str(len(chunks))
        for index, chunk in enumerate(chunks):
            cookies[f"{PRESET_COOKIE_PREFIX}_{index}"] = chunk

        cookies.save()
        return True, "상품 프리셋을 이 브라우저에 저장했습니다."

    except Exception as e:
        return False, f"상품 프리셋 저장 중 오류가 발생했습니다: {e}"


def delete_all_presets_cookie():
    if cookies is None:
        return False, "상품 프리셋 저장 기능을 사용할 수 없습니다."

    try:
        try:
            del cookies[f"{PRESET_COOKIE_PREFIX}_count"]
        except Exception:
            cookies[f"{PRESET_COOKIE_PREFIX}_count"] = "0"

        try:
            del cookies[PRESET_COOKIE_PREFIX]
        except Exception:
            cookies[PRESET_COOKIE_PREFIX] = ""

        for index in range(PRESET_MAX_CHUNKS):
            key = f"{PRESET_COOKIE_PREFIX}_{index}"
            try:
                del cookies[key]
            except Exception:
                cookies[key] = ""

        cookies.save()
        return True, "저장된 상품 프리셋을 모두 삭제했습니다."
    except Exception as e:
        return False, f"상품 프리셋 삭제 중 오류가 발생했습니다: {e}"


def get_products_from_presets(data):
    return normalize_presets_data(data).get("products", [])


def get_store_names(data):
    products = get_products_from_presets(data)
    stores = sorted(list({p.get("store_name", "") for p in products if p.get("store_name", "")}))
    return stores


def get_products_by_store(data, store_name):
    products = get_products_from_presets(data)
    if not store_name or store_name == "전체":
        return products
    return [p for p in products if p.get("store_name", "") == store_name]


def find_preset_product(data, preset_id):
    for product in get_products_from_presets(data):
        if product.get("id") == preset_id:
            return product
    return None


def count_keywords(keywords_text):
    return len(split_lines(keywords_text))


def preset_display_name(product):
    product_name = product.get("product_name", "상품명 없음") or "상품명 없음"
    mall_name = product.get("mall_name", "")
    keyword_count = count_keywords(product.get("keywords_text", ""))
    if mall_name:
        return f"{product_name} / {mall_name} / 키워드 {keyword_count}개"
    return f"{product_name} / 키워드 {keyword_count}개"


def upsert_preset_product(data, product):
    data = normalize_presets_data(data)
    products = data.get("products", [])

    product = dict(product)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not product.get("id"):
        product["id"] = make_preset_id(product.get("store_name", ""), product.get("product_name", ""), product.get("product_url", ""))
        product["created_at"] = now

    product["updated_at"] = now

    normalized_product = normalize_presets_data({"products": [product]}).get("products", [])[0]

    updated = False
    new_products = []
    for old in products:
        if old.get("id") == normalized_product.get("id"):
            if not normalized_product.get("created_at"):
                normalized_product["created_at"] = old.get("created_at", now)
            new_products.append(normalized_product)
            updated = True
        else:
            new_products.append(old)

    if not updated:
        new_products.append(normalized_product)

    data["products"] = new_products
    return data, normalized_product.get("id")


def delete_preset_product(data, preset_id):
    data = normalize_presets_data(data)
    data["products"] = [p for p in data.get("products", []) if p.get("id") != preset_id]
    return data


def merge_presets_data(current_data, imported_data):
    current_data = normalize_presets_data(current_data)
    imported_data = normalize_presets_data(imported_data)

    merged = {p.get("id"): p for p in current_data.get("products", []) if p.get("id")}

    for product in imported_data.get("products", []):
        if not product.get("id"):
            product["id"] = make_preset_id(product.get("store_name", ""), product.get("product_name", ""), product.get("product_url", ""))
        merged[product.get("id")] = product

    current_data["products"] = list(merged.values())
    return normalize_presets_data(current_data)


def sync_rank_inputs_from_product(product):
    st.session_state["rank_store_group_input"] = product.get("store_name", "")
    st.session_state["rank_product_name_input"] = product.get("product_name", "")
    st.session_state["rank_mall_name_input"] = product.get("mall_name", "")
    st.session_state["rank_product_url_input"] = product.get("product_url", "")
    st.session_state["rank_keywords_text_input"] = product.get("keywords_text", "")
    st.session_state["selected_preset_id"] = product.get("id", "")


def build_product_from_rank_inputs(existing_id="", thumbnail_url=""):
    return {
        "id": existing_id,
        "store_name": str(st.session_state.get("rank_store_group_input", "") or "").strip(),
        "product_name": str(st.session_state.get("rank_product_name_input", "") or "").strip(),
        "mall_name": str(st.session_state.get("rank_mall_name_input", "") or "").strip(),
        "product_url": str(st.session_state.get("rank_product_url_input", "") or "").strip(),
        "keywords_text": str(st.session_state.get("rank_keywords_text_input", "") or "").strip(),
        "thumbnail_url": str(thumbnail_url or "").strip(),
    }


def get_first_valid_thumbnail_from_rank_df(rank_df):
    if rank_df is None or rank_df.empty or "썸네일URL" not in rank_df.columns:
        return ""

    exposed = rank_df[(rank_df["상태"] == "노출") & (rank_df["썸네일URL"].astype(str).str.strip() != "")]
    if not exposed.empty:
        return str(exposed.iloc[0].get("썸네일URL", "") or "").strip()

    candidates = rank_df[rank_df["썸네일URL"].astype(str).str.strip() != ""]
    if not candidates.empty:
        return str(candidates.iloc[0].get("썸네일URL", "") or "").strip()

    return ""


def update_selected_preset_after_rank(rank_df):
    selected_id = st.session_state.get("selected_preset_id", "")
    if not selected_id:
        return

    product = find_preset_product(st.session_state.product_presets, selected_id)
    if not product:
        return

    thumbnail_url = get_first_valid_thumbnail_from_rank_df(rank_df)

    updated_product = dict(product)
    updated_product["store_name"] = str(st.session_state.get("rank_store_group_input", "") or "").strip()
    updated_product["product_name"] = str(st.session_state.get("rank_product_name_input", "") or "").strip()
    updated_product["mall_name"] = str(st.session_state.get("rank_mall_name_input", "") or "").strip()
    updated_product["product_url"] = str(st.session_state.get("rank_product_url_input", "") or "").strip()
    updated_product["keywords_text"] = str(st.session_state.get("rank_keywords_text_input", "") or "").strip()
    updated_product["last_checked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if thumbnail_url:
        updated_product["thumbnail_url"] = thumbnail_url

    st.session_state.product_presets, _ = upsert_preset_product(st.session_state.product_presets, updated_product)
    save_presets_to_cookie(st.session_state.product_presets)


# =========================================================
# 상품ID / URL / 상품명 / 쇼핑몰명 매칭 함수
# =========================================================

def extract_product_id(text):
    ids = extract_product_ids(text)
    return list(ids)[0] if ids else ""


def extract_product_ids(text):
    if not text:
        return set()

    text = str(text).strip()
    found_ids = set()

    if text.isdigit():
        found_ids.add(text)

    patterns = [
        r"productId=(\d+)",
        r"productNo=(\d+)",
        r"nvMid=(\d+)",
        r"[?&]id=(\d+)",
        r"/products/(\d+)",
        r"/catalog/(\d+)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            found_ids.add(match.group(1))

    for number in re.findall(r"\d{6,}", text):
        found_ids.add(number)

    return found_ids


def normalize_url_text(text):
    if not text:
        return ""

    text = str(text).strip().lower()
    text = text.replace("https://", "").replace("http://", "")
    text = text.replace("www.", "")
    text = text.split("?")[0]
    text = text.rstrip("/")
    return text


def product_url_match(input_url_or_id, api_link, api_product_id):
    if not input_url_or_id:
        return False

    input_ids = extract_product_ids(input_url_or_id)
    api_link_ids = extract_product_ids(api_link)
    api_product_id = str(api_product_id or "").strip()

    if api_product_id:
        api_link_ids.add(api_product_id)

    if input_ids and api_link_ids and input_ids.intersection(api_link_ids):
        return True

    input_url_norm = normalize_url_text(input_url_or_id)
    api_link_norm = normalize_url_text(api_link)

    if input_url_norm and api_link_norm:
        if input_url_norm in api_link_norm or api_link_norm in input_url_norm:
            return True

    return False


def product_name_match(input_name, api_title):
    input_norm = normalize_text(input_name)
    title_norm = normalize_text(api_title)

    if not input_norm or not title_norm:
        return False

    if input_norm in title_norm:
        return True

    raw_tokens = re.split(r"\s+", str(input_name).strip())

    stop_words = [
        "무료배송",
        "당일배송",
        "국내배송",
        "정품",
        "세트",
        "옵션",
        "색상",
        "사이즈",
        "택배",
        "무료",
        "특가",
        "할인",
        "1개",
        "2개",
        "3개",
    ]

    tokens = []

    for token in raw_tokens:
        token_norm = normalize_text(token)

        if len(token_norm) < 2:
            continue

        if token_norm.isdigit():
            continue

        if token_norm in stop_words:
            continue

        tokens.append(token_norm)

    tokens = list(dict.fromkeys(tokens))

    if not tokens:
        return False

    hit_count = sum(1 for token in tokens if token and token in title_norm)
    ratio = hit_count / len(tokens)

    if len(tokens) <= 2:
        return hit_count == len(tokens)

    return ratio >= 0.7


def mall_name_match(input_mall, api_mall):
    input_norm = normalize_text(input_mall)
    mall_norm = normalize_text(api_mall)

    if not input_norm or not mall_norm:
        return False

    return input_norm == mall_norm or input_norm in mall_norm or mall_norm in input_norm


# =========================================================
# 키워드 분석 속도 모드 함수
# =========================================================

def get_auto_workers(keyword_count):
    keyword_count = int(keyword_count)

    if keyword_count <= 50:
        return 2
    return 4


def get_analysis_mode_settings(mode, keyword_count):
    if mode == "안정 모드":
        return {
            "workers": 1,
            "display": 100,
            "label": "안정 모드: 순차 처리 / 상위 100개 기준"
        }

    if mode == "빠른 모드":
        return {
            "workers": 4,
            "display": 50,
            "label": "빠른 모드: 4개 동시 처리 / 상위 50개 기준"
        }

    if mode == "고속 모드":
        return {
            "workers": 6,
            "display": 40,
            "label": "고속 모드: 6개 동시 처리 / 상위 40개 기준, 오류 발생 시 빠른 모드 권장"
        }

    workers = get_auto_workers(keyword_count)

    if keyword_count >= 400:
        display = 50
    else:
        display = 70

    return {
        "workers": workers,
        "display": display,
        "label": f"자동 추천: {workers}개 동시 처리 / 상위 {display}개 기준"
    }


# =========================================================
# 순위 추적 속도 모드 함수
# =========================================================

def get_rank_workers(keyword_count, mode):
    keyword_count = int(keyword_count)

    if mode == "안정 모드":
        return 1

    if mode == "빠른 모드":
        return 3

    if keyword_count <= 5:
        return 1
    elif keyword_count <= 15:
        return 2
    else:
        return 3


# =========================================================
# 네이버 검색광고 API 인증
# =========================================================

def make_searchad_signature(timestamp, method, uri, secret_key):
    message = f"{timestamp}.{method}.{uri}"

    signature = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).digest()

    return base64.b64encode(signature).decode("utf-8")


def get_searchad_headers(method, uri, settings):
    settings = normalize_settings(settings)

    timestamp = str(round(time.time() * 1000))
    secret_key = settings["NAVER_AD_SECRET_KEY"]

    signature = make_searchad_signature(
        timestamp=timestamp,
        method=method,
        uri=uri,
        secret_key=secret_key
    )

    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": settings["NAVER_AD_API_KEY"],
        "X-Customer": str(settings["NAVER_AD_CUSTOMER_ID"]),
        "X-Signature": signature,
    }


# =========================================================
# 네이버 검색광고 API
# 연관 키워드 + 검색수 전체 조회
# =========================================================

def get_related_keywords(keyword, settings):
    uri = "/keywordstool"
    method = "GET"
    url = SEARCHAD_API_BASE_URL + uri

    hint_keyword = clean_keyword(keyword)

    params = {
        "hintKeywords": hint_keyword,
        "showDetail": "1",
    }

    headers = get_searchad_headers(method, uri, settings)

    response = naver_get_with_retry(
        url,
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT,
        retries=REQUEST_RETRIES
    )

    if response.status_code != 200:
        raise Exception(
            f"검색광고 API 오류\n"
            f"상태코드: {response.status_code}\n"
            f"응답내용: {response.text}"
        )

    data = response.json()
    keyword_list = data.get("keywordList", [])

    rows = []

    for item in keyword_list:
        rel_keyword = str(item.get("relKeyword", "")).strip()

        if not rel_keyword:
            continue

        pc_count = safe_number(item.get("monthlyPcQcCnt"))
        mobile_count = safe_number(item.get("monthlyMobileQcCnt"))
        total_count = pc_count + mobile_count

        rows.append({
            "키워드": rel_keyword,
            "PC검색수": pc_count,
            "모바일검색수": mobile_count,
            "총 검색수": total_count,
            "광고경쟁정도": item.get("compIdx", ""),
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=[
            "키워드",
            "PC검색수",
            "모바일검색수",
            "총 검색수",
            "광고경쟁정도",
        ])

    df = df.drop_duplicates(subset=["키워드"])
    df = df.sort_values(by="총 검색수", ascending=False).reset_index(drop=True)

    main_keyword_clean = clean_keyword(keyword)

    if main_keyword_clean not in df["키워드"].astype(str).tolist():
        main_row = pd.DataFrame([{
            "키워드": main_keyword_clean,
            "PC검색수": 0,
            "모바일검색수": 0,
            "총 검색수": 0,
            "광고경쟁정도": "",
        }])

        df = pd.concat([main_row, df], ignore_index=True)

    return df.reset_index(drop=True)


# =========================================================
# 네이버 쇼핑 검색 API
# 상품수 + 대표 카테고리 조회
# =========================================================

def get_shopping_info(keyword, settings, display_count=100):
    settings = normalize_settings(settings)

    display_count = int(display_count)
    display_count = max(1, min(display_count, 100))

    headers = {
        "X-Naver-Client-Id": settings["NAVER_CLIENT_ID"],
        "X-Naver-Client-Secret": settings["NAVER_CLIENT_SECRET"],
    }

    params = {
        "query": keyword,
        "display": display_count,
        "start": 1,
        "sort": "sim",
        "exclude": "used:rental:cbshop",
    }

    response = naver_get_with_retry(
        SHOPPING_API_URL,
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT,
        retries=REQUEST_RETRIES
    )

    if response.status_code != 200:
        raise Exception(
            f"쇼핑 검색 API 오류\n"
            f"키워드: {keyword}\n"
            f"상태코드: {response.status_code}\n"
            f"응답내용: {response.text}"
        )

    data = response.json()

    product_count = safe_number(data.get("total", 0))
    items = data.get("items", [])

    category_list = []

    for item in items:
        category_name = build_category(item)
        if category_name and category_name != "-":
            category_list.append(category_name)

    if category_list:
        representative_category = Counter(category_list).most_common(1)[0][0]
    else:
        representative_category = "-"

    return product_count, representative_category


# =========================================================
# 내 상품 순위 추적 기능
# =========================================================

def search_shopping_page(keyword, settings, start=1, display=100, use_exclude=False):
    settings = normalize_settings(settings)

    headers = {
        "X-Naver-Client-Id": settings["NAVER_CLIENT_ID"],
        "X-Naver-Client-Secret": settings["NAVER_CLIENT_SECRET"],
    }

    params = {
        "query": keyword,
        "display": display,
        "start": start,
        "sort": "sim",
    }

    if use_exclude:
        params["exclude"] = "used:rental:cbshop"

    response = naver_get_with_retry(
        SHOPPING_API_URL,
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT,
        retries=REQUEST_RETRIES
    )

    if response.status_code != 200:
        raise Exception(
            f"쇼핑 검색 API 오류\n"
            f"검색어: {keyword}\n"
            f"상태코드: {response.status_code}\n"
            f"응답내용: {response.text}"
        )

    return response.json()


def find_product_rank(product_name, mall_name, search_keyword, settings, max_rank=300, product_id_or_url=""):
    product_id_or_url = str(product_id_or_url or "").strip()
    input_product_ids = extract_product_ids(product_id_or_url)
    has_identifier = bool(product_id_or_url) or bool(input_product_ids)

    checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    max_rank = int(max_rank)
    max_rank = max(100, min(max_rank, 1000))

    closest_candidates = []

    for start in range(1, max_rank + 1, 100):
        display = min(100, max_rank - start + 1)

        data = search_shopping_page(
            keyword=search_keyword,
            settings=settings,
            start=start,
            display=display,
            use_exclude=False
        )

        items = data.get("items", [])

        for idx, item in enumerate(items, start=0):
            rank = start + idx

            api_title = strip_html_tags(item.get("title", ""))
            api_mall = str(item.get("mallName", "") or "").strip()
            api_product_id = str(item.get("productId", "") or "").strip()
            api_link = str(item.get("link", "") or "").strip()
            api_image = str(item.get("image", "") or "").strip()

            matched = False
            match_type = ""

            if has_identifier:
                if product_url_match(product_id_or_url, api_link, api_product_id):
                    matched = True
                    match_type = "URL/상품ID 정확 매칭"

            if not has_identifier:
                mall_ok = mall_name_match(mall_name, api_mall) if mall_name else False
                name_ok = product_name_match(product_name, api_title)

                if mall_ok and name_ok:
                    matched = True
                    match_type = "쇼핑몰명+상품명 엄격 매칭"

            if not matched and mall_name:
                if mall_name_match(mall_name, api_mall):
                    closest_candidates.append({
                        "rank": rank,
                        "title": api_title,
                        "mall": api_mall,
                        "product_id": api_product_id,
                        "link": api_link,
                        "image": api_image,
                        "price": safe_number(item.get("lprice", 0)),
                        "category": build_category(item),
                    })

            if matched:
                return {
                    "상품명": product_name,
                    "쇼핑몰명": mall_name,
                    "검색어": search_keyword,
                    "확인일시": checked_at,
                    "순위": rank,
                    "상태": "노출",
                    "매칭방식": match_type,
                    "매칭상품명": api_title,
                    "매칭쇼핑몰명": api_mall,
                    "상품ID": api_product_id,
                    "상품URL": api_link,
                    "썸네일URL": api_image,
                    "현재가": safe_number(item.get("lprice", 0)),
                    "대표 카테고리": build_category(item),
                }

        time.sleep(0.08)

    if closest_candidates:
        first_candidate = closest_candidates[0]

        if has_identifier:
            status_message = (
                f"{max_rank}위 내 URL/상품ID 정확 매칭 실패 / "
                f"동일 쇼핑몰 후보 {first_candidate['rank']}위 발견"
            )
        else:
            status_message = (
                f"{max_rank}위 내 상품명 정확 매칭 실패 / "
                f"동일 쇼핑몰 후보 {first_candidate['rank']}위 발견"
            )

        candidate_title = first_candidate["title"]
        candidate_mall = first_candidate["mall"]
        candidate_product_id = first_candidate["product_id"]
        candidate_link = first_candidate["link"]
        candidate_image = first_candidate["image"]
        candidate_price = first_candidate["price"]
        candidate_category = first_candidate["category"]

    else:
        if has_identifier:
            status_message = f"{max_rank}위 내 URL/상품ID 정확 매칭 상품 없음"
        else:
            status_message = f"{max_rank}위 내 미노출"

        candidate_title = "-"
        candidate_mall = "-"
        candidate_product_id = list(input_product_ids)[0] if input_product_ids else "-"
        candidate_link = "-"
        candidate_image = ""
        candidate_price = "-"
        candidate_category = "-"

    return {
        "상품명": product_name,
        "쇼핑몰명": mall_name,
        "검색어": search_keyword,
        "확인일시": checked_at,
        "순위": "미노출",
        "상태": status_message,
        "매칭방식": "-",
        "매칭상품명": candidate_title,
        "매칭쇼핑몰명": candidate_mall,
        "상품ID": candidate_product_id,
        "상품URL": candidate_link,
        "썸네일URL": candidate_image,
        "현재가": candidate_price,
        "대표 카테고리": candidate_category,
    }


def build_rank_error_row(product_name, mall_name, keyword, product_id_or_url, error):
    return {
        "상품명": product_name,
        "쇼핑몰명": mall_name,
        "검색어": keyword,
        "확인일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "순위": "오류",
        "상태": str(error)[:120],
        "매칭방식": "-",
        "매칭상품명": "-",
        "매칭쇼핑몰명": "-",
        "상품ID": extract_product_id(product_id_or_url) or "-",
        "상품URL": "-",
        "썸네일URL": "",
        "현재가": "-",
        "대표 카테고리": "-",
    }


def track_product_ranks(
    product_name,
    mall_name,
    search_keywords,
    settings,
    max_rank=300,
    product_id_or_url="",
    progress_bar=None,
    status_area=None,
    rank_speed_mode="자동 추천"
):
    rows = []
    total = len(search_keywords)
    workers = get_rank_workers(total, rank_speed_mode)

    if status_area:
        status_area.info(f"순위 추적 시작: 총 {total}개 검색어 / {workers}개 동시 처리")

    if workers <= 1:
        for position, keyword in enumerate(search_keywords, start=1):
            if status_area:
                status_area.info(f"순위 확인 중: {keyword} ({position}/{total})")

            try:
                row = find_product_rank(
                    product_name=product_name,
                    mall_name=mall_name,
                    search_keyword=keyword,
                    settings=settings,
                    max_rank=max_rank,
                    product_id_or_url=product_id_or_url,
                )
            except Exception as e:
                row = build_rank_error_row(product_name, mall_name, keyword, product_id_or_url, e)

            rows.append(row)

            if progress_bar:
                progress_bar.progress(position / total)

            time.sleep(0.08)

    else:
        completed = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_keyword = {}

            for keyword in search_keywords:
                future = executor.submit(
                    find_product_rank,
                    product_name,
                    mall_name,
                    keyword,
                    settings,
                    max_rank,
                    product_id_or_url
                )
                future_to_keyword[future] = keyword

            for future in as_completed(future_to_keyword):
                keyword = future_to_keyword[future]
                completed += 1

                try:
                    row = future.result()
                except Exception as e:
                    row = build_rank_error_row(product_name, mall_name, keyword, product_id_or_url, e)

                rows.append(row)

                if progress_bar:
                    progress_bar.progress(completed / total)

                if status_area and (completed == 1 or completed % 3 == 0 or completed == total):
                    status_area.info(f"순위 확인 중: {completed}/{total}개 완료 ({workers}개 동시 처리)")

    result_df = pd.DataFrame(rows)

    if not result_df.empty:
        order_map = {keyword: index for index, keyword in enumerate(search_keywords)}
        result_df["_순서"] = result_df["검색어"].map(order_map).fillna(999999)
        result_df = result_df.sort_values(by="_순서").drop(columns=["_순서"]).reset_index(drop=True)

    return result_df


# =========================================================
# 경쟁강도 계산
# =========================================================

def calculate_competition(product_count, total_search_count):
    if total_search_count <= 0:
        return "-", "검색수 없음"

    score = product_count / total_search_count

    if score < 0.5:
        level = "매우 낮음"
    elif score < 1:
        level = "낮음"
    elif score < 3:
        level = "보통"
    elif score < 10:
        level = "높음"
    else:
        level = "매우 높음"

    return round(score, 2), level


# =========================================================
# 키워드 분석
# =========================================================

def build_keyword_result_row(row, settings, display_count=100):
    rel_keyword = row["키워드"]
    total_search = safe_number(row["총 검색수"])

    product_count, representative_category = get_shopping_info(
        rel_keyword,
        settings,
        display_count=display_count
    )

    competition_score, competition_level = calculate_competition(
        product_count,
        total_search
    )

    return {
        "키워드": rel_keyword,
        "대표 카테고리": representative_category,
        "총 검색수": total_search,
        "상품수": product_count,
        "경쟁강도": competition_score,
        "경쟁수준": competition_level,
        "PC검색수": safe_number(row.get("PC검색수")),
        "모바일검색수": safe_number(row.get("모바일검색수")),
        "광고경쟁정도": row.get("광고경쟁정도", ""),
    }


def build_keyword_error_row(row, error):
    rel_keyword = row["키워드"]
    total_search = safe_number(row["총 검색수"])

    return {
        "키워드": rel_keyword,
        "대표 카테고리": f"오류: {str(error)[:100]}",
        "총 검색수": total_search,
        "상품수": 0,
        "경쟁강도": "-",
        "경쟁수준": "오류",
        "PC검색수": safe_number(row.get("PC검색수")),
        "모바일검색수": safe_number(row.get("모바일검색수")),
        "광고경쟁정도": row.get("광고경쟁정도", ""),
    }


def analyze_keywords(keyword, settings, progress_bar=None, status_area=None, analysis_mode="자동 추천"):
    related_df = get_related_keywords(keyword, settings)

    if related_df.empty:
        return pd.DataFrame(columns=[
            "키워드",
            "대표 카테고리",
            "총 검색수",
            "상품수",
            "경쟁강도",
            "경쟁수준",
            "PC검색수",
            "모바일검색수",
            "광고경쟁정도",
        ])

    total_rows = len(related_df)
    mode_settings = get_analysis_mode_settings(analysis_mode, total_rows)
    workers = int(mode_settings["workers"])
    display_count = int(mode_settings["display"])

    if status_area:
        status_area.info(
            f"{mode_settings['label']} / 총 {total_rows:,}개 키워드 분석을 시작합니다."
        )

    final_rows = []

    if workers <= 1:
        for position, (_, row) in enumerate(related_df.iterrows(), start=1):
            rel_keyword = row["키워드"]

            if status_area:
                status_area.info(f"분석 중: {rel_keyword} ({position}/{total_rows})")

            try:
                result_row = build_keyword_result_row(
                    row=row,
                    settings=settings,
                    display_count=display_count
                )
                final_rows.append(result_row)

            except Exception as e:
                final_rows.append(build_keyword_error_row(row, e))

            if progress_bar:
                progress_bar.progress(position / total_rows)

            time.sleep(0.03)

    else:
        completed = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_row = {}

            for _, row in related_df.iterrows():
                future = executor.submit(
                    build_keyword_result_row,
                    row,
                    settings,
                    display_count
                )
                future_to_row[future] = row

            for future in as_completed(future_to_row):
                row = future_to_row[future]
                completed += 1

                try:
                    result_row = future.result()
                    final_rows.append(result_row)

                except Exception as e:
                    final_rows.append(build_keyword_error_row(row, e))

                if progress_bar:
                    progress_bar.progress(completed / total_rows)

                if status_area and (completed == 1 or completed % 5 == 0 or completed == total_rows):
                    status_area.info(
                        f"분석 중: {completed:,}/{total_rows:,}개 완료 "
                        f"({mode_settings['label']})"
                    )

    result_df = pd.DataFrame(final_rows)

    if result_df.empty:
        return result_df

    result_df = result_df.sort_values(
        by="총 검색수",
        ascending=False
    ).reset_index(drop=True)

    return result_df


# =========================================================
# API 연결 테스트
# =========================================================

def test_shopping_api(settings):
    settings = normalize_settings(settings)

    headers = {
        "X-Naver-Client-Id": settings["NAVER_CLIENT_ID"],
        "X-Naver-Client-Secret": settings["NAVER_CLIENT_SECRET"],
    }

    params = {
        "query": "사과",
        "display": 1,
        "start": 1,
        "sort": "sim",
    }

    try:
        response = naver_get_with_retry(
            SHOPPING_API_URL,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT,
            retries=REQUEST_RETRIES
        )

        if response.status_code == 200:
            return True, "쇼핑 검색 API 연결 정상"

        return False, f"쇼핑 검색 API 오류: {response.status_code} / {response.text}"

    except Exception as e:
        return False, f"쇼핑 검색 API 연결 실패: {str(e)}"


def test_datalab_api(settings):
    try:
        trend_df, _, _, _ = get_keyword_monthly_trend("사과", settings, current_monthly_search=10000)

        if trend_df is not None:
            return True, "데이터랩 트렌드 API 연결 정상"

        return False, "데이터랩 트렌드 API 응답이 비어 있습니다."

    except Exception as e:
        return False, f"데이터랩 트렌드 API 연결 실패: {str(e)}"


def test_searchad_api(settings):
    uri = "/keywordstool"
    method = "GET"
    url = SEARCHAD_API_BASE_URL + uri

    headers = get_searchad_headers(method, uri, settings)

    params = {
        "hintKeywords": "사과",
        "showDetail": "1",
    }

    try:
        response = naver_get_with_retry(
            url,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT,
            retries=REQUEST_RETRIES
        )

        if response.status_code == 200:
            return True, "검색광고 API 연결 정상"

        return False, f"검색광고 API 오류: {response.status_code} / {response.text}"

    except Exception as e:
        return False, f"검색광고 API 연결 실패: {str(e)}"


# =========================================================
# 엑셀 다운로드용 변환
# =========================================================

def dataframe_to_excel_bytes(df, sheet_name="결과"):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)

        worksheet = writer.sheets[sheet_name]

        for column_cells in worksheet.columns:
            max_length = 0
            column_letter = column_cells[0].column_letter

            for cell in column_cells:
                try:
                    cell_value = str(cell.value) if cell.value is not None else ""
                    max_length = max(max_length, len(cell_value))
                except Exception:
                    pass

            adjusted_width = min(max_length + 2, 70)
            worksheet.column_dimensions[column_letter].width = adjusted_width

    return output.getvalue()


# =========================================================
# 세션 상태 초기화
# =========================================================

if "api_settings" not in st.session_state:
    st.session_state.api_settings = default_settings()

if "cookie_loaded" not in st.session_state:
    st.session_state.cookie_loaded = False

if "presets_loaded" not in st.session_state:
    st.session_state.presets_loaded = False

if "product_presets" not in st.session_state:
    st.session_state.product_presets = default_presets_data()

if "selected_preset_id" not in st.session_state:
    st.session_state.selected_preset_id = ""

if "result_df" not in st.session_state:
    st.session_state.result_df = None

if "rank_result_df" not in st.session_state:
    st.session_state.rank_result_df = None

if "rank_history_df" not in st.session_state:
    st.session_state.rank_history_df = None

if "last_keyword" not in st.session_state:
    st.session_state.last_keyword = ""

if "trend_df" not in st.session_state:
    st.session_state.trend_df = None

if "trend_period_text" not in st.session_state:
    st.session_state.trend_period_text = ""

if "trend_keyword" not in st.session_state:
    st.session_state.trend_keyword = ""

if "trend_current_monthly_search" not in st.session_state:
    st.session_state.trend_current_monthly_search = 0

if "trend_base_month" not in st.session_state:
    st.session_state.trend_base_month = ""

if "rank_store_group_input" not in st.session_state:
    st.session_state.rank_store_group_input = ""

if "rank_product_name_input" not in st.session_state:
    st.session_state.rank_product_name_input = ""

if "rank_mall_name_input" not in st.session_state:
    st.session_state.rank_mall_name_input = ""

if "rank_product_url_input" not in st.session_state:
    st.session_state.rank_product_url_input = ""

if "rank_keywords_text_input" not in st.session_state:
    st.session_state.rank_keywords_text_input = "고양이 발매트\n규조토 발매트\n욕실 발매트\n주방 발매트\n빨아쓰는 발매트"

for key, value in default_settings().items():
    form_key = f"form_{key}"
    if form_key not in st.session_state:
        st.session_state[form_key] = value


# =========================================================
# 쿠키에서 API 설정 / 상품 프리셋 자동 불러오기
# =========================================================

if not st.session_state.cookie_loaded:
    saved_settings = load_settings_from_cookie()

    if has_all_settings(saved_settings) or has_shopping_settings(saved_settings):
        st.session_state.api_settings = saved_settings
        sync_form_from_settings(saved_settings)

    st.session_state.cookie_loaded = True

if not st.session_state.presets_loaded:
    st.session_state.product_presets = load_presets_from_cookie()
    st.session_state.presets_loaded = True


# =========================================================
# 화면 시작
# =========================================================

st.title("🔎 네이버 키워드 & 카테고리 분석기")
st.caption("스마트스토어 운영자를 위한 웹앱 | 키워드 분석 · 추정 월간 검색수 그래프 · 상품 프리셋 · 내 상품 순위 추적 · 엑셀 다운로드")


# =========================================================
# 탭 구성
# =========================================================

tab_analyze, tab_rank, tab_settings, tab_help = st.tabs([
    "📊 키워드 분석",
    "📈 내 상품 순위 추적",
    "⚙️ API 설정",
    "📘 사용 안내"
])


# =========================================================
# 키워드 분석 탭
# =========================================================

with tab_analyze:
    st.subheader("키워드 분석")

    current_settings = normalize_settings(st.session_state.api_settings)

    if not has_all_settings(current_settings):
        st.warning("키워드 분석은 [API 설정] 탭에서 API 키 5개를 모두 입력해야 사용할 수 있습니다.")
    else:
        st.success("API 설정이 입력되어 있습니다. 바로 분석할 수 있습니다.")

    st.info(
        "연관 키워드 개수 제한 없이 전체 연관 키워드를 분석합니다. "
        "분석한 메인 키워드의 최근 36개월 추정 월간 검색수 그래프도 함께 표시합니다."
    )

    col1, col2, col3 = st.columns([3, 1.2, 1.2])

    with col1:
        keyword = st.text_input(
            "분석할 메인 키워드",
            placeholder="예: 매실, 복숭아, 바디브러쉬, 속눈썹고데기",
            value=st.session_state.last_keyword
        )

    with col2:
        sort_option = st.selectbox(
            "기본 정렬",
            options=[
                "총 검색수 높은 순",
                "경쟁강도 낮은 순",
                "상품수 낮은 순",
                "상품수 높은 순",
            ],
            index=0
        )

    with col3:
        analysis_mode = st.selectbox(
            "분석 속도",
            options=[
                "자동 추천",
                "안정 모드",
                "빠른 모드",
                "고속 모드",
            ],
            index=0,
            help="자동 추천은 안정성을 위해 최대 4개까지 동시 처리합니다."
        )

    st.caption(
        "추정 월간 검색수는 현재 월간 검색수와 네이버 데이터랩 상대지수를 결합해 환산한 값입니다. 실제 과거 검색수와 완전히 일치하지 않을 수 있습니다."
    )

    analyze_button = st.button(
        "전체 연관 키워드 분석 시작",
        type="primary",
        use_container_width=True
    )

    st.divider()

    if analyze_button:
        if not keyword.strip():
            st.error("분석할 키워드를 입력해주세요.")

        elif not has_all_settings(current_settings):
            st.error("키워드 분석은 API 키 5개가 모두 필요합니다. [API 설정] 탭에서 API 키를 먼저 입력해주세요.")

        else:
            st.session_state.last_keyword = keyword.strip()

            progress_bar = st.progress(0)
            status_area = st.empty()

            with st.spinner("전체 연관 키워드와 추정 월간 검색수 그래프를 분석 중입니다."):
                try:
                    result_df = analyze_keywords(
                        keyword=keyword.strip(),
                        settings=current_settings,
                        progress_bar=progress_bar,
                        status_area=status_area,
                        analysis_mode=analysis_mode
                    )

                    current_monthly_search = get_current_monthly_search_from_result_df(
                        keyword=keyword.strip(),
                        result_df=result_df
                    )

                    try:
                        trend_df, trend_period_text, trend_current_search, trend_base_month = get_keyword_monthly_trend(
                            keyword=keyword.strip(),
                            settings=current_settings,
                            current_monthly_search=current_monthly_search
                        )

                        st.session_state.trend_df = trend_df
                        st.session_state.trend_period_text = trend_period_text
                        st.session_state.trend_keyword = keyword.strip()
                        st.session_state.trend_current_monthly_search = trend_current_search
                        st.session_state.trend_base_month = trend_base_month

                    except Exception as trend_error:
                        st.session_state.trend_df = None
                        st.session_state.trend_period_text = ""
                        st.session_state.trend_keyword = keyword.strip()
                        st.session_state.trend_current_monthly_search = current_monthly_search
                        st.session_state.trend_base_month = ""
                        st.warning(f"추정 월간 검색수 그래프 조회 중 오류가 발생했습니다: {trend_error}")

                    if result_df.empty:
                        st.warning("분석 결과가 없습니다.")
                        st.session_state.result_df = None

                    else:
                        if sort_option == "경쟁강도 낮은 순":
                            temp_df = result_df.copy()
                            temp_df["_경쟁강도정렬"] = pd.to_numeric(
                                temp_df["경쟁강도"],
                                errors="coerce"
                            )
                            result_df = temp_df.sort_values(
                                by="_경쟁강도정렬",
                                ascending=True,
                                na_position="last"
                            ).drop(columns=["_경쟁강도정렬"])

                        elif sort_option == "상품수 낮은 순":
                            result_df = result_df.sort_values(
                                by="상품수",
                                ascending=True
                            )

                        elif sort_option == "상품수 높은 순":
                            result_df = result_df.sort_values(
                                by="상품수",
                                ascending=False
                            )

                        else:
                            result_df = result_df.sort_values(
                                by="총 검색수",
                                ascending=False
                            )

                        result_df = result_df.reset_index(drop=True)
                        st.session_state.result_df = result_df

                        progress_bar.progress(1.0)
                        status_area.success("분석 완료!")

                except Exception as e:
                    st.session_state.result_df = None
                    status_area.empty()
                    st.error(f"분석 중 오류가 발생했습니다.\n\n{str(e)}")

    if st.session_state.result_df is not None:
        result_df = st.session_state.result_df

        st.subheader("분석 결과")

        if st.session_state.trend_df is not None and not st.session_state.trend_df.empty:
            st.subheader("최근 36개월 추정 월간 검색수")

            st.caption(
                f"키워드: {st.session_state.trend_keyword} / "
                f"기간: {st.session_state.trend_period_text} / "
                f"현재 월간 검색수 기준값: {safe_number(st.session_state.trend_current_monthly_search):,} / "
                f"보정 기준월: {st.session_state.trend_base_month or '-'}"
            )

            chart_df = st.session_state.trend_df.set_index("월")[["추정월간검색수"]]

            st.line_chart(
                chart_df,
                use_container_width=True
            )

            peak_row = st.session_state.trend_df.loc[
                st.session_state.trend_df["추정월간검색수"].idxmax()
            ]

            recent_row = st.session_state.trend_df.iloc[-1]

            trend_metric1, trend_metric2, trend_metric3 = st.columns(3)

            with trend_metric1:
                st.metric(
                    "현재 월간 검색수 기준값",
                    f"{safe_number(st.session_state.trend_current_monthly_search):,}"
                )

            with trend_metric2:
                st.metric(
                    "최근 36개월 최고 추정 검색수",
                    f"{safe_number(peak_row['추정월간검색수']):,}"
                )

            with trend_metric3:
                st.metric(
                    "기준월 추정 검색수",
                    f"{safe_number(recent_row['추정월간검색수']):,}"
                )

            st.info(
                f"최근 36개월 기준 추정 검색수가 가장 높은 월은 **{peak_row['월']}**이며, "
                f"추정 월간 검색수는 **{safe_number(peak_row['추정월간검색수']):,}**입니다. "
                "이 값은 실제 과거 검색수가 아니라, 현재 검색광고 월간 검색수와 데이터랩 상대지수를 결합해 환산한 시즌성 참고용 추정치입니다."
            )

            st.divider()

        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

        with metric_col1:
            st.metric("분석 키워드 수", f"{len(result_df):,}개")

        with metric_col2:
            st.metric("총 검색수 합계", f"{safe_number(result_df['총 검색수'].sum()):,}")

        with metric_col3:
            st.metric("상품수 합계", f"{safe_number(result_df['상품수'].sum()):,}")

        with metric_col4:
            valid_scores = pd.to_numeric(result_df["경쟁강도"], errors="coerce").dropna()
            avg_score = round(valid_scores.mean(), 2) if len(valid_scores) > 0 else "-"
            st.metric("평균 경쟁강도", avg_score)

        display_columns = [
            "키워드",
            "대표 카테고리",
            "총 검색수",
            "상품수",
            "경쟁강도",
            "경쟁수준",
            "PC검색수",
            "모바일검색수",
            "광고경쟁정도",
        ]

        st.dataframe(
            result_df[display_columns],
            use_container_width=True,
            hide_index=True
        )

        excel_bytes = dataframe_to_excel_bytes(result_df[display_columns], sheet_name="키워드분석")

        file_keyword = clean_keyword(st.session_state.last_keyword) or "keyword"
        file_name = f"{file_keyword}_키워드분석.xlsx"

        st.download_button(
            label="📥 엑셀 다운로드",
            data=excel_bytes,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )


# =========================================================
# 내 상품 순위 추적 탭
# =========================================================

with tab_rank:
    st.subheader("내 상품 순위 추적")

    current_settings = normalize_settings(st.session_state.api_settings)

    if not has_shopping_settings(current_settings):
        st.warning("순위 추적은 [API 설정] 탭에서 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET을 입력해야 사용할 수 있습니다.")
    else:
        st.success("쇼핑 검색 API 설정이 입력되어 있습니다. 순위 추적을 사용할 수 있습니다.")

    st.info(
        "스토어별 상품 프리셋을 저장해두면 상품명, 쇼핑몰명, URL, 검색어 목록을 반복 입력하지 않아도 됩니다. "
        "순위 조회 성공 시 썸네일도 자동 저장되어 다음 조회 때 상품을 더 쉽게 구분할 수 있습니다."
    )

    presets_data = normalize_presets_data(st.session_state.product_presets)
    products = get_products_from_presets(presets_data)
    store_names = get_store_names(presets_data)

    with st.expander("📦 저장 상품 불러오기 / 관리", expanded=True):
        preset_col1, preset_col2, preset_col3 = st.columns([1.2, 2.2, 1])

        with preset_col1:
            selected_store_filter = st.selectbox(
                "스토어 선택",
                options=["전체"] + store_names,
                index=0,
                key="preset_store_filter"
            )

        filtered_products = get_products_by_store(presets_data, selected_store_filter)
        product_options = {p.get("id"): preset_display_name(p) for p in filtered_products}
        option_ids = list(product_options.keys())

        selected_index = 0
        if st.session_state.selected_preset_id in option_ids:
            selected_index = option_ids.index(st.session_state.selected_preset_id)

        with preset_col2:
            selected_preset_id = st.selectbox(
                "상품 선택",
                options=option_ids,
                format_func=lambda preset_id: product_options.get(preset_id, "상품 없음"),
                index=selected_index if option_ids else None,
                placeholder="저장된 상품이 없습니다.",
                key="preset_product_select"
            ) if option_ids else ""

        with preset_col3:
            st.metric("저장 상품", f"{len(products):,}개")

        button_col1, button_col2, button_col3, button_col4 = st.columns(4)

        with button_col1:
            if st.button("선택 상품 불러오기", use_container_width=True, disabled=not bool(selected_preset_id)):
                product = find_preset_product(presets_data, selected_preset_id)
                if product:
                    sync_rank_inputs_from_product(product)
                    st.success("선택 상품을 불러왔습니다.")
                    st.rerun()

        with button_col2:
            if st.button("현재 입력값 새 상품 저장", use_container_width=True):
                new_product = build_product_from_rank_inputs(existing_id="")

                if not new_product["store_name"]:
                    st.error("스토어 구분명을 입력해주세요.")
                elif not new_product["product_name"]:
                    st.error("상품명을 입력해주세요.")
                elif not new_product["mall_name"] and not extract_product_id(new_product["product_url"]):
                    st.error("쇼핑몰명 또는 상품URL/상품ID 중 하나는 입력해주세요.")
                else:
                    st.session_state.product_presets, new_id = upsert_preset_product(st.session_state.product_presets, new_product)
                    save_ok, save_msg = save_presets_to_cookie(st.session_state.product_presets)
                    st.session_state.selected_preset_id = new_id
                    if save_ok:
                        st.success("새 상품 프리셋을 저장했습니다.")
                    else:
                        st.warning(save_msg)
                    st.rerun()

        with button_col3:
            if st.button("선택 상품 수정 저장", use_container_width=True, disabled=not bool(st.session_state.selected_preset_id)):
                old_product = find_preset_product(st.session_state.product_presets, st.session_state.selected_preset_id)
                old_thumbnail = old_product.get("thumbnail_url", "") if old_product else ""
                updated_product = build_product_from_rank_inputs(
                    existing_id=st.session_state.selected_preset_id,
                    thumbnail_url=old_thumbnail
                )

                if not updated_product["store_name"]:
                    st.error("스토어 구분명을 입력해주세요.")
                elif not updated_product["product_name"]:
                    st.error("상품명을 입력해주세요.")
                else:
                    st.session_state.product_presets, _ = upsert_preset_product(st.session_state.product_presets, updated_product)
                    save_ok, save_msg = save_presets_to_cookie(st.session_state.product_presets)
                    if save_ok:
                        st.success("선택 상품 프리셋을 수정 저장했습니다.")
                    else:
                        st.warning(save_msg)
                    st.rerun()

        with button_col4:
            if st.button("선택 상품 삭제", use_container_width=True, disabled=not bool(st.session_state.selected_preset_id)):
                st.session_state.product_presets = delete_preset_product(st.session_state.product_presets, st.session_state.selected_preset_id)
                save_ok, save_msg = save_presets_to_cookie(st.session_state.product_presets)
                st.session_state.selected_preset_id = ""
                if save_ok:
                    st.success("선택 상품 프리셋을 삭제했습니다.")
                else:
                    st.warning(save_msg)
                st.rerun()

        selected_product_for_card = find_preset_product(st.session_state.product_presets, st.session_state.selected_preset_id)

        if selected_product_for_card:
            card_col1, card_col2 = st.columns([1, 4])

            with card_col1:
                thumb = selected_product_for_card.get("thumbnail_url", "")
                if thumb:
                    st.image(thumb, use_container_width=True)
                else:
                    st.caption("썸네일 없음\n순위 조회 성공 시 자동 저장")

            with card_col2:
                st.markdown(f"**{selected_product_for_card.get('product_name', '')}**")
                st.caption(
                    f"스토어 구분: {selected_product_for_card.get('store_name', '-')} / "
                    f"쇼핑몰명: {selected_product_for_card.get('mall_name', '-')} / "
                    f"저장 키워드: {count_keywords(selected_product_for_card.get('keywords_text', ''))}개"
                )
                if selected_product_for_card.get("last_checked_at"):
                    st.caption(f"최근 조회: {selected_product_for_card.get('last_checked_at')}")

        with st.expander("프리셋 백업 / 복원"):
            backup_json = json.dumps(
                normalize_presets_data(st.session_state.product_presets),
                ensure_ascii=False,
                indent=2
            )

            backup_col1, backup_col2 = st.columns(2)

            with backup_col1:
                st.download_button(
                    label="📥 상품 프리셋 JSON 백업 다운로드",
                    data=backup_json.encode("utf-8"),
                    file_name=f"smartstore_rank_presets_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    use_container_width=True
                )

            with backup_col2:
                uploaded_preset_file = st.file_uploader(
                    "상품 프리셋 JSON 불러오기",
                    type=["json"],
                    key="preset_json_uploader"
                )

            restore_mode = st.radio(
                "복원 방식",
                options=["기존 목록에 병합", "기존 목록 삭제 후 교체"],
                horizontal=True,
                key="preset_restore_mode"
            )

            if uploaded_preset_file is not None:
                if st.button("업로드한 프리셋 적용", use_container_width=True):
                    try:
                        imported_text = uploaded_preset_file.read().decode("utf-8")
                        imported_data = normalize_presets_data(json.loads(imported_text))

                        if restore_mode == "기존 목록 삭제 후 교체":
                            st.session_state.product_presets = imported_data
                        else:
                            st.session_state.product_presets = merge_presets_data(st.session_state.product_presets, imported_data)

                        save_ok, save_msg = save_presets_to_cookie(st.session_state.product_presets)
                        if save_ok:
                            st.success("상품 프리셋을 적용했습니다.")
                        else:
                            st.warning(save_msg)
                        st.rerun()
                    except Exception as e:
                        st.error(f"프리셋 파일을 읽는 중 오류가 발생했습니다: {e}")

            danger_col1, danger_col2 = st.columns([3, 1])
            with danger_col2:
                if st.button("전체 프리셋 삭제", use_container_width=True):
                    st.session_state.product_presets = default_presets_data()
                    delete_all_presets_cookie()
                    st.session_state.selected_preset_id = ""
                    st.success("전체 상품 프리셋을 삭제했습니다.")
                    st.rerun()

    st.divider()

    st.subheader("순위 조회 입력")

    rank_col0, rank_col1, rank_col2 = st.columns([1, 2, 1])

    with rank_col0:
        rank_store_group = st.text_input(
            "스토어 구분명",
            placeholder="예: 구매대행, 농수산물, 건기식",
            key="rank_store_group_input"
        )

    with rank_col1:
        rank_product_name = st.text_input(
            "상품명",
            placeholder="예: 고양이 규조토 발매트 40x60 욕실 주방 논슬립 빨아쓰는 소프트 매트",
            key="rank_product_name_input"
        )

    with rank_col2:
        rank_mall_name = st.text_input(
            "쇼핑몰명",
            placeholder="예: 내스토어명",
            key="rank_mall_name_input"
        )

    product_id_or_url = st.text_input(
        "상품ID 또는 네이버쇼핑 상품URL 선택 입력",
        placeholder="비슷한 상품을 여러 개 판매한다면 이 칸 입력을 강력 추천합니다. 입력 시 정확히 그 상품만 노출로 인정합니다.",
        key="rank_product_url_input"
    )

    search_keywords_text = st.text_area(
        "검색어 목록",
        height=160,
        help="검색어를 한 줄에 하나씩 입력하세요.",
        key="rank_keywords_text_input"
    )

    rank_col3, rank_col4, rank_col5 = st.columns([1, 1, 2])

    with rank_col3:
        max_rank = st.selectbox(
            "조회 범위",
            options=[100, 300, 500, 1000],
            index=1,
            help="조회 범위가 커질수록 API 호출량과 시간이 늘어납니다."
        )

    with rank_col4:
        rank_speed_mode = st.selectbox(
            "순위 추적 속도",
            options=["자동 추천", "안정 모드", "빠른 모드"],
            index=0,
            help="자동 추천은 검색어 수에 따라 1~3개 동시 처리합니다."
        )

    with rank_col5:
        st.caption(
            "자동 추천: 1~5개는 순차, 6~15개는 2개 동시, 16개 이상은 3개 동시 처리"
        )

    rank_button = st.button(
        "순위 확인 시작",
        type="primary",
        use_container_width=True
    )

    st.divider()

    if rank_button:
        keyword_list = split_lines(st.session_state.get("rank_keywords_text_input", ""))

        if not rank_product_name.strip():
            st.error("상품명을 입력해주세요.")

        elif not rank_mall_name.strip() and not extract_product_id(product_id_or_url):
            st.error("쇼핑몰명을 입력해주세요. 단, 상품ID 또는 상품URL을 입력한 경우 쇼핑몰명 없이도 조회할 수 있습니다.")

        elif not keyword_list:
            st.error("검색어를 한 줄 이상 입력해주세요.")

        elif not has_shopping_settings(current_settings):
            st.error("순위 추적은 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET이 필요합니다. [API 설정] 탭에서 먼저 입력해주세요.")

        else:
            progress_bar = st.progress(0)
            status_area = st.empty()

            with st.spinner("검색어별 순위를 확인 중입니다. 잠시만 기다려주세요."):
                try:
                    rank_df = track_product_ranks(
                        product_name=rank_product_name.strip(),
                        mall_name=rank_mall_name.strip(),
                        search_keywords=keyword_list,
                        settings=current_settings,
                        max_rank=max_rank,
                        product_id_or_url=product_id_or_url.strip(),
                        progress_bar=progress_bar,
                        status_area=status_area,
                        rank_speed_mode=rank_speed_mode
                    )

                    st.session_state.rank_result_df = rank_df

                    if st.session_state.rank_history_df is None:
                        st.session_state.rank_history_df = rank_df.copy()
                    else:
                        st.session_state.rank_history_df = pd.concat(
                            [st.session_state.rank_history_df, rank_df],
                            ignore_index=True
                        )

                    update_selected_preset_after_rank(rank_df)

                    progress_bar.progress(1.0)
                    status_area.success("순위 확인 완료!")

                except Exception as e:
                    st.session_state.rank_result_df = None
                    status_area.empty()
                    st.error(f"순위 확인 중 오류가 발생했습니다.\n\n{str(e)}")

    if st.session_state.rank_result_df is not None:
        rank_df = st.session_state.rank_result_df

        st.subheader("순위 확인 결과")

        exposed_count = len(rank_df[rank_df["상태"] == "노출"])
        hidden_count = len(rank_df) - exposed_count

        metric1, metric2, metric3 = st.columns(3)

        with metric1:
            st.metric("조회 검색어 수", f"{len(rank_df):,}개")

        with metric2:
            st.metric("노출 확인", f"{exposed_count:,}개")

        with metric3:
            st.metric("미노출/오류", f"{hidden_count:,}개")

        display_rank_columns = [
            "상품명",
            "쇼핑몰명",
            "검색어",
            "확인일시",
            "순위",
            "상태",
            "매칭방식",
            "매칭상품명",
            "매칭쇼핑몰명",
            "상품ID",
            "썸네일URL",
            "현재가",
            "대표 카테고리",
            "상품URL",
        ]

        st.dataframe(
            rank_df[display_rank_columns],
            use_container_width=True,
            hide_index=True,
            column_config={
                "썸네일URL": st.column_config.ImageColumn("썸네일", width="small"),
                "상품URL": st.column_config.LinkColumn("상품URL"),
            }
        )

        today = datetime.now().strftime("%Y%m%d")
        product_file_name = clean_filename(rank_df.iloc[0]["상품명"]) if len(rank_df) > 0 else "상품"
        rank_file_name = f"{product_file_name}_{today}_순위추적.xlsx"

        rank_excel_bytes = dataframe_to_excel_bytes(
            rank_df[display_rank_columns],
            sheet_name="순위추적"
        )

        st.download_button(
            label="📥 순위 결과 엑셀 다운로드",
            data=rank_excel_bytes,
            file_name=rank_file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    if st.session_state.rank_history_df is not None:
        with st.expander("현재 세션 이전 기록 보기"):
            st.caption("이 기록은 현재 접속 세션에서만 유지됩니다. 브라우저를 닫거나 앱이 재시작되면 사라질 수 있습니다.")
            st.dataframe(
                st.session_state.rank_history_df,
                use_container_width=True,
                hide_index=True
            )

            history_file_name = f"순위추적_현재세션기록_{datetime.now().strftime('%Y%m%d')}.xlsx"
            history_excel_bytes = dataframe_to_excel_bytes(
                st.session_state.rank_history_df,
                sheet_name="이전기록"
            )

            st.download_button(
                label="📥 현재 세션 이전 기록 다운로드",
                data=history_excel_bytes,
                file_name=history_file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )


# =========================================================
# API 설정 탭
# =========================================================

with tab_settings:
    st.subheader("API 설정")

    if not COOKIE_MANAGER_AVAILABLE:
        st.error(
            "streamlit-cookies-manager 패키지를 불러오지 못했습니다. "
            "requirements.txt에 streamlit-cookies-manager가 포함되어 있는지 확인하세요."
        )

    st.info(
        "사용자 본인의 API 키를 입력해서 사용하는 방식입니다. "
        "이 브라우저에 저장을 선택하면 같은 PC·같은 브라우저·같은 앱 주소에서 다음 접속 시 자동으로 불러옵니다."
    )

    st.warning(
        "공용 PC에서는 API 키 저장을 사용하지 마세요. "
        "저장된 API 키는 아래 [저장된 API 키 삭제] 버튼으로 삭제할 수 있습니다."
    )

    with st.form("api_settings_form"):
        st.text_input(
            "NAVER_CLIENT_ID",
            placeholder="네이버 개발자센터 Client ID",
            key="form_NAVER_CLIENT_ID"
        )

        st.text_input(
            "NAVER_CLIENT_SECRET",
            placeholder="네이버 개발자센터 Client Secret",
            type="password",
            key="form_NAVER_CLIENT_SECRET"
        )

        st.divider()

        st.text_input(
            "NAVER_AD_API_KEY",
            placeholder="검색광고 API 엑세스라이선스",
            key="form_NAVER_AD_API_KEY"
        )

        st.text_input(
            "NAVER_AD_SECRET_KEY",
            placeholder="검색광고 API 비밀키",
            type="password",
            key="form_NAVER_AD_SECRET_KEY"
        )

        st.text_input(
            "NAVER_AD_CUSTOMER_ID",
            placeholder="검색광고 CUSTOMER_ID 숫자만 입력",
            key="form_NAVER_AD_CUSTOMER_ID"
        )

        remember_browser = st.checkbox(
            "이 브라우저에 API 키 저장",
            value=True,
            help="개인 PC에서만 사용하세요. 공용 PC에서는 체크하지 않는 것을 권장합니다."
        )

        submitted = st.form_submit_button(
            "저장하기",
            type="primary",
            use_container_width=True
        )

    if submitted:
        new_settings = {
            "NAVER_CLIENT_ID": st.session_state["form_NAVER_CLIENT_ID"].strip(),
            "NAVER_CLIENT_SECRET": st.session_state["form_NAVER_CLIENT_SECRET"].strip(),
            "NAVER_AD_API_KEY": st.session_state["form_NAVER_AD_API_KEY"].strip(),
            "NAVER_AD_SECRET_KEY": st.session_state["form_NAVER_AD_SECRET_KEY"].strip(),
            "NAVER_AD_CUSTOMER_ID": st.session_state["form_NAVER_AD_CUSTOMER_ID"].strip(),
        }

        st.session_state.api_settings = normalize_settings(new_settings)

        if remember_browser:
            save_ok, save_msg = save_settings_to_cookie(st.session_state.api_settings)

            if save_ok:
                st.success(save_msg)
                st.info("새로고침 후에도 값이 유지되는지 확인해보세요.")
            else:
                st.warning(save_msg)
        else:
            st.success("API 설정이 현재 세션에만 저장되었습니다. 브라우저를 닫으면 다시 입력해야 할 수 있습니다.")

    st.divider()

    st.subheader("API 연결 테스트")

    if st.button("API 연결 테스트", use_container_width=True):
        current_settings = normalize_settings(st.session_state.api_settings)

        if not has_shopping_settings(current_settings):
            st.error("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET은 반드시 입력되어 있어야 합니다.")

        else:
            with st.spinner("API 연결을 테스트 중입니다. 최대 2~3분 정도 걸릴 수 있습니다."):
                shopping_ok, shopping_msg = test_shopping_api(current_settings)
                datalab_ok, datalab_msg = test_datalab_api(current_settings)

                if has_all_settings(current_settings):
                    searchad_ok, searchad_msg = test_searchad_api(current_settings)
                else:
                    searchad_ok, searchad_msg = False, "검색광고 API 3개 값이 비어 있어 키워드 분석 테스트는 건너뛰었습니다."

            if shopping_ok:
                st.success(shopping_msg)
            else:
                st.error(shopping_msg)

            if datalab_ok:
                st.success(datalab_msg)
            else:
                st.warning(datalab_msg)

            if searchad_ok:
                st.success(searchad_msg)
            else:
                st.warning(searchad_msg)

            if shopping_ok and datalab_ok and searchad_ok:
                st.balloons()
                st.success("모든 API 연결이 정상입니다. 키워드 분석, 추정 월간 검색수 그래프, 순위 추적을 모두 사용할 수 있습니다.")
            elif shopping_ok and datalab_ok:
                st.success("쇼핑 검색 API와 데이터랩 API 연결은 정상입니다. 순위 추적과 추정 월간 검색수 그래프 기능은 사용할 수 있습니다.")

    st.divider()

    st.subheader("저장된 API 키 삭제")

    if st.button("저장된 API 키 삭제", use_container_width=True):
        empty_settings = default_settings()
        st.session_state.api_settings = empty_settings
        sync_form_from_settings(empty_settings)
        st.session_state.result_df = None
        st.session_state.rank_result_df = None
        st.session_state.trend_df = None
        st.session_state.trend_period_text = ""
        st.session_state.trend_keyword = ""
        st.session_state.trend_current_monthly_search = 0
        st.session_state.trend_base_month = ""
        st.session_state.cookie_loaded = True

        delete_ok, delete_msg = delete_settings_cookie()

        if delete_ok:
            st.success(delete_msg)
            st.info("완전히 반영되지 않으면 브라우저를 새로고침하세요.")
        else:
            st.warning(delete_msg)


# =========================================================
# 사용 안내 탭
# =========================================================

with tab_help:
    st.subheader("사용 안내")

    st.markdown("""
### 1. 이 웹앱은 사용자 본인 API 키로 작동합니다

운영자의 API 키를 공용으로 쓰는 방식이 아닙니다.  
각 사용자가 본인의 네이버 API 키를 입력해서 분석합니다.

---

### 2. 필요한 API 키

#### 순위 추적 + 추정 월간 검색수 그래프만 사용할 경우

- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`

#### 키워드 분석까지 사용할 경우

- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`
- `NAVER_AD_API_KEY`
- `NAVER_AD_SECRET_KEY`
- `NAVER_AD_CUSTOMER_ID`

---

### 3. 상품 프리셋 기능

[내 상품 순위 추적] 탭에서 상품 프리셋을 저장할 수 있습니다.

저장되는 항목은 아래와 같습니다.

- 스토어 구분명
- 상품명
- 쇼핑몰명
- 상품URL 또는 상품ID
- 검색어 목록
- 썸네일URL
- 최근 조회일

상품을 한 번 저장해두면 다음부터 상품을 선택하는 것만으로 입력값을 자동으로 불러올 수 있습니다.

---

### 4. 상품 프리셋 백업/복원

상품 프리셋은 브라우저 저장소에 저장됩니다.  
같은 PC·같은 브라우저·같은 앱 주소에서 다시 접속하면 불러올 수 있습니다.

브라우저 캐시 삭제, 다른 PC 사용, 다른 브라우저 사용에 대비해 JSON 백업 다운로드를 권장합니다.

---

### 5. 키워드 분석 기능

[키워드 분석] 탭에서는 메인 키워드 입력 후 연관 키워드, 대표 카테고리, 총 검색수, 상품수, 경쟁강도를 확인할 수 있습니다.

메인 키워드의 최근 36개월 추정 월간 검색수 그래프도 함께 표시됩니다.

---

### 6. 추정 월간 검색수 그래프

이 그래프는 실제 과거 월별 검색수가 아닙니다.

계산 방식은 아래와 같습니다.

현재 검색광고 월간 검색수 × 해당월 데이터랩 상대지수 ÷ 기준월 데이터랩 상대지수

즉, 현재 월간 검색수를 기준으로 과거 36개월의 시즌성을 환산한 추정값입니다.

주의할 점:

- 실제 과거 검색수와 완전히 일치하지 않을 수 있습니다.
- 시장 규모와 시즌성을 빠르게 가늠하기 위한 참고용 지표입니다.
- 매실, 복숭아, 자두, 냉방조끼, 전기장판처럼 계절성이 강한 상품 분석에 유용합니다.

---

### 7. 내 상품 순위 추적 사용법

[내 상품 순위 추적] 탭에서 아래 값을 입력합니다.

- 스토어 구분명
- 상품명
- 쇼핑몰명
- 상품ID 또는 네이버쇼핑 상품URL 선택 입력
- 검색어 여러 줄
- 조회 범위

비슷한 상품을 여러 개 판매하는 경우에는 상품URL 또는 상품ID 입력을 강력 추천합니다.  
상품URL 또는 상품ID를 입력하면 정확히 그 상품이 맞을 때만 노출로 인정합니다.

예시는 아래와 같습니다.
    """)

    st.code(
        """스토어 구분명: 농수산물
상품명: 신비복숭아 2kg 산지직송 제철 복숭아
쇼핑몰명: 내스토어명
상품ID 또는 URL: https://smartstore.naver.com/스토어명/products/1234567890

검색어:
신비복숭아
신비복숭아 2kg
복숭아 2kg
제철복숭아
산지직송 복숭아""",
        language="text"
    )

    st.markdown("""
---

### 8. 순위 추적 기준

이 앱의 순위는 네이버 쇼핑 검색 API 기준 순위입니다.  
실제 네이버 쇼핑 화면은 광고, 개인화, 로그인 상태, 기기, 위치, 카테고리 필터 등에 따라 다르게 보일 수 있습니다.

---

### 9. 조회 범위와 API 호출량

조회 범위가 커질수록 API 호출량이 증가합니다.

- 100위까지: 검색어 1개당 최대 1회 호출
- 300위까지: 검색어 1개당 최대 3회 호출
- 500위까지: 검색어 1개당 최대 5회 호출
- 1000위까지: 검색어 1개당 최대 10회 호출

처음에는 300위까지 조회를 추천합니다.

---

### 10. API 키 저장 방식

[API 설정] 탭에서 **이 브라우저에 API 키 저장**을 체크하고 저장하면,  
같은 PC·같은 브라우저·같은 앱 주소로 다시 접속할 때 API 키를 자동으로 불러올 수 있습니다.

이번 버전은 브라우저 쿠키 저장 방식을 사용합니다.  
쿠키 저장이 차단된 브라우저 환경에서는 자동 불러오기가 되지 않을 수 있습니다.

---

### 11. 공용 PC 주의

공용 PC에서는 API 키 저장을 사용하지 않는 것을 권장합니다.  
실수로 저장했다면 [저장된 API 키 삭제] 버튼을 눌러 삭제하세요.

---

### 12. 연결 오류 안내

Streamlit Cloud 서버에서 네이버 API로 연결이 지연될 경우 API 연결 테스트가 실패할 수 있습니다.

이 경우 잠시 후 다시 시도해보세요.  
반복적으로 실패한다면 Streamlit Cloud 서버와 네이버 API 서버 간 네트워크 문제일 수 있습니다.
    """)
