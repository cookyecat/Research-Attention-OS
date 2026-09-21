from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scheduler import AttentionPlan
from app.models.source import Source
from app.services.event_membership import (
    decision_event_for_source,
    ensure_source_local_event,
    safe_legacy_single_member_event,
)

EVENT_ATTENTION_IDENTITY_MIGRATION_VERSION = "event-attention-identity-migration-v0.2"


def _latest_source_plans(db: Session) -> list[AttentionPlan]:
    rows = (
        db.execute(
            select(AttentionPlan)
            .where(AttentionPlan.candidate_type == "SOURCE")
            .order_by(AttentionPlan.created_at.desc(), AttentionPlan.id.desc())
        )
        .scalars()
        .all()
    )
    latest: dict[UUID, AttentionPlan] = {}
    for row in rows:
        latest.setdefault(row.candidate_id, row)
    return list(latest.values())


def _event_plan_exists(db: Session, event_id: UUID) -> bool:
    return (
        db.execute(
            select(AttentionPlan.id)
            .where(
                AttentionPlan.candidate_type == "EVENT",
                AttentionPlan.candidate_id == event_id,
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )


def migrate_safe_source_attention_plans(
    db: Session,
    *,
    apply: bool = False,
) -> dict:
    """Identity-only migration from safe SOURCE plans to EVENT plans.

    No cognition is re-run. No DeliveryEnvelope/WATCH/Kernel side effect is
    created. Historical SOURCE plans remain immutable audit history.
    """

    summary = {
        "version": EVENT_ATTENTION_IDENTITY_MIGRATION_VERSION,
        "apply": bool(apply),
        "source_plan_candidates": 0,
        "eligible_safe_single_member": 0,
        "already_event_migrated": 0,
        "skipped_missing_source": 0,
        "needs_new_source_local_event": 0,
        "skipped_no_safe_event": 0,
        "created_membership_assertions_or_reused": 0,
        "created_event_plans": 0,
        "migrated": [],
        "skipped": [],
    }

    for plan in _latest_source_plans(db):
        summary["source_plan_candidates"] += 1
        source = db.get(Source, plan.candidate_id)
        if source is None:
            summary["skipped_missing_source"] += 1
            summary["skipped"].append(
                {"source_id": str(plan.candidate_id), "reason": "missing-source"}
            )
            continue

        event = decision_event_for_source(db, source.id)
        migration_mode = "AUTHORIZED_EXISTING"
        if event is None:
            event = safe_legacy_single_member_event(db, source.id)
            migration_mode = "SAFE_SINGLE_MEMBER" if event is not None else "CREATE_SOURCE_LOCAL"
        if event is not None:
            summary["eligible_safe_single_member"] += 1
        else:
            summary["needs_new_source_local_event"] += 1

        if event is not None and _event_plan_exists(db, event.id):
            summary["already_event_migrated"] += 1
            continue

        if not apply:
            summary["migrated"].append(
                {
                    "source_id": str(source.id),
                    "event_id": str(event.id) if event is not None else None,
                    "source_plan_id": str(plan.id),
                    "migration_mode": migration_mode,
                    "action": "WOULD_MIGRATE",
                }
            )
            continue

        # Safe one-member legacy Events are reused. Ambiguous/multi-member
        # legacy topology is preserved as history while this Source receives
        # a separate source-local Event hypothesis.
        authorized_event = ensure_source_local_event(
            db,
            source,
            title=(event.title if event is not None else source.title),
            summary=(event.summary if event is not None else (source.content_text or "")[:400]),
        )
        summary["created_membership_assertions_or_reused"] += 1

        debug = deepcopy(plan.score_debug or {})
        debug["identity_migration"] = {
            "version": EVENT_ATTENTION_IDENTITY_MIGRATION_VERSION,
            "from_candidate_type": "SOURCE",
            "from_candidate_id": str(source.id),
            "from_attention_plan_id": str(plan.id),
            "cognition_recomputed": False,
            "delivery_reenqueued": False,
        }
        created_at = plan.created_at
        if created_at is not None:
            created_at = created_at + timedelta(microseconds=1)

        event_plan = AttentionPlan(
            candidate_type="EVENT",
            candidate_id=authorized_event.id,
            disposition=plan.disposition,
            processing_modes=list(plan.processing_modes or []),
            urgency=plan.urgency,
            cognitive_budget_minutes=plan.cognitive_budget_minutes,
            kernel_target_ids=list(plan.kernel_target_ids or []),
            expected_output=plan.expected_output,
            reason=plan.reason,
            watch_after_processing=plan.watch_after_processing,
            scheduler_version=plan.scheduler_version,
            attention_policy_version=plan.attention_policy_version,
            runtime_context_id=plan.runtime_context_id,
            runtime_snapshot=deepcopy(plan.runtime_snapshot or {}),
            score_debug=debug,
            analysis_run_id=plan.analysis_run_id,
            created_at=created_at,
        )
        db.add(event_plan)
        db.flush()
        summary["created_event_plans"] += 1
        summary["migrated"].append(
            {
                "source_id": str(source.id),
                "event_id": str(authorized_event.id),
                "source_plan_id": str(plan.id),
                "event_plan_id": str(event_plan.id),
                "migration_mode": migration_mode,
                "action": "MIGRATED",
            }
        )

    return summary
