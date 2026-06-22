from __future__ import annotations

from pathlib import Path
from typing import Any


async def open_browser_profile(path: str | Path, url: str = "https://www.1688.com") -> dict[str, Any]:
    """Open a human-managed Playwright profile for manual 1688 login/verification."""
    from playwright.async_api import async_playwright

    profile_path = Path(path).expanduser()
    profile_path.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            str(profile_path),
            headless=False,
            viewport={"width": 1365, "height": 900},
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        # Keep the browser open for manual login until the user closes it.
        try:
            await page.wait_for_event("close", timeout=0)
        finally:
            await context.close()
    return {"status": "ok", "profile_path": str(profile_path), "url": url, "profile_saved": True}
