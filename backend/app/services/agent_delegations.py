from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.watch import Watch, WatchDelegation, WatchTrigger

DEFAULT_DECLARED_ACTOR_ID = "agent-default"


def normalize_actor_id(value: str | None) -> str:
    actor = " ".join(str(value or DEFAULT_DECLARED_ACTOR_ID).split())
    if not actor:
        actor = DEFAULT_DECLARED_ACTOR_ID
    return actor[:200]


def normalize_watch_ref(value: str) -> str:
    return " ".join(str(value or "").split()).casefold()


def delegation_public(row: WatchDelegation) -> dict:
    return {
        "id": str(row.id),
        "watch_id": str(row.watch_id),
        "declared_actor_id": row.declared_actor_id,
        "status": row.status,
        "request_context": row.request_context or {},
        "created_reason": row.created_reason,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "cancelled_at": row.cancelled_at.isoformat() if row.cancelled_at else None,
    }


def delegations_for_watch(db, watch_id, *, active_only: bool = False) -> list[WatchDelegation]:
    stmt = select(WatchDelegation).where(WatchDelegation.watch_id == watch_id)
    if active_only:
        stmt = stmt.where(WatchDelegation.status == "ACTIVE")
    return db.execute(stmt.order_by(WatchDelegation.created_at, WatchDelegation.id)).scalars().all()


def find_shared_agent_watch(db, *, target_type: str, target_ref: str) -> Watch | None:
    wanted = normalize_watch_ref(target_ref)
    rows = db.execute(
        select(Watch).where(Watch.status == "ACTIVE", Watch.target_type == target_type)
        .order_by(Watch.created_at, Watch.id)
    ).scalars().all()
    for watch in rows:
        # Only Watches already carrying Agent delegations participate in automatic
        # Agent sharing. A same-named user/core Watch is not silently absorbed.
        if normalize_watch_ref(watch.target_ref) == wanted and delegations_for_watch(db, watch.id, active_only=True):
            return watch
    return None


def canonical_trigger_types(db, watch_id) -> tuple[str, ...]:
    rows = db.execute(select(WatchTrigger).where(WatchTrigger.watch_id == watch_id)).scalars().all()
    return tuple(sorted({str(row.trigger_type) for row in rows}))


def ensure_delegation(
    db,
    *,
    watch: Watch,
    declared_actor_id: str,
    reason: str,
    request_context: dict | None = None,
) -> tuple[WatchDelegation, bool]:
    actor = normalize_actor_id(declared_actor_id)
    existing = db.execute(
        select(WatchDelegation).where(
            WatchDelegation.watch_id == watch.id,
            WatchDelegation.declared_actor_id == actor,
            WatchDelegation.status == "ACTIVE",
        ).order_by(WatchDelegation.created_at.desc(), WatchDelegation.id.desc())
    ).scalars().first()
    if existing is not None:
        return existing, False
    row = WatchDelegation(
        watch_id=watch.id,
        declared_actor_id=actor,
        status="ACTIVE",
        request_context=dict(request_context or {}),
        created_reason=reason,
    )
    db.add(row)
    db.flush()
    return row, True


def cancel_delegation(db, *, watch: Watch, declared_actor_id: str) -> WatchDelegation | None:
    actor = normalize_actor_id(declared_actor_id)
    row = db.execute(
        select(WatchDelegation).where(
            WatchDelegation.watch_id == watch.id,
            WatchDelegation.declared_actor_id == actor,
            WatchDelegation.status == "ACTIVE",
        ).order_by(WatchDelegation.created_at.desc(), WatchDelegation.id.desc())
    ).scalars().first()
    if row is None:
        return None
    row.status = "CANCELLED"
    row.cancelled_at = datetime.now(timezone.utc)
    db.flush()
    return row


def watch_is_core_owned(watch: Watch) -> bool:
    return bool(watch.attention_plan_id or watch.analysis_run_id)
