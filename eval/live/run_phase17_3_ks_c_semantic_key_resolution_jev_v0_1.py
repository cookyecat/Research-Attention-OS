"""Phase17.3-KS-C Jev longitudinal benchmark integration.

Connects replay artifacts with semantic coordinate resolution.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for p in (ROOT, BACKEND):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.services.event_state_semantic_key_resolver import resolve_key

SOURCE = ROOT / "eval/live/results/phase17_jev_longitudinal_state_replay_v0_5"
OUT = ROOT / "eval/live/results/phase17_3_ks_c_semantic_key_resolution_jev_v0_1"


def pick_source():
    return sorted(SOURCE.glob("*n8*.json"))[-1]


def main():
    source = pick_source()
    data = json.loads(source.read_text())
    facts = data.get("summary", {}).get("final_fact_state", {}).get("facts", [])
    slots = [{
        "slot_key": f.get("fact_id", "unknown"),
        "primitive_family": "OTHER",
        "state_question": f.get("text", "")[:120],
    } for f in facts]
    result = {
        "benchmark": "phase17.3-ks-c-jev-longitudinal-v0.1",
        "source": str(source.relative_to(ROOT)),
        "input_fact_count": len(facts),
        "sample_resolutions": [],
    }
    for slot in slots[:20]:
        result["sample_resolutions"].append(resolve_key(
            event_identity="Jev",
            current_slots=slots,
            proposition=slot,
        ).model_dump())
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "phase17_3_ks_c_jev_resolution_v0_1.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(out.relative_to(ROOT))

if __name__ == "__main__":
    main()
