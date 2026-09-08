from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.phase7c_brain_authority_probe_v0_1 import PROBE_VERSION, run_all

OUT_DIR = ROOT / "eval/live/results/phase7c_brain_authority_probe_v0_1"


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def main() -> int:
    rows = run_all()
    payload = {
        "name": "raos-phase7c-brain-authority-probe-v0.1",
        "status": "DEVELOPMENT_CONTROLLED_BRAIN_STATE_PROBE",
        "measurement_timestamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "measurement_git_head": git_head(),
        "probe_version": PROBE_VERSION,
        "n_cases": len(rows),
        "n_match": sum(bool(row["match"]) for row in rows),
        "rows": rows,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"phase7c_brain_authority_probe_v0_1_{payload['measurement_timestamp']}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps({
        "head": payload["measurement_git_head"],
        "n_cases": payload["n_cases"],
        "n_match": payload["n_match"],
        "cases": [
            {
                "case_id": row["case_id"],
                "trusted_threat": row["trusted_threat"],
                "actual_preempt": row["actual_preempt"],
                "disposition": row["disposition"],
                "urgency": row["urgency"],
            }
            for row in rows
        ],
    }, ensure_ascii=False, indent=2))
    return 0 if payload["n_match"] == payload["n_cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
