from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.enums import SourceEdgeRelationship
from app.models.event import EventSource
from app.models.source import Source, SourceEdge
from app.models.watch import Watch, WatchCheck, WatchTrigger
from app.services.pipeline import run_pipeline
from app.services.watch_loop import recheck_watch, watch_cumulative_source_ids

CONTINUOUS_ATTENTION_VERSION = "continuous-attention-v0.1"

SECONDARY_RELATIONSHIPS = {
    SourceEdgeRelationship.REPOSTS,
    SourceEdgeRelationship.REPORTS_ON,
    SourceEdgeRelationship.DERIVED_FROM,
}

RELEVANT_RELATIONSHIPS = SECONDARY_RELATIONSHIPS | {
    SourceEdgeRelationship.EXTENDS,
    SourceEdgeRelationship.CONTRADICTS,
}

@dataclass(frozen=True)
class ArrivalDecision:
    watch_id: str
    relevant: bool
    evidence_class: str
    action: str
    check_id: str | None = None
    disposition: str | None = None
    outcome: str | None = None

    def as_dict(self) -> dict:
        return {
            "watch_id": self.watch_id,
            "relevant": self.relevant,
            "evidence_class": self.evidence_class,
            "action": self.action,
            "check_id": self.check_id,
            "disposition": self.disposition,
            "outcome": self.outcome,
        }


def _event_ids(db: Session, source_ids: list[UUID]) -> set[UUID]:
    if not source_ids:
        return set()
    return set(
        db.execute(
            select(EventSource.event_id).where(EventSource.source_id.in_(source_ids))
        ).scalars().all()
    )

def _edges_between(db: Session, new_source_id: UUID, watched_ids: list[UUID]) -> list[SourceEdge]:
    if not watched_ids:
        return []
    return list(
        db.execute(
            select(SourceEdge).where(
                or_(
                    (SourceEdge.source_id == new_source_id) & SourceEdge.target_id.in_(watched_ids),
                    (SourceEdge.target_id == new_source_id) & SourceEdge.source_id.in_(watched_ids),
                )
            )
        ).scalars().all()
    )


def _relevant_to_watch(db: Session, new_source_id: UUID, watched_ids: list[UUID]) -> bool:
    if not watched_ids:
        return False
    if _event_ids(db, [new_source_id]) & _event_ids(db, watched_ids):
        return True
    return any(edge.relationship in RELEVANT_RELATIONSHIPS for edge in _edges_between(db, new_source_id, watched_ids))


def _evidence_class(db: Session, new_source: Source, watched_ids: list[UUID]) -> str:
    watched = [db.get(Source, source_id) for source_id in watched_ids]
    if new_source.content_hash and any(
        source is not None and source.content_hash == new_source.content_hash for source in watched
    ):
        return "DUPLICATE"
    outgoing = [
        edge for edge in _edges_between(db, new_source.id, watched_ids)
        if edge.source_id == new_source.id
    ]
    if any(edge.relationship == SourceEdgeRelationship.REPOSTS for edge in outgoing):
        return "DUPLICATE"
    if any(edge.relationship in {SourceEdgeRelationship.REPORTS_ON, SourceEdgeRelationship.DERIVED_FROM} for edge in outgoing):
        return "SECONDARY"
    return "INDEPENDENT"

def _new_evidence_trigger(db: Session, watch: Watch) -> WatchTrigger | None:
    triggers = db.execute(
        select(WatchTrigger).where(WatchTrigger.watch_id == watch.id).order_by(WatchTrigger.created_at)
    ).scalars().all()
    return next((trigger for trigger in triggers if trigger.trigger_type == "NEW_EVIDENCE"), triggers[0] if triggers else None)


def _record_duplicate_suppressed(
    db: Session,
    *,
    watch: Watch,
    trigger: WatchTrigger | None,
    new_source_id: UUID,
) -> WatchCheck:
    now = datetime.now(timezone.utc)
    if trigger is not None:
        trigger.last_triggered_at = now
        trigger.last_checked_at = now
    check = WatchCheck(
        watch_id=watch.id,
        trigger_id=trigger.id if trigger else None,
        new_source_id=new_source_id,
        analysis_run_id=None,
        attention_plan_id=None,
        disposition="SKIPPED",
        outcome="DUPLICATE_SUPPRESSED",
        checked_at=now,
    )
    db.add(check)
    db.flush()
    return check

def process_source_arrival(
    db: Session, new_source_id: UUID, *, provider=None, extraction_bridge=None
) -> dict:
    new_source = db.get(Source, new_source_id)
    if new_source is None:
        raise ValueError("Source not found")

    watches = db.execute(
        select(Watch).where(Watch.status == "ACTIVE").order_by(Watch.created_at)
    ).scalars().all()
    decisions: list[ArrivalDecision] = []
    matched_any = False

    for watch in watches:
        watched_ids = watch_cumulative_source_ids(db, watch)
        if not _relevant_to_watch(db, new_source_id, watched_ids):
            continue
        matched_any = True
        evidence_class = _evidence_class(db, new_source, watched_ids)
        trigger = _new_evidence_trigger(db, watch)

        if evidence_class == "DUPLICATE":
            check = _record_duplicate_suppressed(
                db, watch=watch, trigger=trigger, new_source_id=new_source_id
            )
            decisions.append(
                ArrivalDecision(
                    watch_id=str(watch.id), relevant=True, evidence_class=evidence_class,
                    action="SUPPRESS_RECHECK", check_id=str(check.id),
                    disposition=check.disposition, outcome=check.outcome,
                )
            )
            continue

        if trigger is None:
            decisions.append(
                ArrivalDecision(
                    watch_id=str(watch.id), relevant=True, evidence_class=evidence_class,
                    action="NO_TRIGGER", outcome="KEEP_ACTIVE",
                )
            )
            continue

        check, _result = recheck_watch(
            db, watch=watch, trigger=trigger, new_source_id=new_source_id, provider=provider,
            extraction_bridge=extraction_bridge,
        )
        decisions.append(
            ArrivalDecision(
                watch_id=str(watch.id), relevant=True, evidence_class=evidence_class,
                action="RECHECK", check_id=str(check.id), disposition=check.disposition,
                outcome=check.outcome,
            )
        )

    ordinary = None
    if not matched_any:
        ordinary = run_pipeline(
            db, new_source_id, provider=provider, extraction_bridge=extraction_bridge
        )

    return {
        "version": CONTINUOUS_ATTENTION_VERSION,
        "source_id": str(new_source_id),
        "matched_watch": matched_any,
        "watch_decisions": [decision.as_dict() for decision in decisions],
        "ordinary_analysis": ordinary,
    }
