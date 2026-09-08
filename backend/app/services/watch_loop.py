from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.enums import Disposition
from app.models.analysis import AnalysisRun
from app.models.scheduler import AttentionPlan
from app.models.watch import Watch, WatchCheck, WatchTrigger
from app.services.pipeline import run_pipeline

WATCH_LOOP_VERSION = "watch-loop-v0.1"


def _uuid_list(values) -> list[UUID]:
    out: list[UUID] = []
    for value in values or []:
        try:
            out.append(value if isinstance(value, UUID) else UUID(str(value)))
        except (TypeError, ValueError):
            continue
    return out


def _origin_input(db: Session, watch: Watch) -> tuple[UUID | None, list[UUID]]:
    if watch.analysis_run_id:
        run = db.get(AnalysisRun, watch.analysis_run_id)
        if run is not None:
            return run.source_id, _uuid_list(run.extra_source_ids)
    if watch.attention_plan_id:
        plan = db.get(AttentionPlan, watch.attention_plan_id)
        if plan is not None and str(plan.candidate_type) in {"SOURCE", "CandidateType.SOURCE"}:
            return plan.candidate_id, []
    return None, []


def watch_cumulative_source_ids(db: Session, watch: Watch) -> list[UUID]:
    primary_source_id, prior_extra_ids = _origin_input(db, watch)
    if primary_source_id is None:
        return []
    return [primary_source_id, *[sid for sid in prior_extra_ids if sid != primary_source_id]]


def _recheck_outcome(disposition: str) -> str:
    if disposition in {Disposition.AWARE.value, Disposition.ENGAGE.value}:
        return "PROMOTED"
    return "KEEP_ACTIVE"


def recheck_watch(
    db: Session,
    *,
    watch: Watch,
    trigger: WatchTrigger,
    new_source_id: UUID,
    provider=None,
    extraction_bridge=None,
) -> tuple[WatchCheck, dict]:
    if watch.status != "ACTIVE":
        raise ValueError(f"Watch is not ACTIVE: {watch.status}")
    if trigger.watch_id != watch.id:
        raise ValueError("Trigger does not belong to Watch")

    primary_source_id, prior_extra_ids = _origin_input(db, watch)
    if primary_source_id is None:
        primary_source_id = new_source_id
        extra_ids: list[UUID] = []
    else:
        extra_ids = [sid for sid in prior_extra_ids if sid != primary_source_id]
        if new_source_id != primary_source_id and new_source_id not in extra_ids:
            extra_ids.append(new_source_id)
    result = run_pipeline(
        db,
        primary_source_id,
        extra_source_ids=extra_ids,
        reprocess=True,
        allow_watch_creation=False,
        provider=provider,
        extraction_bridge=extraction_bridge,
    )
    plan = result.get("attention_plan") or {}
    disposition = str(plan.get("disposition") or "DROP")
    outcome = _recheck_outcome(disposition)
    if outcome == "PROMOTED":
        watch.status = "PROMOTED"

    now = datetime.now(timezone.utc)
    trigger.last_triggered_at = now
    trigger.last_checked_at = now
    analysis = result.get("analysis_run") or {}
    latest_analysis_run_id = UUID(analysis["id"]) if analysis.get("id") else None
    if latest_analysis_run_id is not None:
        # Advance the Watch's cumulative evidence anchor so the next recheck
        # sees prior evidence plus the new source instead of forgetting history.
        watch.analysis_run_id = latest_analysis_run_id
    check = WatchCheck(
        watch_id=watch.id,
        trigger_id=trigger.id,
        new_source_id=new_source_id,
        analysis_run_id=latest_analysis_run_id,
        attention_plan_id=UUID(plan["id"]) if plan.get("id") else None,
        disposition=disposition,
        outcome=outcome,
        checked_at=now,
    )
    db.add(check)
    db.flush()
    return check, result
