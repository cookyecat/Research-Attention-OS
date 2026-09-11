from __future__ import annotations

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
from app.cognitive.prompts import IMPACT_SYSTEM
from app.cognitive.schemas import CognitiveImpactResponse
from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import (
    CognitiveEffect, CognitiveImpactAssessment, features_from_impact, ground_effects,
    is_update_eligible_node, legal_public_effects, node_proposition,
    normalize_frozen_transition, resolve_target_importance,
)
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core
from eval.live.phase6b_cognitive_semantics_v0_1 import audited_units_to_extraction, build_phase6b_mvp_kernel_nodes
from eval.live.phase8c2_production_sensor_bridge_v0_1 import _project_production_separations
from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map
from eval.live.run_phase10d3_real_web_static_cognitive_map_v0_1 import branch_relation_key
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import selected_cases
from eval.live.run_phase10d6b_prompt_reconciliation_shadow_v0_1 import reconstruct_prod_matches, effect_row

RUN_VERSION = "phase10d6c-canonical-input-reconciliation-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase10d6c_canonical_input_reconciliation_v0_1"
STRATEGY_ID = "pareto-multidelta-magnitude-free-anchored-open-new"
CASES = ("A", "D", "X", "N4")
REPEATS = 6


def git_head():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha256(path: Path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_user_prompt(units, matches, nodes) -> str:
    by_id = {n.id: n for n in nodes}
    canonical = [{
        "unit_id": str(u.get("unit_id") or ""),
        "statement": str(u.get("statement") or ""),
        "epistemic_status": str(u.get("epistemic_status") or ""),
        "confidence": str(u.get("confidence") or ""),
        "supports": list(u.get("supports") or []),
    } for u in units]
    locations = []
    eligible = []
    for m in matches:
        node = by_id[m.node_id]
        base = {
            "id": str(node.id), "type": node.node_type, "title": node.title,
            "proposition": node_proposition(node), "score": m.score,
            "rel": m.relevance_type, "role": "location",
        }
        locations.append(base)
        if is_update_eligible_node(node.node_type):
            payload = node.payload or {}
            eligible.append({**base, "scope": payload.get("scope") if isinstance(payload, dict) else None,
                             "kind": "epistemic_object", "role": "cognitive_target"})
    return (
        "Epistemic objects are Auditor-admitted canonical semantic units. Judge from these units and their supports; raw webpage text is unavailable.\n"
        + "Canonical semantic units:\n" + json.dumps(canonical, ensure_ascii=False)
        + "\n\nKernel locations:\n" + json.dumps(locations, ensure_ascii=False)
        + "\n\nEligible cognitive targets:\n" + json.dumps(eligible, ensure_ascii=False)
        + "\n\nDuplicate: false\nIndependent sources: 1\nSecondary reports: 0\n"
        + "\nReturn JSON:\n"
        + '{"effects":[{"target_kernel_node_id":null,"operation":"REINFORCE","change_magnitude":0.0,"epistemic_strength":0.0,"target_importance":0.0,"reason":"","exploration_candidate":false}],"attention_cost":0.0,"exploration_candidate":false,"evidence_maturity":0.0,"threatens_active_work":false,"marketing_heavy":false,"high_quality_technical":false,"foundational_paper":false}'
    )


def canonical_assess(provider, units, extraction, matches, nodes, *, system_prompt=IMPACT_SYSTEM):
    parsed: CognitiveImpactResponse = provider._complete(
        system_prompt, canonical_user_prompt(units, matches, nodes), CognitiveImpactResponse, stage="impact"
    )
    by_id = {m.node_id: m for m in matches}
    by_id.update({n.id: n for n in nodes})
    raw = []
    for item in parsed.effects:
        node = by_id.get(item.target_kernel_node_id) if item.target_kernel_node_id else None
        ntype = getattr(node, "node_type", None) if node is not None else None
        raw.append(CognitiveEffect(
            target_kernel_node_id=item.target_kernel_node_id,
            operation=CognitiveEffectKind(item.operation),
            change_magnitude=item.change_magnitude,
            epistemic_strength=item.epistemic_strength,
            target_importance=resolve_target_importance(node=node, node_type=ntype, llm_estimate=item.target_importance),
            reason=item.reason,
            exploration_candidate=item.exploration_candidate,
        ))
    provider.last_raw_effects = list(raw)
    grounded = ground_effects(raw, matches, extraction, independent_source_count=1)
    assessment = CognitiveImpactAssessment(
        effects=grounded, attention_cost=parsed.attention_cost,
        exploration_candidate=parsed.exploration_candidate or any(e.exploration_candidate for e in grounded),
        raw_effects=list(raw),
    )
    assessment.features = features_from_impact(
        assessment, matches, extraction,
        attention_cost=parsed.attention_cost,
        exploration_candidate=assessment.exploration_candidate,
        is_duplicate=False, independent_source_count=1, secondary_report_count=0,
        threatens_active_work=False,
        marketing_heavy=parsed.marketing_heavy or extraction.marketing_heavy,
        high_quality_technical=parsed.high_quality_technical,
        foundational_paper=parsed.foundational_paper,
        evidence_maturity=parsed.evidence_maturity,
    )
    provider.last_impact = assessment
    return assessment


def run_one(label, arm, ordinal, case, nodes, matches, strategy):
    extraction = _project_production_separations(audited_units_to_extraction(deepcopy(case["frozen_units"])))
    provider = ModelBackedCognitiveProvider(impact_system_prompt=IMPACT_SYSTEM, impact_contract_version="production-impact-v2.1-legacy")
    if arm == "B0":
        assessment = provider.assess_cognitive_impact(
            "", extraction, matches, nodes=nodes, is_duplicate=False,
            independent_source_count=1, secondary_report_count=0, threatens_active_work=False,
        )
    else:
        assessment = canonical_assess(provider, case["frozen_units"], extraction, matches, nodes)
    normalized = normalize_frozen_transition(assessment, matches).assessment
    legal = legal_public_effects(normalized)
    final_assessment = CognitiveImpactAssessment(
        effects=legal, attention_cost=assessment.attention_cost,
        exploration_candidate=assessment.exploration_candidate,
        features=assessment.features, raw_effects=assessment.raw_effects,
    )
    plan = route(assessment.features, RuntimeView(), assessment=final_assessment, matches=matches, decision_strategy=strategy)
    key = branch_relation_key(nodes, case["frozen_units"])
    report = analyze_decision_causal_core(
        assessment=final_assessment, matches=matches, features=assessment.features,
        decision_strategy=strategy, relation_key=key,
    )
    if report.baseline_decision != plan.disposition.value:
        raise RuntimeError(f"causal baseline mismatch {label}/{arm}/{ordinal}")
    return {
        "sample_id": f"{arm}-{ordinal}", "arm": arm, "status": "OK",
        "raw_effects": [effect_row(e, nodes) for e in provider.last_raw_effects],
        "grounded_effects": [effect_row(e, nodes) for e in legal],
        "raw_effect_count": len(provider.last_raw_effects),
        "grounded_effect_count": len(legal),
        "topology": sorted({key(e) for e in legal}, key=repr),
        "necessary_core": report.necessary_core,
        "sufficient_supports": report.sufficient_supports,
        "attention": plan.disposition.value,
        "causal_profile": report.as_dict(),
        "meta": dict(provider.last_meta),
    }


def summarize(rows):
    ok=[r for r in rows if r.get("status")=="OK"]
    samples=[{k:r[k] for k in ("sample_id","topology","necessary_core","sufficient_supports","attention")} for r in ok]
    return {
        "n_ok":len(ok), "n_error":len(rows)-len(ok),
        "attention_counts":dict(sorted(Counter(r["attention"] for r in ok).items())),
        "raw_effect_count_mean":sum(r["raw_effect_count"] for r in ok)/len(ok) if ok else 0,
        "grounded_effect_count_mean":sum(r["grounded_effect_count"] for r in ok)/len(ok) if ok else 0,
        "map":summarize_static_cognitive_map(samples) if ok else None,
    }


def main():
    selected=selected_cases(); nodes=build_phase6b_mvp_kernel_nodes(); strategy=get_decision_strategy(STRATEGY_ID)
    results={}
    for label in CASES:
        case=selected[label]["case"]; matches=reconstruct_prod_matches(case,nodes); arms={"B0":[],"C1":[]}
        for ordinal in range(1,REPEATS+1):
            for arm in ("B0","C1"):
                try: row=run_one(label,arm,ordinal,case,nodes,matches,strategy)
                except Exception as exc:
                    row={"sample_id":f"{arm}-{ordinal}","arm":arm,"status":"ERROR","error_type":type(exc).__name__,"error":str(exc)[:3000]}
                arms[arm].append(row)
                print(json.dumps({"label":label,"arm":arm,"repeat":ordinal,"status":row["status"],
                    "raw":row.get("raw_effect_count"),"grounded":row.get("grounded_effect_count"),
                    "attention":row.get("attention"),"topology":row.get("topology"),"error":row.get("error")},ensure_ascii=False),flush=True)
        results[label]={"arms":arms,"summary":{a:summarize(v) for a,v in arms.items()},
                        "frozen_units_replay_sha256":case["frozen_units_replay_sha256"],"frozen_locate":case["locate"]["modal"]}
        print(json.dumps({"label":label,"summary":{a:{k:v for k,v in results[label]["summary"][a].items() if k!="map"} for a in arms}},ensure_ascii=False),flush=True)
    out={"run_version":RUN_VERSION,"status":"CANONICAL_INPUT_SHADOW_AB","measurement_sha":git_head(),
         "repeats_per_arm":REPEATS,"cases":list(CASES),"controlled_variable":"impact_user_payload_representation_only",
         "system_prompt":"current production IMPACT_SYSTEM in both arms","decision_strategy":strategy.execution_snapshot(),"results":results,
         "guardrails":["Same frozen world, Kernel, Locate, model path, system prompt, importance resolver, grounding and decision strategy.",
                       "B0 uses ExtractionResult Impact payload; C1 uses canonical Auditor units directly.",
                       "Both arms still use the same ExtractionResult for deterministic production grounding/features.",
                       "Raw pre-grounding and grounded effects are both persisted.","No outcome-dependent expansion or prompt editing.","Production default unchanged."]}
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print('RESULT_PATH='+str(p.relative_to(ROOT))); print('RESULT_SHA256='+sha256(p)); return 0

if __name__=='__main__': raise SystemExit(main())
