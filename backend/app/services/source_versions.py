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



def current_source_ids(
    db: Session,
    source_ids: set[UUID],
) -> dict[UUID, UUID]:
    """Batch-resolve immutable Source versions to current acquisition snapshots."""
    if not source_ids:
        return {}

    origin_rows = (
        db.execute(
            select(InformationSnapshot)
            .where(InformationSnapshot.raos_source_id.in_(source_ids))
            .order_by(
                InformationSnapshot.captured_at.desc(),
                InformationSnapshot.id.desc(),
            )
        )
        .scalars()
        .all()
    )
    item_by_source: dict[UUID, UUID] = {}
    for row in origin_rows:
        item_by_source.setdefault(
            row.raos_source_id,
            row.external_item_id,
        )

    item_ids = set(item_by_source.values())
    latest_by_item: dict[UUID, UUID] = {}
    if item_ids:
        latest_rows = (
            db.execute(
                select(InformationSnapshot)
                .where(
                    InformationSnapshot.external_item_id.in_(
                        item_ids
                    )
                )
                .order_by(
                    InformationSnapshot.captured_at.desc(),
                    InformationSnapshot.id.desc(),
                )
            )
            .scalars()
            .all()
        )
        for row in latest_rows:
            latest_by_item.setdefault(
                row.external_item_id,
                row.raos_source_id,
            )

    return {
        source_id: latest_by_item.get(
            item_by_source.get(source_id),
            source_id,
        )
        for source_id in source_ids
    }


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
