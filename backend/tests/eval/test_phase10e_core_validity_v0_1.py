from __future__ import annotations

from uuid import uuid4

import pytest

from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment
from app.services.matching import KernelMatch
from app.services.scheduler import (
    RuntimeView,
    SchedulerFeatures,
    decision_strategy_snapshot,
    get_decision_strategy,
    route,
    validate_plan,
)
from eval.live.phase10e_core_validity_v0_1 import audit_payload, state_from_payload


def _features() -> SchedulerFeatures:
    return SchedulerFeatures(
        topic_relevance=1.0,
        structural_relevance=1.0,
        decision_relevance=1.0,
        novelty=0.0,
        credibility=1.0,
        kernel_delta=0.0,
        bottleneck_alignment=1.0,
        disagreement=0.0,
        actionability=0.0,
        temporal_value=0.0,
        cognitive_cost=1.0,
    )


def _match(node_type: str = "BOTTLENECK") -> KernelMatch:
    return KernelMatch(
        node_id=uuid4(),
        node_type=node_type,
        title=f"active {node_type.lower()}",
        score=1.0,
        reason="controlled test match",
        structural=False,
        relevance_type="BOTTLENECK" if node_type == "BOTTLENECK" else "DECISION",
    )


def _payload(*, node_type: str = "BOTTLENECK", operation=CognitiveEffectKind.CHALLENGE) -> dict:
    features = _features()
    match = _match(node_type)
    effect = CognitiveEffect(
        target_kernel_node_id=match.node_id,
        operation=operation,
        change_magnitude=0.0,
        epistemic_strength=1.0,
        target_importance=1.0,
        reason="controlled authorized effect",
        target_node_type=node_type,
        support_unit_ids=["unit-1"],
        grounding_class="DIRECT",
        provenance_role="PRIMARY_SOURCE",
        authority_reason="DIRECT_PRIMARY",
    )
    assessment = CognitiveImpactAssessment(effects=[effect])
    strategy = get_decision_strategy("pareto-multidelta-cardinal-free-effect-anchored-open-new")
    draft = validate_plan(
        route(features, RuntimeView(), assessment=assessment, matches=[match], decision_strategy=strategy)
    )
    match_dict = {
        "node_id": str(match.node_id),
        "node_type": match.node_type,
        "title": match.title,
        "score": match.score,
        "reason": match.reason,
        "structural": match.structural,
        "relevance_type": match.relevance_type,
    }
    debug = {
        "features": features.as_dict(),
        "cognitive_impact": assessment.as_dict(),
        "matches": [match_dict],
        "decision_strategy": decision_strategy_snapshot(strategy),
        "decision_cause": draft.decision_effect.as_dict() if draft.decision_effect else None,
        "decision_cause_bound": True,
        "no_delta_awareness": {},
    }
    return {
        "features": features.as_dict(),
        "cognitive_impact": assessment.as_dict(),
        "kernel_matches": [match_dict],
        "attention_plan": {
            "disposition": draft.disposition.value,
            "runtime_snapshot": {},
            "score_debug": debug,
        },
        "execution_snapshot": {"decision_strategy": decision_strategy_snapshot(strategy)},
        "analysis_run": {"id": str(uuid4())},
    }


def test_replay_is_strategy_explicit_and_exact() -> None:
    result = audit_payload(_payload())
    assert result["strategy_identity_parity"] is True
    assert result["disposition_parity"] is True
    assert result["decision_cause_parity"] is True
    assert result["stored_strategy"]["strategy_id"] == "pareto-multidelta-cardinal-free-effect-anchored-open-new"


def test_missing_strategy_snapshot_fails_closed() -> None:
    payload = _payload()
    payload["attention_plan"]["score_debug"].pop("decision_strategy")
    payload.pop("execution_snapshot")
    with pytest.raises(ValueError, match="explicit stored decision-strategy"):
        state_from_payload(payload)


def test_strategy_version_mismatch_fails_closed() -> None:
    payload = _payload()
    payload["attention_plan"]["score_debug"]["decision_strategy"]["version"] = "future-or-stale-version"
    with pytest.raises(ValueError, match="version mismatch"):
        state_from_payload(payload)


def test_observed_style_single_effect_has_no_pareto_join_divergence() -> None:
    result = audit_payload(_payload(node_type="BOTTLENECK", operation=CognitiveEffectKind.REINFORCE))
    assert result["admitted_effect_count"] == 1
    assert result["pareto_vs_all_join_disposition_parity"] is True
