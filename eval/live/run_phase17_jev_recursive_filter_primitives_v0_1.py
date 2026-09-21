from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRACE = ROOT / "eval/live/fixtures/phase17_jev_observed_world_trace_v0_1.json"
OUT_DIR = ROOT / "eval/live/results/phase17_jev_recursive_filter_primitives_v0_1"
RUN_VERSION = "phase17-jev-recursive-filter-primitives-v0.1"


def leaky(previous: float, innovation: float, retention_per_day: float) -> float:
    return previous * retention_per_day + innovation


def run() -> dict:
    trace = json.loads(TRACE.read_text())
    daily = trace["daily"]
    innovations = [float(row["new_items"]) for row in daily]

    cumulative = []
    total = 0.0
    for value in innovations:
        total += value
        cumulative.append(total)

    retentions = (0.25, 0.50, 0.75, 0.90)
    leaky_runs = {}
    for rho in retentions:
        state = 0.0
        values = []
        for innovation in innovations:
            state = leaky(state, innovation, rho)
            values.append(round(state, 6))
        leaky_runs[f"{rho:.2f}"] = values

    return {
        "run_version": RUN_VERSION,
        "status": "CONTROLLED_PRIMITIVE_SENSITIVITY_COMPLETE",
        "trace_contract": trace["contract"],
        "interpretation_boundary": [
            "Input innovation is raw RAOS-observed daily item arrival count.",
            "This is an observational-momentum baseline, not decision evidence.",
            "No retention parameter is selected or tuned against Human Gold.",
            "No Attention labels are produced in this run.",
        ],
        "dates": [row["date"] for row in daily],
        "daily_innovation": innovations,
        "full_history_cumulative_baseline": cumulative,
        "leaky_momentum_by_retention_per_day": leaky_runs,
        "diagnostics": {
            "cumulative_is_monotone": all(
                b >= a for a, b in zip(cumulative, cumulative[1:])
            ),
            "all_leaky_states_bounded_below_cumulative": all(
                values[i] <= cumulative[i]
                for values in leaky_runs.values()
                for i in range(len(cumulative))
            ),
            "trace_peak_daily_arrival": max(innovations),
            "trace_total_items": sum(innovations),
        },
    }


def main() -> None:
    report = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    print("DATES", report["dates"])
    print("DAILY", report["daily_innovation"])
    print("CUMULATIVE", report["full_history_cumulative_baseline"])
    for rho, values in report["leaky_momentum_by_retention_per_day"].items():
        print("RHO", rho, "MOMENTUM", values)
    print("DIAGNOSTICS", json.dumps(report["diagnostics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
