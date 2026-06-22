from __future__ import annotations

from typing import Any


def shortlist_to_markdown(project: str, items: list[dict[str, Any]]) -> str:
    lines = [f"# 1688 Sourcing Shortlist: {project}", ""]
    if not items:
        lines.append("No shortlisted offers yet.")
        return "\n".join(lines)
    for item in items:
        score = item.get("score") or {}
        lines.extend(
            [
                f"## {item.get('offer_id')}",
                f"- URL: {item.get('url') or ''}",
                f"- Image: {item.get('image_url') or ''}",
                f"- Title: {item.get('title_zh') or ''}",
                f"- Price: {item.get('price_min') or ''} - {item.get('price_max') or ''} {item.get('currency') or 'CNY'}",
                f"- MOQ: {item.get('moq') or ''}",
                f"- Month sold: {item.get('month_sold') or ''}",
                f"- Repurchase rate: {item.get('repurchase_rate') or ''}",
                f"- Seller score: {item.get('seller_score') or ''}",
                f"- Sourcing score: {score.get('score') or ''}",
                f"- Why good: {'; '.join(score.get('why_good') or [])}",
                f"- Risks: {'; '.join(score.get('risks') or [])}",
                f"- Notes: {item.get('notes') or ''}",
                "",
            ]
        )
    return "\n".join(lines)
