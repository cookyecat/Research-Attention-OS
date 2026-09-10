import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app.cognitive.schemas import KernelMatchItem
from app.services.scheduler import get_decision_strategy
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map
from eval.live.run_phase10d3_real_web_static_cognitive_map_v0_1 import collect_relation_sample
from eval.live.cognitive_map_distance_v0_1 import (
    attention_distribution,
    compare_cognitive_maps,
    empirical_state_distribution,
    js_divergence_bits,
)
from eval.live.cognitive_map_permutation_calibration_v0_1 import permutation_calibrate

RUN_VERSION = "phase10d4-real-web-basin-persistence-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase10d4_real_web_basin_persistence_v0_1"
STRATEGY_ID = "pareto-multidelta-magnitude-free-anchored-open-new"
PERMUTATIONS = 5000
SEED = 20260910

ARTIFACTS = {
    "10D1": (
        ROOT / "eval/live/results/phase10d1_real_web_static_cognitive_map_v0_1/phase10d1_real_web_static_cognitive_map_v0.1_20260910T094646Z.json",
        "9afb38a1373f3bbb14ae274930e4e861496a7d7c2beb009fd1e468b2b606ccdc",
    ),
    "10D2": (
        ROOT / "eval/live/results/phase10d2_real_web_source_diversity_broadening_v0_1/phase10d2_real_web_source_diversity_broadening_v0.1_20260910T110410Z.json",
        "215eed8ef395e51895d5078128a04afb21705f441ca084f4b9ac3b5c6d8371b4",
    ),
    "10D3": (
        ROOT / "eval/live/results/phase10d3_real_web_static_cognitive_map_v0_1/phase10d3_real_web_static_cognitive_map_v0.1_20260910T151143Z.json",
        "a40f2a6e4690a34552232c7e63c473e87ad7d5b846304a5a89108544b8b63f89",
    ),
}
EXPECTED_SELECTED = ("A", "D", "X", "N4")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_verified(path: Path, expected_sha: str) -> dict:
    actual = sha256(path)
    if actual != expected_sha:
        raise RuntimeError(f"artifact SHA mismatch: {path} {actual} != {expected_sha}")
    return json.loads(path.read_text(encoding="utf-8"))


def reconstruct_matches(case: dict) -> list[KernelMatchItem]:
    out = []
    for row in case["locate"]["modal"]["selected_matches"]:
        out.append(KernelMatchItem(
            kernel_node_id=UUID(str(row["kernel_node_id"])),
            relevance_type=str(row["relevance_type"]),
            score=float(row["score"]),
            reason=str(row["reason"]),
        ))
    return out


def all_real_web_cases() -> dict[str, dict]:
    merged = {}
    for batch, (path, expected) in ARTIFACTS.items():
        data = load_verified(path, expected)
        for label, case in (data.get("cases") or {}).items():
            if label in merged:
                raise RuntimeError(f"duplicate real-web label {label}")
            merged[label] = {"batch": batch, "case": case, "artifact": str(path.relative_to(ROOT))}
    return merged


def selected_cases() -> dict[str, dict]:
    merged = all_real_web_cases()
    selected = {}
    for label, row in merged.items():
        counts = row["case"]["map"]["attention_distribution"]["counts"]
        if len([k for k, v in counts.items() if int(v) > 0]) >= 2:
            selected[label] = row
    if tuple(selected) != EXPECTED_SELECTED:
        raise RuntimeError(f"selection rule mismatch: {tuple(selected)} != {EXPECTED_SELECTED}")
    return selected


def js_stat(field: str):
    if field == "attention":
        return lambda a, b: js_divergence_bits(attention_distribution(a), attention_distribution(b))
    return lambda a, b: js_divergence_bits(
        empirical_state_distribution(a, field), empirical_state_distribution(b, field)
    )


def calibrations(samples0, samples1) -> dict:
    return {
        "attention": permutation_calibrate(
            samples0, samples1, statistic=js_stat("attention"), permutations=PERMUTATIONS, seed=SEED
        ),
        "load_bearing": permutation_calibrate(
            samples0, samples1, statistic=js_stat("load_bearing"), permutations=PERMUTATIONS, seed=SEED + 1
        ),
        "topology": permutation_calibrate(
            samples0, samples1, statistic=js_stat("topology"), permutations=PERMUTATIONS, seed=SEED + 2
        ),
    }


def run_case(label: str, row: dict, nodes, strategy) -> dict:
    case = row["case"]
    units = case["frozen_units"]
    matches = reconstruct_matches(case)
    t1_samples = case["samples"]
    target_n = len(t1_samples)
    t2_samples = []
    for ordinal in range(1, target_n + 1):
        sample = collect_relation_sample(label, ordinal, units, nodes, matches, strategy)
        t2_samples.append(sample)
        print(json.dumps({"label": label, "stage": "T2", "sample": ordinal,
                          "attention": sample["attention"], "topology": sample["topology"]},
                         ensure_ascii=False), flush=True)
    t2_map = summarize_static_cognitive_map(t2_samples)
    comparison = compare_cognitive_maps(case["map"], t1_samples, t2_map, t2_samples)
    nulls = calibrations(t1_samples, t2_samples)
    return {
        "source_batch": row["batch"],
        "source_artifact": row["artifact"],
        "n_t1": len(t1_samples),
        "n_t2": len(t2_samples),
        "frozen_units_replay_sha256": case["frozen_units_replay_sha256"],
        "frozen_locate": case["locate"]["modal"],
        "t1_map": case["map"],
        "t2_map": t2_map,
        "t1_samples": t1_samples,
        "t2_samples": t2_samples,
        "comparison": comparison,
        "permutation_null": nulls,
        "same_basin_compatible": {k: not v["drift_supported_v0_1"] for k, v in nulls.items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--permutations", type=int, default=PERMUTATIONS)
    args = ap.parse_args()
    if args.permutations != PERMUTATIONS:
        raise ValueError(f"preregistered permutations must remain {PERMUTATIONS}")

    selected = selected_cases()
    nodes = build_phase6b_mvp_kernel_nodes()
    node_ids = {str(n.id) for n in nodes}
    strategy = get_decision_strategy(STRATEGY_ID)
    results = {}
    for label, row in selected.items():
        for match in row["case"]["locate"]["modal"]["selected_matches"]:
            if str(match["kernel_node_id"]) not in node_ids:
                raise RuntimeError(f"Kernel fixture mismatch for {label}: {match['kernel_node_id']}")
        results[label] = run_case(label, row, nodes, strategy)
        r = results[label]
        print(json.dumps({
            "label": label,
            "stage": "PERSISTENCE_SUMMARY",
            "t1_attention": r["t1_map"]["attention_distribution"]["counts"],
            "t2_attention": r["t2_map"]["attention_distribution"]["counts"],
            "js": {
                "attention": r["comparison"]["attention_js_bits"],
                "load_bearing": r["comparison"]["load_bearing_state_js_bits"],
                "topology": r["comparison"]["topology_state_js_bits"],
            },
            "same_basin": r["same_basin_compatible"],
        }, ensure_ascii=False), flush=True)

    out = {
        "run_version": RUN_VERSION,
        "status": "REAL_WEB_BASIN_PERSISTENCE",
        "measurement_sha": git_head(),
        "selection_rule": "all successful Phase10D.1/10D.2/10D.3 real-web maps with >=2 observed Attention actions",
        "selected_cases": list(results),
        "decision_strategy": strategy.execution_snapshot(),
        "permutations": PERMUTATIONS,
        "seed_base": SEED,
        "cases": results,
        "guardrails": [
            "No acquisition, Sensor, Auditor, or Locate call is made in T2.",
            "T2 replays exact persisted frozen semantic units and exact persisted modal Locate matches.",
            "T2 sample size equals T1 sample size for each selected case; no outcome-dependent expansion or early stop.",
            "Raw change_magnitude remains debug-only under the frozen decision strategy.",
            "Permutation-null gates are descriptive research evidence, not causal attribution to provider/model drift.",
            "Same-day persistence is not a stochastic-process or dynamical-attractor claim.",
            "Production default remains one-delta-v1.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    print("RESULT_SHA256=" + sha256(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
