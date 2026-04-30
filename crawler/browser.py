"""Playwright-based fallback fetcher for dynamic pages."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserFetchResult:
    """Result returned by the browser fallback fetcher."""

    success: bool
    html: str
    error: str


async def fetch_with_playwright(url: str, timeout: int = 30) -> BrowserFetchResult:
    """Stub implementation for Phase 2.

    The full Playwright rendering logic will be implemented in a later step.
    """
    _ = (url, timeout)
    return BrowserFetchResult(
        success=False,
        html="",
        error="Playwright fallback is not implemented yet.",
    )
