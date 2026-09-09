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
from eval.live.phase6b_cognitive_semantics_v0_1 import admitted_epistemic_units
from eval.live.run_phase8c2_production_sensor_bridge_ab_v0_1 import _arm_summary, _base_world, _load_manifest
from eval.live.run_phase8c2_rs15_event_projection_ablation_v0_1 import FrozenExtractionBridge, _hash_units, _make_extraction

SOURCE_ID = "RS05"
RUN_VERSION = "phase8c2-rs05-historical-downstream-stability-v0.1"
HIST_AUDIT = ROOT / (
    "eval/live/results/phase7a_v0_2_6_epistemic_audit_v0_1/"
    "phase6b_epistemic_unit_audit_v0_1_20260908T090628Z.json"
)
OUT_DIR = ROOT / "eval/live/results/phase8c2_rs05_historical_downstream_stability_v0_1"


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _load_hist4() -> tuple[list[dict[str, Any]], str]:
    raw = HIST_AUDIT.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw)
    source = next(row for row in data["sources"] if row.get("source_id") == SOURCE_ID)
    units = admitted_epistemic_units(list(source.get("audits") or []))
    if len(units) != 4:
        raise RuntimeError(f"expected 4 historical RS05 admitted units, got {len(units)}")
    return units, sha


def _landing(row: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    update = row.get("update") or {}
    attention = row.get("attention") or {}
    return (
        update.get("operation"),
        update.get("target_fixture_code"),
        attention.get("disposition"),
        attention.get("expected_output"),
    )


def _run_once(case: dict[str, Any], units: list[dict[str, Any]], repeat: int) -> dict[str, Any]:
    engine, db, source, code_by_id = _base_world(SOURCE_ID, case)
    provider = get_provider()
    extraction = _make_extraction(units, event_title=source.title or SOURCE_ID)
    bridge = FrozenExtractionBridge(
        condition=f"{RUN_VERSION}:HIST4_PHASE7A",
        extraction=extraction,
        semantic_hash=_hash_units(units),
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
        summary.update({"repeat": repeat, "status": "OK", "error": None})
        return summary
    except Exception as exc:
        return {
            "repeat": repeat,
            "status": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc)[:3000],
        }
    finally:
        db.close()
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=6)
    args = parser.parse_args()
    if args.repeats < 1:
        raise SystemExit("--repeats must be >= 1")
    manifest = _load_manifest()
    case = dict(manifest["cases"][SOURCE_ID])
    units, audit_sha = _load_hist4()
    rows: list[dict[str, Any]] = []
    for repeat in range(1, args.repeats + 1):
        row = _run_once(case, units, repeat)
        rows.append(row)
        print(json.dumps({
            "repeat": repeat,
            "status": row.get("status"),
            "landing": list(_landing(row)) if row.get("status") == "OK" else None,
            "error": row.get("error"),
        }, ensure_ascii=False), flush=True)

    ok = [row for row in rows if row.get("status") == "OK"]
    counts = Counter(str(_landing(row)) for row in ok)
    summary = {
        "n_runs": len(rows),
        "n_ok": len(ok),
        "n_errors": len(rows) - len(ok),
        "landing_counts": dict(counts),
        "landings": [list(_landing(row)) for row in ok],
        "stable_landing": (
            list(_landing(ok[0]))
            if ok and all(_landing(row) == _landing(ok[0]) for row in ok)
            else None
        ),
    }
    output = {
        "run_version": RUN_VERSION,
        "status": "DEVELOPMENT_STABILITY_CONTROL_ONLY",
        "measurement_sha": git_head(),
        "source_id": SOURCE_ID,
        "kernel_fixture": case["kernel_fixture"],
        "historical_audit_artifact": str(HIST_AUDIT.relative_to(ROOT)),
        "historical_audit_sha256": audit_sha,
        "historical_semantic_sha256": _hash_units(units),
        "historical_units": units,
        "summary": summary,
        "runs": rows,
        "interpretation_guardrails": [
            "The Phase 7A canonical four admitted RS05 units are frozen across all repeats.",
            "Only the current production Locate/Delta/Attention realization is repeated.",
            "This distinguishes downstream decision-boundary instability from current Sensor/Auditor realization instability.",
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
