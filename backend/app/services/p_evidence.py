from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.acquisition import AttentionSignalSample, InformationSnapshot
from app.models.event import Event, EventSource
from app.services.attention_normalization import magnitude_free_observation

P_EVIDENCE_BUILDER_VERSION = "p-evidence-builder-v0.1"


def _quality(metric: str) -> str:
    if metric in {"views"}:
        return "weak"
    return "direct"


def _kind(metric: str) -> str:
    if metric in {"comments", "replies"}:
        return "human_discussion"
    if metric in {"views"}:
        return "meaningful_view_or_read"
    return "engagement"


def _latest_samples_for_event(db: Session, event_id: UUID) -> list[AttentionSignalSample]:
    source_ids = db.execute(select(EventSource.source_id).where(EventSource.event_id == event_id)).scalars().all()
    if not source_ids:
        return []
    external_ids = db.execute(
        select(InformationSnapshot.external_item_id).where(InformationSnapshot.raos_source_id.in_(source_ids))
    ).scalars().all()
    latest: dict[tuple[str, str], AttentionSignalSample] = {}
    for external_id in set(external_ids):
        rows = db.execute(
            select(AttentionSignalSample)
            .where(AttentionSignalSample.external_item_id == external_id)
            .order_by(AttentionSignalSample.first_observed_at.desc())
        ).scalars().all()
        for row in rows:
            key = (str(row.external_item_id), row.platform)
            if key not in latest:
                latest[key] = row
    return list(latest.values())


def _recent_history_for_event(db: Session, event_id: UUID, *, per_item_limit: int = 4) -> list[dict]:
    source_ids = db.execute(select(EventSource.source_id).where(EventSource.event_id == event_id)).scalars().all()
    if not source_ids:
        return []
    external_ids = set(db.execute(
        select(InformationSnapshot.external_item_id).where(InformationSnapshot.raos_source_id.in_(source_ids))
    ).scalars().all())
    history: list[dict] = []
    for external_id in external_ids:
        rows = db.execute(
            select(AttentionSignalSample)
            .where(AttentionSignalSample.external_item_id == external_id)
            .order_by(AttentionSignalSample.first_observed_at.desc())
            .limit(max(2, int(per_item_limit)))
        ).scalars().all()
        by_platform: dict[str, list[AttentionSignalSample]] = {}
        for row in rows:
            by_platform.setdefault(row.platform, []).append(row)
        for platform, states in by_platform.items():
            latest = states[0]
            if latest.last_observed_at > latest.first_observed_at:
                duration_s = max(0.0, (latest.last_observed_at - latest.first_observed_at).total_seconds())
                history.append({
                    "window": f"{latest.first_observed_at.isoformat()} to {latest.last_observed_at.isoformat()}",
                    "observation": f"{platform} signal state persisted unchanged for {duration_s / 3600:.2f}h: {latest.metrics}",
                    "source": f"{platform} public telemetry history",
                })
            if len(states) < 2:
                continue
            previous = states[1]
            shared = sorted(set((latest.metrics or {})) & set((previous.metrics or {})))
            changes: list[str] = []
            for metric in shared:
                before = (previous.metrics or {}).get(metric)
                after = (latest.metrics or {}).get(metric)
                if isinstance(before, (int, float)) and isinstance(after, (int, float)):
                    delta = float(after) - float(before)
                    changes.append(f"{metric} {before}→{after} (Δ={delta:+g})")
            if changes:
                history.append({
                    "window": f"{previous.last_observed_at.isoformat()} to {latest.first_observed_at.isoformat()}",
                    "observation": f"{platform} attention signal changed: " + "; ".join(changes),
                    "source": f"{platform} public telemetry history",
                })
    return history[:100]


def build_event_p_evidence_packet(
    db: Session,
    event_id: UUID,
    *,
    as_of: datetime | None = None,
    min_normalization_support: int = 20,
) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise ValueError("Event not found")
    now = as_of or datetime.now(timezone.utc)
    samples = _latest_samples_for_event(db, event_id)
    evidence: list[dict] = []
    platforms: set[str] = set()
    for sample in samples:
        platforms.add(sample.platform)
        for metric, raw in (sample.metrics or {}).items():
            norm = magnitude_free_observation(
                db, sample, metric, min_support=min_normalization_support
            )
            normalized = (
                f"; platform/age percentile={norm.percentile:.3f} (n={norm.support_n})"
                if norm.status == "OK" and norm.percentile is not None
                else f"; normalization=UNKNOWN (support n={norm.support_n})"
            )
            evidence.append({
                "kind": _kind(metric),
                "window": f"observed {sample.first_observed_at.isoformat()} to {sample.last_observed_at.isoformat()}",
                "observation": f"{sample.platform} {metric}={raw}{normalized}",
                "source": f"{sample.platform} public telemetry",
                "observed_at": sample.last_observed_at.isoformat(),
                "independence_group": f"{sample.platform}:{sample.external_item_id}",
                "quality": _quality(metric),
                "contamination": list(sample.contamination or []),
            })
    if len(platforms) >= 2:
        evidence.append({
            "kind": "cross_platform_spread",
            "window": "current observed state",
            "observation": f"Event-linked sources carry measurable attention signals on {len(platforms)} platforms: {', '.join(sorted(platforms))}",
            "source": "RAOS event projection",
            "observed_at": now.isoformat(),
            "independence_group": f"event:{event.id}:cross-platform",
            "quality": "structural",
            "contamination": [],
        })
    return {
        "event": {
            "event_id": str(event.id),
            "as_of": now.isoformat(),
            "semantic_summary": event.summary or event.title,
        },
        "constituency_prior": {
            "description": "Objective constituency not yet externally grounded; infer only from event semantics.",
            "scope": "other",
            "reference_scale": "unknown",
            "reference_size_hint": "unknown",
            "basis": "unknown",
            "provenance": f"{P_EVIDENCE_BUILDER_VERSION}: no constituency prior supplied",
        },
        "collection_context": {
            "channels_checked": sorted(platforms),
            "channels_unavailable": [],
            "notes": f"Built from {len(samples)} latest event-linked platform signal sample(s). UNKNOWN normalization support is not zero evidence.",
        },
        "current_attention_evidence": evidence,
        "recent_attention_history": _recent_history_for_event(db, event_id),
    }
