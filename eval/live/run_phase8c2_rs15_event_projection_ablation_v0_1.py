from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_standing_radar_fit_eval import load_repo_env

load_repo_env()

from app.cognitive.factory import get_provider
from app.services.extraction_bridge import ExtractionBridgeResult
from app.services.pipeline import run_pipeline
from eval.live.phase6b_cognitive_semantics_v0_1 import audited_units_to_extraction
from eval.live.phase8c2_production_sensor_bridge_v0_1 import (
    _admitted_event_units,
    _as_of,
    _audit_non_event_units,
    _fail_on_auditor_transport_error,
    _project_production_separations,
    production_source_to_sensor_source,
)
from eval.live.raw_source_attention_vertical_slice_v0_1 import (
    audit_event_edges,
    project_event_audit_edges,
)
from eval.live.run_phase8c2_production_sensor_bridge_ab_v0_1 import (
    _arm_summary,
    _base_world,
    _load_manifest,
)
from eval.live.semantic_evidence_extractor_v0_2_6 import estimate_semantic_evidence_v0_2_6

OUT_DIR = ROOT / "eval/live/results/phase8c2_rs15_event_projection_ablation_v0_1"
RUN_VERSION = "phase8c2-rs15-event-projection-ablation-v0.1"
SOURCE_ID = "RS15"
CONDITIONS = ("N_NON_EVENT", "E_EVENT_ONLY", "EN_FLATTENED_COMBINED")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _hash_units(units: list[dict[str, Any]]) -> str:
    payload = json.dumps(units, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _make_extraction(units: list[dict[str, Any]], *, event_title: str):
    extraction = _project_production_separations(audited_units_to_extraction(deepcopy(units)))
    extraction.event_title = event_title
    return extraction


class FrozenExtractionBridge:
    def __init__(self, *, condition: str, extraction, semantic_hash: str):
        self.condition = condition
        self.extraction = extraction
        self.semantic_hash = semantic_hash

    def execution_snapshot(self) -> dict[str, Any]:
        return {
            "bridge_version": RUN_VERSION,
            "condition": self.condition,
            "frozen_semantic_sha256": self.semantic_hash,
        }

    def extract(self, source, extra_sources):
        if extra_sources:
            raise ValueError("RS15 ablation expects one source only")
        return ExtractionBridgeResult(
            extraction=deepcopy(self.extraction),
            diagnostics={
                "mode": "frozen-rs15-ablation",
                "condition": self.condition,
                "frozen_semantic_sha256": self.semantic_hash,
            },
        )


def _freeze_semantic_world(case: dict[str, Any]) -> dict[str, Any]:
    engine, db, source, _ = _base_world(SOURCE_ID, case)
    try:
        sensor_source = production_source_to_sensor_source(source)
        sensor_result = estimate_semantic_evidence_v0_2_6(sensor_source, as_of=_as_of(source))
        if not sensor_result.get("scorable") or not sensor_result.get("batch"):
            raise RuntimeError(
                f"Sensor failure: {sensor_result.get('failure_kind')} {sensor_result.get('error')}"
            )
        batch = sensor_result["batch"]
        non_rows, non_admitted = _audit_non_event_units(
            str(source.id), list(batch.get("non_event_units") or [])
        )
        event_units: list[dict[str, Any]] = []
        event_rows: list[dict[str, Any]] = []
        event_projections: list[dict[str, Any]] = []
        for frame in batch.get("event_frames") or []:
            rows = audit_event_edges(project_event_audit_edges(str(source.id), frame))
            _fail_on_auditor_transport_error(rows, source_id=str(source.id))
            admitted, projection = _admitted_event_units(frame, rows)
            event_units.extend(admitted)
            event_rows.extend(rows)
            event_projections.append(projection)

        combined = [*event_units, *non_admitted]
        unit_sets = {
            "N_NON_EVENT": non_admitted,
            "E_EVENT_ONLY": event_units,
            "EN_FLATTENED_COMBINED": combined,
        }
        extractions = {
            name: _make_extraction(units, event_title=source.title or SOURCE_ID)
            for name, units in unit_sets.items()
        }
        return {
            "sensor": {
                "repair_used": bool(sensor_result.get("repair_used")),
                "n_event_frames": len(batch.get("event_frames") or []),
                "n_non_event_units": len(batch.get("non_event_units") or []),
            },
            "non_event_rows": non_rows,
            "event_rows": event_rows,
            "event_projections": event_projections,
            "unit_sets": unit_sets,
            "unit_hashes": {name: _hash_units(units) for name, units in unit_sets.items()},
            "extractions": extractions,
        }
    finally:
        db.close()
        engine.dispose()


def _run_condition(
    case: dict[str, Any],
    frozen: dict[str, Any],
    *,
    condition: str,
    repeat: int,
) -> dict[str, Any]:
    engine, db, source, code_by_id = _base_world(SOURCE_ID, case)
    provider = get_provider()
    bridge = FrozenExtractionBridge(
        condition=condition,
        extraction=frozen["extractions"][condition],
        semantic_hash=frozen["unit_hashes"][condition],
    )
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
        summary.update({"condition": condition, "repeat": repeat, "status": "OK", "error": None})
        return summary
    except Exception as exc:
        return {
            "condition": condition,
            "repeat": repeat,
            "status": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc)[:3000],
        }
    finally:
        db.close()
        engine.dispose()


def _landing(row: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    update = row.get("update") or {}
    attention = row.get("attention") or {}
    return (
        update.get("operation"),
        update.get("target_fixture_code"),
        attention.get("disposition"),
        attention.get("expected_output"),
    )


def _match_scores(row: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for match in row.get("matches") or []:
        code = match.get("fixture_code")
        if code in {"Q2", "B2"}:
            out[str(code)] = float(match.get("score") or 0.0)
    return out


def _compact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "condition": row.get("condition"),
        "repeat": row.get("repeat"),
        "status": row.get("status"),
        "landing": list(_landing(row)) if row.get("status") == "OK" else None,
        "q2_b2_scores": _match_scores(row) if row.get("status") == "OK" else {},
        "delta_content": row.get("delta_content"),
    }


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_condition: dict[str, list[dict[str, Any]]] = {name: [] for name in CONDITIONS}
    for row in rows:
        by_condition[row["condition"]].append(row)
    summary: dict[str, Any] = {}
    for condition, items in by_condition.items():
        landings = [list(_landing(row)) for row in items if row.get("status") == "OK"]
        summary[condition] = {
            "n_runs": len(items),
            "n_ok": sum(row.get("status") == "OK" for row in items),
            "landings": landings,
            "q2_b2_scores": [_match_scores(row) for row in items if row.get("status") == "OK"],
            "stable_landing": landings[0] if landings and all(x == landings[0] for x in landings) else None,
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        raise SystemExit("--repeats must be >= 1")

    manifest = _load_manifest()
    case = dict(manifest["cases"][SOURCE_ID])
    measurement_sha = git_head()
    frozen = _freeze_semantic_world(case)

    rows: list[dict[str, Any]] = []
    for repeat in range(1, args.repeats + 1):
        for condition in CONDITIONS:
            row = _run_condition(case, frozen, condition=condition, repeat=repeat)
            rows.append(row)
            print(json.dumps(_compact_row(row), ensure_ascii=False), flush=True)

    summary = _summarize(rows)
    output = {
        "run_version": RUN_VERSION,
        "status": "DEVELOPMENT_CAUSAL_ATTRIBUTION_ONLY",
        "measurement_sha": measurement_sha,
        "source_id": SOURCE_ID,
        "kernel_fixture": case["kernel_fixture"],
        "repeats": args.repeats,
        "controlled_variable": "flattened audited event-projection admission into cognitive ExtractionResult",
        "frozen_semantic_world": {
            "sensor": frozen["sensor"],
            "n_non_event_admitted": len(frozen["unit_sets"]["N_NON_EVENT"]),
            "n_event_projection_admitted": len(frozen["unit_sets"]["E_EVENT_ONLY"]),
            "unit_hashes": frozen["unit_hashes"],
            "non_event_units": frozen["unit_sets"]["N_NON_EVENT"],
            "event_projection_units": frozen["unit_sets"]["E_EVENT_ONLY"],
        },
        "summary": summary,
        "runs": rows,
        "interpretation_guardrails": [
            "This run does not alter Sensor v0.2.6, Auditor v0.1.1, Delta, or Attention Policy.",
            "N and EN reuse the same single Sensor/Auditor realization; only admitted representation composition changes.",
            "E is diagnostic only and does not claim event semantics should independently drive cognition.",
            "This does not test a native typed-event production interface because production currently accepts ExtractionResult only.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"RESULT_PATH={path.relative_to(ROOT)}", flush=True)
    print(f"RESULT_SHA256={digest}", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
