from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.phase6b_cognitive_semantics_v0_1 import (
    COGNITIVE_SLICE_VERSION,
    admitted_epistemic_units,
    audit_epistemic_unit_edge,
    project_epistemic_unit_edge,
)
from eval.live.run_standing_radar_fit_eval import git_head, load_repo_env
from eval.live.semantic_evidence_auditor_v0_1_1 import AUDITOR_VERSION, PROMPT_VERSION, prompt_sha256

DEFAULT_SENSOR = ROOT / "eval/live/results/semantic_evidence_dev_v0_2_3/semantic_evidence_dev_v0_2_3_20260907T204332Z.json"
DEFAULT_OUT_DIR = ROOT / "eval/live/results/phase6b_epistemic_unit_audit_v0_1"


def run(sensor_path: Path) -> dict:
    load_repo_env()
    sensor = json.loads(sensor_path.read_text(encoding="utf-8"))
    source_rows = []
    all_audits = []
    actual_models = set()
    for source_row in sensor["sources"]:
        source_id = source_row["source"]["source_id"]
        units = (source_row.get("batch") or {}).get("non_event_units") or []
        audits = []
        for unit in units:
            edge = project_epistemic_unit_edge(source_id, unit)
            row = audit_epistemic_unit_edge(edge)
            audits.append(row)
            all_audits.append(row)
            meta = row.get("model_meta") or {}
            if meta.get("model"):
                actual_models.add(str(meta["model"]))
        admitted = admitted_epistemic_units(audits)
        source_rows.append({
            "source_id": source_id,
            "n_units": len(units),
            "n_scorable": sum(bool(r.get("scorable")) for r in audits),
            "n_sufficient": len(admitted),
            "audits": audits,
            "admitted_units": admitted,
        })

    reason_counts = Counter(
        (r.get("audit_result") or {}).get("reason_code") or r.get("failure_kind") or "UNKNOWN"
        for r in all_audits
    )
    return {
        "name": "raos-phase6b-epistemic-unit-audit-v0.1",
        "status": "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION",
        "measurement_timestamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "measurement_git_head": git_head(),
        "cognitive_slice_version": COGNITIVE_SLICE_VERSION,
        "input_sensor_artifact": str(sensor_path),
        "auditor": {
            "version": AUDITOR_VERSION,
            "prompt_version": PROMPT_VERSION,
            "prompt_sha256": prompt_sha256(),
        },
        "actual_models": sorted(actual_models),
        "n_sources": len(source_rows),
        "n_units": len(all_audits),
        "n_scorable": sum(bool(r.get("scorable")) for r in all_audits),
        "n_sufficient": sum(
            bool(r.get("scorable")) and (r.get("audit_result") or {}).get("verdict") == "SUFFICIENT"
            for r in all_audits
        ),
        "reason_counts": dict(sorted(reason_counts.items())),
        "sources": source_rows,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sensor", type=Path, default=DEFAULT_SENSOR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    payload = run(args.sensor)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"phase6b_epistemic_unit_audit_v0_1_{payload['measurement_timestamp']}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps({
        "n_sources": payload["n_sources"],
        "n_units": payload["n_units"],
        "n_scorable": payload["n_scorable"],
        "n_sufficient": payload["n_sufficient"],
        "reason_counts": payload["reason_counts"],
        "per_source": [
            {
                "source_id": row["source_id"],
                "n_units": row["n_units"],
                "n_sufficient": row["n_sufficient"],
            }
            for row in payload["sources"]
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
