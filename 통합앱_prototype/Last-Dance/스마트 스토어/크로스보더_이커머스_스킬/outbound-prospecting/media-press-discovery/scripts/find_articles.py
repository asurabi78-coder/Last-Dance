#!/usr/bin/env python3
"""For each journalist in journalists.jsonl, fetch their Muckrack /articles page
and extract recent articles. Filter by topic keywords.

Input:  journalists.jsonl from discover_journalists.py
        keywords.txt       one keyword/phrase per line
Output: articles.jsonl     one JSON per journalist with their in-topic articles

Each output row:
  {"muckrack_slug": "sara-delgado",
   "topic_articles": [
     {"title": "...", "url": "...", "date": "2025-03-15"},
     ...
   ],
   "all_articles_count": 42,
   "topic_match_count": 3,
   "most_recent_topic_date": "2025-03-15"}
"""

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from _fetcher import fetch, cleanup


DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def gaussian_sleep(mean=2.5, sd=0.7, lo=1.0):
    time.sleep(max(lo, random.gauss(mean, sd)))


def fetch_journalist_articles(muckrack_url, via, **fetch_kwargs):
    """Fetch journalist's /articles page and return parsed article list."""
    url = muckrack_url.rstrip("/") + "/articles"
    html = fetch(url, via=via, **fetch_kwargs)
    if not html:
        return None, []
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    # Muckrack lists articles as <a> with title + datetime-like sibling
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if not href.startswith("http") or "muckrack.com" in href:
            continue
        title = a.get_text(strip=True)
        if not title or len(title) < 12 or len(title) > 250:
            continue
        # Try to find a sibling date
        date_str = ""
        parent = a.find_parent()
        if parent:
            text = parent.get_text(" ", strip=True)
            m = DATE_RE.search(text)
            if m:
                date_str = m.group(0)
        articles.append({"title": title, "url": href, "date": date_str})
    return html, articles


def topic_match(title, keywords):
    title_lower = title.lower()
    return [k for k in keywords if k.lower() in title_lower]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journalists_file", type=Path)
    ap.add_argument("--keywords", type=Path, required=True,
                    help="One keyword/phrase per line")
    ap.add_argument("--out", type=Path, default=Path("articles.jsonl"))
    ap.add_argument("--via", default="remote-chrome",
                    choices=["requests", "remote-chrome", "apify", "html-dir", "auto"])
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--html-dir", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    keywords = [k.strip() for k in args.keywords.read_text().splitlines()
                if k.strip() and not k.startswith("#")]
    journos = [json.loads(line) for line in args.journalists_file.read_text().splitlines() if line.strip()]
    if args.limit:
        journos = journos[:args.limit]

    fetch_kwargs = {}
    if args.via == "remote-chrome":
        fetch_kwargs["port"] = args.port
    elif args.via == "html-dir":
        if not args.html_dir:
            sys.exit("--via=html-dir requires --html-dir <path>")
        fetch_kwargs["html_dir"] = args.html_dir

    try:
        with args.out.open("w") as f:
            for i, j in enumerate(journos, 1):
                print(f"[{i}/{len(journos)}] {j['journalist']}", file=sys.stderr)
                _, articles = fetch_journalist_articles(j["muckrack_url"], args.via, **fetch_kwargs)
                topic_articles = []
                for a in articles:
                    matched = topic_match(a["title"], keywords)
                    if matched:
                        topic_articles.append({**a, "matched_keywords": matched})
                most_recent = ""
                if topic_articles:
                    dates = [a["date"] for a in topic_articles if a["date"]]
                    if dates:
                        most_recent = max(dates)
                f.write(json.dumps({
                    "muckrack_slug": j.get("muckrack_slug", ""),
                    "journalist": j["journalist"],
                    "outlet": j.get("outlet", ""),
                    "outlet_domain": j.get("outlet_domain", ""),
                    "all_articles_count": len(articles),
                    "topic_match_count": len(topic_articles),
                    "topic_articles": topic_articles[:10],
                    "most_recent_topic_date": most_recent,
                }, ensure_ascii=False) + "\n")
                if i < len(journos) and args.via != "html-dir":
                    gaussian_sleep()
    finally:
        cleanup()


if __name__ == "__main__":
    main()
