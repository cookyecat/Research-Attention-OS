from __future__ import annotations

import argparse
import time

from dotenv import load_dotenv


def _is_sqlite_writer_contention(exc: Exception) -> bool:
    from sqlalchemy.exc import OperationalError

    return isinstance(exc, OperationalError) and "database is locked" in str(exc).lower()


def run_once(*, limit_per_source: int = 5, analyze: bool = True) -> list[dict]:
    # Imports are intentionally delayed until after main() loads the selected
    # environment file, so worker cognition uses the same execution contract
    # as the HTTP backend.
    from app.db import SessionLocal
    from app.services.acquisition import poll_due_sources

    db = SessionLocal()
    try:
        # Observation must become durable before model cognition starts.
        # Holding the SQLite writer lock across LLM calls makes unrelated Reader,
        # Delivery and Reprocess traffic fail with `database is locked`. Normal
        # worker analysis therefore persists/delegates first, commits below, and
        # the canonical Cognition Reconciler runs immediately afterwards in main().
        result = poll_due_sources(
            db,
            limit_per_source=limit_per_source,
            analyze=False,
            cognition_defer_reason=("post_commit_cognition" if analyze else "execution_integrity_deferred"),
        )
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="RAOS Acquisition Plane v0.1 source poller")
    parser.add_argument("--interval", type=int, default=60, help="worker wake interval in seconds")
    parser.add_argument("--limit-per-source", type=int, default=5)
    parser.add_argument("--env-file", default=None, help="dotenv file loaded before RAOS runtime imports")
    parser.add_argument("--no-analyze", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=False)
    while True:
        try:
            results = run_once(limit_per_source=args.limit_per_source, analyze=not args.no_analyze)
        except Exception as exc:
            if _is_sqlite_writer_contention(exc):
                results = []
                print({"acquisition": "deferred", "reason": "sqlite-writer-contention"}, flush=True)
            else:
                raise
        if results:
            print(results, flush=True)
        if not args.no_analyze:
            try:
                from app.cognition_reconciler import reconcile_once

                reconciled = reconcile_once(limit=5)
                if reconciled.get("eligible"):
                    print({"cognition_reconciliation": reconciled}, flush=True)
            except RuntimeError as exc:
                # Canonical profile/capability may be intentionally unavailable.
                # Acquisition must continue independently.
                print({"cognition_reconciliation": "deferred", "reason": str(exc)}, flush=True)
            except Exception as exc:
                if _is_sqlite_writer_contention(exc):
                    print({"cognition_reconciliation": "deferred", "reason": "sqlite-writer-contention"}, flush=True)
                else:
                    raise
        if args.once:
            return
        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    main()
