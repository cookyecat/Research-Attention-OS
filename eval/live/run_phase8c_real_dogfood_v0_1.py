import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import UUID

import yaml

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
from app.enums import Disposition, EventStatus, ExpectedOutput, SourceEdgeRelationship
from app.models.analysis import AnalysisRun
from app.models.event import Event, EventSource
from app.models.watch import Watch, WatchCheck, WatchTrigger
from app.services.continuous_attention import process_source_arrival
from app.services.ingestion import ingest_url
from app.services.scheduler import PlanDraft, validate_plan
from app.services.source_graph import persist_source_edge

ARTIFACT_ID = "raos-phase8c-real-dogfood-v0.1"
MANIFEST = ROOT / "eval/live/manifest.phase8c_real_dogfood.v0.1.yaml"
OUTDIR = ROOT / "eval/live/results/phase8c_real_dogfood_v0_1"


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def load_manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text())
def _watch_route(features, *_args, **_kwargs):
    if features.independent_source_count >= 2:
        return validate_plan(
            PlanDraft(
                disposition=Disposition.AWARE,
                expected_output=ExpectedOutput.SUMMARY,
                reason="real dogfood: independent evidence reached surfacing threshold",
                cognitive_budget_minutes=2,
            )
        )
    return validate_plan(
        PlanDraft(
            disposition=Disposition.WATCH,
            expected_output=ExpectedOutput.WATCH,
            reason="real dogfood: evidence remains insufficient; keep watching",
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
            reason="real dogfood unrelated-control ordinary route",
            cognitive_budget_minutes=0,
        )
    )
def _fetch(db: Session, label: str, url: str) -> tuple[object, dict]:
    t0 = perf_counter()
    source = ingest_url(db, url)
    elapsed = perf_counter() - t0
    meta = {
        "label": label,
        "url": url,
        "source_id": str(source.id),
        "title": source.title,
        "canonical_url": source.canonical_url,
        "content_chars": len(source.content_text or ""),
        "fingerprint": source.fingerprint,
        "content_hash": source.content_hash,
        "ingestion_method": source.ingestion_method,
        "fetch_elapsed_s": round(elapsed, 3),
    }
    return source, meta


def _make_watch(db: Session, initial_result: dict) -> Watch:
    run = db.get(AnalysisRun, UUID(initial_result["analysis_run"]["id"]))
    watch = Watch(
        target_type="EVENT",
        target_ref="phase8c-gpt6-astra",
        status="ACTIVE",
        created_reason="Phase 8C supervised real-web dogfood obligation",
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


def _attach(db: Session, event: Event, source_id: UUID, relationship: str = "REPORTS") -> None:
    db.add(EventSource(event_id=event.id, source_id=source_id, relationship=relationship, confidence=1.0))
    db.flush()
def main() -> None:
    manifest = load_manifest()
    sources_cfg = manifest["sources"]
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    provider = RuleBasedCognitiveProvider()
    original_route = pipeline_mod.route

    with Session(engine) as db:
        fetched: dict[str, dict] = {}
        a, fetched["A"] = _fetch(db, "A", sources_cfg["A"]["url"])
        event = Event(
            title="GPT-6 Astra release — supervised dogfood event",
            event_type="MODEL_RELEASE",
            summary="Supervised event relation for Phase 8C dogfood only.",
            confidence=1.0,
            status=EventStatus.CONFIRMED,
        )
        db.add(event); db.flush()
        _attach(db, event, a.id)
        initial = pipeline_mod.run_pipeline(db, a.id, provider=provider, allow_watch_creation=False)
        watch = _make_watch(db, initial)
        initial_watch_count = db.scalar(select(func.count()).select_from(Watch))

        pipeline_mod.route = _watch_route
        c, fetched["C"] = _fetch(db, "C", sources_cfg["C"]["url"])
        _attach(db, event, c.id)
        persist_source_edge(db, c.id, a.id, SourceEdgeRelationship.REPORTS_ON)
        c_result = process_source_arrival(db, c.id, provider=provider)
        c_check = _check_for_source(db, watch, c.id)
        c_rel = _relational(db, c_check)

        x, fetched["X"] = _fetch(db, "X", sources_cfg["X"]["url"])
        pipeline_mod.route = _drop_route
        x_result = process_source_arrival(db, x.id, provider=provider)
        pipeline_mod.route = _watch_route

        d, fetched["D"] = _fetch(db, "D", sources_cfg["D"]["url"])
        _attach(db, event, d.id)
        d_result = process_source_arrival(db, d.id, provider=provider)
        d_check = _check_for_source(db, watch, d.id)
        d_rel = _relational(db, d_check)

        pipeline_mod.route = original_route
        checks = db.execute(
            select(WatchCheck).where(WatchCheck.watch_id == watch.id).order_by(WatchCheck.checked_at)
        ).scalars().all()
        final_watch_count = db.scalar(select(func.count()).select_from(Watch))
        conditions = {
            "all_real_fetches_nonempty": all(item["content_chars"] > 1000 for item in fetched.values()),
            "secondary_rechecked": c_result["watch_decisions"][0]["evidence_class"] == "SECONDARY",
            "secondary_kept_active": c_check.outcome == "KEEP_ACTIVE" and c_check.disposition == "WATCH",
            "secondary_not_independent": c_rel.get("independent_sources") == 1,
            "secondary_counted_as_secondary": c_rel.get("secondary_reports") == 1,
            "unrelated_ordinary_route": (not x_result["matched_watch"]) and x_result["ordinary_analysis"] is not None,
            "independent_promoted": d_result["watch_decisions"][0]["evidence_class"] == "INDEPENDENT" and d_check.outcome == "PROMOTED",
            "independent_count_incremented": d_rel.get("independent_sources") == 2,
            "secondary_count_preserved": d_rel.get("secondary_reports") == 1,
            "single_watch_obligation": initial_watch_count == final_watch_count == 1,
            "watch_history_complete": [check.outcome for check in checks] == ["KEEP_ACTIVE", "PROMOTED"],
            "final_watch_promoted": watch.status == "PROMOTED",
        }

        artifact = {
            "artifact_id": ARTIFACT_ID,
            "measurement_git_head": git_head(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "evidence_type": manifest["controls"]["evidence_type"],
            "manifest_version": manifest["version"],
            "fetched_sources": fetched,
            "decisions": {
                "C_secondary": c_result["watch_decisions"],
                "X_unrelated": {
                    "matched_watch": x_result["matched_watch"],
                    "ordinary_analysis": bool(x_result["ordinary_analysis"]),
                },
                "D_independent": d_result["watch_decisions"],
            },
            "relational_context": {"C_secondary": c_rel, "D_independent": d_rel},
            "watch_check_outcomes": [check.outcome for check in checks],
            "conditions": conditions,
            "all_conditions_pass": all(conditions.values()),
        }
        OUTDIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = OUTDIR / f"phase8c_real_dogfood_v0_1_{stamp}.json"
        out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
        print(f"wrote {out}")
        print(json.dumps(artifact, ensure_ascii=False, indent=2))
        if not artifact["all_conditions_pass"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
