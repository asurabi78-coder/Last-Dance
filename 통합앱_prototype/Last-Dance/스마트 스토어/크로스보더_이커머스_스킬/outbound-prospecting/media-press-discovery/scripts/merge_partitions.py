#!/usr/bin/env python3
"""Merge multiple machines' pitch_db.csv outputs into a single deduped CSV.

Dedup key: (outlet, journalist) lowercase
On dup, keep the row with higher relevance_score; merge email_1..3 if differ.

Usage:
  python3 merge_partitions.py partition_*.csv --out pitch_db_master.csv
"""

import argparse
import csv
from pathlib import Path


def key(row):
    return (row["outlet"].lower().strip(),
            row["journalist"].lower().strip())


def merge_emails(a, b):
    """Combine 3+3 candidate emails, dedup, keep first 3."""
    pool = []
    seen = set()
    for r in (a, b):
        for k in ("email_1", "email_2", "email_3"):
            v = (r.get(k) or "").strip().lower()
            if v and v not in seen:
                seen.add(v)
                pool.append(v)
    while len(pool) < 3:
        pool.append("")
    return pool[:3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=Path("pitch_db_master.csv"))
    args = ap.parse_args()

    merged = {}
    for path in args.inputs:
        with path.open() as f:
            for r in csv.DictReader(f):
                k = key(r)
                if k not in merged:
                    merged[k] = r
                else:
                    cur = merged[k]
                    if int(r.get("relevance_score", 0) or 0) > int(cur.get("relevance_score", 0) or 0):
                        cur = {**cur, **r}
                    e1, e2, e3 = merge_emails(cur, r)
                    cur["email_1"], cur["email_2"], cur["email_3"] = e1, e2, e3
                    merged[k] = cur

    rows = sorted(merged.values(), key=lambda r: -int(r.get("relevance_score", 0) or 0))
    if not rows:
        print("No rows merged.")
        return
    cols = list(rows[0].keys())
    with args.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"Merged {sum(1 for _ in args.inputs)} files → {len(rows)} unique journalists at {args.out}")


if __name__ == "__main__":
    main()
