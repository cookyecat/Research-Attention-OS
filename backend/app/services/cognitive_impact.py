"""Potential cognitive effects for one AnalysisRun / Kernel snapshot.

CognitiveEffect is not a Kernel mutation and not an EvidenceLink.
It answers: what could absorbing this information mean for current control state?
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.enums import CognitiveEffectKind
from app.services.evidence_gate import evidence_conflict_flags
from app.services.extraction import ExtractionResult
from app.services.matching import KernelMatch

TARGET_IMPORTANCE = {
    "GOAL": 0.9,
    "DECISION": 0.85,
    "BOTTLENECK": 0.8,
    "BELIEF": 0.75,
    "MODEL": 0.75,
    "QUESTION": 0.7,
    "PROJECT": 0.65,
    "HYPOTHESIS": 0.55,
    "EXPERIMENT": 0.5,
}

# Single promotional / media source without first-hand evidence cannot justify strong revision.
SINGLE_SOURCE_EPISTEMIC_CAP = 0.35
MARKETING_EPISTEMIC_CAP = 0.25


@dataclass
class CognitiveEffect:
    target_kernel_node_id: UUID | None
    effect: CognitiveEffectKind
    change_magnitude: float
    epistemic_strength: float
    target_importance: float
    reason: str
    exploration_candidate: bool = False

    def as_dict(self) -> dict:
        kind = self.effect.value if hasattr(self.effect, "value") else str(self.effect)
        return {
            "target_kernel_node_id": str(self.target_kernel_node_id) if self.target_kernel_node_id else None,
            "effect": kind,
            "change_magnitude": round(float(self.change_magnitude), 3),
            "epistemic_strength": round(float(self.epistemic_strength), 3),
            "target_importance": round(float(self.target_importance), 3),
            "reason": self.reason,
            "exploration_candidate": bool(self.exploration_candidate),
        }


@dataclass
class CognitiveImpactAssessment:
    effects: list[CognitiveEffect] = field(default_factory=list)
    attention_cost: float = 2.0
    exploration_candidate: bool = False
    features: object | None = None

    def as_dict(self) -> dict:
        return {
            "effects": [e.as_dict() for e in self.effects],
            "attention_cost": round(float(self.attention_cost), 3),
            "exploration_candidate": bool(self.exploration_candidate),
        }

    def material_effects(self) -> list[CognitiveEffect]:
        return [e for e in self.effects if _kind(e.effect) != CognitiveEffectKind.NO_MATERIAL_CHANGE]


def _kind(value) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def epistemic_cap(
    extraction: ExtractionResult,
    *,
    independent_source_count: int = 1,
) -> float:
    cap = 1.0
    if independent_source_count <= 1 and not extraction.observations:
        cap = min(cap, SINGLE_SOURCE_EPISTEMIC_CAP)
    if extraction.marketing_heavy:
        cap = min(cap, MARKETING_EPISTEMIC_CAP)
    if extraction.evidence_maturity < 0.45:
        cap = min(cap, 0.45)
    return cap


def ground_effects(
    effects: list[CognitiveEffect],
    matches: list[KernelMatch],
    extraction: ExtractionResult,
    *,
    independent_source_count: int = 1,
) -> list[CognitiveEffect]:
    """Deterministic caps. LLM remains the effect judge."""
    allowed = {m.node_id for m in matches}
    cap = epistemic_cap(extraction, independent_source_count=independent_source_count)
    grounded: list[CognitiveEffect] = []
    for effect in effects:
        target = effect.target_kernel_node_id
        if target is not None and target not in allowed:
            if _kind(effect.effect) == CognitiveEffectKind.OPEN_NEW:
                target = None
            else:
                continue
        epi = min(float(effect.epistemic_strength), cap)
        change = max(0.0, min(1.0, float(effect.change_magnitude)))
        importance = max(0.0, min(1.0, float(effect.target_importance)))
        kind = CognitiveEffectKind(_kind(effect.effect))
        explore = bool(effect.exploration_candidate) or kind == CognitiveEffectKind.OPEN_NEW
        if kind == CognitiveEffectKind.OPEN_NEW:
            target = target if target in allowed else None
            explore = True
        grounded.append(
            CognitiveEffect(
                target_kernel_node_id=target,
                effect=kind,
                change_magnitude=change,
                epistemic_strength=epi,
                target_importance=importance,
                reason=effect.reason,
                exploration_candidate=explore,
            )
        )
    if not grounded:
        grounded.append(
            CognitiveEffect(
                target_kernel_node_id=None,
                effect=CognitiveEffectKind.NO_MATERIAL_CHANGE,
                change_magnitude=0.1,
                epistemic_strength=min(0.2, cap),
                target_importance=0.2,
                reason="No grounded cognitive effect on the current Kernel snapshot.",
            )
        )
    return grounded


def features_from_impact(
    assessment_or_effects,
    matches: list[KernelMatch],
    extraction: ExtractionResult,
    *,
    attention_cost: float = 2.0,
    exploration_candidate: bool = False,
    is_duplicate: bool = False,
    independent_source_count: int = 1,
    secondary_report_count: int = 0,
    threatens_active_work: bool = False,
    marketing_heavy: bool = False,
    high_quality_technical: bool = False,
    foundational_paper: bool = False,
    evidence_maturity: float | None = None,
    novelty: float | None = None,
    disagreement: float = 0.0,
    temporal_value: float = 0.4,
):
    """Derive compatibility SchedulerFeatures. Localization comes from matches; value from effects."""
    from app.services.scheduler import SchedulerFeatures, ground_features_to_matches

    if isinstance(assessment_or_effects, CognitiveImpactAssessment):
        effects = assessment_or_effects.effects
        attention_cost = assessment_or_effects.attention_cost
        exploration_candidate = assessment_or_effects.exploration_candidate or exploration_candidate
    else:
        effects = list(assessment_or_effects)

    links_present, conflict = evidence_conflict_flags(
        extraction, independent_source_count=independent_source_count
    )
    material = [e for e in effects if _kind(e.effect) != CognitiveEffectKind.NO_MATERIAL_CHANGE]
    max_change = max((e.change_magnitude for e in material), default=0.0)
    if not material:
        max_change = max((e.change_magnitude for e in effects), default=0.0)
    max_epi = max((e.epistemic_strength for e in (material or effects)), default=0.2)
    max_importance = max((e.target_importance for e in (material or effects)), default=0.0)
    challenge = max(
        (e.change_magnitude for e in effects if _kind(e.effect) == CognitiveEffectKind.CHALLENGE),
        default=0.0,
    )
    disagreement = max(disagreement, challenge, 0.8 if conflict else 0.0)

    topic = max(
        (
            m.score
            for m in matches
            if not m.structural and (m.relevance_type or "TOPIC") not in {"STRUCTURAL", "DECISION"}
        ),
        default=0.0,
    )
    structural = max((m.score for m in matches if m.structural or m.relevance_type == "STRUCTURAL"), default=0.0)
    decision = max(
        (m.score for m in matches if m.node_type == "DECISION" or m.relevance_type == "DECISION"),
        default=0.0,
    )
    bottleneck = max(
        (m.score for m in matches if m.node_type == "BOTTLENECK" or m.relevance_type == "BOTTLENECK"),
        default=0.0,
    )

    kernel_delta = max_change
    if disagreement >= 0.7:
        kernel_delta = max(kernel_delta, 0.75)
    if structural >= 0.65:
        kernel_delta = max(kernel_delta, min(max_change, 1.0) if max_change else 0.7)
        if max_change:
            kernel_delta = max(kernel_delta, max_change)

    marketing = marketing_heavy or extraction.marketing_heavy
    maturity = extraction.evidence_maturity if evidence_maturity is None else min(evidence_maturity, extraction.evidence_maturity or evidence_maturity)
    if extraction.evidence_stage_skipped:
        maturity = min(maturity, extraction.evidence_maturity, 0.4)

    novelty_value = 0.15 if is_duplicate else (0.6 if novelty is None else novelty)
    actionability = 0.7 if decision >= 0.6 or bottleneck >= 0.6 or max_importance >= 0.8 else 0.35
    explore = exploration_candidate or any(e.exploration_candidate for e in effects) or any(
        _kind(e.effect) == CognitiveEffectKind.OPEN_NEW for e in effects
    )

    features = SchedulerFeatures(
        topic_relevance=round(topic, 3),
        structural_relevance=round(structural, 3),
        decision_relevance=round(decision, 3),
        novelty=round(novelty_value, 3),
        credibility=round(min(max(max_epi, 0.2 if marketing else 0.35), 1.0), 3),
        kernel_delta=round(kernel_delta, 3),
        bottleneck_alignment=round(bottleneck, 3),
        disagreement=round(disagreement, 3),
        actionability=round(actionability, 3),
        temporal_value=round(temporal_value, 3),
        cognitive_cost=float(attention_cost),
        is_duplicate=is_duplicate,
        evidence_maturity=maturity,
        threatens_active_work=bool(threatens_active_work),
        marketing_heavy=marketing,
        sources_conflict=conflict,
        evidence_links_present=links_present,
        evidence_stage_skipped=bool(extraction.evidence_stage_skipped),
        evidence_skip_reason=extraction.evidence_skip_reason,
        independent_source_count=independent_source_count,
        secondary_report_count=secondary_report_count,
        high_quality_technical=high_quality_technical,
        foundational_paper=foundational_paper,
        exploration_candidate=explore,
        change_magnitude=round(max_change, 3),
        epistemic_strength=round(max_epi, 3),
        target_importance=round(max_importance, 3),
        attention_cost=float(attention_cost),
    )
    return ground_features_to_matches(features, matches)


def assess_impact_from_rules(
    text: str,
    extraction: ExtractionResult,
    matches: list[KernelMatch],
    *,
    is_duplicate: bool = False,
    independent_source_count: int = 1,
    secondary_report_count: int = 0,
    threatens_active_work: bool | None = None,
) -> CognitiveImpactAssessment:
    """Deterministic impact assessment used by the rule provider and as fallback."""
    from app.services.matching import EQUITY_STRUCTURE, tokenize
    from app.services.scheduler import _compatibility_features

    probe = _compatibility_features(
        text,
        extraction,
        matches,
        is_duplicate=is_duplicate,
        independent_source_count=independent_source_count,
        secondary_report_count=secondary_report_count,
        threatens_active_work=threatens_active_work,
    )
    cap = epistemic_cap(extraction, independent_source_count=independent_source_count)
    low = text.lower()
    tokens = tokenize(text)
    effects: list[CognitiveEffect] = []
    hype_only = probe.marketing_heavy and not extraction.technical_claims

    if hype_only or (probe.marketing_heavy and not matches):
        effects.append(
            CognitiveEffect(
                target_kernel_node_id=None,
                effect=CognitiveEffectKind.NO_MATERIAL_CHANGE,
                change_magnitude=0.1,
                epistemic_strength=min(0.15, cap),
                target_importance=0.15,
                reason="Promotional source with no material Kernel effect.",
            )
        )
    else:
        for match in matches:
            importance = TARGET_IMPORTANCE.get(match.node_type, 0.5)
            change = match.score
            epi = min(probe.credibility, cap)
            if "minor" in low and "version" in low:
                kind = CognitiveEffectKind.NO_MATERIAL_CHANGE
                change = min(change, 0.15)
            elif match.node_type == "BELIEF" and probe.disagreement >= 0.55:
                kind = CognitiveEffectKind.CHALLENGE
                change = max(change, 0.7)
            elif match.node_type == "DECISION" or match.structural or match.relevance_type == "STRUCTURAL":
                kind = CognitiveEffectKind.REFINE
            elif match.node_type in {"MODEL", "QUESTION", "BOTTLENECK"}:
                kind = CognitiveEffectKind.REFINE if extraction.technical_claims or probe.disagreement >= 0.4 else CognitiveEffectKind.REINFORCE
            elif match.node_type == "PROJECT" and extraction.technical_claims:
                kind = CognitiveEffectKind.REFINE
                change = max(change, 0.65)
            else:
                kind = CognitiveEffectKind.REINFORCE
            if probe.marketing_heavy:
                epi = min(epi, MARKETING_EPISTEMIC_CAP)
            effects.append(
                CognitiveEffect(
                    target_kernel_node_id=match.node_id,
                    effect=kind,
                    change_magnitude=change,
                    epistemic_strength=epi,
                    target_importance=importance,
                    reason=match.reason or f"{kind} on {match.title or match.node_type}",
                )
            )
        if not matches:
            from app.services.extraction import PROMOTIONAL_CUES, _contains_any

            equity_only = bool(EQUITY_STRUCTURE & tokens) and not ({"robot", "embodied", "motor", "agent"} & tokens)
            promo = probe.marketing_heavy or bool(extraction.promotional_framing) or _contains_any(text, PROMOTIONAL_CUES)
            paperish = "paper" in low or "arxiv" in low or "foundational" in low
            technical = bool(extraction.technical_claims) or paperish
            if technical and not promo and not equity_only:
                effects.append(
                    CognitiveEffect(
                        target_kernel_node_id=None,
                        effect=CognitiveEffectKind.OPEN_NEW,
                        change_magnitude=0.55,
                        epistemic_strength=min(0.3, cap),
                        target_importance=0.55,
                        reason="No current Kernel target; possible new question or model candidate.",
                        exploration_candidate=True,
                    )
                )
            else:
                effects.append(
                    CognitiveEffect(
                        target_kernel_node_id=None,
                        effect=CognitiveEffectKind.NO_MATERIAL_CHANGE,
                        change_magnitude=0.12,
                        epistemic_strength=min(0.2, cap),
                        target_importance=0.2,
                        reason="No Kernel localization and no exploration signal.",
                    )
                )

    if probe.disagreement >= 0.55 or probe.sources_conflict:
        if not any(_kind(e.effect) == CognitiveEffectKind.CHALLENGE for e in effects):
            belief = next((m for m in matches if m.node_type == "BELIEF"), None)
            effects = [e for e in effects if _kind(e.effect) != CognitiveEffectKind.NO_MATERIAL_CHANGE]
            effects.append(
                CognitiveEffect(
                    target_kernel_node_id=belief.node_id if belief else None,
                    effect=CognitiveEffectKind.CHALLENGE,
                    change_magnitude=max(0.75, probe.kernel_delta),
                    epistemic_strength=min(0.45, cap),
                    target_importance=0.75 if belief else 0.5,
                    reason="Attributed claims conflict with observations or an active Belief.",
                )
            )

    effects = ground_effects(effects, matches, extraction, independent_source_count=independent_source_count)
    explore = any(e.exploration_candidate for e in effects)
    attention_cost = probe.cognitive_cost
    features = features_from_impact(
        effects,
        matches,
        extraction,
        attention_cost=attention_cost,
        exploration_candidate=explore,
        is_duplicate=is_duplicate,
        independent_source_count=independent_source_count,
        secondary_report_count=secondary_report_count,
        threatens_active_work=probe.threatens_active_work,
        marketing_heavy=probe.marketing_heavy,
        high_quality_technical=probe.high_quality_technical,
        foundational_paper=probe.foundational_paper,
        evidence_maturity=probe.evidence_maturity,
        novelty=probe.novelty,
        disagreement=probe.disagreement,
        temporal_value=probe.temporal_value,
    )
    # Compatibility: keep localization scores from the existing matcher-derived probe
    # (topic/structural/decision/bottleneck) so A–O routing stays stable. Value
    # (kernel_delta / change_magnitude / epistemic_strength) comes from effects.
    features.topic_relevance = probe.topic_relevance
    features.structural_relevance = probe.structural_relevance
    features.decision_relevance = probe.decision_relevance
    features.bottleneck_alignment = probe.bottleneck_alignment
    features.novelty = probe.novelty
    features.actionability = probe.actionability
    features.temporal_value = probe.temporal_value
    features.high_quality_technical = probe.high_quality_technical
    features.foundational_paper = probe.foundational_paper
    features.threatens_active_work = probe.threatens_active_work
    features.marketing_heavy = probe.marketing_heavy
    features.disagreement = max(features.disagreement, probe.disagreement)
    features.credibility = probe.credibility
    material = [e for e in effects if _kind(e.effect) != CognitiveEffectKind.NO_MATERIAL_CHANGE]
    max_change = max((e.change_magnitude for e in material), default=0.0)
    if not material:
        features.kernel_delta = min(probe.kernel_delta, max((e.change_magnitude for e in effects), default=0.1))
    else:
        features.kernel_delta = max(probe.kernel_delta, max_change)
    features.change_magnitude = round(max_change if material else max((e.change_magnitude for e in effects), default=0.0), 3)
    features.epistemic_strength = round(max((e.epistemic_strength for e in (material or effects)), default=0.2), 3)
    features.target_importance = round(max((e.target_importance for e in (material or effects)), default=0.0), 3)
    features.attention_cost = float(attention_cost)
    features.cognitive_cost = float(attention_cost)
    features.exploration_candidate = explore
    from app.services.scheduler import ground_features_to_matches

    features = ground_features_to_matches(features, matches)
    return CognitiveImpactAssessment(
        effects=effects,
        attention_cost=attention_cost,
        exploration_candidate=explore,
        features=features,
    )
