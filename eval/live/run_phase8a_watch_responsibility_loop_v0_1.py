from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
import app.services.pipeline as pipeline_mod
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.db import Base
from app.enums import Disposition, ExpectedOutput
from app.models.analysis import AnalysisRun
from app.models.source import Source
from app.models.watch import Watch, WatchCheck, WatchTrigger
from app.services.scheduler import PlanDraft, validate_plan
from app.services.watch_loop import recheck_watch

ARTIFACT_ID = "raos-phase8a-watch-responsibility-loop-v0.1"
OUTDIR = ROOT / "eval/live/results/phase8a_watch_responsibility_loop_v0_1"


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _source(db: Session, title: str, text: str, n: int) -> Source:
    row = Source(
        source_type="TEXT",
        title=title,
        content_text=text,
        fingerprint=f"phase8a-{n}",
        content_hash=f"phase8a-hash-{n}",
        ingestion_method="CONTROLLED_SIMULATION",
        raw_metadata={"phase": "8A", "simulated": True},
    )
    db.add(row); db.flush()
    return row

def _watch_route(*_a, **_k):
    return validate_plan(
        PlanDraft(
            disposition=Disposition.WATCH,
            expected_output=ExpectedOutput.WATCH,
            reason="controlled evidence still insufficient; keep watching",
            watch_after_processing=True,
            watch_triggers=["NEW_EVIDENCE"],
            cognitive_budget_minutes=2,
        )
    )


def _aware_route(*_a, **_k):
    return validate_plan(
        PlanDraft(
            disposition=Disposition.AWARE,
            expected_output=ExpectedOutput.SUMMARY,
            reason="controlled cumulative evidence is now worth surfacing",
            cognitive_budget_minutes=2,
        )
    )

def main() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    provider = RuleBasedCognitiveProvider()
    original_route = pipeline_mod.route

    with Session(engine) as db:
        a = _source(db, "Initial watch evidence", "Initial evidence is interesting but not decisive.", 1)
        b = _source(db, "Second evidence", "A second independent report strengthens the same issue.", 2)
        c = _source(db, "Third evidence", "A third report makes the issue worth surfacing now.", 3)

        initial = pipeline_mod.run_pipeline(db, a.id, provider=provider)
        initial_run_id = initial["analysis_run"]["id"]
        watch = Watch(
            target_type="SOURCE",
            target_ref="phase8a-controlled",
            status="ACTIVE",
            created_reason="Phase 8A controlled future-attention obligation",
            kernel_target_ids=[],
            analysis_run_id=UUID(initial_run_id),
        )
        db.add(watch); db.flush()
        trigger = WatchTrigger(
            watch_id=watch.id,
            trigger_type="NEW_EVIDENCE",
            trigger_config={},
        )
        db.add(trigger); db.flush()
        watch_count_before = db.scalar(select(func.count()).select_from(Watch))

        pipeline_mod.route = _watch_route
        first_check, first_result = recheck_watch(
            db, watch=watch, trigger=trigger, new_source_id=b.id
        )
        first_run = db.get(AnalysisRun, first_check.analysis_run_id)

        pipeline_mod.route = _aware_route
        second_check, second_result = recheck_watch(
            db, watch=watch, trigger=trigger, new_source_id=c.id
        )
        second_run = db.get(AnalysisRun, second_check.analysis_run_id)
        pipeline_mod.route = original_route
        checks = db.execute(
            select(WatchCheck).where(WatchCheck.watch_id == watch.id).order_by(WatchCheck.checked_at)
        ).scalars().all()
        watch_count_after = db.scalar(select(func.count()).select_from(Watch))

        first_extra = [str(x) for x in (first_run.extra_source_ids or [])]
        second_extra = [str(x) for x in (second_run.extra_source_ids or [])]
        conditions = {
            "first_keep_active": first_check.outcome == "KEEP_ACTIVE" and first_check.disposition == "WATCH",
            "second_promoted": second_check.outcome == "PROMOTED" and second_check.disposition == "AWARE",
            "first_includes_B": str(b.id) in first_extra,
            "second_includes_B_and_C": str(b.id) in second_extra and str(c.id) in second_extra,
            "two_watch_checks": len(checks) == 2,
            "no_duplicate_watch": watch_count_after == watch_count_before == 1,
            "final_watch_promoted": watch.status == "PROMOTED",
            "watch_creation_suppressed": bool(
                first_result["attention_plan"]["score_debug"]["authorized_artifacts"]["watch_creation_suppressed"]
            ),
        }
        artifact = {
            "artifact_id": ARTIFACT_ID,
            "measurement_git_head": git_head(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "evidence_type": "CONTROLLED_DEVELOPMENT_SIMULATION",
            "sources": {"A": str(a.id), "B": str(b.id), "C": str(c.id)},
            "initial_analysis_run_id": str(initial_run_id),
            "first_recheck": {
                "outcome": first_check.outcome,
                "disposition": first_check.disposition,
                "analysis_run_id": str(first_check.analysis_run_id),
                "cumulative_extra_source_ids": first_extra,
            },
            "second_recheck": {
                "outcome": second_check.outcome,
                "disposition": second_check.disposition,
                "analysis_run_id": str(second_check.analysis_run_id),
                "cumulative_extra_source_ids": second_extra,
            },
            "watch_check_outcomes": [x.outcome for x in checks],
            "conditions": conditions,
            "all_conditions_pass": all(conditions.values()),
        }
        OUTDIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = OUTDIR / f"phase8a_watch_responsibility_loop_v0_1_{stamp}.json"
        out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
        print(f"wrote {out}")
        print(json.dumps(artifact, ensure_ascii=False, indent=2))
        if not artifact["all_conditions_pass"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
