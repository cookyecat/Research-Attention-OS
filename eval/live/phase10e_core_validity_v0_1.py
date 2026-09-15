from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.cognitive_impact import assessment_from_dict, normalize_frozen_transition
from app.services.no_delta_awareness import awareness_signals_from_trace
from app.services.pareto_decision_strategy import _aggregate_frontier_plans, pareto_frontier
from app.services.scheduler import (
    RuntimeView,
    SchedulerFeatures,
    _apply_runtime_overlays,
    _bind_decision_scope,
    _cognitive_disposition,
    decision_strategy_snapshot,
    get_decision_strategy_from_snapshot,
    matches_from_debug,
    route,
    validate_plan,
)

CURRENT_STRATEGY_ID = "pareto-multidelta-cardinal-free-effect-anchored-open-new"
CURRENT_STRATEGY_VERSION = "pareto-multidelta-cardinal-free-effect-anchored-open-new-v0.2"
ATTENTION_RANK = {"DROP": 0, "AWARE": 1, "WATCH": 2, "ENGAGE": 3}


@dataclass(frozen=True)
class FrozenDecisionState:
    run_id: str | None
    persisted_disposition: str
    persisted_decision_cause: dict | None
    strategy_snapshot: dict
    strategy: Any
    features: SchedulerFeatures
    runtime: RuntimeView
    assessment: Any
    matches: list
    awareness: Any


def _filtered_dataclass(cls, raw: dict | None):
    raw = raw or {}
    return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})


def strategy_snapshot_from_payload(payload: dict) -> dict | None:
    plan = payload.get("attention_plan") or {}
    debug = plan.get("score_debug") or {}
    return debug.get("decision_strategy") or (payload.get("execution_snapshot") or {}).get("decision_strategy")


def require_explicit_strategy(snapshot: dict | None):
    if not isinstance(snapshot, dict) or not snapshot.get("strategy_id") or not snapshot.get("version"):
        raise ValueError("Phase 10E replay requires an explicit stored decision-strategy id and version")
    strategy = get_decision_strategy_from_snapshot(snapshot)
    actual = decision_strategy_snapshot(strategy)
    if actual.get("strategy_id") != snapshot.get("strategy_id") or actual.get("version") != snapshot.get("version"):
        raise ValueError(f"Stored decision strategy does not match runtime implementation: stored={snapshot} actual={actual}")
    return strategy


def state_from_payload(payload: dict) -> FrozenDecisionState:
    plan = payload.get("attention_plan") or {}
    if not isinstance(plan, dict) or not plan.get("disposition"):
        raise ValueError("Phase 10E replay requires the original persisted attention_plan")
    debug = plan.get("score_debug") or {}
    snapshot = strategy_snapshot_from_payload(payload)
    strategy = require_explicit_strategy(snapshot)

    feature_raw = payload.get("features") or debug.get("features")
    if not isinstance(feature_raw, dict):
        raise ValueError("Phase 10E replay requires persisted SchedulerFeatures")
    features = _filtered_dataclass(SchedulerFeatures, feature_raw)

    impact_raw = debug.get("cognitive_impact") or payload.get("cognitive_impact")
    assessment = assessment_from_dict(impact_raw)
    if assessment is None:
        raise ValueError("Phase 10E replay requires persisted cognitive_impact")

    match_raw = debug.get("matches") or payload.get("kernel_matches") or []
    matches = matches_from_debug(match_raw)
    runtime = _filtered_dataclass(RuntimeView, plan.get("runtime_snapshot") or {})
    no_delta_trace = debug.get("no_delta_awareness") or payload.get("no_delta_awareness") or {}
    awareness = awareness_signals_from_trace(no_delta_trace)

    run_meta = payload.get("analysis_run") or {}
    return FrozenDecisionState(
        run_id=str(run_meta.get("id")) if run_meta.get("id") else None,
        persisted_disposition=str(plan["disposition"]),
        persisted_decision_cause=debug.get("decision_cause"),
        strategy_snapshot=dict(snapshot),
        strategy=strategy,
        features=features,
        runtime=runtime,
        assessment=assessment,
        matches=matches,
        awareness=awareness,
    )


def replay_state(state: FrozenDecisionState):
    return validate_plan(
        route(
            state.features,
            state.runtime,
            assessment=state.assessment,
            matches=state.matches,
            awareness=state.awareness,
            decision_strategy=state.strategy,
        )
    )


def _effect_dict(effect) -> dict | None:
    return effect.as_dict() if effect is not None else None


def all_admitted_join_route(state: FrozenDecisionState):
    """Counterfactual only: same admission/channel policy, but skip Pareto pruning."""
    strategy = state.strategy
    if not all(hasattr(strategy, name) for name in ("legal_effects", "effect_admission_strategy", "calibration_strategy")):
        raise ValueError("All-effect join comparison is defined only for the Pareto strategy family")

    normalized = normalize_frozen_transition(state.assessment, state.matches).assessment
    legal = strategy.legal_effects(normalized)
    admitted = strategy.effect_admission_strategy.admit(legal, state.matches)
    if not admitted:
        draft = _cognitive_disposition(state.features, None, state.matches, awareness=state.awareness)
        draft.decision_effect = None
        draft.decision_effect_bound = True
        _bind_decision_scope(draft, None, state.matches)
        return validate_plan(
            _apply_runtime_overlays(
                draft,
                state.features,
                state.runtime,
                primary=None,
                matches=state.matches,
            )
        ), admitted, []

    planned = [
        (effect, strategy.calibration_strategy.channel_plan(effect, features=state.features, matches=state.matches))
        for effect in admitted
    ]
    draft, representative = _aggregate_frontier_plans(
        planned,
        state.matches,
        calibration_strategy=strategy.calibration_strategy,
    )
    draft.decision_effect = representative
    draft.decision_effect_bound = True
    _bind_decision_scope(draft, representative, state.matches)
    draft = _apply_runtime_overlays(
        draft,
        state.features,
        state.runtime,
        primary=representative,
        matches=state.matches,
    )
    frontier = pareto_frontier(
        admitted,
        state.matches,
        calibration_strategy=strategy.calibration_strategy,
    )
    return validate_plan(draft), admitted, frontier


def audit_payload(payload: dict) -> dict:
    state = state_from_payload(payload)
    replay = replay_state(state)
    replay_snapshot = decision_strategy_snapshot(state.strategy)
    all_join = None
    admitted: list = []
    frontier: list = []
    if replay_snapshot.get("strategy_id", "").startswith("pareto-"):
        all_join, admitted, frontier = all_admitted_join_route(state)

    replay_cause = _effect_dict(replay.decision_effect)
    result = {
        "run_id": state.run_id,
        "persisted_disposition": state.persisted_disposition,
        "replay_disposition": replay.disposition.value,
        "disposition_parity": replay.disposition.value == state.persisted_disposition,
        "stored_strategy": {
            "strategy_id": state.strategy_snapshot.get("strategy_id"),
            "version": state.strategy_snapshot.get("version"),
        },
        "replay_strategy": {
            "strategy_id": replay_snapshot.get("strategy_id"),
            "version": replay_snapshot.get("version"),
        },
        "strategy_identity_parity": (
            replay_snapshot.get("strategy_id") == state.strategy_snapshot.get("strategy_id")
            and replay_snapshot.get("version") == state.strategy_snapshot.get("version")
        ),
        "persisted_decision_cause": state.persisted_decision_cause,
        "replay_decision_cause": replay_cause,
        "decision_cause_parity": replay_cause == state.persisted_decision_cause,
        "effect_count": len(getattr(state.assessment, "effects", []) or []),
        "admitted_effect_count": len(admitted),
        "pareto_frontier_count": len(frontier),
    }
    if all_join is not None:
        result.update(
            {
                "all_effect_join_disposition": all_join.disposition.value,
                "pareto_vs_all_join_disposition_parity": all_join.disposition == replay.disposition,
                "all_effect_join_decision_cause": _effect_dict(all_join.decision_effect),
                "pareto_vs_all_join_cause_parity": _effect_dict(all_join.decision_effect) == replay_cause,
            }
        )
    return result
