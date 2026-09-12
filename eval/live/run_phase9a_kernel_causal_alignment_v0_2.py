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

from app.cognitive.client import chat_json, chat_json_schema
from app.config import settings
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.cognitive_map_distance_v0_1 import empirical_state_distribution, js_divergence_bits
from eval.live.cognitive_map_permutation_calibration_v0_1 import permutation_calibrate
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core
from eval.live.phase6b_cognitive_semantics_v0_1 import admitted_epistemic_units
from eval.live.phase9a_kernel_causal_alignment_v0_2 import (
    CONTRACT_VERSION, DIRECT_SUPPORT_UNIT_ID, SYSTEM_PROMPT, TARGET_CODE, VERSION as INSTRUMENT_VERSION,
    RelationResponse, authorize_relations, frozen_rs05_match, materialize_rs05_arm,
    neutral_features, normalize_relations, relation_key, relation_user_prompt, target_node,
    target_polarity_state, validate_relation,
)
from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map

RUN_VERSION = "phase9a-kernel-causal-alignment-v0.2"
OUT_DIR = ROOT / "eval/live/results/phase9a_kernel_causal_alignment_v0_2"
STRATEGY_ID = "pareto-multidelta-cardinal-free-anchored-open-new"
INITIAL_N = 12
PERMUTATIONS = 5000
PERMUTATION_SEED = 20260913
AUDITOR_ARTIFACT = ROOT / "eval/live/results/phase7a_v0_2_6_epistemic_audit_v0_1/phase6b_epistemic_unit_audit_v0_1_20260908T090628Z.json"
AUDITOR_SHA256 = "aa594aab2b7b2f0e252dbf3ed8978865e03d9ddd1b905c8f38db0ae60ea5711f"


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rs05_units() -> list[dict]:
    actual = sha256(AUDITOR_ARTIFACT)
    if actual != AUDITOR_SHA256:
        raise RuntimeError(f"RS05 Auditor artifact SHA mismatch: {actual}")
    data = json.loads(AUDITOR_ARTIFACT.read_text())
    row = next(x for x in data["sources"] if x.get("source_id") == "RS05")
    units = admitted_epistemic_units(list(row.get("audits") or []))
    if DIRECT_SUPPORT_UNIT_ID not in {str(x.get("unit_id")) for x in units}:
        raise RuntimeError("preregistered RS05-U01 support missing")
    return units


def forced_chat(messages, **kwargs):
    return chat_json(
        messages,
        timeout=float(kwargs.get("timeout") or 60.0),
        thinking=kwargs.get("thinking"),
        reasoning_effort=kwargs.get("reasoning_effort"),
        temperature=0.1,
    )


def relation_row(effect, nodes) -> dict:
    target = target_node(nodes)
    return {
        "operation": effect.operation,
        "target_kernel_node_id": str(effect.target_kernel_node_id) if effect.target_kernel_node_id else None,
        "target": TARGET_CODE if effect.target_kernel_node_id == target.id else None,
        "reason": effect.reason,
    }


def raw_topology(effects, nodes):
    rows = []
    for effect in effects:
        if effect.operation == "OPEN_NEW":
            rows.append(("OPEN_NEW", "OPEN_NEW"))
        else:
            rows.append((effect.operation, TARGET_CODE if effect.target_kernel_node_id == target_node(nodes).id else str(effect.target_kernel_node_id)))
    return sorted(set(rows), key=repr)


def run_relation_call(arm_name, ordinal, units, arm) -> dict:
    matches = frozen_rs05_match(arm.nodes)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": relation_user_prompt(units, matches, arm.nodes)},
    ]
    parsed, meta, events = chat_json_schema(
        messages,
        RelationResponse,
        chat_fn=forced_chat,
        thinking="disabled",
        timeout=60.0,
    )
    invalid = []
    valid = []
    for effect in parsed.effects:
        ok, reason = validate_relation(effect, arm.nodes)
        if ok:
            valid.append(effect)
        else:
            invalid.append({**relation_row(effect, arm.nodes), "invalid_reason": reason})
    normalized = normalize_relations(valid)
    status = "OK" if not invalid else "INVALID"
    return {
        "sample_id": f"{arm_name}-{ordinal}",
        "ordinal": ordinal,
        "relation_source_arm": arm_name,
        "status": status,
        "raw_effects": [relation_row(e, arm.nodes) for e in parsed.effects],
        "normalized_effects": [relation_row(e, arm.nodes) for e in normalized],
        "normalized_objects": normalized,
        "invalid_effects": invalid,
        "raw_target_polarity": target_polarity_state(normalized, arm.nodes),
        "raw_topology": raw_topology(normalized, arm.nodes),
        "meta": meta,
        "schema_events": events,
    }


def downstream_sample(raw: dict, *, arm_name: str, arm, strategy) -> dict:
    if raw["status"] != "OK":
        return {
            "sample_id": f"{arm_name}-{raw['ordinal']}", "ordinal": raw["ordinal"], "arm": arm_name,
            "status": raw["status"], "raw_target_polarity": raw["raw_target_polarity"],
            "raw_topology": raw["raw_topology"], "invalid_effects": raw["invalid_effects"],
        }
    assessment, authority = authorize_relations(raw["normalized_objects"], arm=arm_name, nodes=arm.nodes)
    matches = frozen_rs05_match(arm.nodes)
    features = neutral_features()
    plan = route(features, RuntimeView(), assessment=assessment, matches=matches, decision_strategy=strategy)
    key = lambda effect: relation_key(effect, arm.nodes)
    core = analyze_decision_causal_core(
        assessment=assessment, matches=matches, features=features, decision_strategy=strategy, relation_key=key
    )
    if core.baseline_decision != plan.disposition.value:
        raise RuntimeError(f"Decision-Causal Core baseline mismatch {arm_name}/{raw['ordinal']}")
    authorized_topology = sorted({key(e) for e in assessment.effects}, key=repr)
    return {
        "sample_id": f"{arm_name}-{raw['ordinal']}",
        "ordinal": raw["ordinal"],
        "arm": arm_name,
        "relation_source_arm": raw["relation_source_arm"],
        "status": "OK",
        "raw_target_polarity": raw["raw_target_polarity"],
        "raw_topology": raw["raw_topology"],
        "topology": authorized_topology,
        "necessary_core": list(core.necessary_core),
        "sufficient_supports": list(core.sufficient_supports),
        "attention": plan.disposition.value,
        "expected_output": plan.expected_output.value if hasattr(plan.expected_output, "value") else str(plan.expected_output),
        "authority": authority,
        "causal_profile": core.as_dict(),
        "raw_effects": raw["raw_effects"],
        "normalized_effects": raw["normalized_effects"],
        "invalid_effects": raw["invalid_effects"],
        "meta": raw["meta"],
        "schema_events": raw["schema_events"],
    }


def polarity_distribution(samples) -> dict:
    ok = [s for s in samples if s.get("status") == "OK"]
    if not ok:
        return {}
    counts = Counter(s["raw_target_polarity"] for s in ok)
    return {k: v / len(ok) for k, v in counts.items()}


def polarity_js(a, b) -> float:
    return js_divergence_bits(polarity_distribution(a), polarity_distribution(b))


def modal_polarity(samples) -> str | None:
    ok = [s for s in samples if s.get("status") == "OK"]
    if not ok:
        return None
    counts = Counter(s["raw_target_polarity"] for s in ok)
    return sorted(counts, key=lambda k: (-counts[k], k))[0]


def summarize_arm(samples) -> dict:
    ok = [s for s in samples if s.get("status") == "OK"]
    return {
        "n_total": len(samples),
        "n_ok": len(ok),
        "n_invalid": len(samples) - len(ok),
        "raw_polarity_counts": dict(sorted(Counter(s.get("raw_target_polarity") for s in ok).items())),
        "attention_counts": dict(sorted(Counter(s.get("attention") for s in ok).items())),
        "map": summarize_static_cognitive_map(ok),
    }


def paired_importance_gate(k0, k1i) -> dict:
    if len(k0) != len(k1i):
        raise ValueError("paired arms differ in length")
    topology_violations = []
    eligible = []
    transitions = Counter()
    for a, b in zip(k0, k1i):
        if a.get("ordinal") != b.get("ordinal"):
            topology_violations.append({"ordinal": a.get("ordinal"), "reason": "ORDINAL_MISMATCH"})
            continue
        if a.get("raw_topology") != b.get("raw_topology") or a.get("raw_target_polarity") != b.get("raw_target_polarity"):
            topology_violations.append({"ordinal": a.get("ordinal"), "reason": "RAW_RELATION_MISMATCH"})
        if a.get("topology") != b.get("topology"):
            topology_violations.append({"ordinal": a.get("ordinal"), "reason": "AUTHORIZED_TOPOLOGY_MISMATCH"})
        if ("CHALLENGE", TARGET_CODE) in [tuple(x) for x in (a.get("topology") or [])]:
            eligible.append(a["ordinal"])
            transitions[(a.get("attention"), b.get("attention"))] += 1
    expected = transitions.get(("ENGAGE", "AWARE"), 0)
    return {
        "topology_invariant_violations": topology_violations,
        "eligible_retained_challenge_pairs": eligible,
        "attention_transition_counts": {repr(k): v for k, v in sorted(transitions.items(), key=lambda kv: repr(kv[0]))},
        "expected_engage_to_aware": expected,
        "gate_pass": not topology_violations and bool(eligible) and expected == len(eligible),
    }


def serialize_arm(arm) -> dict:
    target = target_node(arm.nodes)
    return {
        "arm": arm.arm,
        "target_id": str(target.id),
        "target_title": target.title,
        "target_proposition": str((target.payload or {}).get("proposition") or target.title),
        "target_importance": (target.payload or {}).get("importance"),
        "current_version": int(target.current_version),
        "patch": arm.patch,
        "target_versions": arm.target_versions,
    }


def collect(n: int) -> dict:
    units = load_rs05_units()
    arms = {name: materialize_rs05_arm(name) for name in ("K0", "K1-S", "K1-I")}
    target_ids = {str(target_node(arm.nodes).id) for arm in arms.values()}
    if len(target_ids) != 1:
        raise RuntimeError("target identity changed across Kernel arms")
    p0 = relation_user_prompt(units, frozen_rs05_match(arms["K0"].nodes), arms["K0"].nodes)
    pi = relation_user_prompt(units, frozen_rs05_match(arms["K1-I"].nodes), arms["K1-I"].nodes)
    ps = relation_user_prompt(units, frozen_rs05_match(arms["K1-S"].nodes), arms["K1-S"].nodes)
    if p0 != pi:
        raise RuntimeError("K0/K1-I Relation Mapping payloads are not byte-identical")
    if p0 == ps:
        raise RuntimeError("K0/K1-S Relation Mapping payloads unexpectedly identical")
    strategy = get_decision_strategy(STRATEGY_ID)
    raw_by_arm = {"K0": [], "K1-S": []}
    samples = {"K0": [], "K1-S": [], "K1-I": []}
    for ordinal in range(1, n + 1):
        order = ("K0", "K1-S") if ordinal % 2 else ("K1-S", "K0")
        for arm_name in order:
            try:
                raw = run_relation_call(arm_name, ordinal, units, arms[arm_name])
            except Exception as exc:
                raw = {
                    "sample_id": f"{arm_name}-{ordinal}", "ordinal": ordinal, "relation_source_arm": arm_name,
                    "status": "ERROR", "raw_target_polarity": "NONE", "raw_topology": [],
                    "raw_effects": [], "normalized_effects": [], "normalized_objects": [], "invalid_effects": [],
                    "error_type": type(exc).__name__, "error": str(exc)[:3000], "meta": {}, "schema_events": [],
                }
            raw_by_arm[arm_name].append(raw)
            sample = downstream_sample(raw, arm_name=arm_name, arm=arms[arm_name], strategy=strategy)
            if raw.get("error"):
                sample["error_type"] = raw.get("error_type")
                sample["error"] = raw.get("error")
            samples[arm_name].append(sample)
            print(json.dumps({
                "arm": arm_name, "ordinal": ordinal, "status": sample["status"],
                "polarity": sample.get("raw_target_polarity"), "attention": sample.get("attention"),
                "raw_topology": sample.get("raw_topology"), "authorized_topology": sample.get("topology"),
                "error": sample.get("error"),
            }, ensure_ascii=False), flush=True)
        raw0 = raw_by_arm["K0"][-1]
        replay = dict(raw0)
        replay["sample_id"] = f"K1-I-{ordinal}"
        replay["relation_source_arm"] = "K0_REPLAY"
        samples["K1-I"].append(downstream_sample(replay, arm_name="K1-I", arm=arms["K1-I"], strategy=strategy))
        print(json.dumps({
            "arm": "K1-I", "ordinal": ordinal, "status": samples["K1-I"][-1]["status"],
            "polarity": samples["K1-I"][-1].get("raw_target_polarity"),
            "attention": samples["K1-I"][-1].get("attention"),
        }, ensure_ascii=False), flush=True)
    summaries = {arm: summarize_arm(rows) for arm, rows in samples.items()}
    structural_ok = summaries["K0"]["n_ok"] == n and summaries["K1-S"]["n_ok"] == n
    semantic_perm = None
    if structural_ok:
        semantic_perm = permutation_calibrate(
            samples["K0"], samples["K1-S"], statistic=polarity_js,
            permutations=PERMUTATIONS, seed=PERMUTATION_SEED,
        )
    modal0, modal1 = modal_polarity(samples["K0"]), modal_polarity(samples["K1-S"])
    semantic_gate = {
        "structural_success": structural_ok,
        "k0_modal": modal0,
        "k1s_modal": modal1,
        "directional_modal_flip": modal0 == "CHALLENGE_ONLY" and modal1 == "REINFORCE_ONLY",
        "permutation": semantic_perm,
        "gate_pass": bool(structural_ok and modal0 == "CHALLENGE_ONLY" and modal1 == "REINFORCE_ONLY" and semantic_perm and semantic_perm["drift_supported_v0_1"]),
    }
    paired_gate = paired_importance_gate(samples["K0"], samples["K1-I"])
    return {
        "run_version": RUN_VERSION,
        "status": "PHASE9A_KERNEL_CAUSAL_ALIGNMENT_V0_2",
        "measurement_sha": git_head(),
        "instrument_version": INSTRUMENT_VERSION,
        "relation_contract_version": CONTRACT_VERSION,
        "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "auditor_artifact": str(AUDITOR_ARTIFACT.relative_to(ROOT)),
        "auditor_sha256": AUDITOR_SHA256,
        "model_configuration": {
            "requested_model": settings.llm_model,
            "thinking": "disabled",
            "temperature": 0.1,
        },
        "strategy": strategy.execution_snapshot(),
        "n_per_semantic_arm": n,
        "arms": {name: serialize_arm(arm) for name, arm in arms.items()},
        "samples": samples,
        "summaries": summaries,
        "semantic_gate": semantic_gate,
        "importance_gate": paired_gate,
        "guardrails": [
            "Exact frozen RS05 Auditor artifact; no Sensor/Auditor/Locate call.",
            "K0 and K1-S differ only in materialized target proposition at Relation Mapping.",
            "K1-I reuses each exact K0 Relation Mapping realization; no independent semantic call.",
            "Relation Mapping emits only operation, target id, reason; cardinal authority/provenance/Attention fields are absent.",
            "Targeted support is deterministically bound to preregistered direct unit RS05-U01.",
            "Grounding is deterministic and cannot create the primary raw polarity flip.",
            "OPEN_NEW has no preregistered jurisdiction in this single-belief probe and is rejected downstream.",
            "Cardinal-free effect existence; raw change_magnitude has zero authority.",
            "No outcome-dependent prompt, intervention, support, Grounding, or sample-selection tuning.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=INITIAL_N)
    args = parser.parse_args()
    out = collect(args.n)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    print("RESULT_SHA256=" + sha256(path))
    print("SUMMARY=" + json.dumps({
        "semantic_gate": out["semantic_gate"],
        "importance_gate": out["importance_gate"],
        "attention": {arm: out["summaries"][arm]["attention_counts"] for arm in ("K0", "K1-S", "K1-I")},
        "polarity": {arm: out["summaries"][arm]["raw_polarity_counts"] for arm in ("K0", "K1-S", "K1-I")},
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
