from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.execution_integrity import desired_identity, stored_run_authority
from app.models.analysis import AnalysisRun
from app.models.scheduler import AttentionPlan
from app.services.event_membership import decision_event_for_source


def latest_authoritative_plans(db: Session) -> list[AttentionPlan]:
    rows = (
        db.execute(
            select(AttentionPlan).order_by(
                AttentionPlan.created_at.desc(), AttentionPlan.id.desc()
            )
        )
        .scalars()
        .all()
    )
    latest: dict[tuple[str, UUID], AttentionPlan] = {}
    for row in rows:
        run = db.get(AnalysisRun, row.analysis_run_id) if row.analysis_run_id else None
        if run is None:
            if desired_identity() is not None:
                continue
        elif not stored_run_authority(run).get("authoritative"):
            continue
        key = (str(row.candidate_type), row.candidate_id)
        if key not in latest:
            latest[key] = row
    return list(latest.values())


def current_attention_plans(db: Session) -> list[AttentionPlan]:
    """Project immutable AttentionPlan history into current candidate decisions.

    EVENT plans supersede historical SOURCE plans for Sources whose current
    decision-authorized source-local Event has an EVENT plan. History is never
    deleted.
    """

    latest = latest_authoritative_plans(db)
    event_ids = {
        row.candidate_id
        for row in latest
        if str(row.candidate_type).upper() == "EVENT"
    }

    current: list[AttentionPlan] = []
    for row in latest:
        candidate_type = str(row.candidate_type).upper()
        if candidate_type != "SOURCE":
            current.append(row)
            continue

        event = decision_event_for_source(db, row.candidate_id)
        if event is not None and event.id in event_ids:
            continue
        current.append(row)

    current.sort(
        key=lambda row: (
            row.created_at is not None,
            row.created_at,
            str(row.id),
        ),
        reverse=True,
    )
    return current
