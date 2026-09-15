from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.enums import TriggerType, WatchTargetType
from app.models.acquisition import SourceDefinition
from app.models.scheduler import AttentionPlan
from app.models.source import Source
from app.models.watch import Watch, WatchCheck, WatchTrigger
from app.services.active_acquisition import parse_bundle_locator, upsert_watch_query_bundle
from app.services.analysis_runs import attention_plans_for_run, latest_run_for_source, plan_public, run_public
from app.services.ingestion import ingest_url
from app.services.pipeline import run_pipeline

router = APIRouter()
AGENT_API_VERSION = "agent-interface-v0.1"


@router.get("/capabilities")
def capabilities():
    return {
        "version": AGENT_API_VERSION,
        "authority_contract": {
            "attention_authority": "canonical_raos_only",
            "agent_interface_may_assign_attention": False,
            "read_only_commands": ["capabilities", "today", "attention", "watch-status", "why"],
            "cognition_commands": ["analyze"],
            "delegation_commands": ["watch", "unwatch"],
        },
        "commands": {
            "today": "Return the current human-visible residue plus delegated WATCH responsibilities.",
            "attention": "Return the latest stored canonical AttentionPlan per candidate.",
            "analyze": "Ingest or reuse a Source and run the canonical RAOS pipeline.",
            "watch": "Delegate future-attention responsibility and optionally start active acquisition.",
            "watch-status": "Inspect a WATCH and its accumulated checks without cognition.",
            "unwatch": "Cancel the responsibility and disable its active acquisition bundle.",
            "why": "Explain the latest stored canonical judgment without reanalysis.",
        },
    }


class AgentAnalyzeIn(BaseModel):
    url: str | None = None
    source_id: UUID | None = None
    reprocess: bool = False

    @model_validator(mode="after")
    def validate_target(self):
        if bool(self.url) == bool(self.source_id):
            raise ValueError("Provide exactly one of url or source_id")
        return self


class AgentWatchIn(BaseModel):
    topic: str = Field(min_length=1, max_length=1000)
    target_type: str = "TREND"
    reason: str = "Delegated by an external agent through the RAOS Agent Interface."
    triggers: list[str] = Field(default_factory=lambda: ["NEW_EVIDENCE"])
    active_acquisition: bool = True
    max_queries: int = Field(default=6, ge=1, le=12)
    child_adapters: list[str] = Field(
        default_factory=lambda: ["HACKERNEWS_SEARCH", "BILIBILI_SEARCH"]
    )
    per_query_limit: int = Field(default=10, ge=1, le=50)

    @model_validator(mode="after")
    def validate_semantics(self):
        allowed_types = {item.value for item in WatchTargetType}
        allowed_triggers = {item.value for item in TriggerType}
        self.target_type = self.target_type.upper()
        self.triggers = [str(item).upper() for item in self.triggers]
        if self.target_type not in allowed_types:
            raise ValueError(f"Unsupported WATCH target_type: {self.target_type}")
        unknown = [item for item in self.triggers if item not in allowed_triggers]
        if unknown:
            raise ValueError(f"Unsupported WATCH trigger(s): {unknown}")
        if not self.triggers:
            raise ValueError("WATCH requires at least one trigger")
        return self


def _source_summary(source: Source | None) -> dict | None:
    if source is None:
        return None
    return {
        "id": str(source.id),
        "source_type": source.source_type,
        "title": source.title,
        "canonical_url": source.canonical_url,
        "publisher": source.publisher,
        "published_at": source.published_at.isoformat() if source.published_at else None,
        "ingested_at": source.ingested_at.isoformat() if source.ingested_at else None,
    }


def _latest_plans(db: Session) -> list[AttentionPlan]:
    rows = db.execute(
        select(AttentionPlan).order_by(AttentionPlan.created_at.desc(), AttentionPlan.id.desc())
    ).scalars().all()
    latest: dict[tuple[str, UUID], AttentionPlan] = {}
    for row in rows:
        key = (str(row.candidate_type), row.candidate_id)
        if key not in latest:
            latest[key] = row
    return list(latest.values())


def _agent_plan(db: Session, plan: AttentionPlan) -> dict:
    public = plan_public(plan)
    source = db.get(Source, plan.candidate_id) if str(plan.candidate_type) == "SOURCE" else None
    return {
        "id": str(plan.id),
        "candidate_type": str(plan.candidate_type),
        "candidate_id": str(plan.candidate_id),
        "disposition": public["disposition"],
        "urgency": public["urgency"],
        "expected_output": public["expected_output"],
        "reason": public["reason"],
        "update": public["update"],
        "delta_content": public["delta_content"],
        "cognitive_budget_minutes": public["cognitive_budget_minutes"],
        "created_at": public["created_at"],
        "source": _source_summary(source),
    }


def _watch_public(db: Session, watch: Watch) -> dict:
    triggers = db.execute(
        select(WatchTrigger).where(WatchTrigger.watch_id == watch.id)
    ).scalars().all()
    checks = db.execute(
        select(WatchCheck).where(WatchCheck.watch_id == watch.id).order_by(WatchCheck.checked_at)
    ).scalars().all()
    return {
        "id": str(watch.id),
        "target_type": watch.target_type,
        "target_ref": watch.target_ref,
        "status": watch.status,
        "created_reason": watch.created_reason,
        "created_at": watch.created_at.isoformat() if watch.created_at else None,
        "triggers": [
            {"id": str(row.id), "trigger_type": row.trigger_type,
             "last_triggered_at": row.last_triggered_at.isoformat() if row.last_triggered_at else None}
            for row in triggers
        ],
        "checks": [
            {
                "id": str(row.id),
                "new_source_id": str(row.new_source_id) if row.new_source_id else None,
                "analysis_run_id": str(row.analysis_run_id) if row.analysis_run_id else None,
                "attention_plan_id": str(row.attention_plan_id) if row.attention_plan_id else None,
                "disposition": row.disposition,
                "outcome": row.outcome,
                "checked_at": row.checked_at.isoformat() if row.checked_at else None,
            }
            for row in checks
        ],
    }


def _active_bundle_for_watch(db: Session, watch_id: UUID) -> SourceDefinition | None:
    rows = db.execute(
        select(SourceDefinition).where(SourceDefinition.source_type == "ACTIVE_QUERY_BUNDLE")
    ).scalars().all()
    for row in rows:
        try:
            if parse_bundle_locator(row.locator).watch_id == str(watch_id):
                return row
        except Exception:
            continue
    return None


@router.get("/today")
def today(db: Session = Depends(get_db)):
    plans = _latest_plans(db)
    visible = [row for row in plans if row.disposition in {"AWARE", "ENGAGE"}]
    watches = db.execute(
        select(Watch).where(Watch.status == "ACTIVE").order_by(Watch.created_at.desc())
    ).scalars().all()
    return {
        "version": AGENT_API_VERSION,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "items": [_agent_plan(db, row) for row in visible],
        "delegated_watch_count": len(watches),
        "delegated_watches": [_watch_public(db, row) for row in watches[:20]],
    }


@router.get("/attention")
def attention(
    include_drop: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    plans = _latest_plans(db)
    if not include_drop:
        plans = [row for row in plans if row.disposition != "DROP"]
    return {
        "version": AGENT_API_VERSION,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "items": [_agent_plan(db, row) for row in plans],
    }


@router.post("/analyze")
def analyze(body: AgentAnalyzeIn, db: Session = Depends(get_db)):
    try:
        if body.url:
            source = ingest_url(db, body.url)
        else:
            source = db.get(Source, body.source_id)
            if source is None or source.deleted_at is not None:
                raise HTTPException(404, "Source not found")
        result = run_pipeline(
            db,
            source.id,
            reprocess=body.reprocess,
            persist_suggested_watches=False,
        )
        return {
            "version": AGENT_API_VERSION,
            "source": _source_summary(source),
            "analysis": result,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)[:500]) from exc


@router.post("/watch")
def create_agent_watch(body: AgentWatchIn, db: Session = Depends(get_db)):
    watch = Watch(
        target_type=body.target_type,
        target_ref=body.topic.strip(),
        status="ACTIVE",
        created_reason=body.reason,
        kernel_target_ids=[],
    )
    db.add(watch)
    db.flush()
    for trigger in body.triggers:
        db.add(WatchTrigger(watch_id=watch.id, trigger_type=trigger, trigger_config={}))
    db.flush()
    acquisition = None
    if body.active_acquisition:
        try:
            source_def, expansion, spec = upsert_watch_query_bundle(
                db,
                watch=watch,
                max_queries=body.max_queries,
                child_adapters=body.child_adapters,
                per_query_limit=body.per_query_limit,
                enabled=True,
            )
            acquisition = {
                "source_definition_id": str(source_def.id),
                "enabled": source_def.enabled,
                "expansion": expansion.as_dict(),
                "bundle": spec.as_dict(),
            }
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    return {
        "version": AGENT_API_VERSION,
        "watch": _watch_public(db, watch),
        "active_acquisition": acquisition,
    }


@router.get("/watch/{watch_id}")
def watch_status(watch_id: UUID, db: Session = Depends(get_db)):
    watch = db.get(Watch, watch_id)
    if watch is None:
        raise HTTPException(404, "Watch not found")
    bundle = _active_bundle_for_watch(db, watch_id)
    return {
        "version": AGENT_API_VERSION,
        "watch": _watch_public(db, watch),
        "active_acquisition": {
            "source_definition_id": str(bundle.id),
            "enabled": bundle.enabled,
        } if bundle else None,
    }


@router.post("/watch/{watch_id}/cancel")
def cancel_watch(watch_id: UUID, db: Session = Depends(get_db)):
    watch = db.get(Watch, watch_id)
    if watch is None:
        raise HTTPException(404, "Watch not found")
    watch.status = "CANCELLED"
    bundle = _active_bundle_for_watch(db, watch_id)
    if bundle is not None:
        bundle.enabled = False
    db.flush()
    return {
        "version": AGENT_API_VERSION,
        "watch": _watch_public(db, watch),
        "active_acquisition_disabled": bool(bundle is not None),
    }


@router.get("/why/{source_id}")
def why(source_id: UUID, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None or source.deleted_at is not None:
        raise HTTPException(404, "Source not found")
    run = latest_run_for_source(db, source_id)
    if run is None:
        raise HTTPException(404, "No completed analysis exists for this Source")
    plans = attention_plans_for_run(db, run.id)
    if not plans:
        raise HTTPException(404, "No AttentionPlan exists for the latest analysis")
    plan = plans[0]
    public = plan_public(plan)
    debug = plan.score_debug if isinstance(plan.score_debug, dict) else {}
    return {
        "version": AGENT_API_VERSION,
        "source": _source_summary(source),
        "analysis_run": run_public(run),
        "decision": {
            "attention_plan_id": str(plan.id),
            "disposition": public["disposition"],
            "urgency": public["urgency"],
            "expected_output": public["expected_output"],
            "reason": public["reason"],
            "update": public["update"],
            "delta_content": public["delta_content"],
            "decision_cause": debug.get("decision_cause"),
            "decision_cause_bound": bool(debug.get("decision_cause_bound")),
            "no_delta_awareness": debug.get("no_delta_awareness") or {},
            "created_at": public["created_at"],
        },
        "reanalysis_performed": False,
    }
