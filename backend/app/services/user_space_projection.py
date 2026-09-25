from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from uuid import UUID
from urllib.parse import urlparse

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.acquisition import InformationSnapshot
from app.models.analysis import AnalysisRun
from app.models.event import EventMembershipAssertion
from app.models.scheduler import AttentionPlan
from app.models.source import Source
from app.models.user_space import (
    LOCAL_OWNER_KEY,
    ProjectionCheckpoint,
    ProjectionOutbox,
    SourceSurfaceProjection,
    UserAttentionProjection,
    UserSourceAttentionProjection,
)
from app.services.event_membership import (
    AUTHORIZED_MEMBERSHIP_STATUSES,
    decision_event_for_source,
)
from app.services.source_surface import is_user_visible_source_clause


LOGGER = logging.getLogger(__name__)

PROJECTION_CONTRACT = "user-space-materialized-projection-v0.1"
PROJECTOR_NAME = "user-space-v0.1"

SOURCE_CHANGED = "SOURCE_CHANGED"
SNAPSHOT_CHANGED = "SNAPSHOT_CHANGED"
MEMBERSHIP_CHANGED = "MEMBERSHIP_CHANGED"
ATTENTION_PLAN_CHANGED = "ATTENTION_PLAN_CHANGED"

CHANGE_TYPES = {
    SOURCE_CHANGED,
    SNAPSHOT_CHANGED,
    MEMBERSHIP_CHANGED,
    ATTENTION_PLAN_CHANGED,
}


def enqueue_projection_change(
    db: Session,
    change_type: str,
    entity_id: UUID | None,
    *,
    payload: dict | None = None,
) -> ProjectionOutbox:
    """Append a projection trigger in the canonical mutation transaction."""

    if change_type not in CHANGE_TYPES:
        raise ValueError(f"Unknown projection change type: {change_type}")
    row = ProjectionOutbox(
        change_type=change_type,
        entity_id=entity_id,
        payload=dict(payload or {}),
    )
    db.add(row)
    return row


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _next_surface_seq(db: Session) -> int:
    return int(
        db.scalar(
            select(func.max(SourceSurfaceProjection.surface_seq))
        )
        or 0
    ) + 1


def _next_attention_seq(
    db: Session,
    owner_key: str = LOCAL_OWNER_KEY,
) -> int:
    return int(
        db.scalar(
            select(func.max(UserAttentionProjection.attention_seq)).where(
                UserAttentionProjection.owner_key == owner_key
            )
        )
        or 0
    ) + 1


def _source_base_visible(source: Source | None) -> bool:
    if source is None or source.deleted_at is not None:
        return False
    if str(source.ingestion_method or "").upper() == "REFERENCE_STUB":
        return False
    scope = str((source.raw_metadata or {}).get("content_scope") or "").upper()
    return scope != "METADATA_ONLY"


def _source_version_state(
    db: Session,
    source_id: UUID,
) -> tuple[bool, set[UUID]]:
    """Return (is_current, version_family) without a corpus-wide window query."""

    origins = list(
        db.execute(
            select(InformationSnapshot.external_item_id).where(
                InformationSnapshot.raos_source_id == source_id
            )
        ).scalars().all()
    )
    if not origins:
        return True, {source_id}

    current_ids: set[UUID] = set()
    family: set[UUID] = {source_id}
    for item_id in set(origins):
        rows = (
            db.execute(
                select(InformationSnapshot)
                .where(
                    InformationSnapshot.external_item_id == item_id
                )
                .order_by(
                    InformationSnapshot.captured_at.desc(),
                    InformationSnapshot.id.desc(),
                )
            )
            .scalars()
            .all()
        )
        if rows:
            current_ids.add(rows[0].raos_source_id)
            family.update(row.raos_source_id for row in rows)
    return source_id in current_ids, family


def _current_source_id_targeted(
    db: Session,
    source_id: UUID,
) -> UUID:
    origins = (
        db.execute(
            select(InformationSnapshot)
            .where(InformationSnapshot.raos_source_id == source_id)
            .order_by(
                InformationSnapshot.captured_at.desc(),
                InformationSnapshot.id.desc(),
            )
        )
        .scalars()
        .all()
    )
    if not origins:
        return source_id

    latest_candidates: list[InformationSnapshot] = []
    for item_id in {row.external_item_id for row in origins}:
        latest = (
            db.execute(
                select(InformationSnapshot)
                .where(InformationSnapshot.external_item_id == item_id)
                .order_by(
                    InformationSnapshot.captured_at.desc(),
                    InformationSnapshot.id.desc(),
                )
            )
            .scalars()
            .first()
        )
        if latest is not None:
            latest_candidates.append(latest)
    if not latest_candidates:
        return source_id
    latest_candidates.sort(
        key=lambda row: (
            row.captured_at is not None,
            row.captured_at,
            str(row.id),
        ),
        reverse=True,
    )
    return latest_candidates[0].raos_source_id


def _source_excerpt(source: Source) -> str | None:
    text = " ".join(str(source.content_text or "").split())
    if not text:
        return None
    return text[:320] + ("…" if len(text) > 320 else "")


def _hero_image(source: Source) -> str | None:
    metadata = dict(source.raw_metadata or {})
    return (
        metadata.get("paper_lead_figure_url")
        or metadata.get("hero_image_cached_url")
        or metadata.get("hero_image_url")
    )


def _paper_category_code(metadata: dict) -> str | None:
    value = str(metadata.get("primary_category") or "").strip()
    if not value:
        return None
    if "(" in value and value.endswith(")"):
        inner = value.rsplit("(", 1)[-1][:-1].strip()
        if inner:
            return inner
    return value


def _origin_label(source: Source) -> str:
    metadata = dict(source.raw_metadata or {})
    if metadata.get("paper_profile"):
        category = _paper_category_code(metadata)
        return f"arXiv · {category}" if category else "arXiv"
    if (
        str(source.ingestion_method or "").upper()
        in {"WEIBO_PUBLIC", "X_PUBLIC"}
        and source.publisher
    ):
        return str(source.publisher)
    if source.canonical_url:
        try:
            host = (urlparse(source.canonical_url).hostname or "").lower()
            if host.startswith("www."):
                host = host[4:]
            if host:
                return host
        except Exception:
            pass
    return str(
        source.publisher
        or source.ingestion_method
        or source.source_type
        or "source"
    )


def _reading_minutes(source: Source) -> int | None:
    text = str(source.content_text or "")
    if not text.strip():
        return None
    cjk = sum(1 for char in text if "\u3400" <= char <= "\u9fff")
    words = len(
        [
            part
            for part in "".join(
                " " if "\u3400" <= char <= "\u9fff" else char
                for char in text
            ).split()
            if part
        ]
    )
    estimate = round(words / 230 + cjk / 450)
    return max(1, int(estimate))


def _presentation_metadata(source: Source) -> dict:
    metadata = dict(source.raw_metadata or {})
    keys = {
        "paper_profile",
        "paper_title",
        "abstract",
        "primary_category",
        "feed_fallback",
        "hero_image_alt",
        "social_platform",
        "social_author",
        "published",
    }
    return {
        key: metadata[key]
        for key in keys
        if key in metadata
    }


def _delete_source_surface(
    db: Session,
    source_id: UUID,
    *,
    owner_key: str = LOCAL_OWNER_KEY,
) -> None:
    db.execute(
        delete(UserSourceAttentionProjection).where(
            UserSourceAttentionProjection.owner_key == owner_key,
            UserSourceAttentionProjection.source_id == source_id,
        )
    )
    db.execute(
        delete(SourceSurfaceProjection).where(
            SourceSurfaceProjection.source_id == source_id
        )
    )


def project_source(
    db: Session,
    source_id: UUID,
    *,
    owner_key: str = LOCAL_OWNER_KEY,
    surface_seq: int | None = None,
) -> SourceSurfaceProjection | None:
    source = db.get(Source, source_id)
    current, _family = _source_version_state(db, source_id)

    if not _source_base_visible(source) or not current:
        _delete_source_surface(
            db,
            source_id,
            owner_key=owner_key,
        )
        return None

    event = decision_event_for_source(db, source_id)
    existing = db.get(SourceSurfaceProjection, source_id)
    if existing is None:
        existing = SourceSurfaceProjection(
            source_id=source_id,
            surface_seq=(
                int(surface_seq)
                if surface_seq is not None
                else _next_surface_seq(db)
            ),
            title=source.title,
            publisher=source.publisher,
            source_type=str(source.source_type),
            ingestion_method=source.ingestion_method,
            origin_label=_origin_label(source),
            canonical_url=source.canonical_url,
            published_at=source.published_at,
            ingested_at=source.ingested_at,
            excerpt=_source_excerpt(source),
            hero_image_url=_hero_image(source),
            reading_minutes=_reading_minutes(source),
            presentation_metadata=_presentation_metadata(source),
            current_event_id=event.id if event else None,
            projected_at=_now(),
        )
        db.add(existing)
    else:
        existing.title = source.title
        existing.publisher = source.publisher
        existing.source_type = str(source.source_type)
        existing.ingestion_method = source.ingestion_method
        existing.origin_label = _origin_label(source)
        existing.canonical_url = source.canonical_url
        existing.published_at = source.published_at
        existing.ingested_at = source.ingested_at
        existing.excerpt = _source_excerpt(source)
        existing.hero_image_url = _hero_image(source)
        existing.reading_minutes = _reading_minutes(source)
        existing.presentation_metadata = _presentation_metadata(source)
        existing.current_event_id = event.id if event else None
        existing.projected_at = _now()

    db.flush()
    project_membership(
        db,
        source_id,
        owner_key=owner_key,
    )
    return existing


def project_snapshot(
    db: Session,
    snapshot_id: UUID,
    *,
    owner_key: str = LOCAL_OWNER_KEY,
) -> None:
    snapshot = db.get(InformationSnapshot, snapshot_id)
    if snapshot is None:
        return
    family_ids = set(
        db.execute(
            select(InformationSnapshot.raos_source_id).where(
                InformationSnapshot.external_item_id
                == snapshot.external_item_id
            )
        ).scalars().all()
    )
    for source_id in sorted(family_ids, key=str):
        project_source(
            db,
            source_id,
            owner_key=owner_key,
        )


def _representative_source_for_plan(
    db: Session,
    plan: AttentionPlan,
) -> UUID | None:
    if plan.analysis_run_id is None:
        if str(plan.candidate_type).upper() == "SOURCE":
            return _current_source_id_targeted(
                db,
                plan.candidate_id,
            )
        return None
    run = db.get(AnalysisRun, plan.analysis_run_id)
    if run is None:
        return None
    return _current_source_id_targeted(db, run.source_id)


def _plan_is_newer(
    db: Session,
    existing: UserAttentionProjection,
    incoming: AttentionPlan,
) -> bool:
    if incoming.id == existing.attention_plan_id:
        return False
    prior = db.get(AttentionPlan, existing.attention_plan_id)
    if prior is None:
        return True
    incoming_key = (
        incoming.created_at is not None,
        incoming.created_at,
        str(incoming.id),
    )
    prior_key = (
        prior.created_at is not None,
        prior.created_at,
        str(prior.id),
    )
    return incoming_key > prior_key


def project_attention_plan(
    db: Session,
    plan_id: UUID,
    *,
    owner_key: str = LOCAL_OWNER_KEY,
    attention_seq: int | None = None,
) -> UserAttentionProjection | None:
    plan = db.get(AttentionPlan, plan_id)
    if plan is None:
        return None

    candidate_type = str(plan.candidate_type).upper()
    existing = (
        db.execute(
            select(UserAttentionProjection).where(
                UserAttentionProjection.owner_key == owner_key,
                UserAttentionProjection.candidate_type
                == candidate_type,
                UserAttentionProjection.candidate_id
                == plan.candidate_id,
            )
        )
        .scalars()
        .one_or_none()
    )
    if existing is not None and not _plan_is_newer(
        db,
        existing,
        plan,
    ):
        return existing

    seq = (
        int(attention_seq)
        if attention_seq is not None
        else _next_attention_seq(db, owner_key)
    )
    representative_source_id = _representative_source_for_plan(
        db,
        plan,
    )
    event_id = (
        plan.candidate_id
        if candidate_type == "EVENT"
        else None
    )

    if existing is None:
        existing = UserAttentionProjection(
            owner_key=owner_key,
            candidate_type=candidate_type,
            candidate_id=plan.candidate_id,
            event_id=event_id,
            attention_plan_id=plan.id,
            attention_seq=seq,
            disposition=str(plan.disposition),
            representative_source_id=representative_source_id,
            reason=plan.reason,
            urgency=plan.urgency,
            cognitive_budget_minutes=plan.cognitive_budget_minutes,
            created_at=plan.created_at,
            projected_at=_now(),
        )
        db.add(existing)
    else:
        existing.event_id = event_id
        existing.attention_plan_id = plan.id
        existing.attention_seq = seq
        existing.disposition = str(plan.disposition)
        existing.representative_source_id = (
            representative_source_id
        )
        existing.reason = plan.reason
        existing.urgency = plan.urgency
        existing.cognitive_budget_minutes = (
            plan.cognitive_budget_minutes
        )
        existing.created_at = plan.created_at
        existing.projected_at = _now()

    db.flush()

    if candidate_type == "EVENT":
        source_ids = set(
            db.execute(
                select(EventMembershipAssertion.source_id).where(
                    EventMembershipAssertion.event_id
                    == plan.candidate_id,
                    EventMembershipAssertion.authority_status.in_(
                        AUTHORIZED_MEMBERSHIP_STATUSES
                    ),
                )
            ).scalars().all()
        )
        for source_id in sorted(source_ids, key=str):
            project_membership(
                db,
                source_id,
                owner_key=owner_key,
            )
    elif candidate_type == "SOURCE":
        project_membership(
            db,
            plan.candidate_id,
            owner_key=owner_key,
            direct_plan=existing,
        )

    return existing


def project_membership(
    db: Session,
    source_id: UUID,
    *,
    owner_key: str = LOCAL_OWNER_KEY,
    direct_plan: UserAttentionProjection | None = None,
) -> UserSourceAttentionProjection | None:
    current_source_id = _current_source_id_targeted(
        db,
        source_id,
    )
    surface = db.get(
        SourceSurfaceProjection,
        current_source_id,
    )
    if surface is None:
        db.execute(
            delete(UserSourceAttentionProjection).where(
                UserSourceAttentionProjection.owner_key
                == owner_key,
                UserSourceAttentionProjection.source_id
                == current_source_id,
            )
        )
        return None

    event = decision_event_for_source(db, source_id)
    plan_projection = direct_plan
    if plan_projection is None and event is not None:
        plan_projection = (
            db.execute(
                select(UserAttentionProjection).where(
                    UserAttentionProjection.owner_key
                    == owner_key,
                    UserAttentionProjection.candidate_type
                    == "EVENT",
                    UserAttentionProjection.candidate_id
                    == event.id,
                )
            )
            .scalars()
            .one_or_none()
        )

    event_id = event.id if event else None
    surface.current_event_id = event_id
    surface.projected_at = _now()

    existing = (
        db.execute(
            select(UserSourceAttentionProjection).where(
                UserSourceAttentionProjection.owner_key
                == owner_key,
                UserSourceAttentionProjection.source_id
                == current_source_id,
            )
        )
        .scalars()
        .one_or_none()
    )

    if event_id is None and plan_projection is None:
        if existing is not None:
            db.delete(existing)
        return None

    if existing is None:
        existing = UserSourceAttentionProjection(
            owner_key=owner_key,
            source_id=current_source_id,
            event_id=event_id,
            attention_plan_id=(
                plan_projection.attention_plan_id
                if plan_projection
                else None
            ),
            disposition=(
                plan_projection.disposition
                if plan_projection
                else None
            ),
            attention_seq=(
                plan_projection.attention_seq
                if plan_projection
                else None
            ),
            projected_at=_now(),
        )
        db.add(existing)
    else:
        existing.event_id = event_id
        existing.attention_plan_id = (
            plan_projection.attention_plan_id
            if plan_projection
            else None
        )
        existing.disposition = (
            plan_projection.disposition
            if plan_projection
            else None
        )
        existing.attention_seq = (
            plan_projection.attention_seq
            if plan_projection
            else None
        )
        existing.projected_at = _now()
    db.flush()
    return existing


def _dispatch_change(
    db: Session,
    row: ProjectionOutbox,
) -> None:
    if row.change_type == SOURCE_CHANGED:
        if row.entity_id is not None:
            project_source(db, row.entity_id)
        return
    if row.change_type == SNAPSHOT_CHANGED:
        if row.entity_id is not None:
            project_snapshot(db, row.entity_id)
        return
    if row.change_type == MEMBERSHIP_CHANGED:
        if row.entity_id is not None:
            project_membership(db, row.entity_id)
        return
    if row.change_type == ATTENTION_PLAN_CHANGED:
        if row.entity_id is not None:
            project_attention_plan(db, row.entity_id)
        return
    raise ValueError(
        f"Unsupported projection change type: {row.change_type}"
    )


def _checkpoint(db: Session) -> ProjectionCheckpoint:
    row = db.get(ProjectionCheckpoint, PROJECTOR_NAME)
    if row is None:
        row = ProjectionCheckpoint(
            name=PROJECTOR_NAME,
            last_outbox_seq=0,
            updated_at=_now(),
        )
        db.add(row)
        db.flush()
    return row


def process_projection_outbox(
    db: Session,
    *,
    limit: int = 100,
) -> int:
    """Consume pending triggers idempotently.

    processed_at, not the checkpoint, is the true pending-set authority. This
    avoids skipping a late-committing lower sequence in a future multi-writer
    database. The checkpoint is an observable high-water mark.
    """

    rows = (
        db.execute(
            select(ProjectionOutbox)
            .where(ProjectionOutbox.processed_at.is_(None))
            .order_by(ProjectionOutbox.seq.asc())
            .limit(max(1, min(int(limit), 1000)))
        )
        .scalars()
        .all()
    )
    if not rows:
        return 0

    checkpoint = _checkpoint(db)
    for row in rows:
        _dispatch_change(db, row)
        row.processed_at = _now()
        checkpoint.last_outbox_seq = max(
            int(checkpoint.last_outbox_seq or 0),
            int(row.seq),
        )
        checkpoint.updated_at = _now()
    db.flush()
    return len(rows)


def rebuild_user_space_projections(
    db: Session,
    *,
    owner_key: str = LOCAL_OWNER_KEY,
    acknowledge_outbox: bool = False,
) -> dict:
    """Rebuild every disposable read model from canonical state.

    Run with canonical writers quiesced when acknowledge_outbox=True.
    """

    db.execute(delete(UserSourceAttentionProjection))
    db.execute(delete(UserAttentionProjection))
    db.execute(delete(SourceSurfaceProjection))
    db.flush()

    visible_sources = (
        db.execute(
            select(Source)
            .where(*is_user_visible_source_clause())
            .order_by(
                Source.ingested_at.asc(),
                Source.id.asc(),
            )
        )
        .scalars()
        .all()
    )

    for seq, source in enumerate(
        visible_sources,
        start=1,
    ):
        project_source(
            db,
            source.id,
            owner_key=owner_key,
            surface_seq=seq,
        )

    from app.services.current_attention import (
        _compute_current_attention_plans,
    )

    plans = _compute_current_attention_plans(db)
    plans.sort(
        key=lambda row: (
            row.created_at is not None,
            row.created_at,
            str(row.id),
        )
    )
    for seq, plan in enumerate(plans, start=1):
        project_attention_plan(
            db,
            plan.id,
            owner_key=owner_key,
            attention_seq=seq,
        )

    if acknowledge_outbox:
        now = _now()
        pending = (
            db.execute(
                select(ProjectionOutbox).where(
                    ProjectionOutbox.processed_at.is_(None)
                )
            )
            .scalars()
            .all()
        )
        max_seq = 0
        for row in pending:
            row.processed_at = now
            max_seq = max(max_seq, int(row.seq))
        checkpoint = _checkpoint(db)
        max_existing = int(
            db.scalar(
                select(func.max(ProjectionOutbox.seq))
            )
            or 0
        )
        checkpoint.last_outbox_seq = max(
            int(checkpoint.last_outbox_seq or 0),
            max_seq,
            max_existing,
        )
        checkpoint.updated_at = now

    db.flush()
    return projection_status(db)


def projection_status(db: Session) -> dict:
    checkpoint = db.get(
        ProjectionCheckpoint,
        PROJECTOR_NAME,
    )
    return {
        "contract": PROJECTION_CONTRACT,
        "projector": PROJECTOR_NAME,
        "source_surface_count": int(
            db.scalar(
                select(func.count()).select_from(
                    SourceSurfaceProjection
                )
            )
            or 0
        ),
        "user_attention_count": int(
            db.scalar(
                select(func.count()).select_from(
                    UserAttentionProjection
                )
            )
            or 0
        ),
        "user_source_attention_count": int(
            db.scalar(
                select(func.count()).select_from(
                    UserSourceAttentionProjection
                )
            )
            or 0
        ),
        "pending_outbox": int(
            db.scalar(
                select(func.count())
                .select_from(ProjectionOutbox)
                .where(
                    ProjectionOutbox.processed_at.is_(None)
                )
            )
            or 0
        ),
        "last_outbox_seq": (
            int(checkpoint.last_outbox_seq)
            if checkpoint is not None
            else 0
        ),
    }


def run_projection_worker_forever(
    *,
    idle_sleep_seconds: float = 0.25,
) -> None:
    """Single-process dogfood projector loop.

    Product-scale PostgreSQL deployment may replace this with a claimed
    multi-worker consumer while preserving the same idempotent projection
    contract.
    """

    while True:
        db = SessionLocal()
        processed = 0
        try:
            processed = process_projection_outbox(
                db,
                limit=200,
            )
            db.commit()
        except Exception:
            db.rollback()
            LOGGER.exception(
                "User Space projection worker iteration failed"
            )
        finally:
            db.close()
        time.sleep(
            0.01
            if processed
            else max(0.05, idle_sleep_seconds)
        )
