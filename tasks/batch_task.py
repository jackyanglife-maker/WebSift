"""Batch task processing with in-memory start/pause runtime state."""

import asyncio
import threading
from concurrent.futures import Future
from io import BytesIO, StringIO
from typing import Iterable, Optional

import pandas as pd
from fastapi import HTTPException, UploadFile
from pandas.errors import EmptyDataError, ParserError
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.db import SessionLocal
from database.models import Record, Task
from tasks.single_task import process_existing_record

TASK_RUNTIME_STATE: dict[int, str] = {}
BATCH_WORKERS: dict[int, Future[None]] = {}
URL_COLUMN_CANDIDATES = ("url", "link", "address", "webpage", "website", "href")
_BATCH_LOOP: Optional[asyncio.AbstractEventLoop] = None
_BATCH_LOOP_THREAD: Optional[threading.Thread] = None


def _run_batch_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Own a dedicated asyncio loop for background batch workers."""
    asyncio.set_event_loop(loop)
    loop.run_forever()


def _ensure_batch_loop() -> asyncio.AbstractEventLoop:
    """Start or reuse the dedicated background loop."""
    global _BATCH_LOOP, _BATCH_LOOP_THREAD
    if _BATCH_LOOP is not None and _BATCH_LOOP.is_running():
        return _BATCH_LOOP

    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=_run_batch_loop, args=(loop,), daemon=True)
    thread.start()
    _BATCH_LOOP = loop
    _BATCH_LOOP_THREAD = thread
    return loop


def _read_dataframe(file: UploadFile, payload: bytes) -> pd.DataFrame:
    """Parse uploaded CSV/Excel file into a DataFrame."""
    filename = (file.filename or "").lower()
    if filename.endswith(".csv"):
        try:
            return pd.read_csv(StringIO(payload.decode("utf-8")))
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded.") from exc
        except EmptyDataError as exc:
            raise HTTPException(status_code=400, detail="CSV file is empty.") from exc
        except ParserError as exc:
            raise HTTPException(status_code=400, detail="CSV file could not be parsed.") from exc
    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        try:
            return pd.read_excel(BytesIO(payload))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Excel file could not be parsed.") from exc
        except EmptyDataError as exc:
            raise HTTPException(status_code=400, detail="Excel file is empty.") from exc
    raise HTTPException(status_code=400, detail="Only CSV/Excel files are supported.")


def _find_url_column(df: pd.DataFrame) -> str:
    """Detect URL column name from accepted aliases."""
    mapping = {str(col).strip().lower(): str(col) for col in df.columns}
    for candidate in URL_COLUMN_CANDIDATES:
        if candidate in mapping:
            return mapping[candidate]
    raise HTTPException(
        status_code=400,
        detail="Could not find a URL column. Please use column name: url",
    )


def _normalize_urls(values: Iterable[object]) -> list[str]:
    """Drop empty rows and normalize URL strings."""
    urls: list[str] = []
    for value in values:
        text = str(value).strip()
        if text:
            urls.append(text)
    return urls


def create_batch_task_from_upload(db: Session, file: UploadFile, payload: bytes) -> Task:
    """Create a pending batch task and record rows from an uploaded file."""
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    dataframe = _read_dataframe(file, payload)
    url_column = _find_url_column(dataframe)
    urls = _normalize_urls(dataframe[url_column].dropna().tolist())
    if not urls:
        raise HTTPException(status_code=400, detail="No valid URL rows found in file.")

    task = Task(
        name=file.filename or "batch_upload",
        status="pending",
        total=len(urls),
        completed=0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    for url in urls:
        db.add(Record(task_id=task.id, url=url, status="pending", page_status="valid"))
    db.commit()
    db.refresh(task)
    return task


def _compute_completed(db: Session, task_id: int) -> int:
    """Count completed records for one task."""
    done_statuses = ("done", "failed", "invalid")
    count = (
        db.query(func.count(Record.id))
        .filter(Record.task_id == task_id, Record.status.in_(done_statuses))
        .scalar()
    )
    return int(count or 0)


async def run_batch_task(task_id: int) -> None:
    """Process pending records sequentially for a batch task."""
    TASK_RUNTIME_STATE[task_id] = "running"
    try:
        while True:
            db = SessionLocal()
            try:
                task = db.get(Task, task_id)
                if task is None:
                    return

                state = TASK_RUNTIME_STATE.get(task_id, "running")
                if state == "paused":
                    task.status = "paused"
                    db.commit()
                    return

                pending = (
                    db.query(Record)
                    .filter(Record.task_id == task_id, Record.status == "pending")
                    .order_by(Record.id.asc())
                    .first()
                )
                if pending is None:
                    task.completed = _compute_completed(db, task_id)
                    task.status = "done"
                    db.commit()
                    return

                task.status = "running"
                pending.status = "running"
                db.commit()
                await process_existing_record(db, pending)
                task.completed = _compute_completed(db, task_id)
                db.commit()
            finally:
                db.close()
            await asyncio.sleep(0)
    finally:
        BATCH_WORKERS.pop(task_id, None)
        TASK_RUNTIME_STATE.pop(task_id, None)


def start_batch_worker(task_id: int) -> bool:
    """Start worker if not currently running."""
    existing = BATCH_WORKERS.get(task_id)
    if existing and not existing.done():
        return False
    TASK_RUNTIME_STATE[task_id] = "running"
    loop = _ensure_batch_loop()
    BATCH_WORKERS[task_id] = asyncio.run_coroutine_threadsafe(run_batch_task(task_id), loop)
    return True


def pause_batch_worker(task_id: int) -> None:
    """Mark a running worker as paused."""
    TASK_RUNTIME_STATE[task_id] = "paused"
