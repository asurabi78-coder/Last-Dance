"""Shared HTTP fetcher with 4 backends for Cloudflare-protected pages.

Why 4 backends: Muckrack (and many target outlets) is Cloudflare-protected.
Plain requests/curl_cffi gets 403. Headless Selenium + undetected-chromedriver
get blocked by current Cloudflare WAF (as of 2026-05). The reliable free path
is connecting Selenium to a user-launched real Chrome instance via
--remote-debugging-port. Paid path is Apify.

Use like:
    from _fetcher import fetch
    html = fetch(url, via="remote-chrome", port=9222)
"""

import os
import time
import sys

DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


# --- Backend 1: plain requests (fast, often 403 on Cloudflare) ---

def _fetch_requests(url, timeout=20):
    import requests
    try:
        r = requests.get(url, timeout=timeout,
                         headers={"User-Agent": DESKTOP_UA, "Accept-Language": "en-US,en;q=0.9"})
        if r.status_code == 200 and len(r.text) > 5000:
            return r.text
        if "Just a moment" in r.text or "请稍候" in r.text:
            return None  # Cloudflare challenge — fall back
        return None
    except requests.RequestException:
        return None


# --- Backend 2: remote Chrome via debug port (free + reliable) ---

_REMOTE_DRIVER = None

def _get_remote_driver(port):
    """Connect to user-launched Chrome at 127.0.0.1:{port}. Lazy-init singleton."""
    global _REMOTE_DRIVER
    if _REMOTE_DRIVER is not None:
        return _REMOTE_DRIVER
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    _REMOTE_DRIVER = webdriver.Chrome(options=opts)
    return _REMOTE_DRIVER


def _fetch_remote_chrome(url, port=9222, max_wait=20):
    """Drive user's running Chrome to load URL. Cloudflare passes because real browser.

    Prereq: user has launched Chrome with `--remote-debugging-port={port}`.
    On macOS:
        /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
            --remote-debugging-port=9222 --user-data-dir=/tmp/cf_profile
    """
    driver = _get_remote_driver(port)
    driver.get(url)
    # Wait for Cloudflare to clear
    for i in range(max_wait):
        time.sleep(1)
        title = driver.title or ""
        if title and "请稍候" not in title and "Just a moment" not in title:
            break
    time.sleep(1.5)  # let JS hydrate
    return driver.page_source


# --- Backend 3: Apify (paid, $$ per 1k requests) ---

def _fetch_apify(url, timeout=60):
    """Use Apify's Web Scraper actor. Requires APIFY_TOKEN env var.

    See: https://apify.com/apify/web-scraper
    """
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise RuntimeError("APIFY_TOKEN env var not set")
    try:
        import requests
    except ImportError:
        raise RuntimeError("install: pip install requests")
    api_url = f"https://api.apify.com/v2/acts/apify~web-scraper/run-sync-get-dataset-items?token={token}"
    payload = {
        "startUrls": [{"url": url}],
        "pageFunction": "async function pageFunction(context) { return { html: document.documentElement.outerHTML }; }",
        "proxyConfiguration": {"useApifyProxy": True},
    }
    r = requests.post(api_url, json=payload, timeout=timeout)
    if r.status_code == 200:
        items = r.json()
        if items and isinstance(items, list):
            return items[0].get("html", "")
    return None


# --- Backend 4: read pre-saved HTML from directory ---

def _fetch_html_dir(url, html_dir):
    """Read a previously saved HTML file. Filename = URL with safe-chars.

    User saves Muckrack page in their browser as:
        <html_dir>/<urlencoded-or-slug>.html

    Example slug for https://muckrack.com/media-outlet/teenvogue:
        muckrack.com_media-outlet_teenvogue.html
    """
    from pathlib import Path
    from urllib.parse import urlparse
    p = urlparse(url)
    slug = (p.netloc + p.path).strip("/").replace("/", "_") + ".html"
    f = Path(html_dir) / slug
    if f.exists():
        return f.read_text(encoding="utf-8")
    print(f"  [html-dir] file not found: {f}", file=sys.stderr)
    return None


# --- Unified entry point ---

def fetch(url, via="requests", **kwargs):
    """Fetch URL and return HTML (or None on failure).

    via:
        "requests"      — fast, may 403 on Cloudflare
        "remote-chrome" — connect to running Chrome at port (default 9222)
        "apify"         — paid, requires APIFY_TOKEN env var
        "html-dir"      — read pre-saved HTML from kwargs["html_dir"]
        "auto"          — try requests first, fall back to remote-chrome
    """
    if via == "requests":
        return _fetch_requests(url)
    if via == "remote-chrome":
        return _fetch_remote_chrome(url, port=kwargs.get("port", 9222))
    if via == "apify":
        return _fetch_apify(url)
    if via == "html-dir":
        return _fetch_html_dir(url, kwargs["html_dir"])
    if via == "auto":
        html = _fetch_requests(url)
        if html:
            return html
        print(f"  [auto] requests failed for {url}, trying remote-chrome", file=sys.stderr)
        return _fetch_remote_chrome(url, port=kwargs.get("port", 9222))
    raise ValueError(f"unknown via: {via}")


def cleanup():
    global _REMOTE_DRIVER
    if _REMOTE_DRIVER is not None:
        try:
            _REMOTE_DRIVER.quit()
        except Exception:
            pass
        _REMOTE_DRIVER = None
