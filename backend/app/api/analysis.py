from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.scheduler import RuntimeContext
from app.models.source import Source
from app.schemas.api import AttentionFeedbackIn, ExtractIn, ImpactReplayAbIn, ImpactReplayIn, PlanIn
from app.services.analysis_runs import hydrate_run, latest_run_for_source
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
            reprocess=False,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)[:500]) from exc


@router.post("/run")
def run(body: ExtractIn, db: Session = Depends(get_db)):
    return extract(body, db)


@router.post("/reprocess")
def reprocess(body: ExtractIn, db: Session = Depends(get_db)):
    try:
        return run_pipeline(
            db,
            body.source_id,
            extra_source_ids=body.extra_source_ids,
            persist_suggested_watches=body.persist_suggested_watches,
            reprocess=True,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)[:500]) from exc


@router.get("/by-source/{source_id}")
def get_by_source(source_id: UUID, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "Source not found")
    run = latest_run_for_source(db, source_id)
    if run is None:
        raise HTTPException(404, "No analysis run for this source")
    return hydrate_run(db, run)


@router.get("/{run_id}")
def get_run(run_id: UUID, db: Session = Depends(get_db)):
    from app.models.analysis import AnalysisRun

    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(404, "AnalysisRun not found")
    return hydrate_run(db, run)


@router.get("/{run_id}/attention-plans")
def get_run_attention_plans(run_id: UUID, db: Session = Depends(get_db)):
    from app.models.analysis import AnalysisRun
    from app.services.analysis_runs import attention_plans_for_run, plan_public

    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(404, "AnalysisRun not found")
    plans = attention_plans_for_run(db, run.id)
    latest = plan_public(plans[0]) if plans else None
    return {
        "analysis_run_id": str(run.id),
        "latest_attention_plan": latest,
        "attention_plans": [plan_public(p) for p in plans],
    }


@router.get("/{run_id}/feedback")
def list_run_feedback(run_id: UUID, db: Session = Depends(get_db)):
    from app.models.analysis import AnalysisRun
    from app.services.attention_feedback import feedback_for_run, feedback_public

    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(404, "AnalysisRun not found")
    return [feedback_public(f) for f in feedback_for_run(db, run_id)]


def _replay_config(body: ImpactReplayIn | None):
    from app.services.impact_replay import ImpactReplayConfig

    body = body or ImpactReplayIn()
    return ImpactReplayConfig(
        provider=body.provider,
        model=body.model,
        thinking=body.thinking,
        reasoning_effort=body.reasoning_effort,
        timeout=body.timeout,
        label=body.label,
    )


@router.post("/{run_id}/impact-replay")
def replay_impact(run_id: UUID, body: ImpactReplayIn | None = None, db: Session = Depends(get_db)):
    from app.services.impact_replay import replay_analysis_run

    return replay_analysis_run(db, run_id, config=_replay_config(body), persist=True)


@router.get("/{run_id}/impact-replays")
def list_impact_replays(run_id: UUID, db: Session = Depends(get_db)):
    from app.models.analysis import AnalysisRun
    from app.services.impact_replay import list_replays_for_run, replay_public

    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(404, "AnalysisRun not found")
    return [replay_public(row) for row in list_replays_for_run(db, run_id)]


@router.post("/{run_id}/impact-replay/ab")
def replay_impact_ab(run_id: UUID, body: ImpactReplayAbIn, db: Session = Depends(get_db)):
    from app.services.impact_replay import compare_replays, replay_analysis_run

    a = replay_analysis_run(db, run_id, config=_replay_config(body.a), persist=True)
    b = replay_analysis_run(db, run_id, config=_replay_config(body.b), persist=True)
    return {"a": a, "b": b, "comparison": compare_replays(a, b)}


@router.post("/attention-plans/{plan_id}/feedback")
def submit_attention_feedback(plan_id: UUID, body: AttentionFeedbackIn, db: Session = Depends(get_db)):
    from app.services.attention_feedback import feedback_public, overrides_from_body, record_feedback

    row = record_feedback(
        db,
        plan_id=plan_id,
        kind=body.kind,
        overrides=overrides_from_body(body),
    )
    db.commit()
    return feedback_public(row)


@router.get("/attention-plans/{plan_id}/feedback")
def list_plan_feedback(plan_id: UUID, db: Session = Depends(get_db)):
    from app.models.scheduler import AttentionPlan
    from app.services.attention_feedback import feedback_for_plan, feedback_public

    plan = db.get(AttentionPlan, plan_id)
    if plan is None:
        raise HTTPException(404, "AttentionPlan not found")
    return [feedback_public(f) for f in feedback_for_plan(db, plan_id)]


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
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)[:500]) from exc
