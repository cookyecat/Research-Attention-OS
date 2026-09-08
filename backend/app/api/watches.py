from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.watch import Watch, WatchCheck, WatchTrigger
from app.schemas.api import WatchCreate
from app.services.watch_loop import recheck_watch

router = APIRouter()


@router.post("")
def create_watch(body: WatchCreate, db: Session = Depends(get_db)):
    if not body.triggers:
        raise HTTPException(400, "WATCH requires at least one promotion trigger")
    watch = Watch(
        target_type=body.target_type,
        target_ref=body.target_ref,
        status="ACTIVE",
        created_reason=body.created_reason,
        kernel_target_ids=body.kernel_target_ids,
    )
    db.add(watch)
    db.flush()
    for trig in body.triggers:
        db.add(WatchTrigger(watch_id=watch.id, trigger_type=trig, trigger_config={}))
    db.flush()
    return _watch_out(db, watch)


@router.get("")
def list_watches(db: Session = Depends(get_db)):
    rows = db.execute(select(Watch).order_by(Watch.created_at.desc())).scalars().all()
    return [_watch_out(db, w) for w in rows]


@router.post("/{watch_id}/triggers/{trigger_id}/fire")
def fire_trigger(watch_id: UUID, trigger_id: UUID, source_id: UUID | None = None, db: Session = Depends(get_db)):
    watch = db.get(Watch, watch_id)
    trigger = db.get(WatchTrigger, trigger_id)
    if watch is None or trigger is None or trigger.watch_id != watch.id:
        raise HTTPException(404, "Watch or trigger not found")
    result = None
    check = None
    if source_id:
        try:
            check, result = recheck_watch(
                db, watch=watch, trigger=trigger, new_source_id=source_id
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    else:
        trigger.last_triggered_at = datetime.now(timezone.utc)
        trigger.last_checked_at = trigger.last_triggered_at
        db.flush()
    return {
        "watch": _watch_out(db, watch),
        "message": "Trigger fired; WATCH responsibility re-evaluated against cumulative evidence.",
        "check": _check_out(check) if check else None,
        "analysis": result,
    }


def _watch_out(db: Session, watch: Watch) -> dict:
    db.refresh(watch)
    triggers = db.execute(select(WatchTrigger).where(WatchTrigger.watch_id == watch.id)).scalars().all()
    checks = db.execute(
        select(WatchCheck).where(WatchCheck.watch_id == watch.id).order_by(WatchCheck.checked_at)
    ).scalars().all()
    return {
        "id": str(watch.id),
        "target_type": watch.target_type,
        "target_ref": watch.target_ref,
        "status": watch.status,
        "created_reason": watch.created_reason,
        "kernel_target_ids": watch.kernel_target_ids,
        "checks": [_check_out(check) for check in checks],
        "triggers": [
            {
                "id": str(t.id),
                "trigger_type": t.trigger_type,
                "last_triggered_at": t.last_triggered_at.isoformat() if t.last_triggered_at else None,
            }
            for t in triggers
        ],
    }


def _check_out(check: WatchCheck | None) -> dict | None:
    if check is None:
        return None
    return {
        "id": str(check.id),
        "new_source_id": str(check.new_source_id) if check.new_source_id else None,
        "analysis_run_id": str(check.analysis_run_id) if check.analysis_run_id else None,
        "attention_plan_id": str(check.attention_plan_id) if check.attention_plan_id else None,
        "disposition": check.disposition,
        "outcome": check.outcome,
        "checked_at": check.checked_at.isoformat() if check.checked_at else None,
    }
