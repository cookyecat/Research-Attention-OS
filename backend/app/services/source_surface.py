from __future__ import annotations

from sqlalchemy import exists, func, or_, select

from app.models.acquisition import InformationSnapshot
from app.models.source import Source


def current_source_ids_query():
    """Return a SELECT of the newest immutable Source snapshot per external item."""
    ranked = select(
        InformationSnapshot.raos_source_id.label("source_id"),
        func.row_number().over(
            partition_by=InformationSnapshot.external_item_id,
            order_by=(
                InformationSnapshot.captured_at.desc(),
                InformationSnapshot.id.desc(),
            ),
        ).label("snapshot_rank"),
    ).subquery()
    return select(ranked.c.source_id).where(
        ranked.c.snapshot_rank == 1
    )


def is_current_source_clause():
    versioned = exists(
        select(1).where(
            InformationSnapshot.raos_source_id == Source.id
        )
    )

    return or_(
        ~versioned,
        Source.id.in_(current_source_ids_query()),
    )


def is_user_visible_source_clause():
    """Source rows allowed on human-facing library/search surfaces.

    Internal graph reference stubs and discovery records that contain only
    platform metadata remain durable evidence, but are not readable Sources.
    """
    content_scope = Source.raw_metadata[
        "content_scope"
    ].as_string()
    return (
        Source.deleted_at.is_(None),
        Source.ingestion_method != "REFERENCE_STUB",
        or_(
            content_scope.is_(None),
            content_scope != "METADATA_ONLY",
        ),
        is_current_source_clause(),
    )
