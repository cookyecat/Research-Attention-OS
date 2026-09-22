from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.cognitive.client import chat_json

RUN_VERSION = "phase17-semantic-slot-reuse-n8-to-n20-v0.1"
N20 = ROOT / "eval/live/results/phase17_jev_longitudinal_state_replay_v0_5/phase17_jev_longitudinal_state_replay_v0.5_n20_20260921T193833Z.json"
N8_DIR = ROOT / "eval/live/results/phase17_current_fact_semantic_key_discovery_n8_v0_1"
OUT_DIR = ROOT / "eval/live/results/phase17_semantic_slot_reuse_n8_to_n20_v0_1"

SYSTEM = """You are testing a keyed materialized-view representation for RAOS.

Commercial upsert systems keep a stable primary/upsert key and update its current value. We already have a set of semantic state slots discovered at an earlier time. Treat their slot_key values as stable identities: REUSE an existing key whenever the new facts answer the same broad current-state question. Do not rename existing keys. Create a new key only when the new information truly answers a distinct state question that cannot be represented in an existing slot without making that slot incoherent.

One evidence/fact may contribute to more than one slot if it genuinely affects multiple state dimensions. Peripheral items may be DROP_FROM_CURRENT.

Return JSON only:
{
  "updated_slots": [
    {
      "slot_key": "existing_or_new_key",
      "origin": "REUSED | CREATED",
      "state_question": "...",
      "member_fact_ids": ["..."],
      "current_value": "...",
      "reason": "..."
    }
  ],
  "drop_from_current": [{"fact_id":"...","reason":"..."}],
  "diagnostics": {
    "reused_slot_count": 0,
    "created_slot_count": 0,
    "final_slot_count": 0,
    "input_fact_count": 0
  }
}
"""

def main():
    n8_file = sorted(N8_DIR.glob("*.json"))[-1]
    n8 = json.loads(n8_file.read_text())["result"]
    n20 = json.loads(N20.read_text())
    facts = n20["summary"]["final_fact_state"]["facts"]
    existing = [
        {
            "slot_key": s["slot_key"],
            "state_question": s["state_question"],
            "previous_value": s["merged_current_value"],
        }
        for s in n8["slots"]
    ]
    payload = {
        "event_identity": {
            "title": "Jev model launch / emergence and early validation episode",
            "event_type": "MODEL_LAUNCH_EARLY_VALIDATION",
            "action": "launch, explain, test, and early-validate Jev",
            "object": "Jev model",
        },
        "existing_slots_from_n8": existing,
        "current_facts_at_n20": [
            {"fact_id": f["fact_id"], "text": f["text"]} for f in facts
        ],
    }
    result, usage = chat_json(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        timeout=120.0,
        thinking="disabled",
    )
    out = {
        "run_version": RUN_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "n8_key_source": str(n8_file.relative_to(ROOT)),
        "n20_source": str(N20.relative_to(ROOT)),
        "usage": usage,
        "result": result,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
