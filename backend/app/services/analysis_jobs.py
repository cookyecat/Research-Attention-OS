from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from uuid import UUID, uuid4

from app.db import SessionLocal

_lock = RLock()
_jobs: dict[str, dict] = {}
_active: dict[str, str] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def enqueue_analysis_job(*, source_id: UUID, reprocess: bool, extra_source_ids=None, persist_suggested_watches: bool = False) -> tuple[dict, bool]:
    key = str(source_id)
    with _lock:
        existing_id = _active.get(key)
        if existing_id:
            existing = _jobs.get(existing_id)
            if existing and existing.get("status") in {"QUEUED", "RUNNING"}:
                return dict(existing), False
        job_id = str(uuid4())
        job = {
            "id": job_id, "source_id": str(source_id),
            "mode": "REPROCESS" if reprocess else "ANALYZE",
            "status": "QUEUED", "created_at": _now(),
            "started_at": None, "completed_at": None,
            "analysis_run_id": None, "error": None,
        }
        _jobs[job_id] = job
        _active[key] = job_id
    return dict(job), True


def run_analysis_job(job_id: str, *, extra_source_ids=None, persist_suggested_watches: bool = False) -> None:
    from app.services.pipeline import run_pipeline

    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job["status"] = "RUNNING"
        job["started_at"] = _now()
        source_id = UUID(job["source_id"])
        reprocess = job["mode"] == "REPROCESS"

    try:
        with SessionLocal() as db:
            result = run_pipeline(
                db, source_id,
                extra_source_ids=extra_source_ids or [],
                persist_suggested_watches=persist_suggested_watches,
                reprocess=reprocess,
            )
            db.commit()
        run_payload = result.get("analysis_run") if isinstance(result, dict) else None
        run_id = run_payload.get("id") if isinstance(run_payload, dict) else None
        with _lock:
            job = _jobs[job_id]
            job["status"] = "COMPLETED"
            job["completed_at"] = _now()
            job["analysis_run_id"] = run_id
    except Exception as exc:
        with _lock:
            job = _jobs.get(job_id)
            if job:
                job["status"] = "FAILED"
                job["completed_at"] = _now()
                job["error"] = f"{type(exc).__name__}: {exc}"[:1000]
    finally:
        key = str(source_id)
        with _lock:
            if _active.get(key) == job_id:
                _active.pop(key, None)


def get_analysis_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None

def get_active_analysis_job(source_id: UUID) -> dict | None:
    """Return the active authoritative cognition job for a Source, if any.

    Analyze and Reprocess intentionally share one source-level lease: one Source
    may have at most one authoritative cognition operation at a time.
    """
    key = str(source_id)
    with _lock:
        job_id = _active.get(key)
        if not job_id:
            return None
        job = _jobs.get(job_id)
        if not job or job.get("status") not in {"QUEUED", "RUNNING"}:
            _active.pop(key, None)
            return None
        return dict(job)

