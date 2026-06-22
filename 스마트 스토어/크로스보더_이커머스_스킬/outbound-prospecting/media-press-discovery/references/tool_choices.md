# Tool Choices — Why This Pipeline Looks Like It Does

A record of approaches we evaluated and why we landed on the current design. Read this before adding new fetcher backends or "improving" the pipeline.

## Step 1: Outlet roster discovery

| Approach | Outcome | Verdict |
|---|---|---|
| **Muckrack public outlet page** (`muckrack.com/media-outlet/{slug}`) | When fetched (see Cloudflare section below), returns 15 journalists per outlet with profile URLs. Verified across refinery29 / teenvogue / byrdie 2026-05-06. | **Chosen as anchor** |
| Outlet-side `/search?q=` | Refinery29 served via WebFetch. TeenVogue WebFetch blocked. Byrdie hit Cloudflare. | Fallback only |
| WebSearch with `site:domain` | Inconsistent — TeenVogue/Byrdie returned 0 results despite known content. | Unreliable |
| Outlet's `/about/team/` masthead | Hand-curate; very slow. | Last resort |

## Cloudflare Reality (the elephant in the room)

Muckrack uses Cloudflare. Standard programmatic approaches fail:

| Approach (实测 2026-05-06) | Result |
|---|---|
| `requests` with full headers + desktop UA | 403, "Just a moment..." JS challenge page |
| `curl_cffi` with `impersonate="chrome131"` | 403 — TLS fingerprint OK but JS challenge fails |
| Selenium headless Chrome | Blocked: `navigator.webdriver` true |
| `undetected-chromedriver` (uc) | Apple Silicon binary issue + uc 3.5.5 vs current Cloudflare WAF |
| Selenium-launched normal Chrome with empty profile | Blocked — no `cf_clearance` cookie, fails challenge |
| Selenium-launched normal Chrome + 25s wait | Title remained "请稍候…" indefinitely |

**What works**:
- **Real browser session with prior cf_clearance**: Connect Selenium to user's normal Chrome via `--remote-debugging-port=9222`. The user's Chrome already has the cookie from any prior visit.
- **Apify Web Scraper actor**: Apify's infrastructure handles Cloudflare with rotating residential proxies + headful Chrome.
- **Manual save**: User opens page in browser, "Save Page As" HTML, parser reads from disk.

The pipeline supports all three via `--via {remote-chrome,apify,html-dir}`.

## Step 2: Journalist's bylined articles

Same Cloudflare situation as Step 1. Same `--via` backends apply. `find_articles.py` uses the same `_fetcher.py` module.

| Alternative considered | Verdict |
|---|---|
| Outlet-side `/author/{name}` page | Often works but URL pattern varies per outlet. Heuristic mapping is ~70% accurate. Useful as Muckrack supplement, not replacement. |
| Twitter/X API for byline announcements | API access locked down 2024+. Skip. |
| Google News attribution | Inconsistent journalist→article binding. Skip. |

## Step 3: Cross-link signal

| Approach | Verdict |
|---|---|
| **`extract_kol.py` output (Semrush refdomains)** | Already produced as part of `tools/backlink-kol-extractor`. Reuse. | **Chosen** |
| Ahrefs URL→site lookup | Expensive subscription. Skip. |
| Common Crawl | Stale, noisy. Skip. |

## Step 4: Email finding

| Approach | Cost | Accuracy (推算) | Verdict |
|---|---|---|---|
| **Outlet-pattern guessing + optional SMTP probe** | $0 | ~60-75% land rate | **Chosen** as default |
| Hunter.io API | $49+/mo | ~95% | **Chosen** as `--verify` upgrade |
| RocketReach / Apollo / Lusha | $50-200/mo | ~85-90% | Skip — built for sales not journalism |
| Muckrack contacts (paid tier) | $5,000+/yr | ~99% | Best for enterprise |
| LinkedIn manual lookup | $0, manual | ~90% (senior editors) | Spot-check tool |

**Key finding** (from PR industry research, BuzzStream's 2024 testing): "Email finder tools are built for scaled sales outreach, not PR — accuracy is substantially lower for journalist contacts." This is why our pipeline:
1. Anchors on outlet-pattern guessing (deterministic per publishing group).
2. Treats Hunter.io as *optional* verification.
3. Surfaces multiple guesses (top 3) so user can spot-check during outreach.

## Step 5: Pitch personalization

Out of scope for this skill. The bottleneck for press response is **craft**, not list size.
- Generic LLM-spray pitches: 1-3% response rate (industry baseline)
- Hand-crafted, reading-2-3-of-their-articles personalization: 15-25%
- Warm intro: 30-50%

This skill produces the structured starting point. The pitch-craft step is documented in the project's local PR playbook (see `PR_建联方法论_*.md` if your project has one).

## Tools we deliberately avoided

- **LLM-based byline extraction**: Title regex + Muckrack page structure is sufficient. LLMs add cost and non-determinism without lifting recall meaningfully.
- **DOM-CSS selector targeting on Muckrack class names**: Class names are hashed and unstable. We anchor on `<a href="/journalist-slug">` link patterns instead.
- **Headless Selenium as primary fetcher**: Doesn't pass Cloudflare. Documented above.
- **FlareSolverr Docker**: Was a candidate; works but adds Docker dependency. Listed as future enhancement.

## Future enhancements

- **Browser extension** (cleanest scale path): like the user's `noique/semrush-exporter`, write a Chrome extension that scrapes Muckrack while user browses normally. Cloudflare doesn't gate content from real browsing; an extension is "scripted browsing" with full browser context. Eliminates the manual save step entirely.
- **Apify actor as default**: when Apify becomes affordable for the user's scale, switch default `--via` to `apify`.
- **Semantic relevance scoring**: replace title-keyword match with embedding similarity (RKB integration?) for better discrimination.
- **LinkedIn handle extraction**: from Muckrack profile body, pull LinkedIn URLs for non-email outreach.

## Versioning note

All Cloudflare findings are dated 2026-05. Cloudflare's WAF evolves continuously; if this doc is read months later, retest the failing approaches. They may have changed in either direction.
