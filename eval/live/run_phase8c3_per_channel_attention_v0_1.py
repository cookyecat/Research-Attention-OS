from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
STEP2 = ROOT / "eval/live/results/phase8c3_native_interface_probe_v0_1/phase8c3_native_interface_probe_v0.1_20260909T135412Z.json"
OUT_DIR = ROOT / "eval/live/results/phase8c3_per_channel_attention_v0_1"
RUN_VERSION = "phase8c3-per-channel-attention-v0.1"

MATERIAL_CHANGE_MIN = 0.35
MEANINGFUL_CHANGE = 0.55
LOW_EPISTEMIC = 0.45

RANK = {"DROP": 0, "AWARE": 1, "WATCH": 2, "ENGAGE": 3}

def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
def channel_attention(effect: dict) -> dict:
    op = str(effect["operation"])
    change = float(effect["change_magnitude"])
    epi = float(effect["epistemic_strength"])
    importance = float(effect["target_importance"])

    if op in {"REINFORCE", "CHALLENGE"}:
        if change >= MEANINGFUL_CHANGE and (importance >= 0.55 or op == "CHALLENGE"):
            disposition = "ENGAGE"
        elif change >= MATERIAL_CHANGE_MIN:
            disposition = "WATCH"
        else:
            disposition = "DROP"
    elif op == "OPEN_NEW":
        if change >= 0.65 and importance >= 0.7 and epi >= LOW_EPISTEMIC:
            disposition = "ENGAGE"
        elif change >= MEANINGFUL_CHANGE:
            disposition = "WATCH"
        else:
            disposition = "DROP"
    else:
        disposition = "DROP"

    return {**effect, "channel_attention": disposition, "attention_rank": RANK[disposition]}
def main() -> int:
    data = json.loads(STEP2.read_text(encoding="utf-8"))
    rows = []
    summary = {}
    for case in ("RS05", "RS15", "RS11", "RS12"):
        case_rows = []
        for run in [r for r in data["runs"] if r.get("case") == case and r.get("status") == "OK"]:
            channels = [channel_attention(dict(e)) for e in run.get("effects") or []]
            row = {"case": case, "repeat": run["repeat"], "channels": channels}
            rows.append(row); case_rows.append(row)
        counts = Counter(c["channel_attention"] for r in case_rows for c in r["channels"])
        non_drop = Counter(
            (c["operation"], c["target"], c["channel_attention"])
            for r in case_rows for c in r["channels"] if c["channel_attention"] != "DROP"
        )
        summary[case] = {
            "n_runs": len(case_rows),
            "channel_attention_counts": dict(counts),
            "non_drop_channel_counts": {str(k): v for k, v in non_drop.items()},
        }
    output = {
        "run_version": RUN_VERSION,
        "status": "DEVELOPMENT_PER_CHANNEL_ATTENTION_ONLY",
        "measurement_sha": git_head(),
        "source_artifact": str(STEP2.relative_to(ROOT)),
        "source_artifact_sha256": hashlib.sha256(STEP2.read_bytes()).hexdigest(),
        "thresholds": {"material_change_min": MATERIAL_CHANGE_MIN, "meaningful_change": MEANINGFUL_CHANGE, "low_epistemic": LOW_EPISTEMIC},
        "summary": summary,
        "runs": rows,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"RESULT_PATH={path.relative_to(ROOT)}")
    print(f"RESULT_SHA256={hashlib.sha256(path.read_bytes()).hexdigest()}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
