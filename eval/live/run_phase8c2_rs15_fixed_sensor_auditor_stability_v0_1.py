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

from eval.live.phase8c2_production_sensor_bridge_v0_1 import _audit_non_event_units
from eval.live.run_phase8c2_production_sensor_bridge_ab_v0_1 import _load_manifest
from eval.live.run_phase8c2_rs15_event_projection_ablation_v0_1 import _hash_units
from eval.live.run_phase8c2_rs15_flash_realization_stability_v0_1 import (
    _forced_chat, _landing, _run_frozen_downstream,
)

SOURCE_ID = "RS15"
AUDITOR_MODEL = "deepseek-v4-flash"
RUN_VERSION = "phase8c2-rs15-fixed-sensor-auditor-stability-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase8c2_rs15_fixed_sensor_auditor_stability_v0_1"
SOURCE_ARTIFACT = ROOT / (
    "eval/live/results/phase8c2_rs15_flash_realization_stability_v0_1/"
    "phase8c2_rs15_flash_realization_stability_v0.1_20260909T093742Z.json"
)
SOURCE_ARTIFACT_SHA256 = "207878ba7fe23758cb0a8009e38f52b9d38452cc72e0f52d35a44a121d202490"
FIXED_REALIZATION_REPEAT = 2


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _load_fixed_sensor_units() -> tuple[list[dict[str, Any]], str]:
    raw = SOURCE_ARTIFACT.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_ARTIFACT_SHA256:
        raise RuntimeError(f"source artifact sha mismatch: {digest}")
    data = json.loads(raw)
    row = next(r for r in data["runs"] if int(r["repeat"]) == FIXED_REALIZATION_REPEAT)
    units = list(row["sensor_non_event_units"])
    if _hash_units(units) != row["sensor_non_event_sha256"]:
        raise RuntimeError("fixed Sensor semantic hash mismatch")
    return units, digest

def _target(landing: list[Any]) -> str:
    return str(landing[1] or "NONE")


def _verdict_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(
        str((row.get("audit_result") or {}).get("verdict") or "UNSCORABLE")
        for row in rows
    ).items()))


def _run_baseline(case: dict[str, Any], units: list[dict[str, Any]], repeats: int):
    rows = []
    for repeat in range(1, repeats + 1):
        result = _run_frozen_downstream(case, units, label=f"fixed-sensor-preaudit:r{repeat}")
        landing = _landing(result)
        rows.append({"repeat": repeat, "landing": landing, "result": result})
        print(json.dumps({
            "stage": "BASELINE_PREAUDIT", "repeat": repeat, "landing": landing,
        }, ensure_ascii=False), flush=True)
    return rows


def _one_audit(case: dict[str, Any], units: list[dict[str, Any]], audit_repeat: int, downstream_repeats: int):
    rows, admitted = _audit_non_event_units(
        f"fixed-rs15-{audit_repeat}", units, chat_fn=_forced_chat(AUDITOR_MODEL)
    )
    downstream = []
    for drep in range(1, downstream_repeats + 1):
        result = _run_frozen_downstream(
            case, admitted, label=f"audit{audit_repeat}:downstream{drep}"
        )
        downstream.append({"repeat": drep, "landing": _landing(result), "result": result})
    return {
        "audit_repeat": audit_repeat,
        "verdict_counts": _verdict_counts(rows),
        "n_admitted": len(admitted),
        "admitted_sha256": _hash_units(admitted),
        "admitted_units": admitted,
        "audit_rows": rows,
        "downstream": downstream,
    }

def _summarize(baseline, audits):
    baseline_landings = [row["landing"] for row in baseline]
    audit_landings = [
        drow["landing"] for audit in audits for drow in audit["downstream"]
    ]
    return {
        "baseline_downstream_only": {
            "n_runs": len(baseline_landings),
            "target_counts": dict(sorted(Counter(_target(x) for x in baseline_landings).items())),
            "landings": baseline_landings,
        },
        "auditor": {
            "n_audits": len(audits),
            "admitted_counts": [row["n_admitted"] for row in audits],
            "unique_admitted_semantic_realizations": len({row["admitted_sha256"] for row in audits}),
            "verdict_counts_by_audit": [row["verdict_counts"] for row in audits],
        },
        "audited_downstream": {
            "n_runs": len(audit_landings),
            "target_counts": dict(sorted(Counter(_target(x) for x in audit_landings).items())),
            "landings": audit_landings,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-repeats", type=int, default=6)
    parser.add_argument("--audit-repeats", type=int, default=6)
    parser.add_argument("--downstream-repeats-per-audit", type=int, default=2)
    args = parser.parse_args()
    case = dict(_load_manifest()["cases"][SOURCE_ID])
    units, source_artifact_sha = _load_fixed_sensor_units()
    baseline = _run_baseline(case, units, args.baseline_repeats)
    audits = []
    for repeat in range(1, args.audit_repeats + 1):
        row = _one_audit(case, units, repeat, args.downstream_repeats_per_audit)
        audits.append(row)
        print(json.dumps({
            "stage": "AUDIT", "audit_repeat": repeat,
            "n_admitted": row["n_admitted"],
            "admitted_sha256": row["admitted_sha256"],
            "landings": [x["landing"] for x in row["downstream"]],
        }, ensure_ascii=False), flush=True)

    summary = _summarize(baseline, audits)
    output = {
        "run_version": RUN_VERSION,
        "status": "DEVELOPMENT_CAUSAL_ATTRIBUTION_ONLY",
        "measurement_sha": git_head(),
        "source_id": SOURCE_ID,
        "auditor_model": AUDITOR_MODEL,
        "source_artifact": str(SOURCE_ARTIFACT.relative_to(ROOT)),
        "source_artifact_sha256": source_artifact_sha,
        "fixed_realization_repeat": FIXED_REALIZATION_REPEAT,
        "fixed_sensor_semantic_sha256": _hash_units(units),
        "fixed_sensor_units": units,
        "baseline": baseline,
        "audits": audits,
        "summary": summary,
        "interpretation_guardrails": [
            "Sensor output is frozen from one prior Flash realization and never regenerated.",
            "Baseline repeats quantify downstream-only instability on an identical semantic input.",
            "Audit repeats independently re-audit the exact same Sensor units with the same Auditor model.",
            "Each audited semantic realization is evaluated repeatedly downstream to avoid attributing downstream randomness to the Auditor.",
            "This experiment excludes event projection by design; it isolates the non-event Auditor boundary.",
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
