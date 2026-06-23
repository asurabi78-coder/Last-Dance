from __future__ import annotations

import re

from sourcing1688.models import KeywordExpansion
from sourcing1688.utils import encode_1688_search_keyword


CURATED_SEEDS: dict[str, list[str]] = {
    "암막우산": ["黑胶伞", "防晒伞", "遮阳伞", "晴雨伞", "防紫外线伞", "遮光伞"],
    "여행용 파우치": ["旅行收纳袋", "旅行化妆包", "旅游洗漱包", "行李收纳包", "出差收纳袋"],
    "주방 정리함": ["厨房收纳盒", "厨房置物架", "调料收纳盒", "餐具收纳盒", "厨房收纳架"],
    "반려동물 빗": ["宠物梳子", "宠物刷", "宠物除毛梳", "猫狗梳子", "宠物按摩梳"],
    "차량용 햇빛가리개": ["汽车遮阳挡", "车窗遮阳帘", "汽车防晒帘", "前挡遮阳板", "车用遮阳板"],
    "휴대용 선풍기": ["便携风扇", "手持小风扇", "USB小风扇", "迷你风扇", "挂脖风扇"],
    "무드등": ["氛围灯", "小夜灯", "LED氛围灯", "床头灯", "装饰灯"],
    "수납박스": ["收纳箱", "收纳盒", "塑料收纳箱", "衣物收纳箱", "家用收纳箱"],
    "실리콘 주방용품": ["硅胶厨具", "硅胶厨房用品", "硅胶锅铲", "硅胶烘焙工具", "硅胶餐具"],
    "월드컵 축구 유니폼": ["世界杯球衣", "足球服", "国家队球衣", "2026世界杯球衣", "足球训练服"],
    "운동 양말": ["运动袜", "跑步袜", "毛巾底袜", "中筒运动袜"],
    "남성 벨트": ["男士皮带", "自动扣皮带", "腰带", "商务皮带"],
    "크라프트 포장봉투": ["牛皮纸袋", "外卖包装袋", "食品包装袋", "手提牛皮纸袋"],
    "러닝화": ["跑步鞋", "运动鞋", "透气跑鞋", "休闲运动鞋"],
    "남성 속옷": ["男士内裤", "平角裤", "纯棉男内裤", "男士四角裤"],
    "스마트폰 거치대": ["手机支架", "车载手机支架", "桌面手机支架", "懒人手机支架", "手机架"],
    "휴대폰 거치대": ["手机支架", "车载手机支架", "桌面手机支架", "懒人手机支架", "手机架"],
    "여행용품": ["旅行用品", "旅游用品", "旅行收纳", "便携旅行用品", "洗漱包", "分装瓶", "护照夹", "行李牌", "压缩收纳袋", "旅行收纳袋"],
    "여행 용품": ["旅行用品", "旅游用品", "旅行收纳", "便携旅行用品", "洗漱包", "分装瓶", "护照夹", "行李牌", "压缩收纳袋", "旅行收纳袋"],
}

COMPONENT_HINTS: dict[str, list[str]] = {
    "월드컵": ["世界杯", "2026世界杯"],
    "축구": ["足球", "足球训练"],
    "유니폼": ["球衣", "队服"],
    "양말": ["袜", "运动袜"],
    "벨트": ["皮带", "腰带"],
    "포장": ["包装袋", "食品包装"],
    "봉투": ["纸袋", "手提袋"],
    "우산": ["伞", "防晒伞", "晴雨伞"],
    "파우치": ["收纳袋", "化妆包"],
    "여행": ["旅行用品", "旅行收纳", "洗漱包", "分装瓶"],
    "선풍기": ["便携风扇", "手持小风扇"],
    "속옷": ["男士内裤", "平角裤"],
    "스마트폰": ["手机"],
    "휴대폰": ["手机"],
    "케이스": ["手机壳", "保护壳"],
    "방수": ["防水袋", "防水套"],
    "필름": ["手机膜", "钢化膜"],
    "거치대": ["支架", "车载支架", "桌面支架"],
    "가방": ["包", "背包", "收纳包"],
    "수납": ["收纳", "收纳盒", "收纳袋"],
    "주방": ["厨房用品", "厨具", "厨房收纳"],
    "반려동물": ["宠物用品", "猫狗用品"],
    "강아지": ["狗用品", "宠物用品"],
    "고양이": ["猫用品", "宠物用品"],
    "차량": ["汽车用品", "车载"],
    "캠핑": ["露营用品", "户外用品"],
    "등산": ["户外用品", "登山用品"],
    "운동": ["运动用品", "健身用品"],
    "사무": ["办公用品", "桌面用品"],
    "욕실": ["浴室用品", "卫生间用品"],
}


def _normalize(keyword: str) -> str:
    return " ".join(keyword.strip().split())


def _contains_chinese(value: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", value))


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def _agent_instruction(keyword: str, seed_terms: list[str]) -> str:
    seed_clause = f" Use these as optional seeds, not final answers: {', '.join(seed_terms)}." if seed_terms else ""
    return (
        f"Generate 5-8 practical Chinese 1688 sourcing search terms for the Korean keyword '{keyword}'."
        f"{seed_clause} Search the strongest broad term first, read visible related terms/product titles, "
        "then refine into narrower terms before recommending products. Do not search a Korean placeholder on 1688."
    )


def _workflow() -> list[str]:
    return [
        "Generate Chinese 1688 sourcing terms from the user's Korean intent.",
        "Search a broad Chinese term in the user's Chrome 1688 tab.",
        "Use visible related searches, product titles, seller categories, and network data to refine the next terms.",
        "Recommend products from live results, not from the seed list alone.",
    ]


def _search_urls(terms: list[str]) -> list[str]:
    return [f"https://s.1688.com/selloffer/offer_search.htm?keywords={encode_1688_search_keyword(term)}" for term in terms]


def _component_terms(normalized: str) -> list[str]:
    compact = normalized.replace(" ", "")
    terms: list[str] = []
    for korean_term, chinese_terms in COMPONENT_HINTS.items():
        if korean_term in normalized or korean_term.replace(" ", "") in compact:
            terms.extend(chinese_terms)
    return _dedupe(terms)


def expand_keywords(keyword: str) -> KeywordExpansion:
    normalized = _normalize(keyword)
    if not normalized:
        return KeywordExpansion(
            status="partial_data",
            original_keyword=keyword,
            keywords=[],
            needs_review=True,
            strategy="empty_keyword",
            note="Empty keyword. Ask for a product keyword first.",
            agent_instruction="Ask the user for the product or category they want to source.",
            search_workflow=[],
            warnings=["No keyword was provided."],
        )

    if _contains_chinese(normalized):
        return KeywordExpansion(
            status="ok",
            original_keyword=normalized,
            keywords=[normalized],
            source_language="zh",
            target_language="zh",
            strategy="chinese_passthrough",
            seed_terms=[normalized],
            note="Chinese keyword supplied by the user. Search it directly, then refine from visible 1688 results.",
            agent_instruction=_agent_instruction(normalized, [normalized]),
            search_workflow=_workflow(),
            search_urls=_search_urls([normalized]),
        )

    if normalized in CURATED_SEEDS:
        seeds = CURATED_SEEDS[normalized]
        return KeywordExpansion(
            status="ok",
            original_keyword=normalized,
            keywords=seeds,
            needs_review=True,
            strategy="curated_seed_terms",
            seed_terms=seeds,
            note="These are starter sourcing terms. Refine them from live 1688 search results before recommending products.",
            agent_instruction=_agent_instruction(normalized, seeds),
            search_workflow=_workflow(),
            search_urls=_search_urls(seeds),
        )

    seeds = _component_terms(normalized)
    if seeds:
        return KeywordExpansion(
            status="partial_data",
            original_keyword=normalized,
            keywords=seeds,
            needs_review=True,
            strategy="component_seed_terms",
            seed_terms=seeds,
            note="Only partial seed terms were inferred from Korean components. Generate better Chinese search terms and validate them on live 1688 results.",
            agent_instruction=_agent_instruction(normalized, seeds),
            search_workflow=_workflow(),
            search_urls=_search_urls(seeds),
            warnings=["No exact curated term exists; use these only as hints."],
        )

    return KeywordExpansion(
        status="partial_data",
        original_keyword=normalized,
        keywords=[],
        needs_review=True,
        strategy="agent_generate_terms",
        seed_terms=[],
        note="No built-in seed terms matched. The agent must generate Chinese sourcing terms from the user intent and refine them from live 1688 results.",
        agent_instruction=_agent_instruction(normalized, []),
        search_workflow=_workflow(),
        warnings=["Do not search the Korean keyword directly unless the user explicitly asks for that diagnostic."],
    )
