from __future__ import annotations

import difflib
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.acquisition import InformationSnapshot
from app.models.source import Source
from app.services.event_evidence_frames import event_frame_retrieval_text, latest_event_evidence_frames


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
    frame_by_source = latest_event_evidence_frames(
        db,
        {source.id, *(row.id for row in rows)},
    )
    source_frame = frame_by_source.get(source.id)
    source_frame_text = event_frame_retrieval_text(source_frame, source)[:1600]

    scored = []
    for other in rows:
        if other.id in versioned_ids and other.id not in current_ids:
            continue
        hours = abs((_when(other) - source_time).total_seconds()) / 3600.0
        if hours > max_window_hours:
            continue
        seq, jac = _title_features(source.title, other.title)
        other_frame = frame_by_source.get(other.id)
        frame_seq, frame_jac = 0.0, 0.0
        if source_frame is not None and other_frame is not None:
            other_frame_text = event_frame_retrieval_text(other_frame, other)[:1600]
            frame_seq, frame_jac = _title_features(source_frame_text, other_frame_text)

        title_score = max(seq, jac)
        frame_score = max(frame_seq, frame_jac)
        if title_score <= 0 and frame_score <= 0:
            continue

        time_score = max(0.0, 1.0 - hours / max(max_window_hours, 1.0))
        # Retrieval score only: intentionally broad. A persisted EventEvidenceFrame
        # can improve recall/ranking but can never be interpreted as SAME_EVENT
        # confidence or representation authority.
        if source_frame is not None and other_frame is not None:
            retrieval_score = 0.55 * title_score + 0.27 * frame_score + 0.18 * time_score
            retrieval_method = "source-title+event-frame+time-v0.2"
        else:
            retrieval_score = 0.82 * title_score + 0.18 * time_score
            retrieval_method = "source-title+time-v0.1"
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
                "event_frame_sequence": round(frame_seq, 4),
                "event_frame_bigram_jaccard": round(frame_jac, 4),
                "time_proximity": round(time_score, 4),
            },
            "frame_evidence": {
                "source_frame_id": str(source_frame.id) if source_frame is not None else None,
                "candidate_frame_id": str(other_frame.id) if other_frame is not None else None,
            },
            "retrieval_method": retrieval_method,
            "retrieval_score": round(retrieval_score, 4),
        })

    scored.sort(key=lambda row: (-row["retrieval_score"], row["source_id"]))
    limit = max(1, min(int(limit), 100))
    selected = scored[:limit]
    digest_payload = {
        "source_id": str(source_id),
        "source_frame_id": str(source_frame.id) if source_frame is not None else None,
        "max_window_hours": float(max_window_hours),
        "candidates": [
            {
                "source_id": row["source_id"],
                "candidate_frame_id": row["frame_evidence"]["candidate_frame_id"],
                "retrieval_method": row["retrieval_method"],
                "retrieval_score": row["retrieval_score"],
            }
            for row in selected
        ],
    }
    candidate_set_digest = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "source_id": str(source_id),
        "mode": "SHADOW_CANDIDATE_RETRIEVAL",
        "authority": "NONE",
        "mutates_graph": False,
        "candidate_set_digest": candidate_set_digest,
        "max_window_hours": float(max_window_hours),
        "candidates": selected,
    }


def same_event_frame_candidates(
    db: Session,
    source_id: UUID,
    *,
    source_limit: int = 20,
    max_pairs: int = 100,
    max_window_hours: float = 168.0,
    include_intra_source: bool = True,
) -> dict:
    """Expand high-recall Source candidates into explicit Frame↔Frame candidates.

    This is still retrieval only. It preserves Source-rank and frame-similarity
    as separate signals instead of pretending they are representation truth.
    """
    from itertools import combinations

    from app.services.event_evidence_frames import latest_event_evidence_frames_for_source

    source = db.get(Source, source_id)
    if source is None or source.deleted_at is not None:
        raise ValueError("Source not found")

    source_result = same_event_candidates(
        db,
        source_id,
        limit=source_limit,
        max_window_hours=max_window_hours,
    )
    source_frames = latest_event_evidence_frames_for_source(db, source_id)
    pairs: list[dict] = []

    if include_intra_source and len(source_frames) > 1:
        for frame_a, frame_b in combinations(source_frames, 2):
            text_a = event_frame_retrieval_text(frame_a, source)[:2400]
            text_b = event_frame_retrieval_text(frame_b, source)[:2400]
            seq, jac = _title_features(text_a, text_b)
            pairs.append(
                {
                    "source_id_a": str(source_id),
                    "source_id_b": str(source_id),
                    "frame_id_a": str(frame_a.id),
                    "frame_id_b": str(frame_b.id),
                    "candidate_kind": "INTRA_SOURCE_FRAME_PAIR",
                    "source_rank": -1,
                    "source_retrieval_score": None,
                    "frame_similarity": {
                        "sequence": round(seq, 4),
                        "bigram_jaccard": round(jac, 4),
                    },
                    "frame_summary_a": (frame_a.frame_payload or {}).get("event_summary"),
                    "frame_summary_b": (frame_b.frame_payload or {}).get("event_summary"),
                }
            )

    for rank, candidate in enumerate(source_result["candidates"]):
        candidate_source_id = UUID(candidate["source_id"])
        candidate_source = db.get(Source, candidate_source_id)
        if candidate_source is None:
            continue
        candidate_frames = latest_event_evidence_frames_for_source(db, candidate_source_id)
        if not candidate_frames:
            continue
        for frame_a in source_frames:
            text_a = event_frame_retrieval_text(frame_a, source)[:2400]
            for frame_b in candidate_frames:
                text_b = event_frame_retrieval_text(frame_b, candidate_source)[:2400]
                seq, jac = _title_features(text_a, text_b)
                pairs.append(
                    {
                        "source_id_a": str(source_id),
                        "source_id_b": str(candidate_source_id),
                        "frame_id_a": str(frame_a.id),
                        "frame_id_b": str(frame_b.id),
                        "candidate_kind": "CROSS_SOURCE_FRAME_PAIR",
                        "source_rank": rank,
                        "source_retrieval_score": candidate["retrieval_score"],
                        "frame_similarity": {
                            "sequence": round(seq, 4),
                            "bigram_jaccard": round(jac, 4),
                        },
                        "frame_summary_a": (frame_a.frame_payload or {}).get("event_summary"),
                        "frame_summary_b": (frame_b.frame_payload or {}).get("event_summary"),
                    }
                )

    def _sort_key(row: dict):
        intra = row["candidate_kind"] == "INTRA_SOURCE_FRAME_PAIR"
        sim = max(row["frame_similarity"].values())
        return (0 if intra else 1, int(row["source_rank"]), -sim, row["frame_id_a"], row["frame_id_b"])

    pairs.sort(key=_sort_key)
    max_pairs = max(1, min(int(max_pairs), 500))
    selected = pairs[:max_pairs]
    digest_payload = {
        "source_candidate_set_digest": source_result["candidate_set_digest"],
        "source_id": str(source_id),
        "include_intra_source": bool(include_intra_source),
        "pairs": [
            {
                "frame_id_a": row["frame_id_a"],
                "frame_id_b": row["frame_id_b"],
                "candidate_kind": row["candidate_kind"],
                "source_rank": row["source_rank"],
                "source_retrieval_score": row["source_retrieval_score"],
                "frame_similarity": row["frame_similarity"],
            }
            for row in selected
        ],
    }
    return {
        "source_id": str(source_id),
        "mode": "SHADOW_FRAME_PAIR_CANDIDATE_RETRIEVAL",
        "authority": "NONE",
        "mutates_graph": False,
        "source_candidate_set_digest": source_result["candidate_set_digest"],
        "frame_pair_candidate_set_digest": hashlib.sha256(
            json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "pairs": selected,
    }
