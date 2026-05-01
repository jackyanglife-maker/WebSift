"""Claude-backed parser for structured page extraction."""

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from anthropic import Anthropic

from config import get_settings
from parser.prompt import STRICT_JSON_REMINDER, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

ALLOWED_PAGE_STATUSES = {
    "valid",
    "empty",
    "invalid",
    "file_only",
    "content_only",
    "mixed",
}
FILE_LINK_TYPES = {"pdf", "docx", "xlsx", "zip", "other"}


@dataclass(frozen=True)
class ParseResult:
    """Normalized parse result returned by the LLM parser."""

    page_status: str
    title: str
    content: str
    file_links: list[dict[str, str]]
    summary: str


def _compact_error(exc: Exception) -> str:
    """Keep parser errors compact for logs and API responses."""
    return str(exc).splitlines()[0].strip()


def _trim_text(text: str, max_length: int) -> str:
    """Limit prompt payload size for cost and latency control."""
    return text[:max_length]


def _extract_json_candidate(payload: str) -> str:
    """Pull the JSON object out of plain text or fenced model output."""
    stripped = payload.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise json.JSONDecodeError("No JSON object found", stripped, 0)
    return stripped[start : end + 1]


def _extract_json(payload: str) -> Dict[str, Any]:
    """Parse JSON from raw model response text."""
    data = json.loads(_extract_json_candidate(payload))
    if not isinstance(data, dict):
        raise json.JSONDecodeError("Top-level JSON must be an object", payload, 0)
    return data


def _normalize_file_links(file_links: Any) -> list[dict[str, str]]:
    """Coerce file link items into a stable list-of-dicts schema."""
    if not isinstance(file_links, list):
        return []

    normalized_links: list[dict[str, str]] = []
    for item in file_links:
        if not isinstance(item, dict):
            continue

        file_type = str(item.get("type", "other")).lower()
        normalized_links.append(
            {
                "name": str(item.get("name", "")),
                "url": str(item.get("url", "")),
                "type": file_type if file_type in FILE_LINK_TYPES else "other",
            }
        )
    return normalized_links


def _normalize_output(data: Dict[str, Any]) -> ParseResult:
    """Coerce model output into the expected schema."""
    page_status = str(data.get("page_status", "invalid")).lower()
    if page_status not in ALLOWED_PAGE_STATUSES:
        page_status = "invalid"

    return ParseResult(
        page_status=page_status,
        title=str(data.get("title", "")),
        content=str(data.get("content", "")),
        file_links=_normalize_file_links(data.get("file_links", [])),
        summary=str(data.get("summary", "")),
    )


def _invoke_claude_once(client: Anthropic, prompt: str, model: str) -> str:
    """Call Claude once and return plain text response body."""
    response = client.messages.create(
        model=model,
        max_tokens=1500,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()


def _invoke_with_retry(
    invoke_fn: Callable[[Any, str], str],
    client: Any,
    prompt: str,
) -> str:
    """Retry one failed LLM call before surfacing the error."""
    last_error: Optional[RuntimeError] = None
    for _ in range(2):
        try:
            return invoke_fn(client, prompt)
        except Exception as exc:
            last_error = RuntimeError(f"anthropic request failed: {_compact_error(exc)}")

    if last_error is not None:
        raise last_error
    raise RuntimeError("anthropic request failed")


def parse_with_claude(
    url: str,
    cleaned_text: str,
    invoke_fn: Optional[Callable[[Any, str], str]] = None,
) -> ParseResult:
    """Parse cleaned webpage text into structured JSON with one retry."""
    settings = get_settings()
    if invoke_fn is None and not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is required to run parser.")

    input_text = _trim_text(cleaned_text, settings.max_content_length)
    prompt = USER_PROMPT_TEMPLATE.format(url=url, cleaned_text=input_text)
    client: Any = Anthropic(api_key=settings.anthropic_api_key) if invoke_fn is None else None
    invoke = invoke_fn or (
        lambda active_client, active_prompt: _invoke_claude_once(
            active_client,
            active_prompt,
            settings.anthropic_model,
        )
    )
    raw_first = _invoke_with_retry(invoke, client, prompt)

    try:
        return _normalize_output(_extract_json(raw_first))
    except json.JSONDecodeError:
        retry_prompt = f"{prompt}\n\n{STRICT_JSON_REMINDER}"
        raw_retry = _invoke_with_retry(invoke, client, retry_prompt)
        return _normalize_output(_extract_json(raw_retry))
