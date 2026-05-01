"""Single URL parsing workflow orchestration."""

from sqlalchemy.orm import Session

from crawler.fetcher import fetch_url
from database.models import FileLink, Record
from parser.llm_parser import parse_with_claude


def _compact_error(exc: Exception) -> str:
    """Keep persisted error messages short and readable."""
    return str(exc).splitlines()[0].strip()


def _reset_record_output(record: Record) -> None:
    """Clear previous parse output before writing a new result."""
    record.title = ""
    record.content = ""
    record.summary = ""
    record.error_msg = ""
    record.raw_html = ""


def _replace_file_links(db: Session, record: Record, file_links: list[dict[str, str]]) -> None:
    """Replace stored file links for a record with the latest parse result."""
    db.query(FileLink).filter(FileLink.record_id == record.id).delete()
    for item in file_links:
        db.add(
            FileLink(
                record_id=record.id,
                name=str(item.get("name", "")),
                url=str(item.get("url", "")),
                file_type=str(item.get("type", "other")),
            )
        )


async def process_existing_record(db: Session, record: Record) -> Record:
    """Process an existing record in-place."""
    _reset_record_output(record)
    record.status = "running"
    record.page_status = "valid"
    db.commit()
    db.refresh(record)

    fetch_result = await fetch_url(record.url)
    record.raw_html = fetch_result.html
    if fetch_result.status != "ok":
        record.status = "failed"
        record.page_status = "invalid"
        record.error_msg = fetch_result.error
        db.commit()
        db.refresh(record)
        return record

    try:
        parsed = parse_with_claude(url=record.url, cleaned_text=fetch_result.cleaned_text)
        _replace_file_links(db, record, parsed.file_links)
        record.status = "done"
        record.page_status = parsed.page_status
        record.title = parsed.title
        record.content = parsed.content
        record.summary = parsed.summary
        record.error_msg = fetch_result.error
        db.commit()
    except Exception as exc:
        record.status = "failed"
        record.page_status = "invalid"
        record.error_msg = f"parse error: {_compact_error(exc)}"
        db.commit()

    db.refresh(record)
    return record


async def run_single_parse(db: Session, url: str) -> Record:
    """Fetch, parse, and persist one URL parsing record."""
    record = Record(url=url, status="running", page_status="valid")
    db.add(record)
    db.commit()
    db.refresh(record)
    return await process_existing_record(db, record)
