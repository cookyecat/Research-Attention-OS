from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for p in (ROOT, BACKEND):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app.services.cognitive_impact import legal_public_effects, normalize_frozen_transition
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.cognitive_map_distance_v0_1 import (
    attention_distribution, empirical_state_distribution, js_divergence_bits, compare_cognitive_maps,
)
from eval.live.cognitive_map_permutation_calibration_v0_1 import permutation_calibrate
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core
from eval.live.phase9a_kernel_causal_alignment_v0_1 import (
    VERSION as INSTRUMENT_VERSION, bind_kernel_importance, frozen_rs05_critical_match,
    materialize_rs05_arm,
)
from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map
from eval.live.run_phase8c7_real_web_magnitude_free_validation_v0_1 import _assessment, _features, _matches
from eval.live.run_phase8c8_semantic_topology_stability_v0_1 import (
    _code_maps, _forced_chat, load_units, serialize_effect,
)
from eval.live.run_phase8c14_open_new_branch_causal_attribution_v0_1 import branch_relation_key

RUN_VERSION = "phase9a-kernel-causal-alignment-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase9a_kernel_causal_alignment_v0_1"
STRATEGY_ID = "pareto-multidelta-magnitude-free-anchored-open-new"
ARMS = ("K0", "K1-S", "K1-I")
INITIAL_N = 12
EXPANDED_N = 24
PERMUTATIONS = 5000
PERMUTATION_SEED = 20260911


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _target_relation_prob(samples, operation: str) -> float:
    rel = (operation, "CF-B-PERF")
    if not samples:
        return 0.0
    return sum(rel in set(tuple(x) for x in (s.get("topology") or [])) for s in samples) / len(samples)

def _attention_js(a, b) -> float:
    return js_divergence_bits(attention_distribution(a), attention_distribution(b))


def _topology_js(a, b) -> float:
    return js_divergence_bits(
        empirical_state_distribution(a, "topology"),
        empirical_state_distribution(b, "topology"),
    )


def _load_bearing_js(a, b) -> float:
    return js_divergence_bits(
        empirical_state_distribution(a, "load_bearing"),
        empirical_state_distribution(b, "load_bearing"),
    )


def _arm_order(round_idx: int) -> tuple[str, ...]:
    shift = (round_idx - 1) % len(ARMS)
    return ARMS[shift:] + ARMS[:shift]


def collect_sample(arm_name: str, ordinal: int, arm, units, strategy) -> dict:
    nodes = arm.nodes
    native_matches = frozen_rs05_critical_match(nodes)
    parsed, meta, events = __import__(
        "eval.live.phase8c3_native_cognitive_interface_v0_1",
        fromlist=["native_assess"],
    ).native_assess(units, nodes, native_matches, chat_fn=_forced_chat)
    assessment = bind_kernel_importance(_assessment(parsed, nodes), nodes)
    prod_matches = _matches(native_matches, nodes)
    normalized = normalize_frozen_transition(assessment, prod_matches).assessment
    legal = legal_public_effects(normalized)
    features = _features(parsed)
    plan = route(
        features, RuntimeView(), assessment=normalized, matches=prod_matches,
        decision_strategy=strategy,
    )
