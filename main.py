"""FastAPI application entrypoint for WebSift."""

from pathlib import Path
import time
from types import SimpleNamespace
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from api.routes_batch import router as batch_router
from api.routes_single import router as single_router
from database.db import SessionLocal, init_db
from database.models import FileLink, Record, Task
from tasks.batch_task import create_batch_task_from_upload, pause_batch_worker, start_batch_worker
from tasks.single_task import run_single_parse

app = FastAPI(title="WebSift")
templates = Jinja2Templates(directory="templates")
TMP_DIR = Path("tmp")
EXPORT_RETENTION_SECONDS = 3600
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(single_router)
app.include_router(batch_router)


def cleanup_tmp_exports(now_ts: Optional[float] = None) -> None:
    """Delete exported files older than the configured retention window."""
    reference_ts = now_ts if now_ts is not None else time.time()
    cutoff_ts = reference_ts - EXPORT_RETENTION_SECONDS
    if not TMP_DIR.exists():
        return

    for path in TMP_DIR.iterdir():
        if not path.is_file():
            continue
        if path.stat().st_mtime < cutoff_ts:
            path.unlink()


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize database tables on app startup."""
    init_db()
    cleanup_tmp_exports()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Serve the single URL parse page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/parse/single", response_class=HTMLResponse)
async def parse_single_page(request: Request, url: str = Form(...)) -> HTMLResponse:
    """Handle HTMX single URL parse request and return result fragment."""
    db = SessionLocal()
    try:
        try:
            record = await run_single_parse(db, url)
        except Exception as exc:
            record = SimpleNamespace(
                id=0,
                title="Parse Failed",
                status="failed",
                page_status="invalid",
                url=url,
                created_at="",
                error_msg=f"Unexpected parse error: {str(exc).splitlines()[0].strip()}",
                content="",
                summary="",
            )
            file_links = []
            return templates.TemplateResponse(
                "result_fragment.html",
                {"request": request, "record": record, "file_links": file_links},
                status_code=500,
            )
        file_links = db.query(FileLink).filter(FileLink.record_id == record.id).all()
        return templates.TemplateResponse(
            "result_fragment.html",
            {"request": request, "record": record, "file_links": file_links},
        )
    finally:
        db.close()


@app.get("/record/{record_id}", response_class=HTMLResponse)
async def record_detail(request: Request, record_id: int) -> HTMLResponse:
    """Render full record detail page."""
    db = SessionLocal()
    try:
        record = db.get(Record, record_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        file_links = db.query(FileLink).filter(FileLink.record_id == record_id).all()
        return templates.TemplateResponse(
            "result.html",
            {"request": request, "record": record, "file_links": file_links},
        )
    finally:
        db.close()


@app.get("/batch", response_class=HTMLResponse)
async def batch_page(request: Request, error_message: str = "") -> HTMLResponse:
    """Render batch upload entry page."""
    return templates.TemplateResponse(
        "batch.html",
        {"request": request, "error_message": error_message},
    )


@app.post("/batch/upload")
async def batch_upload_page(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
    """Handle batch upload form and redirect to task detail page."""
    db = SessionLocal()
    try:
        try:
            payload = await file.read()
            task = create_batch_task_from_upload(db, file, payload)
            return RedirectResponse(url=f"/batch/{task.id}", status_code=303)
        except HTTPException as exc:
            return templates.TemplateResponse(
                "batch.html",
                {"request": request, "error_message": str(exc.detail)},
                status_code=exc.status_code,
            )
    finally:
        db.close()


@app.get("/batch/{task_id}", response_class=HTMLResponse)
async def batch_detail_page(request: Request, task_id: int) -> HTMLResponse:
    """Render batch task details with record list."""
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        records = db.query(Record).filter(Record.task_id == task_id).order_by(Record.id.asc()).all()
        return templates.TemplateResponse(
            "batch_detail.html",
            {"request": request, "task": task, "records": records},
        )
    finally:
        db.close()


@app.get("/batch/{task_id}/fragment", response_class=HTMLResponse)
async def batch_detail_fragment(request: Request, task_id: int) -> HTMLResponse:
    """Return HTMX fragment for batch status and record table."""
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        records = db.query(Record).filter(Record.task_id == task_id).order_by(Record.id.asc()).all()
        return templates.TemplateResponse(
            "batch_detail_fragment.html",
            {"request": request, "task": task, "records": records},
        )
    finally:
        db.close()


def _load_task_or_404(db: Session, task_id: int) -> Task:
    """Load task by id or raise 404."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/batch/{task_id}/start", response_class=HTMLResponse)
async def batch_start_page(request: Request, task_id: int) -> HTMLResponse:
    """Start batch worker from page controls and return updated fragment."""
    db = SessionLocal()
    try:
        task = _load_task_or_404(db, task_id)
        if task.status != "done":
            task.status = "running"
            db.commit()
            start_batch_worker(task_id)
        records = db.query(Record).filter(Record.task_id == task_id).order_by(Record.id.asc()).all()
        return templates.TemplateResponse(
            "batch_detail_fragment.html",
            {"request": request, "task": task, "records": records},
        )
    finally:
        db.close()


@app.post("/batch/{task_id}/pause", response_class=HTMLResponse)
async def batch_pause_page(request: Request, task_id: int) -> HTMLResponse:
    """Pause batch worker from page controls and return updated fragment."""
    db = SessionLocal()
    try:
        task = _load_task_or_404(db, task_id)
        pause_batch_worker(task_id)
        task.status = "paused"
        db.commit()
        records = db.query(Record).filter(Record.task_id == task_id).order_by(Record.id.asc()).all()
        return templates.TemplateResponse(
            "batch_detail_fragment.html",
            {"request": request, "task": task, "records": records},
        )
    finally:
        db.close()


@app.post("/batch/{task_id}/resume", response_class=HTMLResponse)
async def batch_resume_page(request: Request, task_id: int) -> HTMLResponse:
    """Resume batch worker from page controls and return updated fragment."""
    db = SessionLocal()
    try:
        task = _load_task_or_404(db, task_id)
        if task.status != "done":
            task.status = "running"
            db.commit()
            start_batch_worker(task_id)
        records = db.query(Record).filter(Record.task_id == task_id).order_by(Record.id.asc()).all()
        return templates.TemplateResponse(
            "batch_detail_fragment.html",
            {"request": request, "task": task, "records": records},
        )
    finally:
        db.close()
