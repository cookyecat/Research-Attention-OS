from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import EventStatus
from app.models.event import Event, EventMembershipAssertion, EventSource
from app.models.source import Source

SOURCE_LOCAL_MEMBERSHIP_POLICY = "source-local-event-membership-v0.1"
SOURCE_LOCAL_AUTHORITY_STATUS = "AUTHORIZED_SOURCE_LOCAL"
CROSS_SOURCE_AUTHORITY_STATUS = "AUTHORIZED"
AUTHORIZED_MEMBERSHIP_STATUSES = {
    SOURCE_LOCAL_AUTHORITY_STATUS,
    CROSS_SOURCE_AUTHORITY_STATUS,
}


def _latest_assertions_for_source(db: Session, source_id: UUID) -> list[EventMembershipAssertion]:
    rows = (
        db.execute(
            select(EventMembershipAssertion)
            .where(
                EventMembershipAssertion.source_id == source_id,
                EventMembershipAssertion.authority_status.in_(AUTHORIZED_MEMBERSHIP_STATUSES),
            )
            .order_by(
                EventMembershipAssertion.created_at.asc(),
                EventMembershipAssertion.id.asc(),
            )
        )
        .scalars()
        .all()
    )
    latest: dict[UUID, EventMembershipAssertion] = {}
    for row in rows:
        latest[row.event_id] = row
    return list(latest.values())


def active_authorized_memberships(
    db: Session, source_id: UUID
) -> list[EventMembershipAssertion]:
    return [
        row
        for row in _latest_assertions_for_source(db, source_id)
        if str(row.action).upper() == "ASSERT"
        and str(row.membership).upper() == "REPORTS_EVENT"
    ]


def decision_event_for_source(db: Session, source_id: UUID) -> Event | None:
    active = active_authorized_memberships(db, source_id)
    if len(active) != 1:
        return None
    return db.get(Event, active[0].event_id)


def safe_legacy_single_member_event(db: Session, source_id: UUID) -> Event | None:
    links = (
        db.execute(select(EventSource).where(EventSource.source_id == source_id))
        .scalars()
        .all()
    )
    if len(links) != 1:
        return None
    event_id = links[0].event_id
    member_count = db.scalar(
        select(func.count())
        .select_from(EventSource)
        .where(EventSource.event_id == event_id)
    )
    if int(member_count or 0) != 1:
        return None
    return db.get(Event, event_id)


def _assert_source_local_membership(
    db: Session,
    *,
    source_id: UUID,
    event_id: UUID,
) -> EventMembershipAssertion:
    existing = [
        row
        for row in active_authorized_memberships(db, source_id)
        if row.event_id == event_id
    ]
    if existing:
        return existing[-1]

    row = EventMembershipAssertion(
        workspace_id="local-default",
        event_id=event_id,
        source_id=source_id,
        frame_ids=[],
        action="ASSERT",
        membership="REPORTS_EVENT",
        contextual_role_fields={
            "origin": "SOURCE_LOCAL_EVENT_HYPOTHESIS",
            "cross_source_commitment": False,
        },
        audit_run_id=None,
        authority_policy_version=SOURCE_LOCAL_MEMBERSHIP_POLICY,
        authority_epoch=1,
        authority_status=SOURCE_LOCAL_AUTHORITY_STATUS,
        supersedes_assertion_id=None,
    )
    db.add(row)
    db.flush()
    return row


def ensure_source_local_event(
    db: Session,
    source: Source,
    *,
    title: str | None,
    summary: str | None,
) -> Event:
    """Resolve/create the Source's decision-safe local Event hypothesis.

    This never attaches the Source to another Source's Event by title/content.
    Cross-Source shared membership remains an explicit topology commitment.
    """

    active = active_authorized_memberships(db, source.id)
    if len(active) > 1:
        raise RuntimeError(
            "Ambiguous authorized Event memberships for Source; refusing Event Attention candidate"
        )
    if len(active) == 1:
        event = db.get(Event, active[0].event_id)
        if event is None:
            raise RuntimeError("Authorized Event membership references a missing Event")
        if db.get(EventSource, (event.id, source.id)) is None:
            db.add(
                EventSource(
                    event_id=event.id,
                    source_id=source.id,
                    relationship="REPORTS",
                    confidence=0.7,
                )
            )
            db.flush()
        return event

    legacy = safe_legacy_single_member_event(db, source.id)
    if legacy is not None:
        _assert_source_local_membership(db, source_id=source.id, event_id=legacy.id)
        return legacy

    event = Event(
        title=title or source.title or "Untitled event",
        event_type="PUBLICATION",
        summary=summary or (source.content_text or "")[:400],
        confidence=0.6,
        status=EventStatus.CANDIDATE,
    )
    db.add(event)
    db.flush()
    db.add(
        EventSource(
            event_id=event.id,
            source_id=source.id,
            relationship="REPORTS",
            confidence=0.7,
        )
    )
    db.flush()
    _assert_source_local_membership(db, source_id=source.id, event_id=event.id)
    return event


def decision_event_ids_for_sources(db: Session, source_ids: list[UUID]) -> set[UUID]:
    event_ids: set[UUID] = set()
    for source_id in source_ids:
        event = decision_event_for_source(db, source_id)
        if event is not None:
            event_ids.add(event.id)
    return event_ids


def membership_debug(db: Session, source_id: UUID) -> dict:
    active = active_authorized_memberships(db, source_id)
    return {
        "contract": SOURCE_LOCAL_MEMBERSHIP_POLICY,
        "source_id": str(source_id),
        "active_event_ids": [str(row.event_id) for row in active],
        "authority_statuses": [str(row.authority_status) for row in active],
        "ambiguous": len(active) > 1,
    }
