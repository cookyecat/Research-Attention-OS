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

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app.cognitive.factory import get_provider
from app.services.pipeline import run_pipeline
from eval.live.phase8c2_production_sensor_bridge_v0_1 import SemanticSensorProductionBridgeV0_1
from eval.live.run_phase8c2_production_sensor_bridge_ab_v0_1 import _arm_summary, _base_world, _load_manifest

RUN_VERSION = "phase8c2-cross-case-stability-controls-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase8c2_cross_case_stability_controls_v0_1"
CASES = ("RS05", "RS11")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _landing(row: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    update = row.get("update") or {}
    attention = row.get("attention") or {}
    return (
        update.get("operation"),
        update.get("target_fixture_code"),
        attention.get("disposition"),
        attention.get("expected_output"),
    )


def _compact(row: dict[str, Any]) -> dict[str, Any]:
    path = row.get("extraction_path") or {}
    diag = path.get("diagnostics") or {}
    sources = diag.get("sources") or []
    sensor = (sources[0].get("sensor") or {}) if sources else {}
    auditor = (sources[0].get("auditor") or {}) if sources else {}
    return {
        "case": row.get("case"),
        "repeat": row.get("repeat"),
        "status": row.get("status"),
        "landing": list(_landing(row)) if row.get("status") == "OK" else None,
        "sensor_n_non_event_units": sensor.get("n_non_event_units"),
        "auditor_n_non_event_admitted": auditor.get("n_non_event_admitted"),
        "auditor_n_event_units_admitted": auditor.get("n_event_units_admitted"),
        "error": row.get("error"),
    }


def _run_case(case_id: str, case: dict[str, Any], repeat: int) -> dict[str, Any]:
    engine, db, source, code_by_id = _base_world(case_id, case)
    provider = get_provider()
    bridge = SemanticSensorProductionBridgeV0_1()
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
        summary.update({
            "case": case_id,
            "repeat": repeat,
            "status": "OK",
            "error": None,
        })
        return summary
    except Exception as exc:
        return {
            "case": case_id,
            "repeat": repeat,
            "status": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc)[:3000],
        }
    finally:
        db.close()
        engine.dispose()


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for case_id in CASES:
        items = [row for row in rows if row.get("case") == case_id]
        ok = [row for row in items if row.get("status") == "OK"]
        landing_counts = Counter(str(_landing(row)) for row in ok)
        out[case_id] = {
            "n_runs": len(items),
            "n_ok": len(ok),
            "n_errors": len(items) - len(ok),
            "landing_counts": dict(landing_counts),
            "landings": [list(_landing(row)) for row in ok],
            "stable_landing": (
                list(_landing(ok[0]))
                if ok and all(_landing(row) == _landing(ok[0]) for row in ok)
                else None
            ),
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=6)
    args = parser.parse_args()
    if args.repeats < 1:
        raise SystemExit("--repeats must be >= 1")

    manifest = _load_manifest()
    rows: list[dict[str, Any]] = []
    for repeat in range(1, args.repeats + 1):
        for case_id in CASES:
            case = dict(manifest["cases"][case_id])
            row = _run_case(case_id, case, repeat)
            rows.append(row)
            print(json.dumps(_compact(row), ensure_ascii=False), flush=True)

    summary = _summarize(rows)
    output = {
        "run_version": RUN_VERSION,
        "status": "DEVELOPMENT_STABILITY_CONTROL_ONLY",
        "measurement_sha": git_head(),
        "cases": list(CASES),
        "repeats": args.repeats,
        "summary": summary,
        "runs": rows,
        "interpretation_guardrails": [
            "RS05 and RS11 are established non-RS15 canonical controls from Phase 7A/8C.2.",
            "Each repeat is a fresh current Sensor v0.2.6 + Auditor v0.1.1 + production downstream realization.",
            "The experiment tests whether RS15-style landing instability generalizes to stable control cases.",
            "No production semantics, prompts, thresholds, or policy code are changed by this runner.",
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
