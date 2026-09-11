from __future__ import annotations

from collections import Counter
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

from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import (
    CognitiveEffect,
    CognitiveImpactAssessment,
    resolve_target_importance,
)
from app.services.scheduler import get_decision_strategy
from eval.live.cognitive_map_distance_v0_1 import (
    attention_distribution,
    compare_cognitive_maps,
    empirical_state_distribution,
    js_divergence_bits,
)
from eval.live.cognitive_map_permutation_calibration_v0_1 import permutation_calibrate
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map
from eval.live.run_phase10d3_real_web_static_cognitive_map_v0_1 import branch_relation_key
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import (
    reconstruct_matches,
    selected_cases,
)
from eval.live.run_phase8c7_real_web_magnitude_free_validation_v0_1 import _matches
from eval.live.run_phase8c13_decision_causal_core_v0_1 import features

RUN_VERSION = "phase10d5-production-semantic-parity-audit-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase10d5_production_semantic_parity_audit_v0_1"
SOURCE = ROOT / "eval/live/results/phase10d4_real_web_basin_persistence_v0_1/phase10d4_real_web_basin_persistence_v0.1_20260910T160403Z.json"
SOURCE_SHA = "5299cab0607779989b896148765f5c6ef9873b001449b73f51cba6b67e7438a7"
STRATEGY_ID = "pareto-multidelta-magnitude-free-anchored-open-new"
PERMUTATIONS = 5000
SEED = 20260910

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def freeze(value):
    if isinstance(value, list):
        return tuple(freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(freeze(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((str(k), freeze(v)) for k, v in value.items()))
    return value


def load_source() -> dict:
    actual = sha256(SOURCE)
    if actual != SOURCE_SHA:
        raise RuntimeError(f"Phase10D.4 artifact SHA mismatch: {actual}")
    return json.loads(SOURCE.read_text(encoding="utf-8"))

def reconstruct_effects(sample: dict, nodes, *, production_importance: bool) -> list[CognitiveEffect]:
    by_id = {str(n.id): n for n in nodes}
    effects = []
    for row in sample.get("effects") or []:
        target_raw = row.get("target_kernel_node_id")
        node = by_id.get(str(target_raw)) if target_raw else None
        importance = float(row.get("target_importance") or 0.0)
        if production_importance:
            importance = resolve_target_importance(
                node=node,
                node_type=getattr(node, "node_type", None),
                llm_estimate=importance,
            )
        op = CognitiveEffectKind(str(row["operation"]))
        effects.append(CognitiveEffect(
            target_kernel_node_id=UUID(str(target_raw)) if target_raw else None,
            operation=op,
            change_magnitude=float(row.get("change_magnitude_debug_only", row.get("change_magnitude", 0.0))),
            epistemic_strength=float(row.get("epistemic_strength") or 0.0),
            target_importance=float(importance),
            reason=str(row.get("reason") or ""),
            exploration_candidate=(op == CognitiveEffectKind.OPEN_NEW),
            target_node_type=getattr(node, "node_type", None),
        ))
    return effects

def project_sample(sample: dict, *, nodes, prod_matches, relation_key, strategy, production_importance: bool) -> dict:
    effects = reconstruct_effects(sample, nodes, production_importance=production_importance)
    assessment = CognitiveImpactAssessment(effects=effects)
    report = analyze_decision_causal_core(
        assessment=assessment,
        matches=prod_matches,
        features=features(),
        decision_strategy=strategy,
        relation_key=relation_key,
    )
    topology = sorted({relation_key(effect) for effect in effects}, key=repr)
    return {
        "sample_id": sample.get("sample_id"),
        "topology": topology,
        "necessary_core": list(report.necessary_core),
        "sufficient_supports": list(report.sufficient_supports),
        "attention": report.baseline_decision,
        "effects": [
            {
                "operation": e.operation.value,
                "target_kernel_node_id": str(e.target_kernel_node_id) if e.target_kernel_node_id else None,
                "change_magnitude_debug_only": float(e.change_magnitude),
                "epistemic_strength": float(e.epistemic_strength),
                "target_importance": float(e.target_importance),
                "reason": e.reason,
            }
            for e in effects
        ],
    }

def js_stat(field: str):
    if field == "attention":
        return lambda a, b: js_divergence_bits(attention_distribution(a), attention_distribution(b))
    return lambda a, b: js_divergence_bits(
        empirical_state_distribution(a, field),
        empirical_state_distribution(b, field),
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


def assert_historical_replay(stored: dict, replay: dict, label: str) -> None:
    for field in ("topology", "necessary_core", "sufficient_supports"):
        if freeze(stored.get(field)) != freeze(replay.get(field)):
            raise RuntimeError(f"historical replay mismatch {label} {stored.get('sample_id')} field={field}")
    if str(stored.get("attention")) != str(replay.get("attention")):
        raise RuntimeError(f"historical replay mismatch {label} {stored.get('sample_id')} field=attention")

def run_case(label: str, source_case: dict, stored_case: dict, nodes, strategy) -> dict:
    native_matches = reconstruct_matches(source_case)
    prod_matches = _matches(native_matches, nodes)
    relation_key = branch_relation_key(nodes, source_case["frozen_units"])

    historical = {"t1": [], "t2": []}
    production = {"t1": [], "t2": []}
    changed_attention = Counter()
    changed_core = Counter()

    for checkpoint, key in (("t1", "t1_samples"), ("t2", "t2_samples")):
        for sample in stored_case[key]:
            replay = project_sample(
                sample, nodes=nodes, prod_matches=prod_matches,
                relation_key=relation_key, strategy=strategy, production_importance=False,
            )
            assert_historical_replay(sample, replay, label)
            projected = project_sample(
                sample, nodes=nodes, prod_matches=prod_matches,
                relation_key=relation_key, strategy=strategy, production_importance=True,
            )
            historical[checkpoint].append(replay)
            production[checkpoint].append(projected)
            if replay["attention"] != projected["attention"]:
                changed_attention[checkpoint] += 1
            if freeze(replay["necessary_core"] + replay["sufficient_supports"]) != freeze(
                projected["necessary_core"] + projected["sufficient_supports"]
            ):
                changed_core[checkpoint] += 1
    t1_map = summarize_static_cognitive_map(production["t1"])
    t2_map = summarize_static_cognitive_map(production["t2"])
    comparison = compare_cognitive_maps(t1_map, production["t1"], t2_map, production["t2"])
    nulls = calibrations(production["t1"], production["t2"])

    return {
        "historical_replay_exact": True,
        "n_t1": len(production["t1"]),
        "n_t2": len(production["t2"]),
        "projection_change_counts": {
            "attention": dict(changed_attention),
            "load_bearing_set": dict(changed_core),
        },
        "historical_attention": {
            "t1": dict(Counter(x["attention"] for x in historical["t1"])),
            "t2": dict(Counter(x["attention"] for x in historical["t2"])),
        },
        "production_attention": {
            "t1": dict(Counter(x["attention"] for x in production["t1"])),
            "t2": dict(Counter(x["attention"] for x in production["t2"])),
        },
        "production_t1_map": t1_map,
        "production_t2_map": t2_map,
        "comparison": comparison,
        "permutation_null": nulls,
        "same_basin_compatible": {k: not v["drift_supported_v0_1"] for k, v in nulls.items()},
        "production_t1_samples": production["t1"],
        "production_t2_samples": production["t2"],
    }

def main() -> int:
    data = load_source()
    selected = selected_cases()
    nodes = build_phase6b_mvp_kernel_nodes()
    strategy = get_decision_strategy(STRATEGY_ID)

    if tuple(data.get("selected_cases") or ()) != tuple(selected):
        raise RuntimeError("Phase10D.4 selected-case order mismatch")

    results = {}
    total_samples = 0
    for label, source_row in selected.items():
        result = run_case(label, source_row["case"], data["cases"][label], nodes, strategy)
        results[label] = result
        total_samples += result["n_t1"] + result["n_t2"]
        print(json.dumps({
            "label": label,
            "historical_attention": result["historical_attention"],
            "production_attention": result["production_attention"],
            "projection_changes": result["projection_change_counts"],
            "js": {
                "attention": result["comparison"]["attention_js_bits"],
                "load_bearing": result["comparison"]["load_bearing_state_js_bits"],
                "topology": result["comparison"]["topology_state_js_bits"],
            },
            "same_basin": result["same_basin_compatible"],
        }, ensure_ascii=False), flush=True)
    if total_samples != 168:
        raise RuntimeError(f"expected exact 168-sample corpus, got {total_samples}")

    out = {
        "run_version": RUN_VERSION,
        "status": "DETERMINISTIC_TARGET_IMPORTANCE_PRODUCTION_PARITY_REPLAY",
        "measurement_sha": git_head(),
        "source_phase10d4": str(SOURCE.relative_to(ROOT)),
        "source_phase10d4_sha256": SOURCE_SHA,
        "n_replayed_samples": total_samples,
        "decision_strategy": strategy.execution_snapshot(),
        "controlled_change": "targeted effect importance: stored LLM estimate -> production resolve_target_importance authority",
        "results": results,
        "guardrails": [
            "No acquisition, Sensor, Auditor, Locate, Relation-Mapping, or LLM call is made.",
            "Historical arm must reproduce all stored topology/core/Attention outputs exactly before parity results are accepted.",
            "Raw change_magnitude remains debug-only.",
            "OPEN_NEW has no target and therefore retains its stored LLM importance estimate.",
            "This v0.1 replay audits the discovered target-importance authority seam only.",
            "It does not prove parity of native_assess prompt semantics with production ModelProvider impact prompting or production ground_effects.",
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
