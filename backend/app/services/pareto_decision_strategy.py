from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from app.enums import CognitiveEffectKind, Disposition, Urgency
from app.services.cognitive_impact import (
    CognitiveEffect,
    CognitiveImpactAssessment,
    legal_public_effects,
    legal_semantic_effects,
    normalize_frozen_transition,
    select_primary_effect,
    visible_prediction_from_decision_cause,
    visible_prediction_from_frozen,
)
from app.services.effect_admission import (
    ANCHORED_OPEN_NEW_ADMISSION,
    LEGAL_PUBLIC_EFFECT_ADMISSION,
)
from app.services.effect_calibration import (
    MAGNITUDE_FREE_CALIBRATION,
    RAW_CARDINAL_CALIBRATION,
    epistemic_band,
    importance_band,
    raw_change_band,
)
from app.services.scheduler import (
    AwarenessSignals,
    PlanDraft,
    RuntimeView,
    _apply_runtime_overlays,
    _bind_decision_scope,
    _cognitive_disposition,
)

ATTENTION_RANK = {
    Disposition.DROP: 0,
    Disposition.AWARE: 1,
    Disposition.WATCH: 2,
    Disposition.ENGAGE: 3,
}
def _kind(effect: CognitiveEffect) -> CognitiveEffectKind:
    op = effect.operation
    if isinstance(op, CognitiveEffectKind):
        return op
    return CognitiveEffectKind(str(getattr(op, "value", op)))


def change_band(value: float) -> int:
    """Compatibility alias for raw-cardinal v1."""
    return raw_change_band(value)


def decision_vector(
    effect: CognitiveEffect,
    matches=None,
    *,
    calibration_strategy=RAW_CARDINAL_CALIBRATION,
) -> tuple[int, ...]:
    return calibration_strategy.decision_vector(effect, matches or [])


def dominates(
    a: CognitiveEffect,
    b: CognitiveEffect,
    matches=None,
    *,
    calibration_strategy=RAW_CARDINAL_CALIBRATION,
) -> bool:
    va = decision_vector(a, matches, calibration_strategy=calibration_strategy)
    vb = decision_vector(b, matches, calibration_strategy=calibration_strategy)
    return all(x >= y for x, y in zip(va, vb)) and any(x > y for x, y in zip(va, vb))


def pareto_frontier(
    effects: list[CognitiveEffect],
    matches=None,
    *,
    calibration_strategy=RAW_CARDINAL_CALIBRATION,
) -> list[CognitiveEffect]:
    """Attention frontier only; does not delete CognitiveEffects from semantic state."""
    return [
        effect
        for i, effect in enumerate(effects)
        if not any(
            j != i
            and dominates(other, effect, matches, calibration_strategy=calibration_strategy)
            for j, other in enumerate(effects)
        )
    ]


def _representative_effect(
    effects: list[CognitiveEffect],
    matches,
    *,
    calibration_strategy,
) -> CognitiveEffect | None:
    if not effects:
        return None
    return max(effects, key=lambda effect: calibration_strategy.representative_key(effect, matches or []))


def _aggregate_frontier_plans(
    planned: list[tuple[CognitiveEffect, PlanDraft]],
    matches,
    *,
    calibration_strategy,
) -> tuple[PlanDraft, CognitiveEffect | None]:
    best_rank = max(ATTENTION_RANK[draft.disposition] for _, draft in planned)
    winners = [(effect, draft) for effect, draft in planned if ATTENTION_RANK[draft.disposition] == best_rank]
    representative = _representative_effect(
        [effect for effect, _ in winners], matches, calibration_strategy=calibration_strategy
    ) or winners[0][0]
    selected = next((draft for effect, draft in winners if effect is representative), winners[0][1])
    draft = deepcopy(selected)
    draft.watch_after_processing = any(d.watch_after_processing for _, d in winners)
    draft.watch_triggers = sorted({trigger for _, d in winners for trigger in d.watch_triggers})
    draft.cognitive_budget_minutes = max(
        (d.cognitive_budget_minutes or 0 for _, d in winners), default=draft.cognitive_budget_minutes or 0
    )
    if any(d.urgency == Urgency.PRIORITY for _, d in winners):
        draft.urgency = Urgency.PRIORITY
    draft.reason = (
        f"Pareto frontier={len(planned)}; article disposition is the join of frontier-channel decisions. "
        f"Compatibility representative: {draft.reason}"
    )
    return draft, representative
@dataclass(frozen=True)
class ParetoMultiDeltaDecisionStrategy:
    strategy_id: str = "pareto-multidelta"
    version: str = "pareto-multidelta-v0.1"
    calibration_strategy: object = RAW_CARDINAL_CALIBRATION
    effect_admission_strategy: object = LEGAL_PUBLIC_EFFECT_ADMISSION
    semantic_effect_existence: bool = False

    def execution_snapshot(self) -> dict:
        snapshot = {
            "strategy_id": self.strategy_id,
            "version": self.version,
            "selection": "ordinal-pareto-frontier-v0.1",
            "article_aggregation": "attention-join-v0.1",
            "effect_calibration": self.calibration_strategy.execution_snapshot(),
            "effect_admission": self.effect_admission_strategy.execution_snapshot(),
            "public_update_projection": "strategy-decision-cause-with-legacy-unbound-fallback-v0.1",
            "decision_scope": "strategy-bound-scope-v0.1",
        }
        if self.semantic_effect_existence:
            snapshot["effect_existence"] = "legal-semantic-relation-v0.1"
        return snapshot

    def legal_effects(self, normalized):
        return (
            legal_semantic_effects(normalized)
            if self.semantic_effect_existence
            else legal_public_effects(normalized)
        )

    def route(
        self,
        features,
        runtime: RuntimeView | None = None,
        assessment=None,
        matches=None,
        *,
        awareness: AwarenessSignals | None = None,
    ) -> PlanDraft:
        runtime = runtime or RuntimeView()
        matches = matches or []
        normalized = normalize_frozen_transition(assessment, matches).assessment
        legal_effects = self.legal_effects(normalized)
        admitted_effects = self.effect_admission_strategy.admit(legal_effects, matches)
        frontier = pareto_frontier(
            admitted_effects,
            matches,
            calibration_strategy=self.calibration_strategy,
        )
        if not frontier:
            draft = _cognitive_disposition(features, None, matches, awareness=awareness)
            draft.decision_effect = None
            draft.decision_effect_bound = True
            _bind_decision_scope(draft, None, matches)
            return _apply_runtime_overlays(draft, features, runtime, primary=None, matches=matches)

        planned = [
            (
                effect,
                self.calibration_strategy.channel_plan(effect, features=features, matches=matches),
            )
            for effect in frontier
        ]
        draft, representative = _aggregate_frontier_plans(
            planned, matches, calibration_strategy=self.calibration_strategy
        )
        draft.decision_effect = representative
        draft.decision_effect_bound = True
        _bind_decision_scope(draft, representative, matches)
        return _apply_runtime_overlays(
            draft, features, runtime, primary=representative, matches=matches
        )

    def visible_prediction(self, *, frozen_impact, frozen_matches, disposition, decision_cause=None, decision_cause_bound=False) -> dict:
        # Single public update is a compatibility projection of the actual decision cause.
        if decision_cause_bound:
            return visible_prediction_from_decision_cause(decision_cause, disposition=disposition)
        return visible_prediction_from_frozen(
            frozen_impact=frozen_impact,
            frozen_matches=frozen_matches,
            disposition=disposition,
        )


PARETO_MULTI_DELTA_DECISION_STRATEGY = ParetoMultiDeltaDecisionStrategy()

MAGNITUDE_FREE_PARETO_DECISION_STRATEGY = ParetoMultiDeltaDecisionStrategy(
    strategy_id="pareto-multidelta-magnitude-free",
    version="pareto-multidelta-magnitude-free-v0.1",
    calibration_strategy=MAGNITUDE_FREE_CALIBRATION,
)

ANCHORED_OPEN_NEW_MAGNITUDE_FREE_PARETO_DECISION_STRATEGY = ParetoMultiDeltaDecisionStrategy(
    strategy_id="pareto-multidelta-magnitude-free-anchored-open-new",
    version="pareto-multidelta-magnitude-free-anchored-open-new-v0.1",
    calibration_strategy=MAGNITUDE_FREE_CALIBRATION,
    effect_admission_strategy=ANCHORED_OPEN_NEW_ADMISSION,
)

CARDINAL_FREE_ANCHORED_OPEN_NEW_PARETO_DECISION_STRATEGY = ParetoMultiDeltaDecisionStrategy(
    strategy_id="pareto-multidelta-cardinal-free-anchored-open-new",
    version="pareto-multidelta-cardinal-free-anchored-open-new-v0.1",
    calibration_strategy=MAGNITUDE_FREE_CALIBRATION,
    effect_admission_strategy=ANCHORED_OPEN_NEW_ADMISSION,
    semantic_effect_existence=True,
)
