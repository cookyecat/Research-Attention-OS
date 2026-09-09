from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from app.enums import CognitiveEffectKind, Disposition, Urgency
from app.services.cognitive_impact import (
    LOW_EPISTEMIC,
    MATERIAL_CHANGE_MIN,
    MEANINGFUL_CHANGE,
    CognitiveEffect,
    CognitiveImpactAssessment,
    legal_public_effects,
    normalize_frozen_transition,
    select_primary_effect,
    visible_prediction_from_frozen,
)
from app.services.scheduler import (
    AwarenessSignals,
    PlanDraft,
    RuntimeView,
    _apply_runtime_overlays,
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
    value = float(value)
    if value <= 0:
        return 0
    if value < MATERIAL_CHANGE_MIN:
        return 1
    if value < MEANINGFUL_CHANGE:
        return 2
    return 3


def epistemic_band(value: float) -> int:
    return 0 if float(value) < LOW_EPISTEMIC else 1


def importance_band(value: float) -> int:
    return 0 if float(value) < 0.55 else 1


def decision_vector(effect: CognitiveEffect) -> tuple[int, int, int, int, int]:
    op = _kind(effect)
    return (
        change_band(effect.change_magnitude),
        epistemic_band(effect.epistemic_strength),
        importance_band(effect.target_importance),
        int(op == CognitiveEffectKind.CHALLENGE),
        int(op == CognitiveEffectKind.OPEN_NEW),
    )
def dominates(a: CognitiveEffect, b: CognitiveEffect) -> bool:
    va = decision_vector(a)
    vb = decision_vector(b)
    return all(x >= y for x, y in zip(va, vb)) and any(x > y for x, y in zip(va, vb))


def pareto_frontier(effects: list[CognitiveEffect]) -> list[CognitiveEffect]:
    """Attention frontier only; does not delete CognitiveEffects from semantic state."""
    return [
        effect
        for i, effect in enumerate(effects)
        if not any(j != i and dominates(other, effect) for j, other in enumerate(effects))
    ]


def _representative_effect(effects: list[CognitiveEffect]) -> CognitiveEffect | None:
    if not effects:
        return None
    return select_primary_effect(CognitiveImpactAssessment(effects=list(effects)))


def _aggregate_frontier_plans(
    planned: list[tuple[CognitiveEffect, PlanDraft]],
) -> tuple[PlanDraft, CognitiveEffect | None]:
    best_rank = max(ATTENTION_RANK[draft.disposition] for _, draft in planned)
    winners = [(effect, draft) for effect, draft in planned if ATTENTION_RANK[draft.disposition] == best_rank]
    representative = _representative_effect([effect for effect, _ in winners]) or winners[0][0]
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

    def execution_snapshot(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "version": self.version,
            "selection": "ordinal-pareto-frontier-v0.1",
            "article_aggregation": "attention-join-v0.1",
            "public_update_projection": "legacy-single-primary-compatibility",
        }

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
        frontier = pareto_frontier(legal_public_effects(normalized))
        if not frontier:
            draft = _cognitive_disposition(features, None, matches, awareness=awareness)
            return _apply_runtime_overlays(draft, features, runtime, primary=None, matches=matches)

        planned = [
            (effect, _cognitive_disposition(features, effect, matches, awareness=None))
            for effect in frontier
        ]
        draft, representative = _aggregate_frontier_plans(planned)
        return _apply_runtime_overlays(
            draft, features, runtime, primary=representative, matches=matches
        )

    def visible_prediction(self, *, frozen_impact, frozen_matches, disposition) -> dict:
        # Public HTTP contract is still single-update. Multi-effect semantics remain in score_debug.
        return visible_prediction_from_frozen(
            frozen_impact=frozen_impact,
            frozen_matches=frozen_matches,
            disposition=disposition,
        )


PARETO_MULTI_DELTA_DECISION_STRATEGY = ParetoMultiDeltaDecisionStrategy()
