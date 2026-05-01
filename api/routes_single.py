"""API routes for single URL parsing."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import FileLink, Record
from exports.docx_exporter import export_record_to_docx
from exports.txt_exporter import export_record_to_txt
from tasks.single_task import run_single_parse

router = APIRouter(prefix="/api", tags=["single"])


class ParseSingleRequest(BaseModel):
    """Payload schema for single URL parse endpoint."""

    url: HttpUrl


@router.post("/parse/single")
async def parse_single(payload: ParseSingleRequest, db: Session = Depends(get_db)) -> dict:
    """Parse one URL and persist result."""
    record = await run_single_parse(db, str(payload.url))
    return {
        "record_id": record.id,
        "status": record.status,
        "page_status": record.page_status,
        "error_msg": record.error_msg,
    }


@router.get("/record/{record_id}")
async def get_record(record_id: int, db: Session = Depends(get_db)) -> dict:
    """Fetch parsed record details with file links."""
    record = db.get(Record, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")

    file_links = db.query(FileLink).filter(FileLink.record_id == record_id).all()
    return {
        "id": record.id,
        "task_id": record.task_id,
        "url": record.url,
        "status": record.status,
        "page_status": record.page_status,
        "title": record.title,
        "content": record.content,
        "summary": record.summary,
        "raw_html": record.raw_html,
        "error_msg": record.error_msg,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "file_links": [
            {"id": item.id, "name": item.name, "url": item.url, "file_type": item.file_type}
            for item in file_links
        ],
    }


def _get_record_and_links(record_id: int, db: Session) -> tuple[Record, list[FileLink]]:
    """Load record and related file links or raise 404."""
    record = db.get(Record, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    file_links = db.query(FileLink).filter(FileLink.record_id == record_id).all()
    return record, file_links


@router.get("/record/{record_id}/export/txt")
async def export_txt(record_id: int, db: Session = Depends(get_db)) -> FileResponse:
    """Export a record into .txt file."""
    record, file_links = _get_record_and_links(record_id, db)
    path = export_record_to_txt(record, file_links)
    return FileResponse(path=str(path), media_type="text/plain", filename=path.name)


@router.get("/record/{record_id}/export/docx")
async def export_docx(record_id: int, db: Session = Depends(get_db)) -> FileResponse:
    """Export a record into .docx file."""
    record, file_links = _get_record_and_links(record_id, db)
    path = export_record_to_docx(record, file_links)
    return FileResponse(
        path=str(path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=path.name,
    )
