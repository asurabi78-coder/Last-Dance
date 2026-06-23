from __future__ import annotations

from statistics import mean

from sourcing1688.models import ProductDetail, ProductSearchResult, SourcingScore


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _sales_score(month_sold: int | None, trade_volume: int | None) -> float:
    volume = month_sold if month_sold is not None else trade_volume
    if volume is None:
        return 0.0
    if volume >= 10000:
        return 100.0
    if volume >= 3000:
        return 85.0
    if volume >= 1000:
        return 70.0
    if volume >= 300:
        return 50.0
    if volume > 0:
        return 30.0
    return 0.0


def _buyer_score(buyer_count: int | None) -> float:
    if buyer_count is None:
        return 0.0
    if buyer_count >= 1000:
        return 100.0
    if buyer_count >= 300:
        return 75.0
    if buyer_count >= 100:
        return 55.0
    if buyer_count > 0:
        return 30.0
    return 0.0


def _repurchase_score(rate: float | None) -> float:
    if rate is None:
        return 0.0
    normalized = rate / 100 if rate > 1 else rate
    return _clamp(normalized / 0.35 * 100)


def _seller_score(score: float | None) -> float:
    if score is None:
        return 0.0
    if score <= 5:
        return _clamp(score / 5 * 100)
    return _clamp(score)


def _price_score(price_min: float | None, price_max: float | None) -> float:
    if price_min is None:
        return 0.0
    price = mean([p for p in [price_min, price_max] if p is not None])
    if price <= 0:
        return 0.0
    if price < 2:
        return 45.0
    if price <= 25:
        return 88.0
    if price <= 60:
        return 72.0
    if price <= 120:
        return 55.0
    return 35.0


def _moq_score(moq: int | None) -> float:
    if moq is None:
        return 0.0
    if moq <= 2:
        return 100.0
    if moq <= 10:
        return 85.0
    if moq <= 50:
        return 60.0
    if moq <= 200:
        return 35.0
    return 15.0


def _shipping_score(badges: list[str]) -> float:
    if not badges:
        return 0.0
    text = " ".join(badges)
    score = 45.0
    if "24" in text or "48" in text or "发货" in text:
        score += 35.0
    if "现货" in text or "一件代发" in text:
        score += 20.0
    return _clamp(score)


def _asset_quality_score(product: ProductSearchResult | ProductDetail) -> float:
    if isinstance(product, ProductSearchResult):
        return 85.0 if product.image_url else 0.0
    count = len(product.main_image_urls) + len(product.detail_image_urls) + len(product.option_image_urls)
    if count >= 8:
        return 100.0
    if count >= 4:
        return 80.0
    if count >= 1:
        return 55.0
    return 0.0


def _missing_fields(product: ProductSearchResult | ProductDetail) -> list[str]:
    if isinstance(product, ProductSearchResult):
        fields = ["price_min", "moq", "month_sold", "trade_volume", "repurchase_rate", "seller_score"]
        missing = [field for field in fields if getattr(product, field) is None]
        if product.month_sold is not None or product.trade_volume is not None:
            missing = [field for field in missing if field not in {"month_sold", "trade_volume"}]
    else:
        fields = ["price_tiers", "stock", "month_sold", "trade_volume", "repurchase_rate", "seller"]
        missing = []
        for field in fields:
            value = getattr(product, field)
            if value is None or value == [] or value == {}:
                missing.append(field)
        if product.month_sold is not None or product.trade_volume is not None:
            missing = [field for field in missing if field not in {"month_sold", "trade_volume"}]
        if product.seller and product.seller.score is None:
            missing.append("seller_score")
    for field in getattr(product, "missing_fields", []):
        if field not in missing:
            missing.append(field)
    return missing


def score_product(product: ProductSearchResult | ProductDetail) -> SourcingScore:
    seller_numeric_score = product.seller.score if isinstance(product, ProductDetail) and product.seller else getattr(product, "seller_score", None)
    price_min = product.price_tiers[-1].price if isinstance(product, ProductDetail) and product.price_tiers else getattr(product, "price_min", None)
    price_max = product.price_tiers[0].price if isinstance(product, ProductDetail) and product.price_tiers else getattr(product, "price_max", None)
    moq = product.price_tiers[0].min_quantity if isinstance(product, ProductDetail) and product.price_tiers else getattr(product, "moq", None)
    shipping_badges = getattr(product, "shipping_badges", [])
    buyer_count = getattr(product, "buyer_count", None)
    seller_years = getattr(product, "seller_years_active", None)
    if isinstance(product, ProductDetail) and product.seller:
        seller_years = product.seller.years_active

    parts = {
        "sales": _sales_score(product.month_sold, product.trade_volume) * 0.21,
        "buyers": _buyer_score(buyer_count) * 0.04,
        "repurchase": _repurchase_score(product.repurchase_rate) * 0.20,
        "seller": _seller_score(seller_numeric_score) * 0.16,
        "seller_years": _clamp((seller_years or 0) / 5 * 100) * 0.04,
        "price": _price_score(price_min, price_max) * 0.15,
        "moq": _moq_score(moq) * 0.10,
        "shipping": _shipping_score(shipping_badges) * 0.05,
        "asset": _asset_quality_score(product) * 0.05,
    }
    final_score = round(sum(parts.values()), 2)
    missing = _missing_fields(product)
    confidence = round(_clamp(1.0 - (len(set(missing)) * 0.12), 0.25, 0.98), 2)

    why_good: list[str] = []
    risks: list[str] = []
    notes: list[str] = []

    volume = product.month_sold if product.month_sold is not None else product.trade_volume
    if volume and volume >= 1000:
        why_good.append(f"월판매/거래량 지표가 {volume:,} 수준으로 수요 신호가 있습니다.")
    if product.repurchase_rate is not None and (product.repurchase_rate >= 0.25 or product.repurchase_rate >= 25):
        why_good.append("복구매율이 높은 편이라 반복 구매형 상품 가능성이 있습니다.")
    if seller_numeric_score is not None and _seller_score(seller_numeric_score) >= 85:
        why_good.append("상점 점수가 높아 공급처 신뢰도 신호가 좋습니다.")
    if seller_years and seller_years >= 3:
        why_good.append(f"판매자 운영 연차가 {seller_years}년 수준이라 지속 운영 신호가 있습니다.")
    if moq is not None and moq <= 10:
        why_good.append(f"MOQ {moq}로 소량 테스트가 비교적 쉽습니다.")

    if price_min is not None and price_min < 2:
        risks.append("단가가 지나치게 낮아 품질, 구성품, 배송 조건을 확인해야 합니다.")
    if moq is not None and moq > 50:
        risks.append(f"MOQ {moq}라 초도 테스트 비용과 재고 부담이 큽니다.")
    if volume and volume >= 5000 and seller_numeric_score is None:
        risks.append("판매량은 높지만 상점 점수 데이터가 없어 공급처 검증이 필요합니다.")
    if _asset_quality_score(product) < 55:
        risks.append("이미지/상세페이지 데이터가 부족해 상세 검수가 필요합니다.")
    if missing:
        risks.append(f"핵심 필드 누락: {', '.join(missing)}")
    if len(missing) >= 4:
        risks.append("누락 필드가 많아 현재 점수의 신뢰도가 낮습니다.")

    if not why_good:
        notes.append("현재 수집된 데이터만으로 강한 추천 근거가 부족합니다.")
    notes.append("한국 셀러 관점 점수는 판매량, 복구매율, 상점 점수, 단가, MOQ, 발송/상세 품질을 가중 합산했습니다.")

    if final_score >= 80 and confidence >= 0.75:
        next_action = "샘플 구매 전 옵션, 실제 배송 조건, KC/수입 요건을 확인하세요."
    elif confidence < 0.65:
        next_action = "누락 필드를 상세 조회나 브라우저 확인으로 보강한 뒤 판단하세요."
    else:
        next_action = "가격 구간, MOQ, 리뷰/상점 정보와 경쟁 상품을 비교하세요."

    return SourcingScore(
        offer_id=product.offer_id,
        score=final_score,
        confidence=confidence,
        why_good=why_good,
        risks=risks,
        missing_fields=missing,
        suggested_next_action=next_action,
        sourcing_notes=notes,
        data_quality="high" if confidence >= 0.85 else "medium" if confidence >= 0.65 else "low",
        source_provider=getattr(product, "provider", None),
        live_verified=bool(getattr(product, "live_verified", False)),
    )
