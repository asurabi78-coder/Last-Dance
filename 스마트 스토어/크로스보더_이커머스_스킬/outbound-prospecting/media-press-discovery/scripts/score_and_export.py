#!/usr/bin/env python3
"""Consolidate journalists + articles + email guesses into a final pitch_db.csv.

Inputs : journalists.jsonl, articles.jsonl, emails.csv
Output : pitch_db.csv (final outreach DB)

Score formula:
  base               = 30  if topic_match_count > 0 else 0
  recency_bonus      = +25 if last article in last 6 mo
                        +15 if last in last 12 mo
                        +5  if last in last 24 mo
  topic_count_bonus  = min(topic_match_count, 5) * 5
  cross_link_bonus   = +20 if journalist's article URL appears in
                            kol_prospects backlink data (optional input)
  email_bonus        = +5 if smtp_ok or hunter_valid

Usage:
  python3 score_and_export.py journalists.jsonl articles.jsonl emails.csv \
      --out pitch_db.csv [--backlinks kol_prospects.csv]
"""

import argparse
import csv
import datetime
import json
from pathlib import Path


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


def recency_bonus(last_date_str, today=None):
    today = today or datetime.date.today()
    d = parse_date(last_date_str)
    if not d:
        return 0
    months_ago = (today - d).days / 30.44
    if months_ago <= 6:  return 25
    if months_ago <= 12: return 15
    if months_ago <= 24: return 5
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journalists_file", type=Path)
    ap.add_argument("articles_file", type=Path)
    ap.add_argument("emails_file", type=Path)
    ap.add_argument("--backlinks", type=Path, default=None,
                    help="Optional kol_prospects.csv from backlink-kol-extractor for cross-link bonus")
    ap.add_argument("--out", type=Path, default=Path("pitch_db.csv"))
    args = ap.parse_args()

    # Load journalists
    journos = {}
    for line in args.journalists_file.read_text().splitlines():
        if not line.strip(): continue
        j = json.loads(line)
        slug = j.get("muckrack_slug", "")
        journos[slug] = j

    # Load articles enrichment
    articles_by_slug = {}
    for line in args.articles_file.read_text().splitlines():
        if not line.strip(): continue
        a = json.loads(line)
        articles_by_slug[a["muckrack_slug"]] = a

    # Load email guesses
    emails_by_slug = {}
    with args.emails_file.open() as f:
        for r in csv.DictReader(f):
            emails_by_slug[r["muckrack_slug"]] = r

    # Optional: load backlink domains for cross-link signal
    linked_domains = set()
    if args.backlinks and args.backlinks.exists():
        with args.backlinks.open() as f:
            for r in csv.DictReader(f):
                if int(r.get("source_count", 0) or 0) >= 2:
                    linked_domains.add(r["domain"])

    # Output
    rows = []
    for slug, j in journos.items():
        a = articles_by_slug.get(slug, {})
        e = emails_by_slug.get(slug, {})
        topic_count = a.get("topic_match_count", 0)
        last_topic_date = a.get("most_recent_topic_date", "")
        topic_articles = a.get("topic_articles", [])
        last_url = topic_articles[0]["url"] if topic_articles else ""

        score = 0
        if topic_count > 0:
            score += 30
        score += recency_bonus(last_topic_date)
        score += min(topic_count, 5) * 5
        # Cross-link bonus: any topic article from outlet domain in linked set
        if linked_domains and j.get("outlet_domain") in linked_domains:
            score += 20
        if e.get("verified") in ("smtp_ok", "hunter_valid", "hunter_accept_all"):
            score += 5

        rows.append({
            "outlet": j.get("outlet", ""),
            "outlet_domain": j.get("outlet_domain", ""),
            "journalist": j.get("journalist", ""),
            "muckrack_url": j.get("muckrack_url", ""),
            "topic_match_count": topic_count,
            "last_topic_article_url": last_url,
            "last_topic_article_date": last_topic_date,
            "relevance_score": score,
            "email_1": e.get("email_1", ""),
            "email_2": e.get("email_2", ""),
            "email_3": e.get("email_3", ""),
            "email_verified": e.get("verified", "unverified"),
        })

    rows.sort(key=lambda r: -r["relevance_score"])
    cols = ["outlet","outlet_domain","journalist","muckrack_url","topic_match_count",
            "last_topic_article_url","last_topic_article_date","relevance_score",
            "email_1","email_2","email_3","email_verified"]
    with args.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    in_topic = sum(1 for r in rows if r["topic_match_count"] > 0)
    print(f"Wrote {len(rows)} rows ({in_topic} in-topic) to {args.out}")


if __name__ == "__main__":
    main()
