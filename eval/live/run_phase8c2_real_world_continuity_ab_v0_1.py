from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
from uuid import UUID

import yaml
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app import models as _models  # noqa: F401
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.db import Base
from app.enums import Disposition, EventStatus, ExpectedOutput, SourceEdgeRelationship
from app.models.analysis import AnalysisRun
from app.models.event import Event, EventSource
from app.models.watch import Watch, WatchCheck, WatchTrigger
from app.services.continuous_attention import process_source_arrival
from app.services.ingestion import ingest_url
import app.services.pipeline as pipeline_mod
from app.services.pipeline import run_pipeline
from app.services.scheduler import PlanDraft, validate_plan
from app.services.source_graph import persist_source_edge
from eval.live.phase8c2_production_sensor_bridge_v0_1 import SemanticSensorProductionBridgeV0_1

MANIFEST = ROOT / "eval/live/manifest.phase8c2_real_world_continuity_ab.v0.1.yaml"
OUT_DIR = ROOT / "eval/live/results/phase8c2_real_world_continuity_ab_v0_1"
RUN_VERSION = "phase8c2-real-world-continuity-ab-v0.1"


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _load_manifest() -> dict[str, Any]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    if data.get("status") != "PREREGISTERED_REAL_WORLD_CONTINUITY":
        raise ValueError("phase8c2 continuity manifest status mismatch")
    return data


def _watch_route(features, *_args, **_kwargs):
    if features.independent_source_count >= 2:
        return validate_plan(
            PlanDraft(
                disposition=Disposition.AWARE,
                expected_output=ExpectedOutput.SUMMARY,
                reason="phase8c2 continuity: independent evidence reached surfacing threshold",
                cognitive_budget_minutes=2,
            )
        )
    return validate_plan(
        PlanDraft(
            disposition=Disposition.WATCH,
            expected_output=ExpectedOutput.WATCH,
            reason="phase8c2 continuity: evidence remains insufficient; keep watching",
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
            reason="phase8c2 continuity unrelated-control ordinary route",
            cognitive_budget_minutes=0,
        )
    )


def _fetch_all(db: Session, manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    sources: dict[str, Any] = {}
    audit: dict[str, Any] = {}
    for label in ("A", "C", "D", "X"):
        spec = manifest["sources"][label]
        source = ingest_url(db, str(spec["url"]))
        sources[label] = source
        expected_hash = str(spec["content_hash"])
        expected_chars = int(spec["content_chars"])
        audit[label] = {
            "source_id": str(source.id),
            "title": source.title,
            "canonical_url": source.canonical_url,
            "expected_content_hash": expected_hash,
            "actual_content_hash": source.content_hash,
            "hash_match": source.content_hash == expected_hash,
            "expected_content_chars": expected_chars,
            "actual_content_chars": len(source.content_text or ""),
            "char_count_match": len(source.content_text or "") == expected_chars,
        }
    return sources, audit


def _attach(db: Session, event: Event, source_id: UUID) -> None:
    db.add(EventSource(event_id=event.id, source_id=source_id, relationship="REPORTS", confidence=1.0))
    db.flush()


def _prepare_base_world() -> tuple[Any, Session, dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = _load_manifest()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    Base.metadata.create_all(engine)
    db = Session(engine, autoflush=False, expire_on_commit=False)
    sources, acquisition = _fetch_all(db, manifest)
    if not all(item["hash_match"] for item in acquisition.values()):
        return engine, db, sources, acquisition, manifest
    event = Event(
        title="GPT-6 Astra release — supervised Phase 8C.1 continuity event",
        event_type="MODEL_RELEASE",
        summary="Supervised event relation replay for Phase 8C.2 continuity only.",
        confidence=1.0,
        status=EventStatus.CONFIRMED,
    )
    db.add(event); db.flush()
    for label in ("A", "C", "D"):
        _attach(db, event, sources[label].id)
    persist_source_edge(db, sources["C"].id, sources["A"].id, SourceEdgeRelationship.REPORTS_ON)
    return engine, db, sources, acquisition, manifest


def _make_watch(db: Session, initial_result: dict[str, Any]) -> Watch:
    run = db.get(AnalysisRun, UUID(initial_result["analysis_run"]["id"]))
    watch = Watch(
        target_type="EVENT",
        target_ref="phase8c-gpt6-astra",
        status="ACTIVE",
        created_reason="Phase 8C.2 real-world continuity obligation",
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


def _relational(db: Session, check: WatchCheck) -> dict[str, Any]:
    run = db.get(AnalysisRun, check.analysis_run_id) if check.analysis_run_id else None
    if run is None:
        return {}
    return ((run.result_payload or {}).get("relational_context") or {}).get("independence") or {}


def _analysis_from_check(db: Session, check: WatchCheck) -> dict[str, Any]:
    run = db.get(AnalysisRun, check.analysis_run_id) if check.analysis_run_id else None
    if run is None:
        raise RuntimeError("WATCH recheck has no AnalysisRun")
    return dict(run.result_payload or {})


def _value(value):
    return value.value if hasattr(value, "value") else value


def _capture(result: dict[str, Any]) -> dict[str, Any]:
    update = result.get("primary_update") or {}
    attention = result.get("attention_plan") or {}
    matches = result.get("kernel_matches") or []
    return {
        "analysis_identity": (result.get("analysis_run") or {}).get("identity_key"),
        "execution_digest": result.get("execution_digest"),
        "extraction_path": result.get("extraction_path"),
        "n_claims": len(result.get("claims") or []),
        "n_observations": len(result.get("observations") or []),
        "n_inferences": len(result.get("inferences") or []),
        "matches": [
            {
                "node_type": row.get("node_type"),
                "title": row.get("title"),
                "score": row.get("score"),
                "relevance_type": row.get("relevance_type"),
            }
            for row in matches
        ],
        "update": {
            "operation": _value(update.get("operation")),
            "target_id": str(update.get("target_id")) if update.get("target_id") else None,
        },
        "delta_content": result.get("delta_content"),
        "attention": {
            "disposition": attention.get("disposition"),
            "expected_output": attention.get("expected_output"),
            "watch_after_processing": attention.get("watch_after_processing"),
        },
    }


def _event_observable(capture: dict[str, Any]) -> bool:
    path = capture.get("extraction_path") or {}
    if path.get("mode") != "bridge":
        return True
    diagnostics = path.get("diagnostics") or {}
    source_rows = diagnostics.get("sources") or []
    for row in source_rows:
        sensor = row.get("sensor") or {}
        events = row.get("events") or []
        if int(sensor.get("n_event_frames") or 0) != len(events):
            return False
    return True


def _arm_mode_ok(arm: dict[str, Any], expected_mode: str) -> bool:
    if arm.get("status") != "OK":
        return False
    analyses = arm.get("analyses") or {}
    return all(
        ((payload.get("extraction_path") or {}).get("mode") == expected_mode)
        for payload in analyses.values()
    )


def _watch_signature(arm: dict[str, Any]) -> tuple[Any, ...]:
    if arm.get("status") != "OK":
        return ("ERROR", arm.get("error_type"))
    decisions = arm.get("decisions") or {}
    return (
        decisions.get("C_secondary"),
        decisions.get("X_unrelated"),
        decisions.get("D_independent"),
        arm.get("final_watch_status"),
    )


def _run_arm(db: Session, sources: dict[str, Any], *, arm: str) -> dict[str, Any]:
    savepoint = db.begin_nested()
    provider = RuleBasedCognitiveProvider()
    bridge = SemanticSensorProductionBridgeV0_1() if arm == "B_SENSOR" else None
    original_route = pipeline_mod.route
    try:
        initial = run_pipeline(
            db,
            sources["A"].id,
            provider=provider,
            extraction_bridge=bridge,
            reprocess=True,
            allow_watch_creation=False,
        )
        watch = _make_watch(db, initial)
        initial_watch_count = db.scalar(select(func.count()).select_from(Watch))

        pipeline_mod.route = _watch_route
        c_result = process_source_arrival(
            db, sources["C"].id, provider=provider, extraction_bridge=bridge
        )
        c_decision = c_result["watch_decisions"][0]
        c_check = _check_for_source(db, watch, sources["C"].id)
        c_analysis = _analysis_from_check(db, c_check)
        c_rel = _relational(db, c_check)

        pipeline_mod.route = _drop_route
        x_result = process_source_arrival(
            db, sources["X"].id, provider=provider, extraction_bridge=bridge
        )
        x_analysis = x_result.get("ordinary_analysis")
        if x_result.get("matched_watch") or x_analysis is None:
            raise RuntimeError("X unrelated control did not take ordinary-analysis route")

        pipeline_mod.route = _watch_route
        d_result = process_source_arrival(
            db, sources["D"].id, provider=provider, extraction_bridge=bridge
        )
        d_decision = d_result["watch_decisions"][0]
        d_check = _check_for_source(db, watch, sources["D"].id)
        d_analysis = _analysis_from_check(db, d_check)
        d_rel = _relational(db, d_check)

        checks = db.execute(
            select(WatchCheck).where(WatchCheck.watch_id == watch.id).order_by(WatchCheck.checked_at)
        ).scalars().all()
        final_watch_count = db.scalar(select(func.count()).select_from(Watch))
        analyses = {
            "A_initial": _capture(initial),
            "C_recheck": _capture(c_analysis),
            "X_ordinary": _capture(x_analysis),
            "D_recheck": _capture(d_analysis),
        }
        return {
            "arm": arm,
            "status": "OK",
            "analyses": analyses,
            "decisions": {
                "C_secondary": (
                    c_decision.get("evidence_class"), c_decision.get("outcome")
                ),
                "X_unrelated": (
                    bool(x_result.get("matched_watch")), bool(x_analysis)
                ),
                "D_independent": (
                    d_decision.get("evidence_class"), d_decision.get("outcome")
                ),
            },
            "relational_context": {"C_secondary": c_rel, "D_independent": d_rel},
            "watch_check_outcomes": [check.outcome for check in checks],
            "initial_watch_count": initial_watch_count,
            "final_watch_count": final_watch_count,
            "final_watch_status": watch.status,
            "bridge_event_observable": all(_event_observable(row) for row in analyses.values()),
        }
    except Exception as exc:
        return {
            "arm": arm,
            "status": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc)[:3000],
        }
    finally:
        pipeline_mod.route = original_route
        if savepoint.is_active:
            savepoint.rollback()
        db.expire_all()


def _identity_distinct(a: dict[str, Any], b: dict[str, Any]) -> dict[str, bool]:
    if a.get("status") != "OK" or b.get("status") != "OK":
        return {}
    out: dict[str, bool] = {}
    for key in ("A_initial", "C_recheck", "X_ordinary", "D_recheck"):
        ai = ((a.get("analyses") or {}).get(key) or {}).get("analysis_identity")
        bi = ((b.get("analyses") or {}).get(key) or {}).get("analysis_identity")
        out[key] = bool(ai and bi and ai != bi)
    return out


def _expected_continuity(arm: dict[str, Any], expected_mode: str) -> dict[str, bool]:
    if arm.get("status") != "OK":
        return {"arm_ok": False}
    decisions = arm.get("decisions") or {}
    rel = arm.get("relational_context") or {}
    c_rel = rel.get("C_secondary") or {}
    d_rel = rel.get("D_independent") or {}
    checks = {
        "arm_ok": True,
        "path_mode_all_points": _arm_mode_ok(arm, expected_mode),
        "C_secondary_keep_active": decisions.get("C_secondary") == ("SECONDARY", "KEEP_ACTIVE"),
        "X_unrelated_ordinary": decisions.get("X_unrelated") == (False, True),
        "D_independent_promoted": decisions.get("D_independent") == ("INDEPENDENT", "PROMOTED"),
        "C_relational_counts": c_rel.get("independent_sources") == 1 and c_rel.get("secondary_reports") == 1,
        "D_relational_counts": d_rel.get("independent_sources") == 2 and d_rel.get("secondary_reports") == 1,
        "watch_history": arm.get("watch_check_outcomes") == ["KEEP_ACTIVE", "PROMOTED"],
        "single_watch_obligation": arm.get("initial_watch_count") == arm.get("final_watch_count") == 1,
        "final_watch_promoted": arm.get("final_watch_status") == "PROMOTED",
    }
    if expected_mode == "bridge":
        checks["bridge_event_observable"] = bool(arm.get("bridge_event_observable"))
    return checks


def _pair_result(db: Session, sources: dict[str, Any], repeat: int) -> dict[str, Any]:
    arm_a = _run_arm(db, sources, arm="A_LEGACY")
    arm_b = _run_arm(db, sources, arm="B_SENSOR")
    identities = _identity_distinct(arm_a, arm_b)
    a_checks = _expected_continuity(arm_a, "legacy")
    b_checks = _expected_continuity(arm_b, "bridge")
    return {
        "repeat": repeat,
        "A_legacy": arm_a,
        "B_sensor": arm_b,
        "identity_distinct": identities,
        "all_identities_distinct": bool(identities) and all(identities.values()),
        "watch_signature_equal": _watch_signature(arm_a) == _watch_signature(arm_b),
        "A_continuity_checks": a_checks,
        "B_continuity_checks": b_checks,
        "A_all_continuity_pass": all(a_checks.values()),
        "B_all_continuity_pass": all(b_checks.values()),
    }


def _needs_confirmation(row: dict[str, Any]) -> bool:
    return not (
        row.get("all_identities_distinct")
        and row.get("watch_signature_equal")
        and row.get("A_all_continuity_pass")
        and row.get("B_all_continuity_pass")
    )


def _analysis_signature(capture: dict[str, Any]) -> tuple[Any, ...]:
    update = capture.get("update") or {}
    attention = capture.get("attention") or {}
    return (
        update.get("operation"),
        update.get("target_id"),
        attention.get("disposition"),
        attention.get("expected_output"),
    )


def _diagnostic_differences(row: dict[str, Any]) -> dict[str, Any]:
    if row["A_legacy"].get("status") != "OK" or row["B_sensor"].get("status") != "OK":
        return {}
    out: dict[str, Any] = {}
    for key in ("A_initial", "C_recheck", "X_ordinary", "D_recheck"):
        a = row["A_legacy"]["analyses"][key]
        b = row["B_sensor"]["analyses"][key]
        out[key] = {
            "A": _analysis_signature(a),
            "B": _analysis_signature(b),
            "same": _analysis_signature(a) == _analysis_signature(b),
        }
    return out


def _pair_gate_pass(row: dict[str, Any]) -> bool:
    return bool(
        row.get("all_identities_distinct")
        and row.get("watch_signature_equal")
        and row.get("A_all_continuity_pass")
        and row.get("B_all_continuity_pass")
    )


def run() -> dict[str, Any]:
    engine, db, sources, acquisition, manifest = _prepare_base_world()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        continuity_gate = all(
            item["hash_match"] and item["char_count_match"]
            for item in acquisition.values()
        )
        base = {
            "name": "raos-phase8c2-real-world-continuity-ab-v0.1",
            "run_version": RUN_VERSION,
            "measurement_timestamp": timestamp,
            "measurement_git_head": git_head(),
            "manifest": str(MANIFEST.relative_to(ROOT)),
            "acquisition": acquisition,
            "production_normalized_continuity_gate": continuity_gate,
        }
        if not continuity_gate:
            return {
                **base,
                "status": "REAL_WEB_CONTENT_DRIFT_ABORTED_BEFORE_AB",
                "pairs": [],
                "all_gates_pass": False,
                "note": "No Sensor/legacy A/B or model call was permitted after the continuity gate failed.",
            }

        rows = [_pair_result(db, sources, 1)]
        confirmation_triggered = _needs_confirmation(rows[0])
        if confirmation_triggered:
            rows.extend(_pair_result(db, sources, repeat) for repeat in (2, 3))
        n_pair_passes = sum(_pair_gate_pass(row) for row in rows)
        required = 2 if len(rows) == 3 else 1
        all_gates_pass = n_pair_passes >= required
        return {
            **base,
            "status": "DEVELOPMENT_REAL_WORLD_CONTINUITY_NOT_HOLDOUT",
            "confirmation_triggered": confirmation_triggered,
            "n_pairs": len(rows),
            "n_pair_passes": n_pair_passes,
            "required_pair_passes": required,
            "all_gates_pass": all_gates_pass,
            "pairs": [
                {
                    **row,
                    "pair_gate_pass": _pair_gate_pass(row),
                    "diagnostic_cognitive_differences": _diagnostic_differences(row),
                }
                for row in rows
            ],
            "methodology_note": (
                "Tier 2 replays the supervised Phase 8C.1 relation/WATCH topology. "
                "WATCH continuity, bridge propagation, identity separation, and event observability are gates; "
                "ungolded cognitive differences on A/C/D/X are diagnostics only."
            ),
        }
    finally:
        db.close()
        engine.dispose()


def _compact(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "measurement_git_head": payload.get("measurement_git_head"),
        "production_normalized_continuity_gate": payload.get("production_normalized_continuity_gate"),
        "acquisition": payload.get("acquisition"),
        "confirmation_triggered": payload.get("confirmation_triggered"),
        "n_pairs": payload.get("n_pairs"),
        "n_pair_passes": payload.get("n_pair_passes"),
        "all_gates_pass": payload.get("all_gates_pass"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)
    payload = run()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"phase8c2_real_world_continuity_ab_v0_1_{payload['measurement_timestamp']}.json"
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps(_compact(payload), ensure_ascii=False, indent=2, default=str))
    if payload.get("status") == "REAL_WEB_CONTENT_DRIFT_ABORTED_BEFORE_AB":
        return 3
    return 0 if payload.get("all_gates_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
