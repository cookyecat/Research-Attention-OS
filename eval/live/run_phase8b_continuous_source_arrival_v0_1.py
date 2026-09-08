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
from app.enums import Disposition, ExpectedOutput, SourceEdgeRelationship
from app.models.analysis import AnalysisRun
from app.models.event import EventSource
from app.models.watch import Watch, WatchCheck, WatchTrigger
from app.services.continuous_attention import process_source_arrival
from app.services.ingestion import ingest_text
from app.services.scheduler import PlanDraft, validate_plan
from app.services.source_graph import persist_source_edge

ARTIFACT_ID = "raos-phase8b-continuous-source-arrival-v0.1"
OUTDIR = ROOT / "eval/live/results/phase8b_continuous_source_arrival_v0_1"

def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _watch_route(features, *_args, **_kwargs):
    if features.independent_source_count >= 2:
        return validate_plan(
            PlanDraft(
                disposition=Disposition.AWARE,
                expected_output=ExpectedOutput.SUMMARY,
                reason="controlled independent evidence reached surfacing threshold",
                cognitive_budget_minutes=2,
            )
        )
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


def _drop_route(*_args, **_kwargs):
    return validate_plan(
        PlanDraft(
            disposition=Disposition.DROP,
            expected_output=ExpectedOutput.NONE,
            reason="controlled unrelated ordinary source",
            cognitive_budget_minutes=0,
        )
    )

def _make_watch(db: Session, initial_result: dict) -> Watch:
    run = db.get(AnalysisRun, UUID(initial_result["analysis_run"]["id"]))
    watch = Watch(
        target_type="SOURCE",
        target_ref="phase8b-controlled",
        status="ACTIVE",
        created_reason="Phase 8B controlled continuous-arrival obligation",
        kernel_target_ids=[],
        analysis_run_id=run.id,
    )
    db.add(watch); db.flush()
    db.add(WatchTrigger(watch_id=watch.id, trigger_type="NEW_EVIDENCE", trigger_config={}))
    db.flush()
    return watch


def _check_for_source(db: Session, watch: Watch, source_id: UUID) -> WatchCheck:
    check = db.execute(
        select(WatchCheck).where(
            WatchCheck.watch_id == watch.id,
            WatchCheck.new_source_id == source_id,
        ).order_by(WatchCheck.checked_at.desc())
    ).scalars().first()
    if check is None:
        raise RuntimeError(f"missing WatchCheck for {source_id}")
    return check


def _relational(db: Session, check: WatchCheck) -> dict:
    run = db.get(AnalysisRun, check.analysis_run_id) if check.analysis_run_id else None
    if run is None:
        return {}
    return ((run.result_payload or {}).get("relational_context") or {}).get("independence") or {}

def main() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    provider = RuleBasedCognitiveProvider()
    original_route = pipeline_mod.route

    with Session(engine) as db:
        a_text = "Original evidence about a developing research result with one source."
        a = ingest_text(db, a_text, title="phase8b-A")
        initial = pipeline_mod.run_pipeline(db, a.id, provider=provider)
        watch = _make_watch(db, initial)
        initial_watch_count = db.scalar(select(func.count()).select_from(Watch))

        pipeline_mod.route = _watch_route

        b = ingest_text(db, a_text, title="phase8b-B-repost")
        b_result = process_source_arrival(db, b.id, provider=provider)
        b_check = _check_for_source(db, watch, b.id)

        c = ingest_text(
            db,
            "A secondary report repeats the result and adds commentary without independent verification.",
            title="phase8b-C-secondary",
        )
        persist_source_edge(db, c.id, a.id, SourceEdgeRelationship.REPORTS_ON)
        c_result = process_source_arrival(db, c.id, provider=provider)
        c_check = _check_for_source(db, watch, c.id)
        c_rel = _relational(db, c_check)

        # Unrelated source must not be injected into the existing Watch.
        x = ingest_text(db, "An unrelated cooking note about bread hydration.", title="phase8b-X-unrelated")
        pipeline_mod.route = _drop_route
        x_result = process_source_arrival(db, x.id, provider=provider)
        pipeline_mod.route = _watch_route

        # D is independent evidence attached to the same Event as A.
        a_event = db.execute(
            select(EventSource).where(EventSource.source_id == a.id)
        ).scalars().first()
        if a_event is None:
            raise RuntimeError("initial source was not attached to an Event")
        d = ingest_text(
            db,
            "An independent replication confirms the developing result with separate measurements.",
            title="phase8b-D-independent",
        )
        db.add(EventSource(event_id=a_event.event_id, source_id=d.id, relationship="REPORTS", confidence=0.9))
        db.flush()
        d_result = process_source_arrival(db, d.id, provider=provider)
        d_check = _check_for_source(db, watch, d.id)
        d_rel = _relational(db, d_check)

        pipeline_mod.route = original_route
        checks = db.execute(
            select(WatchCheck).where(WatchCheck.watch_id == watch.id).order_by(WatchCheck.checked_at)
        ).scalars().all()
        final_watch_count = db.scalar(select(func.count()).select_from(Watch))

        conditions = {
            "repost_suppressed": b_result["watch_decisions"][0]["outcome"] == "DUPLICATE_SUPPRESSED",
            "repost_no_analysis": b_check.analysis_run_id is None,
            "secondary_rechecked": c_result["watch_decisions"][0]["evidence_class"] == "SECONDARY",
            "secondary_kept_active": c_check.outcome == "KEEP_ACTIVE" and c_check.disposition == "WATCH",
            "secondary_not_independent": c_rel.get("independent_sources") == 1,
            "secondary_counted_as_secondary": c_rel.get("secondary_reports") == 1,
            "unrelated_ordinary_route": (not x_result["matched_watch"]) and x_result["ordinary_analysis"] is not None,
            "independent_promoted": d_result["watch_decisions"][0]["evidence_class"] == "INDEPENDENT" and d_check.outcome == "PROMOTED",
            "independent_count_incremented": d_rel.get("independent_sources") == 2,
            "secondary_count_preserved": d_rel.get("secondary_reports") == 1,
            "single_watch_obligation": initial_watch_count == final_watch_count == 1,
            "watch_history_complete": [check.outcome for check in checks] == [
                "DUPLICATE_SUPPRESSED", "KEEP_ACTIVE", "PROMOTED"
            ],
            "final_watch_promoted": watch.status == "PROMOTED",
        }

        artifact = {
            "artifact_id": ARTIFACT_ID,
            "measurement_git_head": git_head(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "evidence_type": "CONTROLLED_DEVELOPMENT_SIMULATION",
            "sources": {"A": str(a.id), "B": str(b.id), "C": str(c.id), "D": str(d.id), "X": str(x.id)},
            "decisions": {
                "B_repost": b_result["watch_decisions"],
                "C_secondary": c_result["watch_decisions"],
                "X_unrelated": {"matched_watch": x_result["matched_watch"], "ordinary_analysis": bool(x_result["ordinary_analysis"])},
                "D_independent": d_result["watch_decisions"],
            },
            "relational_context": {"C_secondary": c_rel, "D_independent": d_rel},
            "watch_check_outcomes": [check.outcome for check in checks],
            "conditions": conditions,
            "all_conditions_pass": all(conditions.values()),
        }
        OUTDIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = OUTDIR / f"phase8b_continuous_source_arrival_v0_1_{stamp}.json"
        out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
        print(f"wrote {out}")
        print(json.dumps(artifact, ensure_ascii=False, indent=2))
        if not artifact["all_conditions_pass"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
