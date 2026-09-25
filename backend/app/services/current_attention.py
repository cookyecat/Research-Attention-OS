from __future__ import annotations

from threading import Lock, Thread
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine

from app.execution_integrity import (
    desired_identity,
    runtime_profile_hash,
    stored_run_authority,
)
from app.models.analysis import AnalysisRun
from app.models.event import Event, EventMembershipAssertion
from app.models.scheduler import AttentionPlan
from app.services.event_membership import AUTHORIZED_MEMBERSHIP_STATUSES


_ATTENTION_CACHE_LOCK = Lock()
_ATTENTION_CACHE_PLANS: tuple[AttentionPlan, ...] = ()
_ATTENTION_CACHE_SIGNATURE: tuple[int, str] | None = None
_ATTENTION_CACHE_REFRESHING = False


def _attention_cache_signature(db: Session) -> tuple[int, str]:
    count = int(
        db.scalar(
            select(func.count()).select_from(AttentionPlan)
        )
        or 0
    )
    return (count, str(runtime_profile_hash() or ""))


def _set_attention_cache(
    signature: tuple[int, str],
    plans: list[AttentionPlan],
) -> None:
    global _ATTENTION_CACHE_PLANS, _ATTENTION_CACHE_SIGNATURE
    with _ATTENTION_CACHE_LOCK:
        _ATTENTION_CACHE_SIGNATURE = signature
        _ATTENTION_CACHE_PLANS = tuple(plans)


def _refresh_attention_cache_background() -> None:
    global _ATTENTION_CACHE_REFRESHING
    db = SessionLocal()
    try:
        signature = _attention_cache_signature(db)
        plans = _compute_current_attention_plans(db)
        _set_attention_cache(signature, plans)
    finally:
        db.close()
        with _ATTENTION_CACHE_LOCK:
            _ATTENTION_CACHE_REFRESHING = False


def warm_current_attention_cache() -> None:
    """Synchronously prewarm canonical User-Space Attention projection."""
    db = SessionLocal()
    try:
        signature = _attention_cache_signature(db)
        plans = _compute_current_attention_plans(db)
        _set_attention_cache(signature, plans)
    finally:
        db.close()


def _runs_by_id(
    db: Session,
    run_ids: set[UUID],
) -> dict[UUID, AnalysisRun]:
    if not run_ids:
        return {}
    rows = (
        db.execute(
            select(AnalysisRun).where(AnalysisRun.id.in_(run_ids))
        )
        .scalars()
        .all()
    )
    return {row.id: row for row in rows}


def latest_authoritative_plans(db: Session) -> list[AttentionPlan]:
    """Return the newest authoritative plan per semantic candidate.

    Phase13-attested runs are filtered by their small persisted authority fields
    in SQL. Only the legacy tail falls back to loading full AnalysisRun payloads.
    This avoids deserializing thousands of large result_payload JSON blobs on
    every UI request while preserving the historical authority semantics.
    """

    rows = db.execute(
        select(
            AttentionPlan.id,
            AttentionPlan.candidate_type,
            AttentionPlan.candidate_id,
            AttentionPlan.analysis_run_id,
            AttentionPlan.created_at,
        ).order_by(
            AttentionPlan.created_at.desc(),
            AttentionPlan.id.desc(),
        )
    ).all()

    desired = desired_identity()
    run_ids = {
        row.analysis_run_id
        for row in rows
        if row.analysis_run_id is not None
    }

    authoritative_run_ids: set[UUID] = set()
    if run_ids and desired is not None:
        current_hash = runtime_profile_hash()
        phase13_rows = db.execute(
            select(AnalysisRun.id).where(
                AnalysisRun.id.in_(run_ids),
                AnalysisRun.result_payload[
                    "execution_authority"
                ][
                    "runtime_profile_hash"
                ].as_string() == current_hash,
                AnalysisRun.result_payload[
                    "execution_authority"
                ][
                    "authority"
                ][
                    "attention_authorized"
                ].as_boolean().is_(True),
            )
        ).scalars().all()
        authoritative_run_ids.update(phase13_rows)

        unresolved_run_ids = run_ids - authoritative_run_ids
        legacy_runs = _runs_by_id(db, unresolved_run_ids)
        authoritative_run_ids.update(
            run_id
            for run_id, run in legacy_runs.items()
            if stored_run_authority(run).get("authoritative")
        )

    selected_ids: list[UUID] = []
    seen: set[tuple[str, UUID]] = set()
    for row in rows:
        if row.analysis_run_id is None:
            if desired is not None:
                continue
        elif row.analysis_run_id not in authoritative_run_ids:
            continue

        key = (str(row.candidate_type), row.candidate_id)
        if key in seen:
            continue
        seen.add(key)
        selected_ids.append(row.id)

    if not selected_ids:
        return []

    selected = (
        db.execute(
            select(AttentionPlan).where(
                AttentionPlan.id.in_(selected_ids)
            )
        )
        .scalars()
        .all()
    )
    by_id = {row.id: row for row in selected}
    return [
        by_id[plan_id]
        for plan_id in selected_ids
        if plan_id in by_id
    ]


def _decision_event_ids_by_source(
    db: Session,
    source_ids: set[UUID],
) -> dict[UUID, UUID]:
    """Batch form of decision_event_for_source with identical active semantics."""
    if not source_ids:
        return {}

    rows = (
        db.execute(
            select(EventMembershipAssertion)
            .where(
                EventMembershipAssertion.source_id.in_(source_ids),
                EventMembershipAssertion.authority_status.in_(
                    AUTHORIZED_MEMBERSHIP_STATUSES
                ),
            )
            .order_by(
                EventMembershipAssertion.created_at.asc(),
                EventMembershipAssertion.id.asc(),
            )
        )
        .scalars()
        .all()
    )

    latest_by_pair: dict[
        tuple[UUID, UUID],
        EventMembershipAssertion,
    ] = {}
    for row in rows:
        latest_by_pair[(row.source_id, row.event_id)] = row

    active_by_source: dict[UUID, list[UUID]] = {}
    for (source_id, event_id), row in latest_by_pair.items():
        if (
            str(row.action).upper() == "ASSERT"
            and str(row.membership).upper() == "REPORTS_EVENT"
        ):
            active_by_source.setdefault(source_id, []).append(event_id)

    unique = {
        source_id: event_ids[0]
        for source_id, event_ids in active_by_source.items()
        if len(event_ids) == 1
    }
    if not unique:
        return {}

    existing_event_ids = set(
        db.execute(
            select(Event.id).where(
                Event.id.in_(set(unique.values()))
            )
        )
        .scalars()
        .all()
    )
    return {
        source_id: event_id
        for source_id, event_id in unique.items()
        if event_id in existing_event_ids
    }


def current_attention_source_map(
    db: Session,
    plans: list[AttentionPlan] | None = None,
) -> dict[UUID, AttentionPlan]:
    """Project current Attention candidates onto their evidence Sources.

    SOURCE candidates map directly. EVENT candidates map only through the same
    unique, authorized membership semantics used by decision_event_for_source.
    Ambiguous Source membership deliberately produces no UI projection.
    """

    current = list(plans) if plans is not None else current_attention_plans(db)
    by_source = {
        row.candidate_id: row
        for row in current
        if str(row.candidate_type).upper() == "SOURCE"
    }
    event_plans = {
        row.candidate_id: row
        for row in current
        if str(row.candidate_type).upper() == "EVENT"
    }
    if not event_plans:
        return by_source

    candidate_source_ids = set(
        db.execute(
            select(EventMembershipAssertion.source_id)
            .where(
                EventMembershipAssertion.event_id.in_(
                    set(event_plans)
                ),
                EventMembershipAssertion.authority_status.in_(
                    AUTHORIZED_MEMBERSHIP_STATUSES
                ),
            )
        )
        .scalars()
        .all()
    )
    decision_event_by_source = _decision_event_ids_by_source(
        db,
        candidate_source_ids,
    )
    for source_id, event_id in decision_event_by_source.items():
        plan = event_plans.get(event_id)
        if plan is not None:
            by_source[source_id] = plan
    return by_source


def _compute_current_attention_plans(
    db: Session,
) -> list[AttentionPlan]:
    """Compute current Attention projection from immutable history."""

    latest = latest_authoritative_plans(db)
    event_ids = {
        row.candidate_id
        for row in latest
        if str(row.candidate_type).upper() == "EVENT"
    }

    source_ids = {
        row.candidate_id
        for row in latest
        if str(row.candidate_type).upper() == "SOURCE"
    }
    decision_event_by_source = _decision_event_ids_by_source(
        db,
        source_ids,
    )

    current: list[AttentionPlan] = []
    for row in latest:
        candidate_type = str(row.candidate_type).upper()
        if candidate_type != "SOURCE":
            current.append(row)
            continue

        event_id = decision_event_by_source.get(row.candidate_id)
        if event_id is not None and event_id in event_ids:
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


def current_attention_plans(db: Session) -> list[AttentionPlan]:
    """Return current Attention using stale-while-revalidate materialization.

    On the canonical runtime, Attention history is append-only. A cheap count +
    runtime-profile signature detects invalidation. If a prior materialization
    exists, users keep receiving it while a background thread refreshes the
    projection. Tests / alternate engines compute directly to avoid leaking
    canonical cache state into isolated databases.
    """

    if db.get_bind() is not engine:
        return _compute_current_attention_plans(db)

    signature = _attention_cache_signature(db)
    global _ATTENTION_CACHE_REFRESHING

    with _ATTENTION_CACHE_LOCK:
        cached = list(_ATTENTION_CACHE_PLANS)
        current_signature = _ATTENTION_CACHE_SIGNATURE
        refreshing = _ATTENTION_CACHE_REFRESHING

        if cached and current_signature == signature:
            return cached

        if cached:
            if not refreshing:
                _ATTENTION_CACHE_REFRESHING = True
                Thread(
                    target=_refresh_attention_cache_background,
                    name="raos-attention-projection-refresh",
                    daemon=True,
                ).start()
            return cached

    plans = _compute_current_attention_plans(db)
    _set_attention_cache(signature, plans)
    return plans
