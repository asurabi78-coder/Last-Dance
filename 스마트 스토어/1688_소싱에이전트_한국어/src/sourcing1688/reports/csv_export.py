from __future__ import annotations

import csv
import io
from typing import Any


def shortlist_to_csv(items: list[dict[str, Any]]) -> str:
    output = io.StringIO()
    fieldnames = [
        "project",
        "offer_id",
        "url",
        "image_url",
        "title_zh",
        "price_min",
        "price_max",
        "currency",
        "moq",
        "month_sold",
        "trade_volume",
        "repurchase_rate",
        "seller_score",
        "source_keyword",
        "provider",
        "live_verified",
        "notes",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for item in items:
        writer.writerow(item)
    return output.getvalue()
