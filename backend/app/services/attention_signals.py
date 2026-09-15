from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.acquisition import AttentionSignalSample, ExternalInformationItem, SourceDefinition
from app.services.acquisition_types import DiscoveredExternalItem

SIGNAL_SENSOR_VERSION = "attention-signal-sensor-v0.1"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _platform(metadata: dict) -> str | None:
    value = metadata.get("platform") or metadata.get("social_platform")
    return str(value).strip().upper() if value else None


def _clean_metrics(value) -> dict[str, float | int]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, float | int] = {}
    for key, raw in value.items():
        if isinstance(raw, bool):
            continue
        if isinstance(raw, (int, float)) and math.isfinite(float(raw)) and raw >= 0:
            out[str(key)] = int(raw) if float(raw).is_integer() else float(raw)
    return dict(sorted(out.items()))


def _signal_hash(platform: str, metrics: dict, age_bucket: str) -> str:
    payload = json.dumps(
        {"platform": platform, "metrics": metrics, "content_age_bucket": age_bucket},
        sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _age_bucket(item: ExternalInformationItem, observed_at: datetime) -> str:
    published = item.published_at
    if published is None:
        return "unknown"
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age = max(0.0, (observed_at - published).total_seconds())
    if age < 3600:
        return "lt_1h"
    if age < 6 * 3600:
        return "1h_6h"
    if age < 24 * 3600:
        return "6h_24h"
    if age < 3 * 86400:
        return "1d_3d"
    if age < 7 * 86400:
        return "3d_7d"
    return "gte_7d"


def record_attention_signal_sample(
    db: Session,
    *,
    source: SourceDefinition,
    item: ExternalInformationItem,
    discovered: DiscoveredExternalItem,
    observed_at: datetime | None = None,
) -> tuple[AttentionSignalSample | None, str]:
    metadata = dict(discovered.metadata or {})
    platform = _platform(metadata)
    metrics = _clean_metrics(metadata.get("engagement"))
    if not platform or not metrics:
        return None, "NO_SIGNAL"
    now = observed_at or _utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    age_bucket = _age_bucket(item, now)
    digest = _signal_hash(platform, metrics, age_bucket)
    latest = db.execute(
        select(AttentionSignalSample)
        .where(
            AttentionSignalSample.source_definition_id == source.id,
            AttentionSignalSample.external_item_id == item.id,
            AttentionSignalSample.platform == platform,
        )
        .order_by(AttentionSignalSample.first_observed_at.desc())
    ).scalars().first()
    if latest is not None and latest.signal_hash == digest:
        latest.last_observed_at = now
        db.flush()
        return latest, "EXTENDED"

    bundle = metadata.get("active_query_bundle") if isinstance(metadata.get("active_query_bundle"), dict) else None
    context = {
        "sensor_version": SIGNAL_SENSOR_VERSION,
        "source_type": source.source_type,
        "content_age_bucket": age_bucket,
        "platform_item_url": metadata.get("platform_item_url"),
        "query_matches": (bundle or {}).get("matches") or [],
    }
    row = AttentionSignalSample(
        source_definition_id=source.id,
        external_item_id=item.id,
        platform=platform,
        first_observed_at=now,
        last_observed_at=now,
        signal_hash=digest,
        metrics=metrics,
        signal_context=context,
        quality="direct",
        contamination=list(metadata.get("contamination") or []),
    )
    db.add(row)
    db.flush()
    return row, "CREATED"
