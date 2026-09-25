from __future__ import annotations

import base64
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.source import Source
from app.models.user_space import (
    LOCAL_OWNER_KEY,
    SourceSurfaceProjection,
    UserAttentionProjection,
    UserSourceAttentionProjection,
)
from app.services.user_space_projection import (
    PROJECTION_CONTRACT,
    projection_status,
)


router = APIRouter()


def _iso(value):
    return value.isoformat() if value is not None else None


def _encode_seq_cursor(value: int) -> str:
    raw = str(int(value)).encode("ascii")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_seq_cursor(cursor: str) -> int:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(
            padded.encode("ascii")
        ).decode("ascii")
        value = int(raw)
        if value < 0:
            raise ValueError
        return value
    except Exception as exc:
        raise HTTPException(400, "Invalid cursor") from exc


def _source_card(
    source: SourceSurfaceProjection,
    *,
    disposition: str | None = None,
    event_id=None,
    attention_plan_id=None,
) -> dict:
    metadata = dict(source.presentation_metadata or {})
    return {
        "id": str(source.source_id),
        "source_id": str(source.source_id),
        "title": source.title,
        "publisher": source.publisher,
        "source_type": source.source_type,
        "ingestion_method": source.ingestion_method,
        "origin_label": source.origin_label,
        "canonical_url": source.canonical_url,
        "published_at": _iso(source.published_at),
        "ingested_at": _iso(source.ingested_at),
        "excerpt": source.excerpt,
        "hero_image_url": source.hero_image_url,
        "hero_image_alt": metadata.get("hero_image_alt"),
        "reading_minutes": source.reading_minutes,
        "presentation_metadata": metadata,
        "event_id": (
            str(event_id)
            if event_id is not None
            else (
                str(source.current_event_id)
                if source.current_event_id is not None
                else None
            )
        ),
        "attention_plan_id": (
            str(attention_plan_id)
            if attention_plan_id is not None
            else None
        ),
        "disposition": disposition,
    }


def _inbox_summary(db: Session) -> dict:
    total = int(
        db.scalar(
            select(func.count()).select_from(
                SourceSurfaceProjection
            )
        )
        or 0
    )
    state_counts = {
        "ALL": total,
        "ENGAGE": 0,
        "WATCH": 0,
        "AWARE": 0,
        "DROP": 0,
        "UNANALYZED": 0,
    }
    rows = db.execute(
        select(
            UserSourceAttentionProjection.disposition,
            func.count(),
        )
        .where(
            UserSourceAttentionProjection.owner_key
            == LOCAL_OWNER_KEY
        )
        .group_by(
            UserSourceAttentionProjection.disposition
        )
    ).all()
    projected = 0
    for disposition, count in rows:
        count = int(count)
        if disposition is None:
            continue
        key = str(disposition).upper()
        if key in state_counts:
            state_counts[key] = count
            projected += count
    state_counts["UNANALYZED"] = max(0, total - projected)

    origin_rows = db.execute(
        select(
            SourceSurfaceProjection.origin_label,
            func.count(),
        )
        .group_by(SourceSurfaceProjection.origin_label)
        .order_by(func.count().desc())
        .limit(20)
    ).all()
    return {
        "source_count": total,
        "state_counts": state_counts,
        "origins": [
            {
                "name": str(name or "source"),
                "count": int(count),
            }
            for name, count in origin_rows
        ],
    }


def _attention_counts(db: Session) -> dict:
    counts = {
        "ENGAGE": 0,
        "AWARE": 0,
        "WATCH": 0,
        "DROP": 0,
    }
    rows = db.execute(
        select(
            UserAttentionProjection.disposition,
            func.count(),
        )
        .where(
            UserAttentionProjection.owner_key
            == LOCAL_OWNER_KEY
        )
        .group_by(UserAttentionProjection.disposition)
    ).all()
    for disposition, count in rows:
        key = str(disposition).upper()
        if key in counts:
            counts[key] = int(count)
    counts["CURRENT"] = (
        counts["ENGAGE"]
        + counts["AWARE"]
        + counts["WATCH"]
    )
    counts["ALL"] = sum(
        counts[key]
        for key in ("ENGAGE", "AWARE", "WATCH", "DROP")
    )
    return counts


@router.get("/status")
def status(db: Session = Depends(get_db)):
    return projection_status(db)


@router.get("/inbox")
def inbox(
    limit: int = 30,
    cursor: str | None = None,
    state: str = "ALL",
    origin: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    page_size = max(1, min(int(limit), 100))
    before_seq = (
        _decode_seq_cursor(cursor)
        if cursor
        else None
    )
    wanted_state = str(state or "ALL").upper()
    allowed_states = {
        "ALL",
        "ENGAGE",
        "WATCH",
        "AWARE",
        "DROP",
        "UNANALYZED",
    }
    if wanted_state not in allowed_states:
        raise HTTPException(400, "Invalid state filter")

    stmt = (
        select(
            SourceSurfaceProjection,
            UserSourceAttentionProjection,
        )
        .outerjoin(
            UserSourceAttentionProjection,
            (
                UserSourceAttentionProjection.source_id
                == SourceSurfaceProjection.source_id
            )
            & (
                UserSourceAttentionProjection.owner_key
                == LOCAL_OWNER_KEY
            ),
        )
    )
    if q and q.strip():
        # Search is an explicit user action and may inspect canonical body text.
        # Normal navigation remains projection-only and bounded.
        pattern = f"%{q.strip()}%"
        stmt = stmt.join(
            Source,
            Source.id == SourceSurfaceProjection.source_id,
        ).where(
            or_(
                SourceSurfaceProjection.title.ilike(pattern),
                SourceSurfaceProjection.excerpt.ilike(pattern),
                SourceSurfaceProjection.origin_label.ilike(pattern),
                Source.content_text.ilike(pattern),
            )
        )
    if wanted_state == "UNANALYZED":
        stmt = stmt.where(
            UserSourceAttentionProjection.disposition.is_(None)
        )
    elif wanted_state != "ALL":
        stmt = stmt.where(
            UserSourceAttentionProjection.disposition
            == wanted_state
        )
    if origin and origin != "ALL":
        stmt = stmt.where(
            SourceSurfaceProjection.origin_label == origin
        )
    if before_seq is not None:
        stmt = stmt.where(
            SourceSurfaceProjection.surface_seq < before_seq
        )

    rows = db.execute(
        stmt.order_by(
            SourceSurfaceProjection.surface_seq.desc()
        ).limit(page_size + 1)
    ).all()

    has_more = len(rows) > page_size
    page = rows[:page_size]
    items = [
        _source_card(
            source,
            disposition=bridge.disposition if bridge else None,
            event_id=bridge.event_id if bridge else source.current_event_id,
            attention_plan_id=(
                bridge.attention_plan_id
                if bridge
                else None
            ),
        )
        for source, bridge in page
    ]

    return {
        "contract": "user-space-inbox-v0.3",
        "projection_contract": PROJECTION_CONTRACT,
        "items": items,
        "next_cursor": (
            _encode_seq_cursor(
                page[-1][0].surface_seq
            )
            if has_more and page
            else None
        ),
        "page_size": len(items),
        "summary": _inbox_summary(db),
        "filter": {
            "state": wanted_state,
            "origin": origin or "ALL",
            "q": q or "",
        },
    }


@router.get("/attention")
def attention(
    limit: int = 30,
    disposition: str | None = None,
    cursor: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    page_size = max(1, min(int(limit), 100))
    wanted = disposition.upper() if disposition else None
    if wanted == "CURRENT":
        wanted = None
        exclude_drop = True
    else:
        exclude_drop = False
    if wanted and wanted not in {
        "ENGAGE",
        "AWARE",
        "WATCH",
        "DROP",
    }:
        raise HTTPException(400, "Invalid Attention filter")
    before_seq = (
        _decode_seq_cursor(cursor)
        if cursor
        else None
    )

    stmt = (
        select(
            UserAttentionProjection,
            SourceSurfaceProjection,
        )
        .join(
            SourceSurfaceProjection,
            SourceSurfaceProjection.source_id
            == UserAttentionProjection.representative_source_id,
        )
        .where(
            UserAttentionProjection.owner_key
            == LOCAL_OWNER_KEY
        )
    )
    if exclude_drop:
        stmt = stmt.where(
            UserAttentionProjection.disposition != "DROP"
        )
    elif wanted:
        stmt = stmt.where(
            UserAttentionProjection.disposition == wanted
        )
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                SourceSurfaceProjection.title.ilike(pattern),
                SourceSurfaceProjection.excerpt.ilike(pattern),
                SourceSurfaceProjection.origin_label.ilike(pattern),
                UserAttentionProjection.reason.ilike(pattern),
            )
        )
    if before_seq is not None:
        stmt = stmt.where(
            UserAttentionProjection.attention_seq
            < before_seq
        )

    rows = db.execute(
        stmt.order_by(
            UserAttentionProjection.attention_seq.desc()
        ).limit(page_size + 1)
    ).all()

    has_more = len(rows) > page_size
    page = rows[:page_size]
    items = []
    for plan, source in page:
        card = _source_card(
            source,
            disposition=plan.disposition,
            event_id=plan.event_id,
            attention_plan_id=plan.attention_plan_id,
        )
        card["attention_created_at"] = _iso(
            plan.created_at
        )
        card["reason"] = plan.reason
        card["urgency"] = plan.urgency
        card["cognitive_budget_minutes"] = (
            plan.cognitive_budget_minutes
        )
        items.append(card)

    return {
        "contract": "user-space-attention-v0.3",
        "projection_contract": PROJECTION_CONTRACT,
        "items": items,
        "next_cursor": (
            _encode_seq_cursor(
                page[-1][0].attention_seq
            )
            if has_more and page
            else None
        ),
        "page_size": len(items),
        "counts": _attention_counts(db),
        "filter": wanted or ("CURRENT" if exclude_drop else "ALL"),
        "q": q or "",
    }


def _today_rows(
    db: Session,
    disposition: str,
    limit: int,
):
    if limit <= 0:
        return []
    return db.execute(
        select(
            UserAttentionProjection,
            SourceSurfaceProjection,
        )
        .join(
            SourceSurfaceProjection,
            SourceSurfaceProjection.source_id
            == UserAttentionProjection.representative_source_id,
        )
        .where(
            UserAttentionProjection.owner_key
            == LOCAL_OWNER_KEY,
            UserAttentionProjection.disposition
            == disposition,
        )
        .order_by(
            UserAttentionProjection.attention_seq.desc()
        )
        .limit(limit)
    ).all()


@router.get("/today")
def today(
    limit: int = 7,
    since_ms: int | None = None,
    db: Session = Depends(get_db),
):
    max_items = max(1, min(int(limit), 20))

    engage = _today_rows(
        db,
        "ENGAGE",
        max_items,
    )
    remaining = max_items - len(engage)
    aware = _today_rows(
        db,
        "AWARE",
        remaining,
    )
    rows = engage + aware
    counts = _attention_counts(db)

    items = []
    for plan, source in rows:
        card = _source_card(
            source,
            disposition=plan.disposition,
            event_id=plan.event_id,
            attention_plan_id=plan.attention_plan_id,
        )
        card["attention_created_at"] = _iso(plan.created_at)
        card["reason"] = plan.reason
        card["urgency"] = plan.urgency
        card["cognitive_budget_minutes"] = (
            plan.cognitive_budget_minutes
        )
        items.append(card)

    continuity = None
    if since_ms is not None and since_ms > 0:
        since = datetime.fromtimestamp(
            since_ms / 1000.0,
            tz=timezone.utc,
        )
        observed = int(
            db.scalar(
                select(func.count())
                .select_from(SourceSurfaceProjection)
                .where(
                    SourceSurfaceProjection.ingested_at > since
                )
            )
            or 0
        )
        surfaced = int(
            db.scalar(
                select(func.count())
                .select_from(UserAttentionProjection)
                .where(
                    UserAttentionProjection.owner_key
                    == LOCAL_OWNER_KEY,
                    UserAttentionProjection.created_at > since,
                    UserAttentionProjection.disposition.in_(
                        ["ENGAGE", "AWARE"]
                    ),
                )
            )
            or 0
        )
        continuity = {
            "since_ms": since_ms,
            "observed": observed,
            "surfaced": surfaced,
        }

    return {
        "contract": "user-space-today-v0.3",
        "projection_contract": PROJECTION_CONTRACT,
        "lead": items[0] if items else None,
        "briefs": items[1:],
        "counts": counts,
        "current_attention_count": counts["ALL"],
        "continuity": continuity,
    }
