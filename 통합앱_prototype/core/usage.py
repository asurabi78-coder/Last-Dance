# -*- coding: utf-8 -*-
"""API 사용량/추정 비용 추적 — 호출마다 토큰/이미지를 JSONL에 영구 기록, 일/주/월 집계.
주의: 비용은 요금표 기반 '추정'이며 계정 잔액과 무관. 요금은 바뀔 수 있어 PRICES에서 조정."""
import os
import json
import time
import threading
from datetime import datetime

LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "usage_log.jsonl"))
_LOCK = threading.Lock()

# 1M 토큰당 USD (대략치 — 필요시 수정)
PRICES = {
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "gpt-4o": {"in": 2.50, "out": 10.0},
    "claude-sonnet-4-6": {"in": 3.0, "out": 15.0},
    "gemini-2.5-flash": {"in": 0.10, "out": 0.40},
}
DEFAULT_TEXT = {"in": 1.0, "out": 3.0}

# 이미지 1장당 USD (대략치)
IMAGE_PRICES = {
    "gpt-image-1": 0.04,
    "gemini-2.5-flash-image": 0.04,
    "_default": 0.04,
}


def text_cost(model, in_tokens, out_tokens):
    p = PRICES.get(model, DEFAULT_TEXT)
    return round((int(in_tokens or 0) / 1_000_000.0) * p["in"]
                 + (int(out_tokens or 0) / 1_000_000.0) * p["out"], 6)


def image_cost(model, n):
    return round(IMAGE_PRICES.get(model, IMAGE_PRICES["_default"]) * int(n or 0), 6)


def _append(rec):
    try:
        with _LOCK:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 기록 실패가 본 기능을 막지 않게


def record_text(provider, model, in_tokens, out_tokens, when=None):
    ts = when if when else time.time()
    dt = datetime.fromtimestamp(ts)
    rec = {"ts": ts, "date": dt.strftime("%Y-%m-%d"), "provider": provider, "model": model,
           "kind": "text", "in_tokens": int(in_tokens or 0), "out_tokens": int(out_tokens or 0),
           "images": 0, "cost": text_cost(model, in_tokens, out_tokens)}
    _append(rec)
    return rec


def record_image(provider, model, n=1, when=None):
    ts = when if when else time.time()
    dt = datetime.fromtimestamp(ts)
    rec = {"ts": ts, "date": dt.strftime("%Y-%m-%d"), "provider": provider, "model": model,
           "kind": "image", "in_tokens": 0, "out_tokens": 0, "images": int(n or 0),
           "cost": image_cost(model, n)}
    _append(rec)
    return rec


def load_records(path=None):
    p = path or LOG_PATH
    out = []
    if not os.path.isfile(p):
        return out
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        pass
    return out


def _week_key(date_str):
    iso = datetime.strptime(date_str, "%Y-%m-%d").isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def aggregate(period="day", records=None):
    """period: day|week|month. 반환: [{'period','cost','tokens','images'}] 시간순."""
    recs = records if records is not None else load_records()
    buckets = {}
    for r in recs:
        ds = r.get("date") or ""
        if not ds:
            continue
        if period == "week":
            key = _week_key(ds)
        elif period == "month":
            key = ds[:7]
        else:
            key = ds
        b = buckets.setdefault(key, {"period": key, "cost": 0.0, "tokens": 0, "images": 0})
        b["cost"] += float(r.get("cost") or 0)
        b["tokens"] += int(r.get("in_tokens") or 0) + int(r.get("out_tokens") or 0)
        b["images"] += int(r.get("images") or 0)
    out = sorted(buckets.values(), key=lambda x: x["period"])
    for b in out:
        b["cost"] = round(b["cost"], 4)
    return out


def totals(records=None):
    recs = records if records is not None else load_records()
    by_provider = {}
    tot = {"cost": 0.0, "tokens": 0, "images": 0, "calls": len(recs)}
    for r in recs:
        pv = r.get("provider") or "?"
        bp = by_provider.setdefault(pv, {"cost": 0.0, "tokens": 0, "images": 0})
        c = float(r.get("cost") or 0)
        tk = int(r.get("in_tokens") or 0) + int(r.get("out_tokens") or 0)
        im = int(r.get("images") or 0)
        bp["cost"] += c
        bp["tokens"] += tk
        bp["images"] += im
        tot["cost"] += c
        tot["tokens"] += tk
        tot["images"] += im
    tot["cost"] = round(tot["cost"], 4)
    for pv in by_provider:
        by_provider[pv]["cost"] = round(by_provider[pv]["cost"], 4)
    return {"total": tot, "by_provider": by_provider}


def reset():
    try:
        with _LOCK:
            if os.path.isfile(LOG_PATH):
                os.remove(LOG_PATH)
        return True
    except Exception:
        return False
