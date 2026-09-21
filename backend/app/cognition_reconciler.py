from __future__ import annotations

import argparse
from datetime import datetime, timezone

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
        "already_authoritative": 0,
        "reconciled": 0,
        "failed": 0,
        "skipped_unanalyzable": 0,
    }
    with SessionLocal() as db:
        rows = db.execute(
            select(InformationSnapshot).order_by(InformationSnapshot.captured_at.asc())
        ).scalars().all()
        candidates = []
        metadata_changed = False
        for row in rows:
            meta = dict(row.snapshot_metadata or {})
            if not (meta.get("cognition_deferred") and meta.get("cognition_reconcile_eligible")):
                continue

            source = db.get(Source, row.raos_source_id)
            if source is None or not str(source.content_text or "").strip():
                meta["cognition_deferred"] = False
                meta["cognition_reconcile_eligible"] = False
                meta["reconciliation_outcome"] = "skipped_unanalyzable_no_content"
                meta["reconciled_at"] = datetime.now(timezone.utc).isoformat()
                row.snapshot_metadata = meta
                flag_modified(row, "snapshot_metadata")
                counts["skipped_unanalyzable"] += 1
                metadata_changed = True
                continue

            candidates.append(row)
            if len(candidates) >= max(1, int(limit)):
                break
        if metadata_changed:
            db.commit()
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
