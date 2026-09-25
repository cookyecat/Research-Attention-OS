"""Phase17.3-KS-E live pairwise Direct-Answer benchmark v0.4."""
from pathlib import Path
import json
import sys
import time

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.cognitive.client import LLMError, SchemaValidationError, chat_json
from app.services.semantic_coordinate.direct_answer import judge_direct_answer

ARTIFACT = ROOT / (
    "eval/live/results/phase17_jev_longitudinal_state_replay_v0_7/"
    "phase17_jev_longitudinal_state_replay_v0.7_n8_20260922T122031Z.json"
)

EVENT_IDENTITY = {
    "title": "Jev model launch / emergence and early validation episode",
    "event_type": "MODEL_LAUNCH_EARLY_VALIDATION",
    "actors": ["TypeSafe AI / Jev authors and ecosystem participants"],
    "action": "launch, explain, test, and early-validate Jev",
    "object": "Jev model",
    "time_context": "2026-09-16 through 2026-09-20 emergence episode",
}

STRICT_CASES = [
    (2, "P001", "S001", "DIRECT", "DOOM capability -> demonstrated capabilities"),
    (2, "P003", "S002", "DIRECT", "use cases -> real-time suitability"),
    (5, "P001", "S006", "DIRECT", "Tetris capability -> demonstrated capabilities"),
    (5, "P003", "S009", "DIRECT", "fast generation -> operational performance"),
    (6, "P001", "S006", "DIRECT", "FSD rebuild capability -> demonstrated capabilities"),
    (8, "P003", "S006", "DIRECT", "Buy/Sell judgment form -> output form"),
    (8, "P006", "S013", "DIRECT", "speed/cost report -> operational performance"),
    (6, "P003", "S006", "NOT_DIRECT", "claimed unlock != demonstrated capability"),
    (7, "P002", "S009", "NOT_DIRECT", "per-step design != base model architecture"),
    (7, "P001", "S008", "NOT_DIRECT", "integration speed != real-time suitability"),
    (8, "P001", "S005", "NOT_DIRECT", "integration occurrence != integration performance"),
    (8, "P002", "S005", "NOT_DIRECT", "workflow description != integration performance"),
    (8, "P005", "S005", "NOT_DIRECT", "trading-system relation != integration performance"),
    (8, "P004", "S009", "NOT_DIRECT", "design disposition != demonstrated capability"),
    (8, "P004", "S004", "NOT_DIRECT", "design disposition != claimed overall impact"),
    (6, "P002", "S009", "DIRECT", "task completion duration -> operational performance"),
]

EXPLORATORY_CASES = [
    (7, "P001", "S005", None, "integration performance vs intended deployment"),
    (8, "P001", "S007", None, "actual trading use vs intended deployment"),
]
def previous_slots_for(data, ordinal):
    previous = next(
        row for row in data["trajectory"]
        if row["ordinal"] == ordinal - 1
    )
    ordered = sorted(
        previous["slot_state"]["slots"],
        key=lambda row: row["slot_id"],
    )
    return {
        f"S{i:03d}": slot
        for i, slot in enumerate(ordered, 1)
    }


def propositions_for(data, ordinal):
    step = next(
        row for row in data["trajectory"]
        if row["ordinal"] == ordinal
    )
    props = step["proposition_flatmap"]["world_propositions"]
    return {
        f"P{i:03d}": proposition
        for i, proposition in enumerate(props, 1)
    }


RETRYABLE = (ValueError, LLMError, SchemaValidationError)


def run_pair(data, spec, repeat):
    ordinal, pkey, skey, expected, note = spec
    proposition = propositions_for(data, ordinal)[pkey]
    slot = previous_slots_for(data, ordinal)[skey]
    judgments = []
    errors = []
    latency = 0.0

    for rep in range(repeat):
        started = time.perf_counter()
        try:
            result = judge_direct_answer(
                event_identity=EVENT_IDENTITY,
                proposition=proposition,
                slot=slot,
                chat_fn=chat_json,
            )
            latency += time.perf_counter() - started
            judgments.append({
                "repeat": rep + 1,
                "decision": result.decision,
                "rationale": result.rationale,
            })
        except RETRYABLE as exc:
            latency += time.perf_counter() - started
            errors.append({
                "repeat": rep + 1,
                "type": type(exc).__name__,
                "message": str(exc),
            })

    decisions = [row["decision"] for row in judgments]
    strict = expected is not None
    return {
        "ordinal": ordinal,
        "proposition_key": pkey,
        "slot_key": skey,
        "note": note,
        "primitive_family": proposition["primitive_family"],
        "proposition": proposition["statement"],
        "slot_label": slot["slot_label"],
        "state_question": slot["state_question"],
        "expected": expected,
        "strict": strict,
        "judgments": judgments,
        "errors": errors,
        "all_repeats_valid": len(judgments) == repeat,
        "all_repeats_agree": len(set(decisions)) <= 1 and len(decisions) == repeat,
        "all_repeats_correct": (
            strict
            and len(decisions) == repeat
            and all(decision == expected for decision in decisions)
        ),
        "latency_s": latency,
    }
def main():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    repeat = 2
    strict_rows = [
        run_pair(data, spec, repeat)
        for spec in STRICT_CASES
    ]
    exploratory_rows = [
        run_pair(data, spec, repeat)
        for spec in EXPLORATORY_CASES
    ]

    strict_judgments = [
        judgment
        for row in strict_rows
        for judgment in row["judgments"]
    ]
    expected_by_case = {
        (row["ordinal"], row["proposition_key"], row["slot_key"]): row["expected"]
        for row in strict_rows
    }
    direct_total = 0
    direct_correct = 0
    negative_total = 0
    negative_correct = 0
    for row in strict_rows:
        expected = row["expected"]
        for judgment in row["judgments"]:
            if expected == "DIRECT":
                direct_total += 1
                direct_correct += judgment["decision"] == "DIRECT"
            else:
                negative_total += 1
                negative_correct += judgment["decision"] == "NOT_DIRECT"

    result = {
        "benchmark": "phase17.3-ks-e-pairwise-direct-answer-v0.4",
        "artifact": str(ARTIFACT.relative_to(ROOT)),
        "repeat_per_case": repeat,
        "strict_case_count": len(strict_rows),
        "exploratory_case_count": len(exploratory_rows),
        "strict_judgment_count": len(strict_judgments),
        "strict_accuracy": (
            sum(
                judgment["decision"] == row["expected"]
                for row in strict_rows
                for judgment in row["judgments"]
            ) / len(strict_judgments)
            if strict_judgments else None
        ),
        "direct_recall": (
            direct_correct / direct_total if direct_total else None
        ),
        "not_direct_accuracy": (
            negative_correct / negative_total if negative_total else None
        ),
        "stable_case_count": sum(
            row["all_repeats_agree"] for row in strict_rows
        ),
        "fully_correct_case_count": sum(
            row["all_repeats_correct"] for row in strict_rows
        ),
        "uncertain_count": sum(
            judgment["decision"] == "UNCERTAIN"
            for row in strict_rows
            for judgment in row["judgments"]
        ),
        "error_count": sum(len(row["errors"]) for row in strict_rows),
        "strict_cases": strict_rows,
        "exploratory_cases": exploratory_rows,
    }
    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_e_pairwise_direct_answer_v0_4"
        / "phase17_3_ks_e_pairwise_direct_answer_v0_4.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps({
        "benchmark": result["benchmark"],
        "strict_case_count": result["strict_case_count"],
        "strict_judgment_count": result["strict_judgment_count"],
        "strict_accuracy": result["strict_accuracy"],
        "direct_recall": result["direct_recall"],
        "not_direct_accuracy": result["not_direct_accuracy"],
        "stable_case_count": result["stable_case_count"],
        "fully_correct_case_count": result["fully_correct_case_count"],
        "uncertain_count": result["uncertain_count"],
        "error_count": result["error_count"],
        "strict_summary": [
            {
                "ordinal": row["ordinal"],
                "pair": f"{row['proposition_key']}->{row['slot_key']}",
                "expected": row["expected"],
                "decisions": [
                    judgment["decision"]
                    for judgment in row["judgments"]
                ],
                "stable": row["all_repeats_agree"],
                "correct": row["all_repeats_correct"],
                "note": row["note"],
            }
            for row in strict_rows
        ],
        "exploratory_summary": [
            {
                "ordinal": row["ordinal"],
                "pair": f"{row['proposition_key']}->{row['slot_key']}",
                "decisions": [
                    judgment["decision"]
                    for judgment in row["judgments"]
                ],
                "note": row["note"],
            }
            for row in exploratory_rows
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
