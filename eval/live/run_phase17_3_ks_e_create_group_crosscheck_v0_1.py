"""Minimal ordinal-8 CREATE-group cross-direct audit."""
from pathlib import Path
import json
import sys
import time

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
sys.path.insert(0, str(ROOT / "backend"))

from app.cognitive.client import chat_json
from app.services.semantic_coordinate.direct_answer import (
    judge_direct_answer_parallel_consensus,
)

ARTIFACT = ROOT / (
    "eval/live/results/phase17_jev_longitudinal_state_replay_v0_7/"
    "phase17_jev_longitudinal_state_replay_v0.7_n8_20260922T122031Z.json"
)

EVENT_IDENTITY = {
    "object": "Jev model",
    "event_type": "MODEL_LAUNCH_EARLY_VALIDATION",
}

def main():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    step = next(row for row in data["trajectory"] if row["ordinal"] == 8)
    props = {
        f"P{i:03d}": row
        for i, row in enumerate(
            step["proposition_flatmap"]["world_propositions"], 1
        )
    }
    integration_slot = {
        "slot_id": "NEW_RELATION_INTEGRATION",
        "primitive_family": "RELATION",
        "slot_label": "External integration and deployment context",
        "state_question": (
            "In what external systems or workflows is this system "
            "integrated or deployed?"
        ),
    }
    resemblance_slot = {
        "slot_id": "NEW_RELATION_RESEMBLANCE",
        "primitive_family": "RELATION",
        "slot_label": "System composition resemblance",
        "state_question": (
            "What broader system pattern does this system's "
            "composition resemble?"
        ),
    }
    specs = [
        ("P001", integration_slot),
        ("P002", integration_slot),
        ("P005", integration_slot),
        ("P005", resemblance_slot),
        ("P001", resemblance_slot),
        ("P002", resemblance_slot),
    ]
    pairs = [(props[pkey], slot) for pkey, slot in specs]
    started = time.perf_counter()
    rows = judge_direct_answer_parallel_consensus(
        event_identity=EVENT_IDENTITY,
        pairs=pairs,
        chat_fn=chat_json,
        repeats=2,
        max_workers=8,
    )
    result = []
    for (pkey, slot), row in zip(specs, rows):
        result.append({
            "pair": f"{pkey}->{slot['slot_id']}",
            "decision": row.decision,
            "rationale": row.rationale,
        })
    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_e_create_group_crosscheck_v0_1"
        / "phase17_3_ks_e_create_group_crosscheck_v0_1.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "latency_s": time.perf_counter() - started,
                "results": result,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
