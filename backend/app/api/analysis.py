from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.scheduler import RuntimeContext
from app.schemas.api import ExtractIn, PlanIn
from app.services.pipeline import run_pipeline
from app.services.scheduler import RuntimeView

router = APIRouter()


@router.post("/extract")
def extract(body: ExtractIn, db: Session = Depends(get_db)):
    try:
        return run_pipeline(
            db,
            body.source_id,
            extra_source_ids=body.extra_source_ids,
            persist_suggested_watches=body.persist_suggested_watches,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/run")
def run(body: ExtractIn, db: Session = Depends(get_db)):
    return extract(body, db)


@router.post("/plan")
def plan(body: PlanIn, db: Session = Depends(get_db)):
    runtime = None
    ctx_id = None
    if body.runtime_context:
        ctx = RuntimeContext(
            current_task=body.runtime_context.current_task,
            session_topic=body.runtime_context.session_topic,
            available_attention_minutes=body.runtime_context.available_attention_minutes,
            interruptibility=body.runtime_context.interruptibility,
            cognitive_capacity=body.runtime_context.cognitive_capacity,
            deadline_at=body.runtime_context.deadline_at,
            captured_at=datetime.now(timezone.utc),
        )
        db.add(ctx)
        db.flush()
        ctx_id = ctx.id
        deadline_minutes = None
        if ctx.deadline_at:
            deadline_minutes = (ctx.deadline_at - datetime.now(timezone.utc)).total_seconds() / 60.0
        runtime = RuntimeView(
            current_task=ctx.current_task,
            session_topic=ctx.session_topic,
            available_attention_minutes=ctx.available_attention_minutes,
            interruptibility=ctx.interruptibility,
            cognitive_capacity=ctx.cognitive_capacity,
            deadline_minutes=deadline_minutes,
        )
    try:
        return run_pipeline(
            db,
            body.source_id,
            extra_source_ids=body.extra_source_ids,
            runtime_context_id=ctx_id,
            runtime=runtime,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
