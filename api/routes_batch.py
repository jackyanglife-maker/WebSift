"""API routes for batch upload and task initialization."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Record, Task
from tasks.batch_task import (
    BATCH_WORKERS,
    TASK_RUNTIME_STATE,
    create_batch_task_from_upload,
    pause_batch_worker,
    start_batch_worker,
)

router = APIRouter(prefix="/api/batch", tags=["batch"])


@router.post("/upload")
async def upload_batch(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    """Upload CSV/Excel and create a pending batch task with records."""
    payload = await file.read()
    task = create_batch_task_from_upload(db, file, payload)
    return {"task_id": task.id, "total": task.total}


@router.post("/{task_id}/start")
async def start_batch(task_id: int, db: Session = Depends(get_db)) -> dict:
    """Start batch processing worker."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status == "done":
        return {"task_id": task_id, "status": "done", "message": "Task already completed."}
    task.status = "running"
    db.commit()
    started = start_batch_worker(task_id)
    return {
        "task_id": task_id,
        "status": "running",
        "worker_started": started,
    }


@router.post("/{task_id}/pause")
async def pause_batch(task_id: int, db: Session = Depends(get_db)) -> dict:
    """Pause a running batch worker."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    pause_batch_worker(task_id)
    task.status = "paused"
    db.commit()
    return {"task_id": task_id, "status": "paused"}


@router.post("/{task_id}/resume")
async def resume_batch(task_id: int, db: Session = Depends(get_db)) -> dict:
    """Resume a paused batch worker."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status == "done":
        return {"task_id": task_id, "status": "done", "message": "Task already completed."}
    task.status = "running"
    db.commit()
    started = start_batch_worker(task_id)
    return {
        "task_id": task_id,
        "status": "running",
        "worker_started": started,
    }


@router.get("/{task_id}/status")
async def batch_status(task_id: int, db: Session = Depends(get_db)) -> dict:
    """Get batch status and progress."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    progress = int((task.completed / task.total) * 100) if task.total else 0
    runtime_state = TASK_RUNTIME_STATE.get(task_id, "")
    worker_running = bool(BATCH_WORKERS.get(task_id) and not BATCH_WORKERS[task_id].done())
    return {
        "task_id": task.id,
        "status": task.status,
        "runtime_state": runtime_state,
        "worker_running": worker_running,
        "completed": task.completed,
        "total": task.total,
        "progress": progress,
    }


@router.get("/{task_id}/records")
async def batch_records(task_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """List records for one batch task."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    records = db.query(Record).filter(Record.task_id == task_id).order_by(Record.id.asc()).all()
    return [
        {
            "id": row.id,
            "url": row.url,
            "status": row.status,
            "page_status": row.page_status,
            "title": row.title,
            "error_msg": row.error_msg,
        }
        for row in records
    ]
