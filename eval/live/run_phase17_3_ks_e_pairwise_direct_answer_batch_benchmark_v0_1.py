"""Phase17.3-KS-E batched Direct-Answer transport benchmark v0.1."""
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
    judge_direct_answer_batch,
)
import eval.live.run_phase17_3_ks_e_pairwise_direct_answer_benchmark_v0_9 as ref

SERIAL_RESULT = ROOT / (
    "eval/live/results/phase17_3_ks_e_pairwise_direct_answer_v0_9/"
    "phase17_3_ks_e_pairwise_direct_answer_v0_9.json"
)


def materialize_case(data, spec):
    ordinal, pkey, skey, expected, note = spec
    proposition = ref.propositions_for(data, ordinal)[pkey]
    slot = ref.previous_slots_for(data, ordinal)[skey]
    return {
        "ordinal": ordinal,
        "proposition_key": pkey,
        "slot_key": skey,
        "expected": expected,
        "note": note,
        "proposition": proposition,
        "slot": slot,
    }
def main():
    data = json.loads(ref.ARTIFACT.read_text(encoding="utf-8"))
    cases = [
        materialize_case(data, spec)
        for spec in [*ref.STRICT_CASES, *ref.EXPLORATORY_CASES]
    ]
    pairs = [
        (case["proposition"], case["slot"])
        for case in cases
    ]

    repeats = 2
    run_rows = []
    total_latency = 0.0
    for repeat in range(1, repeats + 1):
        started = time.perf_counter()
        judgments = judge_direct_answer_batch(
            event_identity=ref.EVENT_IDENTITY,
            pairs=pairs,
            chat_fn=chat_json,
        )
        latency = time.perf_counter() - started
        total_latency += latency
        if len(judgments) != len(cases):
            raise RuntimeError("batch judgment cardinality mismatch")
        run_rows.append({
            "repeat": repeat,
            "latency_s": latency,
            "judgments": [
                {
                    "ordinal": case["ordinal"],
                    "proposition_key": case["proposition_key"],
                    "slot_key": case["slot_key"],
                    "expected": case["expected"],
                    "decision": judgment.decision,
                    "rationale": judgment.rationale,
                }
                for case, judgment in zip(cases, judgments)
            ],
        })

    by_case = []
    for index, case in enumerate(cases):
        decisions = [
            row["judgments"][index]["decision"]
            for row in run_rows
        ]
        by_case.append({
            "ordinal": case["ordinal"],
            "proposition_key": case["proposition_key"],
            "slot_key": case["slot_key"],
            "expected": case["expected"],
            "note": case["note"],
            "strict": case["expected"] is not None,
            "decisions": decisions,
            "stable": len(set(decisions)) == 1,
            "all_correct": (
                case["expected"] is not None
                and all(
                    decision == case["expected"]
                    for decision in decisions
                )
            ),
        })
    strict = [row for row in by_case if row["strict"]]
    strict_judgment_count = len(strict) * repeats
    strict_correct = sum(
        decision == row["expected"]
        for row in strict
        for decision in row["decisions"]
    )

    serial = json.loads(SERIAL_RESULT.read_text(encoding="utf-8"))
    serial_map = {
        (
            row["ordinal"],
            row["proposition_key"],
            row["slot_key"],
        ): tuple(
            judgment["decision"]
            for judgment in row["judgments"]
        )
        for row in [
            *serial["strict_cases"],
            *serial["exploratory_cases"],
        ]
    }
    serial_latency = sum(
        row["latency_s"]
        for row in [
            *serial["strict_cases"],
            *serial["exploratory_cases"],
        ]
    )
    serial_equivalent = all(
        tuple(row["decisions"]) == serial_map[
            (
                row["ordinal"],
                row["proposition_key"],
                row["slot_key"],
            )
        ]
        for row in by_case
    )

    result = {
        "benchmark": "phase17.3-ks-e-pairwise-direct-answer-batch-v0.1",
        "case_count": len(cases),
        "strict_case_count": len(strict),
        "repeat_count": repeats,
        "batch_transport_call_count": repeats,
        "strict_judgment_count": strict_judgment_count,
        "strict_accuracy": (
            strict_correct / strict_judgment_count
            if strict_judgment_count else None
        ),
        "stable_case_count": sum(row["stable"] for row in by_case),
        "fully_correct_strict_case_count": sum(
            row["all_correct"] for row in strict
        ),
        "serial_decision_equivalence": serial_equivalent,
        "serial_total_pair_latency_s": serial_latency,
        "batch_total_latency_s": total_latency,
        "latency_speedup": (
            serial_latency / total_latency
            if total_latency > 0 else None
        ),
        "runs": run_rows,
        "cases": by_case,
    }
    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_e_pairwise_direct_answer_batch_v0_1"
        / "phase17_3_ks_e_pairwise_direct_answer_batch_v0_1.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "benchmark": result["benchmark"],
        "case_count": result["case_count"],
        "strict_case_count": result["strict_case_count"],
        "batch_transport_call_count": result["batch_transport_call_count"],
        "strict_accuracy": result["strict_accuracy"],
        "stable_case_count": result["stable_case_count"],
        "fully_correct_strict_case_count": (
            result["fully_correct_strict_case_count"]
        ),
        "serial_decision_equivalence": (
            result["serial_decision_equivalence"]
        ),
        "serial_total_pair_latency_s": round(
            result["serial_total_pair_latency_s"], 3
        ),
        "batch_total_latency_s": round(
            result["batch_total_latency_s"], 3
        ),
        "latency_speedup": round(result["latency_speedup"], 2),
        "failures": [
            row
            for row in by_case
            if row["strict"] and not row["all_correct"]
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
