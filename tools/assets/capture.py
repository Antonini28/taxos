"""Capture product screenshots at full resolution.

Every asset is regenerable by script (Phase 12 asset plan): a screenshot that cannot be
reproduced rots the moment the UI moves, and a portfolio full of stale images is worse
than one with none.

Prerequisites: `just up`, `just demo`, and both servers running.

Usage:  uv run python tools/assets/capture.py [--light-only|--dark-only]
"""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

OUT = Path(__file__).resolve().parents[2] / "docs" / "assets" / "screens"
BASE = "http://localhost:3000"
VIEWPORT = {"width": 1440, "height": 900}

# Interactions that reveal what a screen is *for*. A dashboard screenshot shows layout;
# an opened lineage panel shows the argument.
SHOTS = [
    ("dashboard", "/dashboard", None),
    ("vat-return", "/tax/vat", "box_4"),
    ("ingestion", "/data/batches", "first-batch"),
    ("agents", "/agents", "first-run"),
    ("approvals", "/work/approvals", "first-item"),
    ("audit", "/audit", None),
    ("operations", "/", None),
]


async def reveal(page, action: str | None) -> None:
    """Open the panel that makes the screen's point, then wait for its data."""
    if action is None:
        return
    try:
        if action == "box_4":
            await page.get_by_role("button", name="VAT reclaimed on purchases").click()
        elif action == "first-batch":
            await page.locator("tbody tr").first.click()
        elif action in ("first-run", "first-item"):
            await page.locator("ul li button").first.click()
        await page.wait_for_timeout(1200)
    except Exception as exc:  # noqa: BLE001 — a missing panel should not fail the run
        print(f"    (could not open {action}: {exc})")


async def capture(theme: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        context = await browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        page = await context.new_page()

        # Set the theme once; the app persists it in localStorage as a real user would.
        await page.goto(BASE, wait_until="networkidle")
        await page.evaluate(
            "t => { localStorage.setItem('taxos-theme', t);"
            "document.documentElement.classList.toggle('dark', t === 'dark'); }",
            theme,
        )

        for name, path, action in SHOTS:
            await page.goto(f"{BASE}{path}", wait_until="networkidle")
            await page.wait_for_timeout(1500)  # let queries settle so nothing shows a skeleton
            await reveal(page, action)

            target = OUT / f"{name}-{theme}.png"
            await page.screenshot(path=str(target), full_page=False)
            print(f"  ✓ {target.relative_to(OUT.parents[2])}")

        await browser.close()


async def main() -> None:
    themes = ["light", "dark"]
    if "--light-only" in sys.argv:
        themes = ["light"]
    if "--dark-only" in sys.argv:
        themes = ["dark"]

    for theme in themes:
        print(f"\n▸ {theme}")
        await capture(theme)
    print(f"\nWritten to {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
