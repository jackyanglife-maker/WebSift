"""Manual CLI tester for crawler fetch + clean flow."""

import asyncio
import sys
from typing import Iterable, List

from crawler.fetcher import FetchResult, fetch_url

DEFAULT_URLS = (
    "https://example.com",
    "https://httpbin.org/html",
    "https://httpbin.org/status/404",
)


def pick_urls(argv: List[str]) -> Iterable[str]:
    """Return CLI URLs if provided, otherwise use defaults."""
    return argv[1:] if len(argv) > 1 else DEFAULT_URLS


def print_result(url: str, result: FetchResult) -> None:
    """Print a compact summary for quick manual verification."""
    preview = result.cleaned_text[:250].replace("\n", " ")
    print("=" * 80)
    print(f"URL: {url}")
    print(f"status={result.status} source={result.source} cleaned_len={len(result.cleaned_text)}")
    if result.error:
        print(f"error={result.error}")
    print(f"preview={preview}")


async def run() -> int:
    """Run crawler checks over one or more URLs."""
    urls = list(pick_urls(sys.argv))
    if not urls:
        print("No URL provided.")
        return 1

    for url in urls:
        result = await fetch_url(url)
        print_result(url, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
