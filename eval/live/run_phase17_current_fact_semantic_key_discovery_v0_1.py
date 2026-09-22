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

RUN_VERSION = "phase17-current-fact-semantic-key-discovery-v0.1"
SOURCE = ROOT / "eval/live/results/phase17_jev_longitudinal_state_replay_v0_5/phase17_jev_longitudinal_state_replay_v0.5_n20_20260921T193833Z.json"
OUT_DIR = ROOT / "eval/live/results/phase17_current_fact_semantic_key_discovery_v0_1"

SYSTEM = """You are evaluating a candidate RAOS current-state representation.

Commercial streaming systems such as Kafka compacted logs, KTables, Flink upsert tables, and Materialize UPSERT rely on a stable key: updates with the same key replace or revise the current value instead of creating another live row.

Your task is semantic-key discovery, NOT summarization.

Given:
- one coarse Event Identity
- a set of currently live derived facts

Infer the smallest defensible set of dynamic semantic state keys such that:
1. facts answering the same current-state question share one key;
2. each key has at most one normal live merged value (unless explicitly contested);
3. keys are coarse enough to absorb later examples without one-fact-per-source growth;
4. keys are not a fixed global ontology; derive them from this Event;
5. do not merge genuinely independent dimensions merely to reduce count;
6. preserve important uncertainty/validation distinctions;
7. peripheral details that should not be Current State may be marked DROP_FROM_CURRENT.

Return JSON only:
{
  "slots": [
    {
      "slot_key": "stable_snake_case_key",
      "state_question": "what current-state question this slot answers",
      "member_fact_ids": ["..."],
      "merged_current_value": "one concise current value",
      "reason": "why these facts are the same state dimension"
    }
  ],
  "drop_from_current": [
    {"fact_id": "...", "reason": "..."}
  ],
  "diagnostics": {
    "input_fact_count": 0,
    "slot_count": 0,
    "drop_count": 0
  }
}
"""

def main():
    report = json.loads(SOURCE.read_text())
    facts = report["summary"]["final_fact_state"]["facts"]
    payload = {
        "event_identity": {
            "title": "Jev model launch / emergence and early validation episode",
            "event_type": "MODEL_LAUNCH_EARLY_VALIDATION",
            "action": "launch, explain, test, and early-validate Jev",
            "object": "Jev model",
            "time_context": "2026-09-16 through 2026-09-20 emergence episode",
        },
        "current_facts": [
            {"fact_id": f["fact_id"], "text": f["text"]}
            for f in facts
        ],
    }
    result, usage = chat_json([
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
    ], timeout=120.0, thinking="disabled")
    out = {
        "run_version": RUN_VERSION,
        "source": str(SOURCE.relative_to(ROOT)),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_fact_count": len(facts),
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
