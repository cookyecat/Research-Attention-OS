"""Oracle-Δ Attention Policy eval: Human Gold / frozen Δ → production route().

Does not call Extract, Locate, or Impact. Does not copy Scheduler thresholds.
Positive Δ is scored only from a complete FrozenDelta. Human Gold public Update
without FrozenDelta is diagnostic and oracle-unscorable. Δ=NONE (update null)
is a complete definition and is scored.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID, uuid5, NAMESPACE_URL

from eval.live.schema import (
    FrozenDelta,
    HumanGold,
    PolicyRuntime,
    assert_gold_frozen_consistent,
    gold_update_operation,
    is_complete_positive_frozen_delta,
)

_DISPOSITION_RANK = {"ENGAGE": 3, "WATCH": 2, "AWARE": 1, "DROP": 0}
OracleKind = Literal["none", "positive", "unscorable", "skip"]


def snapshot_node_uuid(picker_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"raos.kernel.snapshot.{picker_id}")


def compare_disposition(gold: str | None, pred: str | None) -> dict[str, Any]:
    if not gold or gold not in _DISPOSITION_RANK or not pred or pred not in _DISPOSITION_RANK:
        return {
            "disposition_distance": None,
            "exact_disposition_hit": None,
            "false_drop": None,
            "over_attention": None,
            "under_attention": None,
            "critical_under_attention": None,
        }
    g = _DISPOSITION_RANK[gold]
    p = _DISPOSITION_RANK[pred]
    under = p < g
    return {
        "disposition_distance": abs(p - g),
        "exact_disposition_hit": pred == gold,
        "false_drop": bool(pred == "DROP" and gold != "DROP"),
        "over_attention": p > g,
        "under_attention": under,
        "critical_under_attention": bool(under and (g - p) >= 2),
    }


def oracle_kind(gold: HumanGold | None, frozen: FrozenDelta | None) -> OracleKind:
    """none = Δ=NONE scored; positive = complete FrozenDelta; unscorable = gold update only."""
    gold_op = gold_update_operation(gold)
    if is_complete_positive_frozen_delta(frozen):
        return "positive"
    if gold_op or (frozen is not None and frozen.operation is not None):
        return "unscorable"
    if gold is not None and gold.disposition:
        return "none"
    return "skip"


def _neutral_features():
    from app.services.scheduler import SchedulerFeatures

    return SchedulerFeatures(
        topic_relevance=0.0,
        structural_relevance=0.0,
        decision_relevance=0.0,
        novelty=0.0,
        credibility=0.0,
        kernel_delta=0.0,
        bottleneck_alignment=0.0,
        disagreement=0.0,
        actionability=0.0,
        temporal_value=0.0,
        cognitive_cost=1.0,
        evidence_maturity=0.6,
        threatens_active_work=False,
    )


def _runtime_view(runtime: PolicyRuntime | None):
    from app.services.scheduler import RuntimeView

    if runtime is None:
        return RuntimeView()
    return RuntimeView(
        current_task=runtime.current_task,
        session_topic=runtime.session_topic,
        available_attention_minutes=runtime.available_attention_minutes,
        interruptibility=runtime.interruptibility or "MEDIUM",
        cognitive_capacity=runtime.cognitive_capacity or "NORMAL",
        deadline_minutes=runtime.deadline_minutes,
    )


def build_oracle_inputs(*, frozen_delta: FrozenDelta | None = None):
    """Build production assessment from a complete FrozenDelta, or empty Δ=NONE."""
    from app.enums import CognitiveEffectKind
    from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment
    from app.services.matching import KernelMatch

    if frozen_delta is None or frozen_delta.operation is None:
        return CognitiveImpactAssessment(effects=[]), []

    operation = frozen_delta.operation
    node_type = (frozen_delta.target_type or "").upper()
    nid = snapshot_node_uuid(str(frozen_delta.target_node_id)) if frozen_delta.target_node_id else None
    matches: list[KernelMatch] = []
    if nid is not None and node_type:
        structural = node_type == "DECISION"
        matches.append(
            KernelMatch(
                node_id=nid,
                node_type=node_type,
                title=str(frozen_delta.target_node_id),
                score=0.9,
                reason="oracle frozen Δ target",
                structural=structural,
                relevance_type="STRUCTURAL" if structural else "TOPIC",
            )
        )
    kind = CognitiveEffectKind(operation)
    effect = CognitiveEffect(
        target_kernel_node_id=None if operation == "OPEN_NEW" else nid,
        operation=kind,
        change_magnitude=float(frozen_delta.change_magnitude),
        epistemic_strength=float(frozen_delta.epistemic_strength),
        target_importance=float(frozen_delta.target_importance),
        reason=frozen_delta.reason or "oracle frozen Δ",
        exploration_candidate=operation == "OPEN_NEW",
        target_node_type=None if operation == "OPEN_NEW" else node_type,
    )
    return CognitiveImpactAssessment(effects=[effect], exploration_candidate=operation == "OPEN_NEW"), matches


def run_oracle_policy(
    gold: HumanGold | None = None,
    *,
    frozen_delta: FrozenDelta | None = None,
    runtime_context: PolicyRuntime | None = None,
) -> dict[str, Any]:
    """Call production route() + validate_plan() only when the Δ is complete."""
    from app.services.scheduler import route, validate_plan

    assert_gold_frozen_consistent(gold, frozen_delta)
    kind = oracle_kind(gold, frozen_delta)
    base = {
        "skipped_stages": ["extract", "locate", "impact"],
        "oracle_kind": kind,
    }
    if kind == "skip":
        return {
            **base,
            "disposition": None,
            "scorable": False,
            "unscorable_reason": "no gold disposition and no complete FrozenDelta",
            "used_production_route": False,
        }
    if kind == "unscorable":
        reason = (
            "positive Human Gold update requires a complete FrozenDelta"
            if gold_update_operation(gold)
            else "FrozenDelta is incomplete for Oracle-Δ scoring"
        )
        return {
            **base,
            "disposition": None,
            "scorable": False,
            "unscorable_reason": reason,
            "used_production_route": False,
        }

    assessment, matches = build_oracle_inputs(frozen_delta=frozen_delta if kind == "positive" else None)
    features = _neutral_features()
    assessment.features = features
    draft = validate_plan(
        route(features, _runtime_view(runtime_context), assessment=assessment, matches=matches)
    )
    disposition = draft.disposition.value if hasattr(draft.disposition, "value") else str(draft.disposition)
    expected = draft.expected_output.value if hasattr(draft.expected_output, "value") else str(draft.expected_output)
    return {
        **base,
        "disposition": disposition,
        "expected_output": expected,
        "reason": draft.reason,
        "watch_after_processing": bool(draft.watch_after_processing),
        "used_production_route": True,
        "scorable": True,
        "unscorable_reason": None,
    }


def attention_policy_eval_row(
    *,
    gold: HumanGold | None,
    production_disposition: str | None,
    production_update: dict | None,
    oracle: dict[str, Any] | None,
) -> dict[str, Any]:
    gold_disp = gold.disposition if gold is not None else None
    gold_update = None
    if gold is not None:
        upd = gold.update
        gold_update = {
            "operation": upd.operation if upd else None,
            "target_node_id": upd.target_node_id if upd else None,
        }
    oracle = oracle or {}
    scorable = bool(oracle.get("scorable"))
    oracle_disp = oracle.get("disposition") if scorable else None
    return {
        "gold_disposition": gold_disp,
        "gold_update": gold_update,
        "production_disposition": production_disposition,
        "production_update": production_update,
        "oracle_policy_disposition": oracle_disp,
        "oracle_scorable": scorable,
        "oracle_unscorable_reason": None if scorable else oracle.get("unscorable_reason"),
        "production": compare_disposition(gold_disp, production_disposition),
        "oracle": compare_disposition(gold_disp, oracle_disp) if scorable else compare_disposition(gold_disp, None),
    }
