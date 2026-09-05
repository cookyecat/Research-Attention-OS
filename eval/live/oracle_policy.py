"""Oracle-Δ Attention Policy eval: Human Gold / frozen Δ → production route().

Does not call Extract, Locate, or Impact. Does not copy Scheduler thresholds.
When Human Gold only has a public Update, magnitudes are explicit eval defaults
so a canonical effect exists; they are not production policy constants.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid5, NAMESPACE_URL

from eval.live.schema import FrozenDelta, HumanGold, PolicyRuntime

# Eval-only construction when gold specifies an operation without frozen magnitudes.
ORACLE_PUBLIC_UPDATE_DEFAULTS = {
    "change_magnitude": 0.75,
    "epistemic_strength": 0.50,
    "target_importance": 0.75,
}

_DISPOSITION_RANK = {"ENGAGE": 3, "WATCH": 2, "AWARE": 1, "DROP": 0}

# Fixture types for KernelMatch construction. Picker UI still omits ontology.
MVP_NODE_TYPES = {
    "G1": "GOAL",
    "P1": "PROJECT",
    "BT1": "BOTTLENECK",
    "Q1": "QUESTION",
    "B1": "BELIEF",
    "M1": "MODEL",
    "P2": "PROJECT",
    "Q2": "QUESTION",
    "B2": "BELIEF",
    "D1": "DECISION",
}


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
    return {
        "disposition_distance": abs(p - g),
        "exact_disposition_hit": pred == gold,
        "false_drop": bool(pred == "DROP" and gold != "DROP"),
        "over_attention": p > g,
        "under_attention": p < g,
        "critical_under_attention": bool(gold in {"ENGAGE", "WATCH"} and pred == "DROP"),
    }


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


def _operation_and_target(
    gold: HumanGold | None,
    frozen: FrozenDelta | None,
) -> tuple[str | None, str | None, str | None]:
    if frozen is not None and (frozen.operation or frozen.target_node_id or frozen.target_type):
        return frozen.operation, frozen.target_node_id, frozen.target_type
    update = gold.update if gold is not None else None
    if update is None:
        return None, None, None
    return update.operation, update.target_node_id, None


def _magnitudes(frozen: FrozenDelta | None) -> dict[str, float]:
    values = dict(ORACLE_PUBLIC_UPDATE_DEFAULTS)
    if frozen is None:
        return values
    if frozen.change_magnitude is not None:
        values["change_magnitude"] = float(frozen.change_magnitude)
    if frozen.epistemic_strength is not None:
        values["epistemic_strength"] = float(frozen.epistemic_strength)
    if frozen.target_importance is not None:
        values["target_importance"] = float(frozen.target_importance)
    return values


def build_oracle_inputs(
    gold: HumanGold | None = None,
    *,
    frozen_delta: FrozenDelta | None = None,
):
    """Turn gold/frozen Δ into production CognitiveImpactAssessment + KernelMatch list."""
    from app.enums import CognitiveEffectKind
    from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment
    from app.services.matching import KernelMatch

    operation, target_id, target_type = _operation_and_target(gold, frozen_delta)
    if not operation:
        return CognitiveImpactAssessment(effects=[]), []

    node_type = (target_type or MVP_NODE_TYPES.get(str(target_id or ""), "") or "BELIEF").upper()
    mags = _magnitudes(frozen_delta)
    nid = snapshot_node_uuid(str(target_id)) if target_id else None
    if operation in {"REINFORCE", "CHALLENGE"} and nid is None:
        return CognitiveImpactAssessment(effects=[]), []

    matches: list[KernelMatch] = []
    if nid is not None:
        structural = node_type == "DECISION"
        matches.append(
            KernelMatch(
                node_id=nid,
                node_type=node_type,
                title=str(target_id),
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
        change_magnitude=mags["change_magnitude"],
        epistemic_strength=mags["epistemic_strength"],
        target_importance=mags["target_importance"],
        reason=(frozen_delta.reason if frozen_delta and frozen_delta.reason else "oracle frozen Δ"),
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
    """Call production route() + validate_plan() on frozen/gold Δ. No Extract/Locate/Impact."""
    from app.services.scheduler import route, validate_plan

    assessment, matches = build_oracle_inputs(gold, frozen_delta=frozen_delta)
    features = _neutral_features()
    assessment.features = features
    draft = validate_plan(
        route(features, _runtime_view(runtime_context), assessment=assessment, matches=matches)
    )
    disposition = draft.disposition.value if hasattr(draft.disposition, "value") else str(draft.disposition)
    expected = draft.expected_output.value if hasattr(draft.expected_output, "value") else str(draft.expected_output)
    return {
        "disposition": disposition,
        "expected_output": expected,
        "reason": draft.reason,
        "watch_after_processing": bool(draft.watch_after_processing),
        "used_production_route": True,
        "skipped_stages": ["extract", "locate", "impact"],
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
    oracle_disp = (oracle or {}).get("disposition")
    return {
        "gold_disposition": gold_disp,
        "gold_update": gold_update,
        "production_disposition": production_disposition,
        "production_update": production_update,
        "oracle_policy_disposition": oracle_disp,
        "production": compare_disposition(gold_disp, production_disposition),
        "oracle": compare_disposition(gold_disp, oracle_disp),
    }
