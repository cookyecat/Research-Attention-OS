from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import models as _models  # noqa: F401
from app.db import Base
from app.models.source import Source
from app.services.pipeline import run_pipeline
from eval.live.phase6b_cognitive_semantics_v0_1 import (
    build_phase6b_mvp_kernel_nodes,
    build_phase6b_perf_challenge_nodes,
)
from eval.live.phase8c2_production_sensor_bridge_v0_1 import SemanticSensorProductionBridgeV0_1
from eval.live.run_standing_radar_fit_eval import load_repo_env
from eval.live.semantic_source_loader_v0_1 import load_dev_manifest, load_manifest_source

MANIFEST = ROOT / "eval/live/manifest.phase8c2_production_sensor_bridge_ab.v0.1.yaml"
OUT_DIR = ROOT / "eval/live/results/phase8c2_production_sensor_bridge_ab_v0_1"
RUN_VERSION = "phase8c2-production-sensor-bridge-ab-v0.1"
FIXED_TIME = datetime(2026, 9, 9, 0, 0, tzinfo=timezone.utc)


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _value(value):
    return value.value if hasattr(value, "value") else value


def _load_manifest() -> dict[str, Any]:
    raw = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    if raw.get("status") != "PREREGISTERED_DEVELOPMENT_AB":
        raise ValueError("phase8c2 A/B manifest status mismatch")
    return raw


def _dev_entry(source_id: str) -> dict[str, Any]:
    dev = load_dev_manifest()
    return next(item for item in dev["sources"] if str(item["id"]) == source_id)


def _raw_text(entry: dict[str, Any]) -> str:
    path = ROOT / str(entry["path"])
    return path.read_text(encoding="utf-8-sig").strip()


def _fixture_nodes(name: str):
    if name == "phase6b-perf-challenge-counterfactual":
        return build_phase6b_perf_challenge_nodes()
    if name == "phase6b-mvp-in-memory-copy":
        return build_phase6b_mvp_kernel_nodes()
    raise KeyError(name)


def _base_world(source_id: str, case: dict[str, Any]) -> tuple[Any, Session, Source, dict[str, str]]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    Base.metadata.create_all(engine)
    db = Session(engine, autoflush=False, expire_on_commit=False)
    nodes = _fixture_nodes(str(case["kernel_fixture"]))
    for node in nodes:
        db.add(node)
    entry = _dev_entry(source_id)
    load_manifest_source(entry)  # exact pinned development-source verification
    raw = _raw_text(entry)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    source = Source(
        id=uuid5(NAMESPACE_URL, f"raos.phase8c2.source.{source_id}"),
        source_type="TEXT", title=Path(str(entry["path"])).stem, content_text=raw,
        fingerprint=f"phase8c2:{source_id}", content_hash=digest,
        ingestion_method="PHASE8C2_EVAL", raw_metadata={"dev_source_id": source_id},
        ingested_at=FIXED_TIME, created_at=FIXED_TIME, updated_at=FIXED_TIME,
    )
    db.add(source)
    db.flush()
    code_by_id = {str(node.id): str((node.payload or {}).get("phase6b_fixture_code") or node.title) for node in nodes}
    return engine, db, source, code_by_id


def _arm_summary(result: dict[str, Any], provider, code_by_id: dict[str, str]) -> dict[str, Any]:
    update = result.get("update") or {}
    target_id = update.get("target_node_id")
    matches = result.get("kernel_matches") or []
    return {
        "analysis_identity": (result.get("analysis_run") or {}).get("identity_key"),
        "execution_digest": result.get("execution_digest"),
        "execution_snapshot": result.get("execution_snapshot"),
        "extraction_path": result.get("extraction_path"),
        "n_claims": len(result.get("claims") or []),
        "n_observations": len(result.get("observations") or []),
        "n_inferences": len(result.get("inferences") or []),
        "matches": [
            {
                "fixture_code": code_by_id.get(str(row.get("node_id"))),
                "node_type": row.get("node_type"),
                "title": row.get("title"),
                "score": row.get("score"),
                "relevance_type": row.get("relevance_type"),
            }
            for row in matches
        ],
        "update": {
            "operation": _value(update.get("operation")),
            "target_fixture_code": code_by_id.get(str(target_id)) if target_id else None,
        },
        "delta_content": result.get("delta_content"),
        "attention": {
            "disposition": (result.get("attention_plan") or {}).get("disposition"),
            "expected_output": (result.get("attention_plan") or {}).get("expected_output"),
            "watch_after_processing": (result.get("attention_plan") or {}).get("watch_after_processing"),
        },
        "fallback_used": bool(getattr(provider, "fallback_used", False)),
        "stage_provenance": dict(getattr(provider, "stage_provenance", {}) or {}),
    }


def _run_arm(db: Session, source: Source, code_by_id: dict[str, str], *, arm: str) -> dict[str, Any]:
    from app.cognitive.factory import get_provider

    savepoint = db.begin_nested()
    provider = get_provider()
    bridge = SemanticSensorProductionBridgeV0_1() if arm == "B_SENSOR" else None
    try:
        result = run_pipeline(
            db,
            source.id,
            provider=provider,
            extraction_bridge=bridge,
            reprocess=True,
            allow_watch_creation=False,
        )
        summary = _arm_summary(result, provider, code_by_id)
        summary.update({"arm": arm, "status": "OK", "error": None})
        return summary
    except Exception as exc:
        return {
            "arm": arm,
            "status": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc)[:3000],
            "fallback_used": bool(getattr(provider, "fallback_used", False)),
            "stage_provenance": dict(getattr(provider, "stage_provenance", {}) or {}),
        }
    finally:
        if savepoint.is_active:
            savepoint.rollback()
        db.expire_all()


def _signature(arm: dict[str, Any]) -> tuple[Any, ...]:
    if arm.get("status") != "OK":
        return ("ERROR", arm.get("error_type"))
    update = arm.get("update") or {}
    attention = arm.get("attention") or {}
    return (
        update.get("operation"), update.get("target_fixture_code"),
        attention.get("disposition"), attention.get("expected_output"),
    )


def _candidate_expectation(case: dict[str, Any], arm: dict[str, Any]) -> dict[str, Any]:
    expected_update = case.get("expected_candidate_update")
    expected_attention = case.get("expected_candidate_attention")
    checks: dict[str, Any] = {}
    if expected_update is not None:
        actual = arm.get("update") or {}
        checks["update_match"] = (
            actual.get("operation") == expected_update.get("operation")
            and actual.get("target_fixture_code") == expected_update.get("target")
        )
    else:
        checks["update_match"] = None
    if expected_attention is not None:
        checks["attention_match"] = (
            (arm.get("attention") or {}).get("disposition") == expected_attention
        )
    else:
        checks["attention_match"] = None
    checks["all_specified_match"] = all(value is not False for value in checks.values())
    return checks


def _paired_run(source_id: str, case: dict[str, Any], repeat: int) -> dict[str, Any]:
    engine, db, source, code_by_id = _base_world(source_id, case)
    try:
        arm_a = _run_arm(db, source, code_by_id, arm="A_LEGACY")
        arm_b = _run_arm(db, source, code_by_id, arm="B_SENSOR")
        identity_distinct = (
            arm_a.get("status") == arm_b.get("status") == "OK"
            and arm_a.get("analysis_identity") != arm_b.get("analysis_identity")
        )
        return {
            "source_id": source_id,
            "repeat": repeat,
            "kernel_fixture": case["kernel_fixture"],
            "A_legacy": arm_a,
            "B_sensor": arm_b,
            "identity_distinct": identity_distinct,
            "pair_diverged": _signature(arm_a) != _signature(arm_b),
            "candidate_expectation": _candidate_expectation(case, arm_b),
        }
    finally:
        db.close()
        engine.dispose()


def _needs_confirmation(row: dict[str, Any]) -> bool:
    if row["A_legacy"].get("status") != "OK" or row["B_sensor"].get("status") != "OK":
        return True
    if row.get("pair_diverged"):
        return True
    return not bool((row.get("candidate_expectation") or {}).get("all_specified_match", True))


def _event_transport_observable(arm: dict[str, Any]) -> bool | None:
    if arm.get("status") != "OK":
        return None
    path = arm.get("extraction_path") or {}
    diagnostics = path.get("diagnostics") or {}
    for source in diagnostics.get("sources") or []:
        n_frames = int((source.get("sensor") or {}).get("n_event_frames") or 0)
        if n_frames and len(source.get("events") or []) != n_frames:
            return False
    return True


def _stable_pair_divergence(rows: list[dict[str, Any]]) -> dict[str, Any]:
    divergent = [
        (str(_signature(row["A_legacy"])), str(_signature(row["B_sensor"])))
        for row in rows if row.get("pair_diverged")
    ]
    counts = Counter(divergent)
    signature, count = counts.most_common(1)[0] if counts else (None, 0)
    return {"stable": count >= 2, "count": count, "pair_signature": signature}


def _case_summary(case: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    expectation_matches = [
        bool((row.get("candidate_expectation") or {}).get("all_specified_match")) for row in rows
    ]
    required = 2 if len(rows) >= 3 else 1
    return {
        "n_pairs": len(rows),
        "n_identity_distinct": sum(bool(row.get("identity_distinct")) for row in rows),
        "n_pair_diverged": sum(bool(row.get("pair_diverged")) for row in rows),
        "stable_pair_divergence": _stable_pair_divergence(rows),
        "candidate_expected_relation": {
            "expected_update": case.get("expected_candidate_update"),
            "expected_attention": case.get("expected_candidate_attention"),
            "n_matching": sum(expectation_matches),
            "required": required,
            "passes": sum(expectation_matches) >= required,
        },
        "event_transport_observable": all(
            _event_transport_observable(row["B_sensor"]) is not False for row in rows
        ),
        "n_arm_errors": sum(
            arm.get("status") != "OK" for row in rows for arm in (row["A_legacy"], row["B_sensor"])
        ),
    }


def run(selected_cases: list[str] | None = None) -> dict[str, Any]:
    load_repo_env()
    from app.config import settings

    manifest = _load_manifest()
    cases = manifest["cases"]
    case_ids = selected_cases or list(cases)
    unknown = [case_id for case_id in case_ids if case_id not in cases]
    if unknown:
        raise KeyError(f"unknown phase8c2 case(s): {unknown}")

    rows: list[dict[str, Any]] = []
    confirmation_cases: list[str] = []
    for source_id in case_ids:
        first = _paired_run(source_id, cases[source_id], 1)
        rows.append(first)
        if _needs_confirmation(first) or _event_transport_observable(first["B_sensor"]) is False:
            confirmation_cases.append(source_id)

    for source_id in confirmation_cases:
        for repeat in (2, 3):
            rows.append(_paired_run(source_id, cases[source_id], repeat))

    grouped = {source_id: [row for row in rows if row["source_id"] == source_id] for source_id in case_ids}
    summaries = {source_id: _case_summary(cases[source_id], grouped[source_id]) for source_id in case_ids}
    return {
        "name": "raos-phase8c2-production-sensor-bridge-ab-v0.1",
        "status": "DEVELOPMENT_CONTROLLED_AB_NOT_HOLDOUT",
        "run_version": RUN_VERSION,
        "measurement_timestamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "measurement_git_head": git_head(),
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "model_environment": {
            "cognitive_provider": settings.cognitive_provider,
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
        },
        "procedure": manifest["procedure"],
        "confirmation_cases": confirmation_cases,
        "case_summaries": summaries,
        "rows": rows,
        "methodology_note": (
            "Each pair starts from the same in-memory base world. A and B run inside rollback SAVEPOINTs, "
            "so Source UUID, Kernel UUID, relational context, and initial persistent state are identical. "
            "Only the pre-ExtractionResult representation path differs. Development cases are not fresh holdout evidence."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", dest="cases", help="Optional case id; repeat flag for multiple")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)
    payload = run(args.cases)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"phase8c2_production_sensor_bridge_ab_v0_1_{payload['measurement_timestamp']}.json"
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps({
        "measurement_git_head": payload["measurement_git_head"],
        "confirmation_cases": payload["confirmation_cases"],
        "case_summaries": payload["case_summaries"],
        "pairs": [
            {
                "source_id": row["source_id"], "repeat": row["repeat"],
                "A": _signature(row["A_legacy"]), "B": _signature(row["B_sensor"]),
                "identity_distinct": row["identity_distinct"],
                "candidate_expectation": row["candidate_expectation"],
            }
            for row in payload["rows"]
        ],
    }, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
