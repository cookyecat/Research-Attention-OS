from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.scheduler import RuntimeContext
from app.models.source import Source
from app.schemas.api import AttentionFeedbackIn, ExtractIn, ImpactReplayAbIn, ImpactReplayIn, PlanIn
from app.services.analysis_runs import hydrate_run, latest_run_for_source
from app.services.pipeline import run_pipeline
from app.services.scheduler import RuntimeView
from app.services.source_versions import current_source_id

router = APIRouter()


@router.post("/extract")
def extract(body: ExtractIn, db: Session = Depends(get_db)):
    try:
        resolved_source_id = current_source_id(db, body.source_id)
        return run_pipeline(
            db,
            resolved_source_id,
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


@router.post("/jobs", status_code=202)
def start_analysis_job(
    body: ExtractIn,
    background_tasks: BackgroundTasks,
    reprocess: bool = False,
    db: Session = Depends(get_db),
):
    from app.execution_integrity import health_contract
    from app.services.analysis_jobs import enqueue_analysis_job, run_analysis_job

    health = health_contract()
    authority = health.get("authority") or {}
    if not authority.get("side_effects_authorized"):
        raise HTTPException(503, "Authoritative cognition is not ready")
    resolved_source_id = current_source_id(db, body.source_id)
    if db.get(Source, resolved_source_id) is None:
        raise HTTPException(404, "Source not found")
    job, dispatch_required = enqueue_analysis_job(
        source_id=resolved_source_id,
        reprocess=reprocess,
        extra_source_ids=body.extra_source_ids,
        persist_suggested_watches=body.persist_suggested_watches,
    )
    if dispatch_required:
        background_tasks.add_task(
            run_analysis_job,
            job["id"],
            extra_source_ids=body.extra_source_ids,
            persist_suggested_watches=body.persist_suggested_watches,
        )
    return job


@router.get("/jobs/source/{source_id}/active")
def get_active_analysis_job_status(source_id: UUID, db: Session = Depends(get_db)):
    from app.services.analysis_jobs import get_active_analysis_job

    resolved_source_id = current_source_id(db, source_id)
    if db.get(Source, resolved_source_id) is None:
        raise HTTPException(404, "Source not found")
    job = get_active_analysis_job(resolved_source_id)
    return {"active": job is not None, "job": job}


@router.get("/jobs/{job_id}")
def get_analysis_job_status(job_id: str):
    from app.services.analysis_jobs import get_analysis_job

    job = get_analysis_job(job_id)
    if job is None:
        raise HTTPException(404, "Analysis job not found")
    return job


@router.post("/reprocess")
def reprocess(body: ExtractIn, db: Session = Depends(get_db)):
    try:
        resolved_source_id = current_source_id(db, body.source_id)
        return run_pipeline(
            db,
            resolved_source_id,
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
    resolved_source_id = current_source_id(db, source_id)
    source = db.get(Source, resolved_source_id)
    if source is None:
        raise HTTPException(404, "Source not found")
    run = latest_run_for_source(db, resolved_source_id)
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
        causal_scope=body.causal_scope,
        evidence_provenance=body.evidence_provenance,
        attribution_rationale=body.attribution_rationale,
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
            threatens_active_work=body.runtime_context.threatens_active_work,
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
            threatens_active_work=ctx.threatens_active_work,
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
