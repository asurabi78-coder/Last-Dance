from sourcing1688.models import ProductSearchResult, SourcingScore
from sourcing1688.storage import SourcingStorage


def test_storage_saves_shortlist_and_exports_json(tmp_path):
    db_path = tmp_path / "sourcing.duckdb"
    storage = SourcingStorage(db_path)
    product = ProductSearchResult(
        offer_id="123456789",
        url="https://detail.1688.com/offer/123456789.html",
        title_zh="黑胶防晒晴雨伞 三折遮阳伞",
        price_min=12.5,
        moq=2,
    )
    score = SourcingScore(
        offer_id="123456789",
        score=88.0,
        confidence=0.92,
        why_good=["소량 테스트 가능"],
        risks=[],
        missing_fields=[],
        suggested_next_action="샘플 구매 전 상세 옵션 확인",
        sourcing_notes=["fixture data"],
    )

    storage.save_search_results("umbrellas", "黑胶伞", [product])
    storage.save_sourcing_score(score)
    storage.add_to_shortlist("umbrellas", "123456789", notes="test")

    shortlist = storage.list_shortlist("umbrellas")
    exported = storage.export_project("umbrellas", "json")

    assert shortlist[0]["offer_id"] == "123456789"
    assert exported["status"] == "ok"
    assert exported["project"] == "umbrellas"
    assert exported["items"][0]["offer_id"] == "123456789"
