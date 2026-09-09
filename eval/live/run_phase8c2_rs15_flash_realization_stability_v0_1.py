from __future__ import annotations

import argparse
from collections import Counter
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

from app.cognitive.client import chat_json
from app.cognitive.factory import get_provider
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
from eval.live.raw_source_attention_vertical_slice_v0_1 import audit_event_edges, project_event_audit_edges
from eval.live.semantic_evidence_extractor_v0_2_6 import estimate_semantic_evidence_v0_2_6, prompt_sha256
from eval.live.run_phase8c2_production_sensor_bridge_ab_v0_1 import _arm_summary, _base_world, _load_manifest
from eval.live.run_phase8c2_rs15_event_projection_ablation_v0_1 import FrozenExtractionBridge, _hash_units

OUT_DIR = ROOT / "eval/live/results/phase8c2_rs15_flash_realization_stability_v0_1"
RUN_VERSION = "phase8c2-rs15-flash-realization-stability-v0.1"
SOURCE_ID = "RS15"
SENSOR_MODEL = "deepseek-v4-flash"
AUDITOR_MODEL = "deepseek-v4-flash"


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _forced_chat(model_name: str):
    def _chat(messages, **kwargs):
        return chat_json(messages, model=model_name, timeout=float(kwargs.get("timeout") or 45.0), thinking=kwargs.get("thinking"), reasoning_effort=kwargs.get("reasoning_effort"))
    return _chat

def _run_frozen_downstream(case: dict[str, Any], units: list[dict[str, Any]], *, label: str):
    engine, db, source, code_by_id = _base_world(SOURCE_ID, case)
    provider = get_provider()
    extraction = _project_production_separations(audited_units_to_extraction(deepcopy(units)))
    extraction.event_title = source.title or SOURCE_ID
    bridge = FrozenExtractionBridge(
        condition=f"{RUN_VERSION}:{label}",
        extraction=extraction,
        semantic_hash=_hash_units(units),
    )
    try:
        result = run_pipeline(
            db, source.id, provider=provider, extraction_bridge=bridge,
            reprocess=True, allow_watch_creation=False,
        )
        return _arm_summary(result, provider, code_by_id)
    finally:
        db.close()
        engine.dispose()


def _landing(row: dict[str, Any]) -> list[Any]:
    update = row.get("update") or {}
    attention = row.get("attention") or {}
    return [
        update.get("operation"), update.get("target_fixture_code"),
        attention.get("disposition"), attention.get("expected_output"),
    ]

def _one_realization(case: dict[str, Any], repeat: int) -> dict[str, Any]:
    engine, db, source, _ = _base_world(SOURCE_ID, case)
    try:
        sensor_source = production_source_to_sensor_source(source)
        sensor = estimate_semantic_evidence_v0_2_6(
            sensor_source,
            as_of=_as_of(source),
            chat_fn=_forced_chat(SENSOR_MODEL),
        )
        if not sensor.get("scorable") or not sensor.get("batch"):
            return {
                "repeat": repeat, "status": "ERROR", "stage": "sensor",
                "failure_kind": sensor.get("failure_kind"), "error": sensor.get("error"),
            }
        batch = sensor["batch"]
        sensor_non = list(batch.get("non_event_units") or [])
        non_rows, non_admitted = _audit_non_event_units(
            str(source.id), sensor_non, chat_fn=_forced_chat(AUDITOR_MODEL)
        )

        event_units: list[dict[str, Any]] = []
        event_rows: list[dict[str, Any]] = []
        for frame in batch.get("event_frames") or []:
            rows = audit_event_edges(
                project_event_audit_edges(str(source.id), frame),
                chat_fn=_forced_chat(AUDITOR_MODEL),
            )
            _fail_on_auditor_transport_error(rows, source_id=str(source.id))
            admitted, _ = _admitted_event_units(frame, rows)
            event_units.extend(admitted)
            event_rows.extend(rows)
    finally:
        db.close()
        engine.dispose()

    combined = [*event_units, *non_admitted]
    downstream = {
        "SENSOR_NON_PREAUDIT": _run_frozen_downstream(
            case, sensor_non, label=f"r{repeat}:sensor-non-preaudit"
        ),
        "AUDITED_NON_EVENT": _run_frozen_downstream(
            case, non_admitted, label=f"r{repeat}:audited-non"
        ),
        "AUDITED_EVENT_PLUS_NON": _run_frozen_downstream(
            case, combined, label=f"r{repeat}:audited-event-plus-non"
        ),
    }
    verdicts = Counter(
        str((row.get("audit_result") or {}).get("verdict") or "UNSCORABLE")
        for row in non_rows
    )
    return {
        "repeat": repeat,
        "status": "OK",
        "sensor_model": SENSOR_MODEL,
        "auditor_model": AUDITOR_MODEL,
        "sensor_repair_used": bool(sensor.get("repair_used")),
        "sensor_n_non_event_units": len(sensor_non),
        "sensor_non_event_sha256": _hash_units(sensor_non),
        "sensor_non_event_units": sensor_non,
        "auditor_non_event_verdict_counts": dict(sorted(verdicts.items())),
        "auditor_n_non_event_admitted": len(non_admitted),
        "audited_non_event_sha256": _hash_units(non_admitted),
        "audited_non_event_units": non_admitted,
        "auditor_n_event_units_admitted": len(event_units),
        "event_units": event_units,
        "combined_sha256": _hash_units(combined),
        "downstream": downstream,
        "landings": {name: _landing(row) for name, row in downstream.items()},
    }

def _target(landing: list[Any] | None) -> str:
    if not landing:
        return "ERROR"
    return str(landing[1] or "NONE")


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [row for row in rows if row.get("status") == "OK"]
    summary: dict[str, Any] = {
        "n_runs": len(rows),
        "n_ok": len(ok),
        "n_errors": len(rows) - len(ok),
        "sensor_non_event_counts": [row["sensor_n_non_event_units"] for row in ok],
        "audited_non_event_counts": [row["auditor_n_non_event_admitted"] for row in ok],
        "event_admitted_counts": [row["auditor_n_event_units_admitted"] for row in ok],
        "unique_sensor_semantic_realizations": len({row["sensor_non_event_sha256"] for row in ok}),
        "unique_audited_semantic_realizations": len({row["audited_non_event_sha256"] for row in ok}),
    }
    for condition in (
        "SENSOR_NON_PREAUDIT", "AUDITED_NON_EVENT", "AUDITED_EVENT_PLUS_NON"
    ):
        landings = [row["landings"][condition] for row in ok]
        summary[condition] = {
            "target_counts": dict(sorted(Counter(_target(x) for x in landings).items())),
            "landings": landings,
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=6)
    args = parser.parse_args()
    if args.repeats < 1:
        raise SystemExit("--repeats must be >= 1")
    case = dict(_load_manifest()["cases"][SOURCE_ID])
    rows: list[dict[str, Any]] = []
    for repeat in range(1, args.repeats + 1):
        try:
            row = _one_realization(case, repeat)
        except Exception as exc:
            row = {
                "repeat": repeat, "status": "ERROR", "stage": "runtime",
                "error_type": type(exc).__name__, "error": str(exc)[:3000],
            }
        rows.append(row)
        compact = {k: row.get(k) for k in (
            "repeat", "status", "stage", "sensor_repair_used",
            "sensor_n_non_event_units", "auditor_n_non_event_admitted",
            "auditor_n_event_units_admitted", "landings", "error",
        )}
        print(json.dumps(compact, ensure_ascii=False), flush=True)

    summary = _summarize(rows)
    output = {
        "run_version": RUN_VERSION,
        "status": "DEVELOPMENT_CAUSAL_ATTRIBUTION_ONLY",
        "measurement_sha": git_head(),
        "source_id": SOURCE_ID,
        "sensor_model": SENSOR_MODEL,
        "auditor_model": AUDITOR_MODEL,
        "sensor_prompt_sha256": prompt_sha256(),
        "repeats": args.repeats,
        "summary": summary,
        "runs": rows,
        "interpretation_guardrails": [
            "Each repeat is an independent Sensor realization under identical source/prompt/model settings.",
            "Within a repeat, pre-audit Sensor semantics, audited non-event semantics, and audited event-plus-non semantics are each frozen before downstream evaluation.",
            "Pre-audit downstream is diagnostic only and is not production truth.",
            "No Sensor/Auditor/Delta/Attention semantics are changed by this runner.",
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
