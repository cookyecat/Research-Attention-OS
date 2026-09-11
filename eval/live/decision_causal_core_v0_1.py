from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Hashable

from app.services.cognitive_impact import CognitiveImpactAssessment, legal_public_effects, normalize_frozen_transition
from app.services.scheduler import RuntimeView, route

VERSION = "decision-causal-core-v0.1"


def default_relation_key(effect) -> tuple[str, str | None]:
    op = effect.operation.value if hasattr(effect.operation, "value") else str(effect.operation)
    target = str(effect.target_kernel_node_id) if effect.target_kernel_node_id is not None else None
    return (str(op), target)


def disposition_key(plan) -> str:
    value = plan.disposition
    return value.value if hasattr(value, "value") else str(value)


@dataclass(frozen=True)
class RelationCausalResult:
    relation: Hashable
    multiplicity: int
    baseline_decision: Hashable
    without_decision: Hashable
    alone_decision: Hashable
    necessary: bool
    sufficient: bool

    @property
    def classification(self) -> str:
        if self.necessary and self.sufficient:
            return "SINGULAR_LOAD_BEARING"
        if (not self.necessary) and self.sufficient:
            return "REDUNDANT_LOAD_BEARING"
        if self.necessary and (not self.sufficient):
            return "INTERACTION_DEPENDENT"
        return "PERIPHERAL"

    def as_dict(self) -> dict:
        return {
            "relation": self.relation,
            "multiplicity": self.multiplicity,
            "baseline_decision": self.baseline_decision,
            "without_decision": self.without_decision,
            "alone_decision": self.alone_decision,
            "necessary": self.necessary,
            "sufficient": self.sufficient,
            "classification": self.classification,
        }


@dataclass(frozen=True)
class DecisionCausalCoreReport:
    baseline_decision: Hashable
    relations: tuple[RelationCausalResult, ...]

    @property
    def necessary_core(self) -> tuple[Hashable, ...]:
        return tuple(r.relation for r in self.relations if r.necessary)

    @property
    def sufficient_supports(self) -> tuple[Hashable, ...]:
        return tuple(r.relation for r in self.relations if r.sufficient)

    def as_dict(self) -> dict:
        return {
            "version": VERSION,
            "decision_projection": "article-attention-disposition",
            "baseline_decision": self.baseline_decision,
            "necessary_core": list(self.necessary_core),
            "sufficient_supports": list(self.sufficient_supports),
            "relations": [r.as_dict() for r in self.relations],
            "guardrail": "first-order-single-relation-counterfactuals-only; redundant joint cut sets are not enumerated",
        }


def analyze_decision_causal_core(
    *,
    assessment: CognitiveImpactAssessment,
    matches,
    features,
    decision_strategy,
    runtime: RuntimeView | None = None,
    awareness=None,
    relation_key: Callable = default_relation_key,
    decision_key: Callable = disposition_key,
) -> DecisionCausalCoreReport:
    runtime = runtime or RuntimeView()
    normalized = normalize_frozen_transition(assessment, matches).assessment
    selector = getattr(decision_strategy, "legal_effects", None)
    legal = selector(normalized) if callable(selector) else legal_public_effects(normalized)
    relations = sorted({relation_key(effect) for effect in legal}, key=repr)

    def decide(effects) -> Hashable:
        candidate = replace(normalized, effects=list(effects))
        plan = route(
            features, runtime, assessment=candidate, matches=matches,
            awareness=awareness, decision_strategy=decision_strategy,
        )
        return decision_key(plan)

    baseline = decide(legal)
    null_decision = decide([])
    rows = []
    for relation in relations:
        members = [e for e in legal if relation_key(e) == relation]
        without = [e for e in legal if relation_key(e) != relation]
        alone = members
        without_decision = decide(without)
        alone_decision = decide(alone)
        rows.append(RelationCausalResult(
            relation=relation,
            multiplicity=len(members),
            baseline_decision=baseline,
            without_decision=without_decision,
            alone_decision=alone_decision,
            necessary=without_decision != baseline,
            sufficient=(alone_decision == baseline and baseline != null_decision),
        ))
    return DecisionCausalCoreReport(baseline_decision=baseline, relations=tuple(rows))


def execution_snapshot() -> dict:
    return {
        "version": VERSION,
        "ablation_unit": "decision-relation(operation,target)",
        "decision_projection": "article-attention-disposition",
        "counterfactuals": ["without-relation", "relation-alone"],
        "scope": "first-order-only",
    }
