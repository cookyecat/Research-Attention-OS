from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
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

from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.prompts import IMPACT_SYSTEM, IMPACT_SYSTEM_PARETO_COMPAT
from app.services.cognitive_impact import CognitiveImpactAssessment, legal_public_effects, normalize_frozen_transition
from app.services.matching import KernelMatch
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core
from eval.live.phase6b_cognitive_semantics_v0_1 import audited_units_to_extraction, build_phase6b_mvp_kernel_nodes
from eval.live.phase8c2_production_sensor_bridge_v0_1 import _project_production_separations
from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map
from eval.live.run_phase10d3_real_web_static_cognitive_map_v0_1 import branch_relation_key
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import selected_cases

RUN_VERSION = "phase10d6l1-minimal-prompt-authority-shadow-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase10d6l1_minimal_prompt_authority_shadow_v0_1"
STRATEGY_ID = "pareto-multidelta-magnitude-free-anchored-open-new"
CASES = ("A", "D", "X", "N4")
REPEATS = 6


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconstruct_prod_matches(case: dict, nodes) -> list[KernelMatch]:
    by_id = {str(n.id): n for n in nodes}
    out = []
    for row in case["locate"]["modal"]["selected_matches"]:
        node = by_id[str(row["kernel_node_id"])]
        out.append(KernelMatch(
            node_id=node.id,
            node_type=node.node_type,
            title=node.title,
            score=float(row["score"]),
            reason=str(row["reason"]),
            structural=str(row["relevance_type"]).upper() == "STRUCTURAL",
            relevance_type=str(row["relevance_type"]),
        ))
    return out


def effect_row(effect, nodes) -> dict:
    by_id = {str(n.id): str((n.payload or {}).get("phase6b_fixture_code") or n.title) for n in nodes}
    op = effect.operation.value if hasattr(effect.operation, "value") else str(effect.operation)
    return {
        "operation": op,
        "target": by_id.get(str(effect.target_kernel_node_id)) if effect.target_kernel_node_id else None,
        "target_kernel_node_id": str(effect.target_kernel_node_id) if effect.target_kernel_node_id else None,
        "change_magnitude_debug_only": float(effect.change_magnitude),
        "epistemic_strength": float(effect.epistemic_strength),
        "target_importance": float(effect.target_importance),
        "reason": str(effect.reason or ""),
    }


def run_one(label: str, arm: str, ordinal: int, case: dict, nodes, matches, strategy) -> dict:
    system = IMPACT_SYSTEM if arm == "P0" else IMPACT_SYSTEM_PARETO_COMPAT
    version = "production-impact-v2.1-legacy" if arm == "P0" else "production-impact-v2.1-pareto-compat-v0.1"
    provider = ModelBackedCognitiveProvider(impact_system_prompt=system, impact_contract_version=version)
    extraction = _project_production_separations(audited_units_to_extraction(deepcopy(case["frozen_units"])))
    assessment = provider.assess_cognitive_impact(
        "", extraction, matches, nodes=nodes,
        is_duplicate=False, independent_source_count=1, secondary_report_count=0,
        threatens_active_work=False,
    )
    raw_effects = list(getattr(assessment, "raw_effects", None) or [])
    grounded_effects = list(assessment.effects or [])
    normalized = normalize_frozen_transition(assessment, matches).assessment
    legal = legal_public_effects(normalized)
    legal_assessment = CognitiveImpactAssessment(
        effects=legal,
        attention_cost=assessment.attention_cost,
        exploration_candidate=assessment.exploration_candidate,
        features=assessment.features,
        raw_effects=assessment.raw_effects,
    )
    plan = route(
        assessment.features, RuntimeView(), assessment=legal_assessment, matches=matches,
        decision_strategy=strategy,
    )
    key = branch_relation_key(nodes, case["frozen_units"])
    report = analyze_decision_causal_core(
        assessment=legal_assessment, matches=matches, features=assessment.features,
        decision_strategy=strategy, relation_key=key,
    )
    if report.baseline_decision != plan.disposition.value:
        raise RuntimeError(f"causal baseline mismatch {label}/{arm}/{ordinal}")
    topology = sorted({key(e) for e in legal}, key=repr)
    family_rows = [(effect_row(e, nodes)["operation"], effect_row(e, nodes)["target"]) for e in legal]
    duplicate_family_count = len(family_rows) - len(set(family_rows))
    return {
        "sample_id": f"{arm}-{ordinal}",
        "arm": arm,
        "topology": topology,
        "necessary_core": report.necessary_core,
        "sufficient_supports": report.sufficient_supports,
        "attention": plan.disposition.value,
        "effects": [effect_row(e, nodes) for e in legal],
        "raw_effect_count": len(raw_effects),
        "grounded_effect_count": len(grounded_effects),
        "effect_count": len(legal),
        "relation_families": [list(x) for x in family_rows],
        "duplicate_family_count": duplicate_family_count,
        "causal_profile": report.as_dict(),
        "meta": dict(provider.last_meta),
        "impact_contract_version": version,
    }


def summarize_arm(samples: list[dict]) -> dict:
    ok = [s for s in samples if s.get("status") == "OK"]
    if not ok:
        return {"n_ok": 0, "n_error": len(samples)}
    map_samples = [{k: s[k] for k in ("sample_id", "topology", "necessary_core", "sufficient_supports", "attention")} for s in ok]
    m = summarize_static_cognitive_map(map_samples)
    return {
        "n_ok": len(ok), "n_error": len(samples) - len(ok),
        "attention_counts": dict(sorted(Counter(s["attention"] for s in ok).items())),
        "raw_effect_count_mean": sum(s["raw_effect_count"] for s in ok) / len(ok),
        "grounded_effect_count_mean": sum(s["grounded_effect_count"] for s in ok) / len(ok),
        "effect_count_mean": sum(s["effect_count"] for s in ok) / len(ok),
        "empty_legal_count": sum(1 for s in ok if s["effect_count"] == 0),
        "duplicate_family_total": sum(s["duplicate_family_count"] for s in ok),
        "map": m,
    }


def assert_prompt_delta() -> None:
    from app.cognitive.prompts import _IMPACT_DOWNSTREAM_POLICY_LINES
    expected = IMPACT_SYSTEM
    for line in _IMPACT_DOWNSTREAM_POLICY_LINES:
        if line not in expected:
            raise RuntimeError("preregistered downstream-policy line missing from P0")
        expected = expected.replace(line, "")
    if expected != IMPACT_SYSTEM_PARETO_COMPAT:
        raise RuntimeError("P1 prompt differs from P0 beyond preregistered deletions")


def main() -> int:
    assert_prompt_delta()
    selected = selected_cases()
    if tuple(selected) != CASES:
        raise RuntimeError(f"case order mismatch: {tuple(selected)}")
    strategy = get_decision_strategy(STRATEGY_ID)
    nodes = build_phase6b_mvp_kernel_nodes()
    results = {}
    for label in CASES:
        case = selected[label]["case"]
        matches = reconstruct_prod_matches(case, nodes)
        arms = {"P0": [], "P1": []}
        # interleave by ordinal to reduce provider-time drift
        for ordinal in range(1, REPEATS + 1):
            for arm in ("P0", "P1"):
                try:
                    row = run_one(label, arm, ordinal, case, nodes, matches, strategy)
                    row["status"] = "OK"
                except Exception as exc:
                    row = {
                        "sample_id": f"{arm}-{ordinal}", "arm": arm, "status": "ERROR",
                        "error_type": type(exc).__name__, "error": str(exc)[:3000],
                    }
                arms[arm].append(row)
                print(json.dumps({
                    "label": label, "arm": arm, "repeat": ordinal, "status": row["status"],
                    "attention": row.get("attention"), "topology": row.get("topology"),
                    "effect_count": row.get("effect_count"), "error": row.get("error"),
                }, ensure_ascii=False), flush=True)
        results[label] = {
            "source_batch": selected[label]["batch"],
            "frozen_units_replay_sha256": case["frozen_units_replay_sha256"],
            "frozen_locate": case["locate"]["modal"],
            "arms": arms,
            "summary": {arm: summarize_arm(rows) for arm, rows in arms.items()},
        }
        print(json.dumps({"label": label, "summary": {
            a: results[label]["summary"][a].get("attention_counts") for a in ("P0", "P1")
        }}, ensure_ascii=False), flush=True)

    out = {
        "run_version": RUN_VERSION,
        "status": "MINIMAL_PROMPT_AUTHORITY_REMOVAL_SHADOW_AB",
        "measurement_sha": git_head(),
        "repeats_per_arm": REPEATS,
        "cases": list(CASES),
        "prompt_sha256": {"P0": sha_text(IMPACT_SYSTEM), "P1": sha_text(IMPACT_SYSTEM_PARETO_COMPAT)},
        "decision_strategy": strategy.execution_snapshot(),
        "controlled_variable": "delete_two_downstream_policy_instructions_only",
        "results": results,
        "guardrails": [
            "Same frozen real-web audited semantic units and same modal Locate per arm.",
            "Same audited-units to ExtractionResult adapter and production projection per arm.",
            "Same ModelProvider grounding, importance resolver, epistemic handling, runtime and decision strategy per arm.",
            "Only the two preregistered downstream-policy lines are deleted from the P1 Impact system prompt; all other semantic instructions are byte-preserved.",
            "P0/P1 calls are interleaved by ordinal within case.",
            "No outcome-dependent prompt editing or sample expansion.",
            "Production default remains P0 during this gate.",
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
