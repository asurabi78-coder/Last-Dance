---
name: sourcing-agent-1688
description: Use this skill when the user asks Codex Desktop to inspect, analyze, compare, or save data from 1688 product pages.
---

# 1688 Sourcing Agent

Use this plugin as a Chrome DevTools-first 1688 sourcing agent.

Primary path:

1. Use `chrome-devtools` to inspect the user's Chrome tab.
2. Read visible page state, DOM, screenshots, and network responses.
3. Use `sourcing1688` tools to normalize 1688 HTML and network JSON into seller-facing product data.

Use Chrome DevTools first. Do not open a separate window unless the user explicitly asks or the plugin reports that it is using the Windows port-mode Chrome profile.
Do not run synthetic fixture, demo, or parser self-tests during a user sourcing task.

## First-Run Chrome Setup

Before calling `open_chrome_devtools_setup`, retry `chrome-devtools/list_pages` once. Call setup only when Chrome DevTools still cannot connect, has no pages, or reports `DevToolsActivePort`.

If setup is needed:

1. Call `open_chrome_devtools_setup`.
2. If the tool returns `endpoint_verified: true`, continue with the Chrome tabs exposed by that endpoint.
3. If the tool still reports `DevToolsActivePort`, or no endpoint is verified on Windows, call `start_chrome_devtools` and use the dedicated Chrome window it opens.
4. If the setup tool returns `skipped: true` without `endpoint_verified: true`, check the endpoint with `check_chrome_devtools` before continuing.
5. Tell the user that the Chrome setup tab was opened only when `opened` is non-empty.
6. Ask the user to allow the Chrome DevTools connection in the opened Chrome settings page.
7. Ask the user to open the target 1688 page in the verified Chrome profile.
8. Stop there until the user confirms setup is done or provides the target page.

Do not treat a setup marker as proof of connectivity unless it says `status: verified` or the endpoint check passes.
Do not resize, reposition, minimize, or maximize the user's Chrome windows.

If a Chrome DevTools tool call times out during first connection, do not call it a parser bug or a 1688 failure. Treat it as a pending Chrome permission dialog, tell the user to click Allow if the dialog is visible, then retry the same Chrome DevTools call after the user confirms. The bundled MCP config gives Chrome DevTools a long tool timeout so the user has time to notice and approve the prompt.

## Product Page

When the user gives a 1688 product URL or asks about the current Chrome page:

1. Use `list_pages` and select the 1688 page.
2. If needed, navigate Chrome to the provided URL.
3. Use `take_snapshot`, `take_screenshot`, and `evaluate_script` to inspect the visible page.
4. Capture a compact visible snapshot with `evaluate_script`: page URL, document title, body innerText, and visible image/video/source URLs. Call `parse_1688_visible_page_snapshot` first so visible price, MOQ, seller, sold count, and media are not lost.
5. If more data is needed, capture rendered HTML and call `parse_1688_rendered_html_content`.
6. Use `list_network_requests` and `get_network_request` for relevant 1688 responses.
7. Pass useful JSON bodies to `parse_1688_network_payload_content`.
8. For reviews, click/open the buyer review area (`买家评价`) when visible, capture body text plus review-related network responses, then call `parse_1688_review_snapshot`.
9. Summarize product fit for a Korean seller: product type, price in CNY and estimated KRW when a rate is available, options, seller signals, visible demand signals, review tags, image/video assets, risks, and next buying checks.

## Search

When the user asks for sourcing candidates:

1. Call `expand_sourcing_keywords`.
2. Treat returned keywords as seed terms only. They are not a closed dictionary.
3. If the tool returns `strategy: agent_generate_terms`, or the seed terms look too broad, generate 5-8 practical Chinese 1688 search terms yourself from the user's Korean intent. Do not search a Korean placeholder on 1688.
4. If no 1688 tab is open, open a new tab in the verified Chrome session to the 1688 search URL for the best Chinese keyword. Do not wait for the user to open 1688 manually when the task is a keyword search.
5. Use Chrome DevTools to search 1688 with the best Chinese keyword first. For `s.1688.com` search URLs, GBK-percent-encode Chinese keywords; UTF-8 encoded Chinese keywords can render as broken text and return unrelated results.
6. Inspect visible related searches, product titles, seller category words, and network responses. Use those live signals to refine the next query instead of relying only on the seed list.
7. Capture at least 10 visible candidate cards unless the user asks for fewer or the page has fewer visible results. Scroll/load more before giving up at 3-5 items.
8. Capture product card fields with `evaluate_script`: title, URL, price text, sold text, seller/shop name, image URL, and visible badges. If a card URL is a `dj.1688.com` ad redirect, also look for a nearby `detail.1688.com`, `detail.m.1688.com`, or `offerId=` URL in the same card before passing it to the parser.
9. Call `parse_1688_search_results_snapshot` with the captured items. Pass a current or user-provided CNY/KRW rate when available.
10. Present the result in Korean with a real product explanation, CNY price, estimated KRW price, sold count, seller/shop, why it may be a candidate, and what to check next. Translate/summarize Chinese titles yourself; parser category hints are not final user-facing descriptions.

## Save Assets

When the user asks to save images or page data:

1. Capture rendered HTML from Chrome.
2. Call `download_1688_product_assets_from_html_content`.
3. Return saved directory, manifest path, counts, and failures.
