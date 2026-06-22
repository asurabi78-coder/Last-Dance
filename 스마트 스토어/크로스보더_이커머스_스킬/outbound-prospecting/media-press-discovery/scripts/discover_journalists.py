#!/usr/bin/env python3
"""Discover journalists at media outlets via Muckrack public outlet pages.

Input:  outlets.txt — one line per outlet, format: muckrack_slug,outlet_domain
Output: journalists.jsonl — one JSON object per journalist

Each line is:
  {"outlet": "teenvogue", "outlet_domain": "teenvogue.com",
   "journalist": "Sara Delgado", "muckrack_url": "https://muckrack.com/sara-delgado"}

Usage:
  python3 discover_journalists.py outlets.txt --out journalists.jsonl
  python3 discover_journalists.py outlets.txt --out journalists.jsonl --selenium-fallback
"""

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("install: pip install beautifulsoup4")

# Add scripts/ to path for shared fetcher
sys.path.insert(0, str(Path(__file__).parent))
from _fetcher import fetch, cleanup


MUCKRACK_BASE = "https://muckrack.com"


def gaussian_sleep(mean=2.5, sd=0.7, lo=1.0):
    """Pace requests so we don't get rate-limited."""
    time.sleep(max(lo, random.gauss(mean, sd)))


def fetch_outlet(slug, via, **fetch_kwargs):
    """Return raw HTML for muckrack.com/media-outlet/{slug}, or None on hard fail."""
    url = f"{MUCKRACK_BASE}/media-outlet/{slug}"
    return fetch(url, via=via, **fetch_kwargs)


def parse_journalists(html, outlet_slug):
    """Extract journalist roster from a Muckrack outlet page.

    Muckrack lists journalists in card form linking to /<journalist-slug>.
    The selector is fragile (hashed class names); we anchor on link patterns.
    """
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    out = []

    # Muckrack journalist profile URLs are /<slug> where slug isn't a known
    # reserved path. Filter out reserved prefixes.
    RESERVED = {
        "media-outlet", "search", "trends", "blog", "about", "pricing",
        "login", "logout", "signup", "settings", "messages", "saved",
        "topics", "campaigns", "lists", "dashboard", "account",
    }
    LINK_RE = re.compile(r"^/([A-Za-z0-9_\-]+)/?$")

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        m = LINK_RE.match(href)
        if not m:
            continue
        slug = m.group(1)
        if slug in RESERVED or slug.lower() == outlet_slug.lower():
            continue
        # Heuristic: a journalist link is wrapped in or near a card with a name
        text = (a.get_text(strip=True) or "").strip()
        if not text or len(text) < 3 or len(text) > 60:
            continue
        # Looks like a name (has a comma "Last, First" or "First Last")
        if "," not in text and " " not in text:
            continue
        if slug in seen:
            continue
        seen.add(slug)

        # Normalize "Last, First" → "First Last" (Muckrack default)
        if "," in text:
            parts = [p.strip() for p in text.split(",", 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                text = f"{parts[1]} {parts[0]}"

        out.append({
            "journalist": text,
            "muckrack_url": urljoin(MUCKRACK_BASE, "/" + slug),
            "muckrack_slug": slug,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outlets_file", type=Path,
                    help="One outlet per line: muckrack_slug,outlet_domain")
    ap.add_argument("--out", type=Path, default=Path("journalists.jsonl"))
    ap.add_argument("--via", default="remote-chrome",
                    choices=["requests", "remote-chrome", "apify", "html-dir", "auto"],
                    help="Fetcher backend. Muckrack is Cloudflare-protected: 'requests' "
                         "usually 403s; 'remote-chrome' connects to your locally-running Chrome "
                         "(start with --remote-debugging-port=9222); 'apify' uses paid Apify "
                         "Web Scraper actor; 'html-dir' reads pre-saved HTML files.")
    ap.add_argument("--port", type=int, default=9222,
                    help="Port for --via=remote-chrome (default 9222)")
    ap.add_argument("--html-dir", type=Path, default=None,
                    help="For --via=html-dir: directory of pre-saved HTML files")
    ap.add_argument("--limit", type=int, default=None,
                    help="Stop after N outlets (testing)")
    args = ap.parse_args()

    outlets = []
    for line in args.outlets_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "," in line:
            slug, domain = (x.strip() for x in line.split(",", 1))
        else:
            slug, domain = line, line + ".com"
        outlets.append((slug, domain))

    if args.limit:
        outlets = outlets[:args.limit]

    fetch_kwargs = {}
    if args.via == "remote-chrome":
        fetch_kwargs["port"] = args.port
    elif args.via == "html-dir":
        if not args.html_dir:
            sys.exit("--via=html-dir requires --html-dir <path>")
        fetch_kwargs["html_dir"] = args.html_dir

    total = 0
    try:
        with args.out.open("w") as f:
            for i, (slug, domain) in enumerate(outlets, 1):
                print(f"[{i}/{len(outlets)}] {slug}  →  {domain}", file=sys.stderr)
                html = fetch_outlet(slug, args.via, **fetch_kwargs)
                if not html:
                    print(f"  no HTML, skipping", file=sys.stderr)
                    continue
                journos = parse_journalists(html, slug)
                print(f"  found {len(journos)} journalists", file=sys.stderr)
                for j in journos:
                    j["outlet"] = slug
                    j["outlet_domain"] = domain
                    f.write(json.dumps(j, ensure_ascii=False) + "\n")
                    total += 1
                if i < len(outlets) and args.via != "html-dir":
                    gaussian_sleep()
    finally:
        cleanup()

    print(f"\nWrote {total} journalist rows to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
