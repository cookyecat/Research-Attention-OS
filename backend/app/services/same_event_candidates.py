from __future__ import annotations

import difflib
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.acquisition import InformationSnapshot
from app.models.source import Source


def _normalize_title(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "").lower()
    text = re.sub(r"https?://\S+", " ", text)
    return re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE)


def _char_ngrams(value: str | None, n: int = 2) -> set[str]:
    text = _normalize_title(value)
    if not text:
        return set()
    if len(text) < n:
        return {text}
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def _title_features(a: str | None, b: str | None) -> tuple[float, float]:
    na, nb = _normalize_title(a), _normalize_title(b)
    if not na or not nb:
        return 0.0, 0.0
    seq = difflib.SequenceMatcher(None, na, nb).ratio()
    ga, gb = _char_ngrams(na), _char_ngrams(nb)
    jac = len(ga & gb) / max(1, len(ga | gb))
    return float(seq), float(jac)


def _current_source_ids(db: Session) -> tuple[set[UUID], set[UUID]]:
    snapshots = db.execute(
        select(InformationSnapshot).order_by(InformationSnapshot.captured_at.desc())
    ).scalars().all()
    versioned = {snapshot.raos_source_id for snapshot in snapshots}
    current: set[UUID] = set()
    seen_items: set[UUID] = set()
    for snapshot in snapshots:
        if snapshot.external_item_id in seen_items:
            continue
        seen_items.add(snapshot.external_item_id)
        current.add(snapshot.raos_source_id)
    return versioned, current


def _when(source: Source) -> datetime:
    value = source.published_at or source.ingested_at
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _host(source: Source) -> str | None:
    try:
        return (urlparse(source.canonical_url or "").hostname or "").lower() or None
    except Exception:
        return None


def same_event_candidates(
    db: Session,
    source_id: UUID,
    *,
    limit: int = 20,
    max_window_hours: float = 168.0,
) -> dict:
    """High-recall, non-authoritative candidate retrieval for later adjudication.

    This function never mutates Event, EventSource, or SourceEdge.
    """
    source = db.get(Source, source_id)
    if source is None or source.deleted_at is not None:
        raise ValueError("Source not found")

    versioned_ids, current_ids = _current_source_ids(db)
    source_time = _when(source)
    rows = db.execute(
        select(Source).where(Source.id != source_id, Source.deleted_at.is_(None))
    ).scalars().all()

    scored = []
    for other in rows:
        if other.id in versioned_ids and other.id not in current_ids:
            continue
        hours = abs((_when(other) - source_time).total_seconds()) / 3600.0
        if hours > max_window_hours:
            continue
        seq, jac = _title_features(source.title, other.title)
        if seq <= 0 and jac <= 0:
            continue

        title_score = max(seq, jac)
        time_score = max(0.0, 1.0 - hours / max(max_window_hours, 1.0))
        # Retrieval score only: intentionally broad. It must never be interpreted
        # as same-event confidence.
        retrieval_score = 0.82 * title_score + 0.18 * time_score
        scored.append({
            "source_id": str(other.id),
            "title": other.title,
            "publisher": other.publisher,
            "canonical_url": other.canonical_url,
            "host": _host(other),
            "published_at": other.published_at.isoformat() if other.published_at else None,
            "time_distance_hours": round(hours, 2),
            "features": {
                "title_sequence": round(seq, 4),
                "title_bigram_jaccard": round(jac, 4),
                "time_proximity": round(time_score, 4),
            },
            "retrieval_score": round(retrieval_score, 4),
        })

    scored.sort(key=lambda row: (-row["retrieval_score"], row["source_id"]))
    limit = max(1, min(int(limit), 100))
    return {
        "source_id": str(source_id),
        "mode": "SHADOW_CANDIDATE_RETRIEVAL",
        "authority": "NONE",
        "mutates_graph": False,
        "max_window_hours": float(max_window_hours),
        "candidates": scored[:limit],
    }
