"""HTTP fetcher with dynamic-page fallback trigger."""

from dataclasses import dataclass
from http import HTTPStatus

import httpx

from config import get_settings
from crawler.browser import fetch_with_playwright
from crawler.cleaner import clean_html


@dataclass(frozen=True)
class FetchResult:
    """Normalized fetch result for crawler consumers."""

    status: str
    html: str
    cleaned_text: str
    source: str
    error: str


async def fetch_url(url: str) -> FetchResult:
    """Fetch a URL with httpx and fallback to browser on thin content."""
    settings = get_settings()
    timeout = httpx.Timeout(settings.request_timeout)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
    except httpx.RequestError as exc:
        return FetchResult(
            status="invalid",
            html="",
            cleaned_text="",
            source="httpx",
            error=f"request error: {exc}",
        )

    if response.status_code >= HTTPStatus.BAD_REQUEST:
        return FetchResult(
            status="invalid",
            html=response.text,
            cleaned_text="",
            source="httpx",
            error=f"http status {response.status_code}",
        )

    html = response.text
    cleaned_text = clean_html(html)
    if len(cleaned_text) >= settings.playwright_fallback_threshold:
        return FetchResult(
            status="ok",
            html=html,
            cleaned_text=cleaned_text,
            source="httpx",
            error="",
        )

    browser_result = await fetch_with_playwright(url, timeout=settings.request_timeout)
    if browser_result.success:
        rendered_cleaned_text = clean_html(browser_result.html)
        return FetchResult(
            status="ok",
            html=browser_result.html,
            cleaned_text=rendered_cleaned_text,
            source="playwright",
            error="",
        )

    return FetchResult(
        status="ok",
        html=html,
        cleaned_text=cleaned_text,
        source="httpx",
        error=f"fallback skipped: {browser_result.error}",
    )
