"""Focused stability A/B for Phase 6A audited evidence context envelope.

Compares v0.1 semantic-only audited text vs v0.1.1 semantic+SUFFICIENT-evidence context
for RS11-E1/E2. Development-only; no Human Gold claim.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()
from app.cognitive.client import chat_json
from eval.live.standing_radar_fit_v4 import estimate_standing_radar_fit_v4
from eval.live.material_consequence_v1 import estimate_material_consequence_v1

BASE = ROOT / "eval/live/results/phase6a_aware_drop_vertical_slice_v0_1/phase6a_aware_drop_vertical_slice_v0_1_20260908T003637Z.json"
ENRICHED = ROOT / "eval/live/results/phase6a_aware_drop_vertical_slice_v0_1_1/phase6a_aware_drop_vertical_slice_v0_1_1_20260908T003719Z.json"
OUT_DIR = ROOT / "eval/live/results/phase6a_context_envelope_stability_v0_1"
EVENT_IDS = ("RS11-E1", "RS11-E2")
REPEATS = 3


def _head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _chat(model_name: str):
    def call(messages, **kwargs):
        kwargs.pop("model", None)
        return chat_json(messages, model=model_name, **kwargs)
    return call


def _rows_by_event(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(row["event_id"]): row for row in data["rows"]}


def main() -> None:
    base = _rows_by_event(BASE)
    enriched = _rows_by_event(ENRICHED)
    d_chat = _chat("deepseek-v4-pro")
    s_chat = _chat("deepseek-v4-flash")
    rows = []
    for event_id in EVENT_IDS:
        conditions = {
            "SEMANTIC_ONLY": str(base[event_id]["rendered_event_text"]),
            "SEMANTIC_PLUS_ADMITTED_EVIDENCE": str(enriched[event_id]["event_text"]),
        }
        for condition, event_text in conditions.items():
            for repeat in range(1, REPEATS + 1):
                d = estimate_standing_radar_fit_v4(event_text, chat_fn=d_chat)
                s = estimate_material_consequence_v1(event_text, chat_fn=s_chat)
                rows.append({
                    "event_id": event_id,
                    "condition": condition,
                    "repeat": repeat,
                    "D": d.get("standing_radar_fit"),
                    "S": s.get("material_consequence"),
                    "D_reason": d.get("reason"),
                    "S_reason": s.get("reason"),
                    "D_model": (d.get("model_meta") or {}).get("model"),
                    "S_model": (s.get("model_meta") or {}).get("model"),
                })

    summaries = {}
    for event_id in EVENT_IDS:
        summaries[event_id] = {}
        for condition in ("SEMANTIC_ONLY", "SEMANTIC_PLUS_ADMITTED_EVIDENCE"):
            subset = [r for r in rows if r["event_id"] == event_id and r["condition"] == condition]
            summaries[event_id][condition] = {
                "D_counts": dict(Counter(r["D"] for r in subset)),
                "S_counts": dict(Counter(r["S"] for r in subset)),
            }
    payload = {
        "name": "raos-phase6a-context-envelope-stability-v0.1",
        "status": "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION",
        "measurement_timestamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "measurement_git_head": _head(),
        "base_artifact": str(BASE),
        "enriched_artifact": str(ENRICHED),
        "repeats": REPEATS,
        "events": list(EVENT_IDS),
        "summaries": summaries,
        "rows": rows,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"phase6a_context_envelope_stability_v0_1_{payload['measurement_timestamp']}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}")
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
