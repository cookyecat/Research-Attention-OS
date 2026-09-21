from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.db import SessionLocal
from app.execution_integrity import require_side_effects_authorized
from app.services.event_attention_migration import migrate_safe_source_attention_plans

OUT_DIR = ROOT / "eval/live/results/phase16_event_attention_identity_migration_v0_2"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.apply:
        require_side_effects_authorized()

    with SessionLocal() as db:
        report = migrate_safe_source_attention_plans(db, apply=args.apply)
        if args.apply:
            db.commit()
        else:
            db.rollback()

    report["ran_at"] = datetime.now(timezone.utc).isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "apply" if args.apply else "dry_run"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"phase16_event_attention_identity_migration_v0_2_{suffix}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    for key in (
        "source_plan_candidates",
        "eligible_safe_single_member",
        "already_event_migrated",
        "needs_new_source_local_event",
        "skipped_missing_source",
        "skipped_no_safe_event",
        "created_event_plans",
    ):
        print(key, report[key])


if __name__ == "__main__":
    main()
