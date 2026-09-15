from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment
from app.services.matching import KernelMatch
from app.services.scheduler import (
    AwarenessSignals,
    RuntimeView,
    SchedulerFeatures,
    decision_strategy_snapshot,
    get_decision_strategy,
    route,
    validate_plan,
)

STRATEGY_ID = "pareto-multidelta-cardinal-free-effect-anchored-open-new"


def neutral_features(*, threatens_active_work: bool = False) -> SchedulerFeatures:
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
        threatens_active_work=threatens_active_work,
    )


def _band_value(name: str | None) -> float:
    return 1.0 if str(name or "").upper() == "HIGH" else 0.0


def _match(case_index: int, node_type: str) -> KernelMatch:
    return KernelMatch(
        node_id=UUID(int=case_index + 1),
        node_type=node_type,
        title=f"Phase10E {node_type.lower()} fixture",
        score=1.0,
        reason="Phase10E frozen proxy-Gold fixture",
        structural=node_type in {"GOAL", "PROJECT"},
        relevance_type="STRUCTURAL" if node_type in {"GOAL", "PROJECT"} else node_type,
    )


@dataclass(frozen=True)
class BuiltCase:
    case: dict
    features: SchedulerFeatures
    runtime: RuntimeView
    assessment: CognitiveImpactAssessment
    matches: list[KernelMatch]
    awareness: AwarenessSignals | None


def build_case(case: dict, case_index: int) -> BuiltCase:
    runtime_raw = case.get("runtime") or {}
    runtime = RuntimeView(**{k: v for k, v in runtime_raw.items() if k in RuntimeView.__dataclass_fields__})
    features = neutral_features(threatens_active_work=bool(runtime.threatens_active_work))
    awareness_raw = case.get("awareness")
    awareness = AwarenessSignals(**awareness_raw) if isinstance(awareness_raw, dict) else None
    operation = case.get("operation")
    if not operation:
        return BuiltCase(case, features, runtime, CognitiveImpactAssessment(effects=[]), [], awareness)

    kind = CognitiveEffectKind(str(operation))
    matches: list[KernelMatch] = []
    target_id = None
    target_node_type = case.get("node_type")
    jurisdiction_anchor_ids: list[str] = []
    if kind == CognitiveEffectKind.OPEN_NEW:
        anchor = _match(case_index, "PROJECT")
        matches = [anchor]
        jurisdiction_anchor_ids = [str(anchor.node_id)]
        target_node_type = None
    else:
        match = _match(case_index, str(target_node_type or "BELIEF"))
        matches = [match]
        target_id = match.node_id

    effect = CognitiveEffect(
        target_kernel_node_id=target_id,
        operation=kind,
        change_magnitude=0.0,
        epistemic_strength=_band_value(case.get("epistemic_band")),
        target_importance=_band_value(case.get("importance_band")),
        reason="Phase10E proxy Human-Gold frozen effect",
        exploration_candidate=kind == CognitiveEffectKind.OPEN_NEW,
        target_node_type=target_node_type,
        support_unit_ids=[f"proxy-unit-{case_index:02d}"],
        jurisdiction_anchor_ids=jurisdiction_anchor_ids,
        grounding_class="DIRECT" if _band_value(case.get("epistemic_band")) else "PARTIAL",
        provenance_role="PRIMARY_SOURCE",
        authority_reason="PHASE10E_PROXY_FIXTURE",
    )
    return BuiltCase(case, features, runtime, CognitiveImpactAssessment(effects=[effect]), matches, awareness)


def evaluate_case(case: dict, case_index: int) -> dict:
    built = build_case(case, case_index)
    strategy = get_decision_strategy(STRATEGY_ID)
    draft = validate_plan(
        route(
            built.features,
            built.runtime,
            assessment=built.assessment,
            matches=built.matches,
            awareness=built.awareness,
            decision_strategy=strategy,
        )
    )
    predicted = draft.disposition.value
    gold = str(case["gold_disposition"])
    return {
        "id": case["id"],
        "regime": case["regime"],
        "gold_disposition": gold,
        "predicted_disposition": predicted,
        "exact_hit": predicted == gold,
        "reason": draft.reason,
        "decision_cause": draft.decision_effect.as_dict() if draft.decision_effect else None,
        "strategy": decision_strategy_snapshot(strategy),
        "proxy_rationale": case.get("rationale"),
    }


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text())
