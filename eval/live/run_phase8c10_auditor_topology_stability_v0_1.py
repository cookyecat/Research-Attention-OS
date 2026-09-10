from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for p in (ROOT, BACKEND):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from eval.live.phase8c2_production_sensor_bridge_v0_1 import _audit_non_event_units
from eval.live.run_phase8c2_rs15_flash_realization_stability_v0_1 import _forced_chat
from eval.live.topology_stability_metrics_v0_1 import summarize_topology_stability, jaccard, execution_snapshot

AUDITOR_MODEL = "deepseek-v4-flash"
RUN_VERSION = "phase8c10-auditor-topology-stability-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase8c10_auditor_topology_stability_v0_1"

HIST_SENSOR = ROOT / "eval/live/results/semantic_evidence_dev_v0_2_6/semantic_evidence_dev_v0_2_6_20260908T090345Z.json"
HIST_SENSOR_SHA = "212f7e1569946485de469de1f8484fad3aa192d5d0266a8616e92c5e72826ddc"
REG_SENSOR = ROOT / "eval/live/results/semantic_evidence_dev_v0_2_6_regression/semantic_evidence_dev_v0_2_6_20260908T091024Z.json"
REG_SENSOR_SHA = "b05b52c272e87543a1929726d096c640bf97169d9da536a007d11d5cd0f2fb27"

HIST_AUDIT = ROOT / "eval/live/results/phase7a_v0_2_6_epistemic_audit_v0_1/phase6b_epistemic_unit_audit_v0_1_20260908T090628Z.json"
REG_AUDIT = ROOT / "eval/live/results/phase7a_v0_2_6_regression_audit_v0_1/phase6b_epistemic_unit_audit_v0_1_20260908T094903Z.json"
CASES = ("RS05", "RS15", "RS11", "RS12")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def verify(path: Path, expected: str) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(f"artifact SHA mismatch {path}: {actual}")


def _sensor_row(case_id: str):
    path, expected = (HIST_SENSOR, HIST_SENSOR_SHA) if case_id in {"RS05", "RS15"} else (REG_SENSOR, REG_SENSOR_SHA)
    verify(path, expected)
    data = json.loads(path.read_text())
    row = next(x for x in data["sources"] if x["source"]["source_id"] == case_id)
    return list(row["batch"].get("non_event_units") or []), {
        "artifact": str(path.relative_to(ROOT)), "sha256": expected,
        "sensor_version": "semantic-sensor-v0.2.6",
    }


def _historical_reference(case_id: str):
    path = HIST_AUDIT if case_id in {"RS05", "RS15"} else REG_AUDIT
    data = json.loads(path.read_text())
    row = next(x for x in data["sources"] if x["source_id"] == case_id)
    ids = tuple(sorted(a["unit_id"] for a in row.get("audits") or [] if (a.get("audit_result") or {}).get("verdict") == "SUFFICIENT"))
    return ids, {
        "artifact": str(path.relative_to(ROOT)),
        "auditor": data.get("auditor"),
        "actual_models": data.get("actual_models"),
    }


def _verdict_counts(rows):
    return dict(sorted(Counter(str((r.get("audit_result") or {}).get("verdict") or "UNSCORABLE") for r in rows).items()))


def run_case(case_id: str, repeats: int):
    units, sensor_meta = _sensor_row(case_id)
    candidate_ids = {str(u["unit_id"]) for u in units}
    reference_ids, reference_meta = _historical_reference(case_id)
    runs = []
    for repeat in range(1, repeats + 1):
        try:
            audit_rows, admitted = _audit_non_event_units(
                f"phase8c10-{case_id}-r{repeat}", units, chat_fn=_forced_chat(AUDITOR_MODEL)
            )
            admitted_ids = tuple(sorted(str(u["unit_id"]) for u in admitted))
            if not set(admitted_ids).issubset(candidate_ids):
                raise RuntimeError("Auditor admitted a unit not present in frozen Sensor candidates")
            row = {
                "repeat": repeat, "status": "OK",
                "admitted_ids": admitted_ids,
                "admitted_units": admitted,
                "verdict_counts": _verdict_counts(audit_rows),
                "audit_rows": audit_rows,
                "reference_jaccard": jaccard(admitted_ids, reference_ids),
                "reference_exact": admitted_ids == reference_ids,
            }
        except Exception as exc:
            row = {"repeat": repeat, "status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:3000]}
        runs.append(row)
        print(json.dumps({
            "case": case_id, "repeat": repeat, "status": row["status"],
            "admitted_ids": row.get("admitted_ids"),
            "verdict_counts": row.get("verdict_counts"),
            "reference_jaccard": row.get("reference_jaccard"),
            "error": row.get("error"),
        }, ensure_ascii=False), flush=True)

    ok = [r for r in runs if r["status"] == "OK"]
    report = summarize_topology_stability([r["admitted_ids"] for r in ok])
    return {
        "case": case_id,
        "sensor": sensor_meta,
        "reference": {**reference_meta, "admitted_ids": reference_ids},
        "n_candidates": len(units),
        "metrics": report.as_dict(),
        "reference_exact_rate": sum(r["reference_exact"] for r in ok) / len(ok) if ok else 0.0,
        "mean_reference_jaccard": sum(r["reference_jaccard"] for r in ok) / len(ok) if ok else 0.0,
        "runs": runs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=4)
    args = parser.parse_args()
    results = [run_case(case_id, args.repeats) for case_id in CASES]
    summary = {
        r["case"]: {
            "n_candidates": r["n_candidates"],
            "exact_mode_rate": r["metrics"]["exact_mode_rate"],
            "mean_pairwise_jaccard": r["metrics"]["mean_pairwise_jaccard"],
            "entropy_bits": r["metrics"]["entropy_bits"],
            "reference_exact_rate": r["reference_exact_rate"],
            "mean_reference_jaccard": r["mean_reference_jaccard"],
        }
        for r in results
    }
    output = {
        "run_version": RUN_VERSION,
        "status": "AUDITOR_GATE2A_FROZEN_SENSOR",
        "measurement_sha": git_head(),
        "auditor_model": AUDITOR_MODEL,
        "auditor_version": "semantic-evidence-auditor-v0.1.1",
        "repeats": args.repeats,
        "metrics_chip": execution_snapshot(),
        "scope": "non-event Auditor boundary only",
        "results": results,
        "summary": summary,
        "guardrails": [
            "Sensor candidate units are frozen from exact Phase 7A v0.2.6 artifacts.",
            "Historical Phase 7A audit is a reference only, not counted as a fresh repeat.",
            "No downstream LLM is called in Gate 2A.",
            "Only materially variable admitted worlds may trigger Gate 2B.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"RESULT_PATH={path.relative_to(ROOT)}")
    print(f"RESULT_SHA256={hashlib.sha256(path.read_bytes()).hexdigest()}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
