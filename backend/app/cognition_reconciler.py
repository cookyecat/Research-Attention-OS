from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv


def _authoritative_completed_run(db, source_id):
    from sqlalchemy import select
    from app.models.analysis import AnalysisRun

    rows = db.execute(
        select(AnalysisRun)
        .where(AnalysisRun.source_id == source_id, AnalysisRun.status == "COMPLETED")
        .order_by(AnalysisRun.completed_at.desc(), AnalysisRun.created_at.desc())
    ).scalars().all()
    for row in rows:
        payload = row.result_payload if isinstance(row.result_payload, dict) else {}
        authority = payload.get("execution_authority") if isinstance(payload, dict) else None
        if isinstance(authority, dict) and ((authority.get("authority") or {}).get("attention_authorized") is True):
            return row
    return None


def _retry_delay(failure_count: int) -> timedelta:
    """Bound repeated cognition retries so one poison pill cannot burn every loop."""
    minutes = min(60, 2 ** max(1, min(int(failure_count), 6)))
    return timedelta(minutes=minutes)


def _parse_iso(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def reconcile_once(*, limit: int = 20) -> dict:
    from sqlalchemy import select
    from sqlalchemy.orm.attributes import flag_modified

    from app.db import SessionLocal
    from app.execution_integrity import health_contract
    from app.models.acquisition import InformationSnapshot
    from app.models.source import Source
    from app.services.pipeline import run_pipeline

    health = health_contract()
    if not health["attestation"].get("enforced"):
        raise RuntimeError("Cognition reconciliation requires an explicit canonical runtime profile")
    if health["capabilities"].get("cognition") != "READY":
        raise RuntimeError("Canonical cognition is not ready; reconciliation deferred")

    counts = {
        "eligible": 0,
        "fresh_selected": 0,
        "retry_selected": 0,
        "retry_backoff": 0,
        "already_authoritative": 0,
        "reconciled": 0,
        "failed": 0,
        "skipped_unanalyzable": 0,
    }
    with SessionLocal() as db:
        rows = db.execute(
            select(InformationSnapshot).order_by(
                InformationSnapshot.captured_at.asc()
            )
        ).scalars().all()
        fresh_candidates = []
        retry_candidates = []
        metadata_changed = False
        now = datetime.now(timezone.utc)

        for row in rows:
            meta = dict(row.snapshot_metadata or {})
            if not (
                meta.get("cognition_deferred")
                and meta.get("cognition_reconcile_eligible")
            ):
                continue

            source = db.get(Source, row.raos_source_id)
            content_scope = str(
                ((source.raw_metadata or {}) if source is not None else {})
                .get("content_scope")
                or ""
            ).upper()
            if content_scope == "METADATA_ONLY":
                meta["cognition_deferred"] = False
                meta["cognition_reconcile_eligible"] = False
                meta["reconciliation_outcome"] = (
                    "skipped_unanalyzable_metadata_only"
                )
                meta["reconciled_at"] = now.isoformat()
                row.snapshot_metadata = meta
                flag_modified(row, "snapshot_metadata")
                counts["skipped_unanalyzable"] += 1
                metadata_changed = True
                continue

            if source is None or not str(source.content_text or "").strip():
                meta["cognition_deferred"] = False
                meta["cognition_reconcile_eligible"] = False
                meta["reconciliation_outcome"] = (
                    "skipped_unanalyzable_no_content"
                )
                meta["reconciled_at"] = now.isoformat()
                row.snapshot_metadata = meta
                flag_modified(row, "snapshot_metadata")
                counts["skipped_unanalyzable"] += 1
                metadata_changed = True
                continue

            last_attempt = _parse_iso(
                meta.get("last_reconciliation_attempt_at")
            )
            if last_attempt is None:
                fresh_candidates.append(row)
                continue

            failure_count = max(
                1,
                int(meta.get("reconciliation_failure_count") or 1),
            )
            next_after = _parse_iso(
                meta.get("next_reconciliation_after")
            ) or (last_attempt + _retry_delay(failure_count))
            if now >= next_after:
                retry_candidates.append((last_attempt, row))
            else:
                counts["retry_backoff"] += 1

        if metadata_changed:
            db.commit()

        max_candidates = max(1, int(limit))
        candidates = fresh_candidates[:max_candidates]
        counts["fresh_selected"] = len(candidates)
        if len(candidates) < max_candidates:
            retry_candidates.sort(key=lambda item: item[0])
            retry_rows = [
                row
                for _, row in retry_candidates[
                    : max_candidates - len(candidates)
                ]
            ]
            candidates.extend(retry_rows)
            counts["retry_selected"] = len(retry_rows)
        counts["eligible"] = len(candidates)

        for snapshot in candidates:
            if _authoritative_completed_run(db, snapshot.raos_source_id) is not None:
                counts["already_authoritative"] += 1
                meta = dict(snapshot.snapshot_metadata or {})
                meta["cognition_deferred"] = False
                meta["cognition_reconcile_eligible"] = False
                meta["reconciliation_outcome"] = "already_authoritative"
                snapshot.snapshot_metadata = meta
                flag_modified(snapshot, "snapshot_metadata")
                db.commit()
                continue
            try:
                result = run_pipeline(db, snapshot.raos_source_id)
                authority = result.get("execution_authority") if isinstance(result, dict) else None
                if not isinstance(authority, dict) or not ((authority.get("authority") or {}).get("attention_authorized")):
                    raise RuntimeError("reconciliation produced a non-authoritative result")
                meta = dict(snapshot.snapshot_metadata or {})
                meta["cognition_deferred"] = False
                meta["cognition_reconcile_eligible"] = False
                meta["reconciled_at"] = datetime.now(timezone.utc).isoformat()
                meta["reconciliation_outcome"] = "authoritative_cognition_completed"
                meta.pop("last_reconciliation_error", None)
                meta.pop("last_reconciliation_attempt_at", None)
                meta.pop("reconciliation_failure_count", None)
                meta.pop("next_reconciliation_after", None)
                snapshot.snapshot_metadata = meta
                flag_modified(snapshot, "snapshot_metadata")
                counts["reconciled"] += 1
                db.commit()
            except Exception as exc:
                counts["failed"] += 1
                meta = dict(snapshot.snapshot_metadata or {})
                meta["last_reconciliation_error"] = f"{type(exc).__name__}: {exc}"[:1000]
                meta["last_reconciliation_attempt_at"] = datetime.now(timezone.utc).isoformat()
                db.rollback()
                snapshot = db.get(InformationSnapshot, snapshot.id)
                if snapshot is not None:
                    meta = dict(snapshot.snapshot_metadata or {})
                    meta["last_reconciliation_error"] = f"{type(exc).__name__}: {exc}"[:1000]
                    meta["last_reconciliation_attempt_at"] = datetime.now(timezone.utc).isoformat()
                    snapshot.snapshot_metadata = meta
                    flag_modified(snapshot, "snapshot_metadata")
                    db.commit()
                continue
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="RAOS deferred-cognition reconciler")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=False)
    print(reconcile_once(limit=args.limit), flush=True)


if __name__ == "__main__":
    main()
