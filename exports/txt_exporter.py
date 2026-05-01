"""Plain text export for parsed records."""

from pathlib import Path
from typing import Iterable

from database.models import FileLink, Record


def _display_text(value: str) -> str:
    """Render empty text fields with a stable placeholder."""
    return value.strip() or "(empty)"


def _build_text(record: Record, file_links: Iterable[FileLink]) -> str:
    """Format record data into a readable text output."""
    lines = [
        f"Title: {record.title}",
        f"URL: {record.url}",
        f"Status: {record.status}",
        f"Page Status: {record.page_status}",
        "",
        "Summary:",
        _display_text(record.summary),
        "",
        "Content:",
        _display_text(record.content),
        "",
        "Downloadable Files:",
    ]
    links = list(file_links)
    if not links:
        lines.append("- None")
    else:
        for item in links:
            lines.append(f"- {item.name or item.url} ({item.file_type}): {item.url}")
    return "\n".join(lines).strip() + "\n"


def export_record_to_txt(record: Record, file_links: Iterable[FileLink], output_dir: str = "tmp") -> Path:
    """Write parsed record as .txt file and return file path."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / f"record_{record.id}.txt"
    file_path.write_text(_build_text(record, file_links), encoding="utf-8")
    return file_path
