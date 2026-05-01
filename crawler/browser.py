"""Playwright-based fallback fetcher for dynamic pages."""

import asyncio
from dataclasses import dataclass

from playwright.sync_api import Browser
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


@dataclass(frozen=True)
class BrowserFetchResult:
    """Result returned by the browser fallback fetcher."""

    success: bool
    html: str
    error: str


def _compact_error(exc: Exception) -> str:
    """Keep only the first line to avoid noisy playwright logs."""
    return str(exc).splitlines()[0].strip()


def _stabilize_page(page: Page, timeout_ms: int) -> None:
    """Wait briefly for the page to settle without failing the whole fetch."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        pass

    page.wait_for_timeout(1200)


def _build_page(browser: Browser, timeout_ms: int) -> Page:
    """Create a page with a conservative desktop-like browser context."""
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()
    page.set_default_timeout(timeout_ms)
    return page


def _fetch_with_playwright_sync(url: str, timeout: int) -> BrowserFetchResult:
    """Fetch rendered HTML in a dedicated sync Playwright context."""
    timeout_ms = max(timeout, 1) * 1000

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = _build_page(browser, timeout_ms)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    _stabilize_page(page, timeout_ms)
                    html = page.content()
                    return BrowserFetchResult(success=True, html=html, error="")
                finally:
                    page.context.close()
            finally:
                browser.close()
    except PlaywrightTimeoutError:
        return BrowserFetchResult(success=False, html="", error="playwright timeout")
    except PlaywrightError as exc:
        return BrowserFetchResult(
            success=False,
            html="",
            error=f"playwright error: {_compact_error(exc)}",
        )
    except Exception as exc:
        return BrowserFetchResult(
            success=False,
            html="",
            error=f"playwright error: {_compact_error(exc)}",
        )


async def fetch_with_playwright(url: str, timeout: int = 30) -> BrowserFetchResult:
    """Fetch rendered HTML using a thread wrapper around sync Playwright."""
    return await asyncio.to_thread(_fetch_with_playwright_sync, url, timeout)
