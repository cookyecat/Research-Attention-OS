from __future__ import annotations

from collections import Counter, defaultdict
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

from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment
from app.services.scheduler import SchedulerFeatures, RuntimeView, get_decision_strategy, route
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core, execution_snapshot as core_snapshot
from eval.live.run_phase8c8_semantic_topology_stability_v0_1 import _code_maps, _nodes
from eval.live.run_phase8c12_locate_relation_longitudinal_v0_1 import reconstruct_historical_modal_matches
from eval.live.run_phase8c7_real_web_magnitude_free_validation_v0_1 import _matches
from eval.live.topology_stability_metrics_v0_1 import summarize_topology_stability

RUN_VERSION = "phase8c13-decision-causal-core-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase8c13_decision_causal_core_v0_1"
SOURCE12 = ROOT / "eval/live/results/phase8c12_locate_relation_longitudinal_v0_1/phase8c12_locate_relation_longitudinal_v0.1_20260910T072032Z.json"
SOURCE12_SHA = "a67d7e40e403c7ad9bd7dd6a82312fd5c720ada0f2bf683b506475eb3d92e8be"
SOURCE8 = ROOT / "eval/live/results/phase8c8_semantic_topology_stability_v0_1/phase8c8_semantic_topology_stability_v0.1_20260909T195553Z.json"
SOURCE8_SHA = "f1d41669867e8cdddd5d8beb62b65348b24e42facbd783d031844297f60f8216"
STRATEGY_ID = "pareto-multidelta-magnitude-free-anchored-open-new"
CASES = ("RS05", "RS15", "RS11", "RS12")


def git_head():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verified(path, expected):
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f"artifact SHA mismatch: {path}: {actual}")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def features():
    return SchedulerFeatures(
        topic_relevance=.5, structural_relevance=.2, decision_relevance=.2,
        novelty=.5, credibility=.6, kernel_delta=.2, bottleneck_alignment=.1,
        disagreement=0, actionability=.3, temporal_value=.3, cognitive_cost=2,
        evidence_maturity=.6, threatens_active_work=False,
    )


def reconstruct_effects(effect_rows, nodes):
    by_code = {str((n.payload or {}).get("phase6b_fixture_code") or n.title): n for n in nodes}
    effects = []
    for row in effect_rows:
        op = CognitiveEffectKind(str(row["operation"]))
        code = row.get("target")
        node = by_code.get(str(code)) if code is not None else None
        effects.append(CognitiveEffect(
            target_kernel_node_id=node.id if node else None,
            operation=op,
            change_magnitude=float(row.get("change_magnitude_debug_only", row.get("change_magnitude", .5))),
            epistemic_strength=float(row.get("epistemic_strength", 0.0)),
            target_importance=float(row.get("target_importance", 0.0)),
            reason=str(row.get("reason") or "replayed effect"),
            exploration_candidate=op == CognitiveEffectKind.OPEN_NEW,
            target_node_type=node.node_type if node else None,
        ))
    return effects


def relation_key_for(nodes):
    _, code_by_str = _code_maps(nodes)
    def key(effect):
        op = effect.operation.value if hasattr(effect.operation, "value") else str(effect.operation)
        target = code_by_str.get(str(effect.target_kernel_node_id)) if effect.target_kernel_node_id else None
        return (op, target)
    return key


def analyze_rows(case_id, effect_samples, native_matches, expected_attention):
    nodes = _nodes(case_id) if case_id.startswith("RS") else _nodes("RS11")
    prod_matches = _matches(native_matches, nodes)
    strategy = get_decision_strategy(STRATEGY_ID)
    rkey = relation_key_for(nodes)
    sample_rows = []
    occurrence = Counter(); necessary = Counter(); sufficient = Counter(); classes = defaultdict(Counter)
    necessary_topologies = []; support_topologies = []

    for sample in effect_samples:
        effects = reconstruct_effects(sample["effects"], nodes)
        assessment = CognitiveImpactAssessment(effects=effects)
        baseline = route(features(), RuntimeView(), assessment=assessment, matches=prod_matches, decision_strategy=strategy).disposition.value
        expected = str(sample[expected_attention])
        if baseline != expected:
            raise RuntimeError(f"baseline replay mismatch {case_id} sample {sample.get('repeat')}: {baseline} != {expected}")
        core = analyze_decision_causal_core(
            assessment=assessment, matches=prod_matches, features=features(), decision_strategy=strategy,
            relation_key=rkey,
        )
        for rel in {rkey(e) for e in effects}:
            occurrence[rel] += 1
        for rel in core.necessary_core:
            necessary[rel] += 1
        for rel in core.sufficient_supports:
            sufficient[rel] += 1
        for rr in core.relations:
            classes[rr.relation][rr.classification] += 1
        necessary_topologies.append(core.necessary_core)
        support_topologies.append(core.sufficient_supports)
        sample_rows.append({
            "repeat": sample.get("repeat"), "baseline_attention": baseline,
            "topology": sorted({rkey(e) for e in effects}, key=repr),
            "causal_profile": core.as_dict(),
        })
        print(json.dumps({
            "case": case_id, "repeat": sample.get("repeat"), "attention": baseline,
            "necessary_core": core.necessary_core, "sufficient_supports": core.sufficient_supports,
        }, ensure_ascii=False), flush=True)

    n = len(effect_samples)
    relation_stats = {}
    all_rel = sorted(set(occurrence) | set(necessary) | set(sufficient), key=repr)
    for rel in all_rel:
        present = occurrence[rel]
        relation_stats[str(rel)] = {
            "occurrence_frequency": present / n if n else 0.0,
            "necessary_frequency": necessary[rel] / n if n else 0.0,
            "sufficient_frequency": sufficient[rel] / n if n else 0.0,
            "necessary_given_present": necessary[rel] / present if present else 0.0,
            "sufficient_given_present": sufficient[rel] / present if present else 0.0,
            "classification_counts": dict(classes[rel]),
        }
    return {
        "n_samples": n,
        "relation_stats": relation_stats,
        "necessary_core_stability": summarize_topology_stability(necessary_topologies).as_dict(),
        "sufficient_support_stability": summarize_topology_stability(support_topologies).as_dict(),
        "samples": sample_rows,
    }


def main():
    src12 = verified(SOURCE12, SOURCE12_SHA)
    src8 = verified(SOURCE8, SOURCE8_SHA)
    row12 = {r["case"]: r for r in src12["cases"]}
    row8 = {r["case"]: r for r in src8["cases"]}
    results = {}

    for case in CASES:
        nodes = _nodes(case)
        native_matches = reconstruct_historical_modal_matches(row8[case], nodes)
        samples = []
        for r in row12[case]["gate12b_relation"]["current"]["runs"]:
            if r["status"] == "OK":
                samples.append({"repeat": r["repeat"], "effects": r["effects"], "attention": r["attention"]})
        results[case] = analyze_rows(case, samples, native_matches, "attention")

    # D negative control: replay the Phase 8C.8 empty-Locate runs. Anchored OPEN_NEW must never become load-bearing.
    d = row8["D"]
    d_nodes = _nodes("RS11")
    d_matches = reconstruct_historical_modal_matches(d, d_nodes)
    d_samples = []
    for r in d["impact"]["runs"]:
        if r["status"] == "OK":
            d_samples.append({"repeat": r["repeat"], "effects": r["effects"], "attention": "DROP"})
    results["D"] = analyze_rows("D", d_samples, d_matches, "attention")

    output = {
        "run_version": RUN_VERSION,
        "status": "DETERMINISTIC_COUNTERFACTUAL_REPLAY",
        "measurement_sha": git_head(),
        "source_phase8c12": str(SOURCE12.relative_to(ROOT)), "source_phase8c12_sha256": SOURCE12_SHA,
        "source_phase8c8": str(SOURCE8.relative_to(ROOT)), "source_phase8c8_sha256": SOURCE8_SHA,
        "decision_strategy": get_decision_strategy(STRATEGY_ID).execution_snapshot(),
        "core_chip": core_snapshot(),
        "results": results,
        "interpretation_guardrails": [
            "No LLM calls occur in Phase 8C.13; it is deterministic counterfactual replay of frozen CognitiveEffects.",
            "Baseline replay must exactly reproduce every stored Article Attention disposition or the run fails closed.",
            "Necessary core is singleton-deletion necessity; sufficient supports capture first-order redundant load-bearing relations.",
            "High occurrence frequency is not equivalent to causal importance.",
            "No multi-relation minimal cut sets or Shapley values are estimated in v0.1.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str)+"\n",encoding="utf-8")
    print('RESULT_PATH='+str(path.relative_to(ROOT)))
    print('RESULT_SHA256='+sha256(path))
    for case, result in results.items():
        print('\n'+case)
        for rel, stat in result['relation_stats'].items(): print(rel, stat)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
