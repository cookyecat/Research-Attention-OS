"""Phase17.3-KS-E single-judgment stability stress v0.10.

Runs the frozen 16 strict Direct-Answer cases for multiple independent rounds
with repeats=1. Each pair still uses the original single-pair prompt; only
scheduling is parallel.
"""
from pathlib import Path
import json
import sys
import time

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from app.cognitive.client import chat_json
from app.services.semantic_coordinate.direct_answer import (
    judge_direct_answer_parallel_consensus,
)
import eval.live.run_phase17_3_ks_e_pairwise_direct_answer_benchmark_v0_9 as base

ROUNDS = 5
MAX_WORKERS = 8


def build_pairs(data):
    specs = []
    pairs = []
    for spec in base.STRICT_CASES:
        ordinal, pkey, skey, expected, note = spec
        proposition = base.propositions_for(data, ordinal)[pkey]
        slot = base.previous_slots_for(data, ordinal)[skey]
        specs.append({
            "ordinal": ordinal,
            "proposition_key": pkey,
            "slot_key": skey,
            "expected": expected,
            "note": note,
        })
        pairs.append((proposition, slot))
    return specs, pairs
def main():
    data = json.loads(base.ARTIFACT.read_text(encoding="utf-8"))
    specs, pairs = build_pairs(data)
    rounds = []

    for round_index in range(1, ROUNDS + 1):
        started = time.perf_counter()
        judgments = judge_direct_answer_parallel_consensus(
            event_identity=base.EVENT_IDENTITY,
            pairs=pairs,
            chat_fn=chat_json,
            repeats=1,
            max_workers=MAX_WORKERS,
        )
        latency = time.perf_counter() - started
        rows = []
        for spec, judgment in zip(specs, judgments):
            rows.append({
                **spec,
                "decision": judgment.decision,
                "correct": judgment.decision == spec["expected"],
                "rationale": judgment.rationale,
            })
        round_result = {
            "round": round_index,
            "accuracy": sum(row["correct"] for row in rows) / len(rows),
            "latency_s": latency,
            "rows": rows,
        }
        rounds.append(round_result)
        print(json.dumps({
            "round": round_index,
            "accuracy": round_result["accuracy"],
            "latency_s": round(latency, 3),
            "failures": [
                {
                    "ordinal": row["ordinal"],
                    "pair": f"{row['proposition_key']}->{row['slot_key']}",
                    "expected": row["expected"],
                    "decision": row["decision"],
                }
                for row in rows
                if not row["correct"]
            ],
        }, ensure_ascii=False), flush=True)
    per_case = []
    for case_index, spec in enumerate(specs):
        decisions = [
            round_result["rows"][case_index]["decision"]
            for round_result in rounds
        ]
        per_case.append({
            **spec,
            "decisions": decisions,
            "all_rounds_stable": len(set(decisions)) == 1,
            "all_rounds_correct": all(
                decision == spec["expected"]
                for decision in decisions
            ),
        })

    total = len(specs) * ROUNDS
    correct = sum(
        row["correct"]
        for round_result in rounds
        for row in round_result["rows"]
    )
    result = {
        "benchmark": "phase17.3-ks-e-single-judgment-stability-v0.10",
        "round_count": ROUNDS,
        "strict_case_count": len(specs),
        "judgment_count": total,
        "accuracy": correct / total,
        "fully_stable_case_count": sum(
            row["all_rounds_stable"] for row in per_case
        ),
        "fully_correct_case_count": sum(
            row["all_rounds_correct"] for row in per_case
        ),
        "mean_round_latency_s": sum(
            row["latency_s"] for row in rounds
        ) / len(rounds),
        "max_workers": MAX_WORKERS,
        "per_case": per_case,
        "rounds": rounds,
    }

    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_e_single_judgment_stability_v0_10"
        / "phase17_3_ks_e_single_judgment_stability_v0_10.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "benchmark": result["benchmark"],
        "round_count": result["round_count"],
        "strict_case_count": result["strict_case_count"],
        "judgment_count": result["judgment_count"],
        "accuracy": result["accuracy"],
        "fully_stable_case_count": result["fully_stable_case_count"],
        "fully_correct_case_count": result["fully_correct_case_count"],
        "mean_round_latency_s": round(result["mean_round_latency_s"], 3),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
