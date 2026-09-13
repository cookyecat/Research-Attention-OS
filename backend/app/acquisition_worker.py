from __future__ import annotations

import argparse
import time

from dotenv import load_dotenv


def run_once(*, limit_per_source: int = 5, analyze: bool = True) -> list[dict]:
    # Imports are intentionally delayed until after main() loads the selected
    # environment file, so worker cognition uses the same execution contract
    # as the HTTP backend.
    from app.db import SessionLocal
    from app.services.acquisition import poll_due_sources

    db = SessionLocal()
    try:
        result = poll_due_sources(db, limit_per_source=limit_per_source, analyze=analyze)
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
        results = run_once(limit_per_source=args.limit_per_source, analyze=not args.no_analyze)
        if results:
            print(results, flush=True)
        if args.once:
            return
        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    main()
