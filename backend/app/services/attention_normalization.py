from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.acquisition import AttentionSignalSample

NORMALIZER_VERSION = "attention-signal-magnitude-free-v0.1"


@dataclass(frozen=True)
class MagnitudeFreeObservation:
    status: str
    platform: str
    metric: str
    raw_value: float | int
    age_bucket: str
    percentile: float | None
    support_n: int
    version: str = NORMALIZER_VERSION

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "platform": self.platform,
            "metric": self.metric,
            "raw_value": self.raw_value,
            "age_bucket": self.age_bucket,
            "percentile": self.percentile,
            "support_n": self.support_n,
            "version": self.version,
        }


def magnitude_free_observation(
    db: Session,
    sample: AttentionSignalSample,
    metric: str,
    *,
    min_support: int = 20,
    reference_limit: int = 2000,
) -> MagnitudeFreeObservation:
    if metric not in (sample.metrics or {}):
        raise ValueError(f"Metric {metric!r} not present in signal sample")
    raw = sample.metrics[metric]
    age_bucket = str((sample.signal_context or {}).get("content_age_bucket") or "unknown")
    # Cross-sectional, bounded reference scan. Select the latest state per
    # external item first, so an item that changed many times does not receive
    # extra weight in the reference distribution.
    latest_ts = (
        select(
            AttentionSignalSample.external_item_id.label("external_item_id"),
            func.max(AttentionSignalSample.first_observed_at).label("max_first_observed_at"),
        )
        .where(AttentionSignalSample.platform == sample.platform)
        .group_by(AttentionSignalSample.external_item_id)
        .subquery()
    )
    rows = db.execute(
        select(AttentionSignalSample)
        .join(
            latest_ts,
            and_(
                AttentionSignalSample.external_item_id == latest_ts.c.external_item_id,
                AttentionSignalSample.first_observed_at == latest_ts.c.max_first_observed_at,
            ),
        )
        .where(
            AttentionSignalSample.platform == sample.platform,
            AttentionSignalSample.external_item_id != sample.external_item_id,
        )
        .order_by(AttentionSignalSample.first_observed_at.desc())
        .limit(max(int(reference_limit), int(min_support)))
    ).scalars().all()

    values: list[float] = []
    for row in rows:
        if str((row.signal_context or {}).get("content_age_bucket") or "unknown") != age_bucket:
            continue
        value = (row.metrics or {}).get(metric)
        if isinstance(value, (int, float)):
            values.append(float(value))
    n = len(values)
    if n < min_support:
        return MagnitudeFreeObservation(
            status="INSUFFICIENT_SUPPORT",
            platform=sample.platform,
            metric=metric,
            raw_value=raw,
            age_bucket=age_bucket,
            percentile=None,
            support_n=n,
        )
    x = float(raw)
    less = sum(value < x for value in values)
    equal = sum(value == x for value in values)
    percentile = (less + 0.5 * equal) / n
    return MagnitudeFreeObservation(
        status="OK",
        platform=sample.platform,
        metric=metric,
        raw_value=raw,
        age_bucket=age_bucket,
        percentile=round(percentile, 6),
        support_n=n,
    )
