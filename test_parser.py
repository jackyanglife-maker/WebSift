"""Manual parser test script for Phase 3 validation."""

import json
from typing import Callable, Tuple

from config import get_settings
from parser import llm_parser
from parser.llm_parser import ParseResult

TEST_CASES: Tuple[Tuple[str, str], ...] = (
    ("https://example.com/content", "A tutorial page with headings and body text."),
    ("https://example.com/files", "Download reports: report.pdf and table.xlsx"),
    ("https://example.com/empty", ""),
)


def _mock_invoke_factory() -> Callable[[object, str], str]:
    """Return deterministic mock outputs for local parser testing."""
    state = {"count": 0}

    def _mock_invoke(_client: object, prompt: str) -> str:
        state["count"] += 1
        if state["count"] == 1:
            return "not-json"
        if "report.pdf" in prompt:
            return """```json
{
  "page_status": "mixed",
  "title": "Files and Notes",
  "content": "- report details\\n- attachment list",
  "file_links": [
    {"name": "report.pdf", "url": "https://example.com/report.pdf", "type": "pdf"}
  ],
  "summary": "This page contains notes and downloadable report files."
}
```"""
        if "--- PAGE CONTENT START ---\n\n--- PAGE CONTENT END ---" in prompt:
            return json.dumps(
                {
                    "page_status": "empty",
                    "title": "",
                    "content": "",
                    "file_links": [],
                    "summary": "",
                }
            )
        return json.dumps(
            {
                "page_status": "content_only",
                "title": "Sample Content",
                "content": "# Intro\nSome parsed text.",
                "file_links": [],
                "summary": "This page includes only readable content.",
            }
        )

    return _mock_invoke


def run_mock_mode() -> None:
    """Run parser tests without external API calls."""
    print("Running parser tests in MOCK mode.")
    mock_invoke = _mock_invoke_factory()
    for url, text in TEST_CASES:
        result: ParseResult = llm_parser.parse_with_claude(url, text, invoke_fn=mock_invoke)
        print(f"{url} -> status={result.page_status}, title={result.title!r}")


def run_live_mode() -> None:
    """Run parser tests with real Claude API calls."""
    print("Running parser tests in LIVE mode.")
    for url, text in TEST_CASES:
        result: ParseResult = llm_parser.parse_with_claude(url, text)
        print(f"{url} -> status={result.page_status}, title={result.title!r}")


if __name__ == "__main__":
    settings = get_settings()
    if settings.anthropic_api_key:
        run_live_mode()
    else:
        run_mock_mode()
