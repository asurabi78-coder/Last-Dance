from sourcing1688.models import ProductSearchResult
from sourcing1688.scoring import score_product


def test_scores_strong_low_moq_repeat_purchase_candidate():
    product = ProductSearchResult(
        offer_id="123456789",
        url="https://detail.1688.com/offer/123456789.html",
        title_zh="黑胶防晒晴雨伞 三折遮阳伞",
        price_min=12.5,
        price_max=18.8,
        moq=2,
        month_sold=3200,
        trade_volume=8900,
        repurchase_rate=0.34,
        seller_score=4.8,
        seller_name="义乌优伞工厂",
        badges=["实力商家", "源头工厂"],
        shipping_badges=["48小时发货"],
        image_url="https://example.com/main.jpg",
    )

    score = score_product(product)

    assert score.score >= 75
    assert score.confidence >= 0.8
    assert any("MOQ" in reason or "소량" in reason for reason in score.why_good)
    assert score.suggested_next_action


def test_missing_fields_lower_confidence_and_create_risks():
    product = ProductSearchResult(
        offer_id="987654321",
        url="https://detail.1688.com/offer/987654321.html",
        title_zh="防紫外线遮阳伞 批发定制",
        price_min=1.2,
        price_max=1.4,
        moq=200,
        month_sold=10000,
        seller_name="广州伞业批发",
    )

    score = score_product(product)

    assert score.confidence < 0.8
    assert "repurchase_rate" in score.missing_fields
    assert "seller_score" in score.missing_fields
    assert score.risks
