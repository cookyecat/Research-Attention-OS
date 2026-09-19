from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.acquisition import InformationSnapshot


def current_source_id(db: Session, source_id: UUID) -> UUID:
    """Resolve an acquisition-backed Source version to the newest immutable snapshot.

    Non-acquisition Sources are returned unchanged. Historical Sources/AnalysisRuns stay
    persisted; normal user-space reads follow the current ExternalInformationItem version.
    """
    origin = db.execute(
        select(InformationSnapshot)
        .where(InformationSnapshot.raos_source_id == source_id)
        .order_by(InformationSnapshot.captured_at.desc())
    ).scalars().first()
    if origin is None:
        return source_id
    latest = db.execute(
        select(InformationSnapshot)
        .where(InformationSnapshot.external_item_id == origin.external_item_id)
        .order_by(InformationSnapshot.captured_at.desc())
    ).scalars().first()
    return latest.raos_source_id if latest is not None else source_id



def source_version_ids(db: Session, source_id: UUID) -> tuple[UUID, ...]:
    """Return every immutable RAOS Source version for one ExternalInformationItem.

    Non-acquisition Sources form a singleton version family.
    """
    origin = db.execute(
        select(InformationSnapshot)
        .where(InformationSnapshot.raos_source_id == source_id)
        .order_by(InformationSnapshot.captured_at.desc(), InformationSnapshot.id.desc())
    ).scalars().first()
    if origin is None:
        return (source_id,)

    rows = db.execute(
        select(InformationSnapshot)
        .where(InformationSnapshot.external_item_id == origin.external_item_id)
        .order_by(InformationSnapshot.captured_at.asc(), InformationSnapshot.id.asc())
    ).scalars().all()
    ordered: list[UUID] = []
    seen: set[UUID] = set()
    for row in rows:
        if row.raos_source_id in seen:
            continue
        seen.add(row.raos_source_id)
        ordered.append(row.raos_source_id)
    return tuple(ordered or [source_id])
