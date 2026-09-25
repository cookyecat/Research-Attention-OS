"""KS-F expected LLM-call model for semantic-address serving."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]

LOCKED_RESULT = (
    ROOT
    / "eval/live/results/phase17_3_ks_e_address_locked_comparison_v0_6/"
    / "phase17_3_ks_e_address_locked_comparison_v0_6.json"
)

CACHE_RATES = [0.0, 0.25, 0.5]
STUDENT_COVERAGES = [0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
PAIR_CONSENSUS_REPEATS = 2


def main():
    locked = json.loads(LOCKED_RESULT.read_text(encoding="utf-8"))

    observation_count = locked["successful_case_count"]
    existing_pair_count = locked["pairwise_judgment_count"]
    create_group_pair_count = locked["create_group_check_count"]
    semantic_pair_count = existing_pair_count + create_group_pair_count

    baseline_pair_calls = semantic_pair_count * PAIR_CONSENSUS_REPEATS
    synthesis_calls = observation_count
    baseline_total_calls = baseline_pair_calls + synthesis_calls

    scenarios = []
    for cache_rate in CACHE_RATES:
        for student_coverage in STUDENT_COVERAGES:
            unresolved_fraction = (
                (1.0 - cache_rate)
                * (1.0 - student_coverage)
            )
            expected_pair_calls = (
                baseline_pair_calls * unresolved_fraction
            )
            expected_total_calls = (
                expected_pair_calls + synthesis_calls
            )
            scenarios.append({
                "cache_hit_rate": cache_rate,
                "student_safe_coverage": student_coverage,
                "expected_pair_llm_calls": expected_pair_calls,
                "fixed_synthesis_calls": synthesis_calls,
                "expected_total_llm_calls": expected_total_calls,
                "call_reduction_fraction": (
                    1.0
                    - expected_total_calls / baseline_total_calls
                ),
            })

    result = {
        "benchmark": "phase17.3-ks-f-llm-call-cost-model-v0.1",
        "source": str(LOCKED_RESULT.relative_to(ROOT)),
        "observation_count": observation_count,
        "existing_pair_count": existing_pair_count,
        "create_group_pair_count": create_group_pair_count,
        "semantic_pair_count": semantic_pair_count,
        "pair_consensus_repeats": PAIR_CONSENSUS_REPEATS,
        "baseline_pair_llm_calls": baseline_pair_calls,
        "fixed_address_locked_synthesis_calls": synthesis_calls,
        "baseline_total_llm_calls": baseline_total_calls,
        "assumption": (
            "cache/student apply to semantic pair judgments only; "
            "one address-locked synthesis call per observation remains"
        ),
        "scenarios": scenarios,
    }

    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_f_llm_call_cost_model_v0_1"
        / "phase17_3_ks_f_llm_call_cost_model_v0_1.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    selected = [
        row for row in scenarios
        if (
            row["cache_hit_rate"] in {0.0, 0.25}
            and row["student_safe_coverage"] in {0.5, 0.75, 0.9, 0.95}
        )
    ]
    print(json.dumps({
        "baseline": {
            "observations": observation_count,
            "semantic_pairs": semantic_pair_count,
            "pair_llm_calls": baseline_pair_calls,
            "synthesis_calls": synthesis_calls,
            "total_llm_calls": baseline_total_calls,
        },
        "selected_scenarios": [
            {
                "cache_hit_rate": row["cache_hit_rate"],
                "student_safe_coverage": row["student_safe_coverage"],
                "expected_total_llm_calls": round(
                    row["expected_total_llm_calls"], 2
                ),
                "call_reduction_fraction": round(
                    row["call_reduction_fraction"], 4
                ),
            }
            for row in selected
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
