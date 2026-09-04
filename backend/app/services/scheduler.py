from __future__ import annotations

from dataclasses import dataclass, field

from app.enums import CandidateType, Disposition, ExpectedOutput, Urgency
from app.services.evidence_gate import evidence_conflict_flags
from app.services.extraction import ExtractionResult
from app.services.matching import KernelMatch

SCHEDULER_VERSION = "raos-scheduler-0.5.0"
# Compatibility projection cap for debug/Live Eval. Routing no longer branches on these scores.
UNSUPPORTED_RELEVANCE_CAP = 0.34


@dataclass
class SchedulerFeatures:
    """Compatibility/debug projection of CognitiveImpactAssessment + Kernel Match.

    Attention Policy consumes CognitiveImpactAssessment directly. These fields remain
    for Live Eval, reschedule of older runs, and score_debug.
    """

    topic_relevance: float
    structural_relevance: float
    decision_relevance: float
    novelty: float
    credibility: float
    kernel_delta: float
    bottleneck_alignment: float
    disagreement: float
    actionability: float
    temporal_value: float
    cognitive_cost: float
    is_duplicate: bool = False
    evidence_maturity: float = 0.4
    threatens_active_work: bool = False
    marketing_heavy: bool = False
    sources_conflict: bool = False
    evidence_links_present: bool = False
    evidence_stage_skipped: bool = False
    evidence_skip_reason: str | None = None
    independent_source_count: int = 1
    secondary_report_count: int = 0
    high_quality_technical: bool = False
    foundational_paper: bool = False
    exploration_candidate: bool = False
    change_magnitude: float = 0.0
    epistemic_strength: float = 0.0
    target_importance: float = 0.0
    attention_cost: float = 0.0

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class RuntimeView:
    current_task: str | None = None
    session_topic: str | None = None
    available_attention_minutes: int | None = None
    interruptibility: str | None = "MEDIUM"
    cognitive_capacity: str | None = "NORMAL"
    deadline_minutes: float | None = None


@dataclass
class PlanDraft:
    disposition: Disposition
    urgency: Urgency = Urgency.NORMAL
    cognitive_budget_minutes: int | None = None
    expected_output: ExpectedOutput = ExpectedOutput.NONE
    reason: str = ""
    watch_after_processing: bool = False
    watch_triggers: list[str] = field(default_factory=list)


def _match_supported(
    matches: list[KernelMatch],
    *,
    node_types: tuple[str, ...] = (),
    relevance_types: tuple[str, ...] = (),
    structural: bool = False,
) -> bool:
    wanted = {r.upper() for r in relevance_types}
    for match in matches:
        if match.node_type in node_types:
            return True
        rel = (match.relevance_type or "").upper()
        if rel in wanted:
            return True
        if structural and match.structural:
            return True
    return False


def ground_features_to_matches(features: SchedulerFeatures, matches: list[KernelMatch]) -> SchedulerFeatures:
    """Cap unsupported localization scores on the compatibility projection.

    Routing uses CognitiveEffect target semantics, not these scores. The cap remains
    so debug/Live Eval cannot display a free-floating HIGH decision_relevance.
    """
    if not _match_supported(matches, node_types=("DECISION",), relevance_types=("DECISION",)):
        features.decision_relevance = min(features.decision_relevance, UNSUPPORTED_RELEVANCE_CAP)
    if not _match_supported(matches, relevance_types=("STRUCTURAL",), structural=True):
        features.structural_relevance = min(features.structural_relevance, UNSUPPORTED_RELEVANCE_CAP)
    if not _match_supported(matches, node_types=("BOTTLENECK",), relevance_types=("BOTTLENECK",)):
        features.bottleneck_alignment = min(features.bottleneck_alignment, UNSUPPORTED_RELEVANCE_CAP)
    return features


def _compatibility_features(
    text: str,
    extraction: ExtractionResult,
    matches: list[KernelMatch],
    *,
    is_duplicate: bool = False,
    independent_source_count: int = 1,
    secondary_report_count: int = 0,
    threatens_active_work: bool | None = None,
) -> SchedulerFeatures:
    match_score = max((m.score for m in matches), default=0.0)
    structural = max((m.score for m in matches if m.structural), default=0.0)
    decision = max((m.score for m in matches if m.node_type == "DECISION"), default=0.0)
    bottleneck = max((m.score for m in matches if m.node_type == "BOTTLENECK"), default=0.0)

    marketing = extraction.marketing_heavy
    credibility = 0.35 if marketing else 0.65
    if extraction.observations:
        credibility = max(credibility, 0.7)
    if extraction.technical_claims:
        credibility = max(credibility, 0.72)

    links_present, conflict = evidence_conflict_flags(
        extraction, independent_source_count=independent_source_count
    )
    disagreement = 0.0
    if conflict:
        disagreement = 0.8
    low = text.lower()

    kernel_delta = match_score
    topic = match_score
    if disagreement >= 0.7:
        kernel_delta = max(kernel_delta, 0.75)
    if structural >= 0.65:
        kernel_delta = max(kernel_delta, 0.7)
    if marketing and not extraction.technical_claims:
        kernel_delta = min(kernel_delta, 0.2)
        topic = min(topic, 0.22)
        credibility = min(credibility, 0.35)

    if "minor" in low and "version" in low:
        novelty = 0.15
        kernel_delta = min(kernel_delta, 0.15)
        topic = min(topic, 0.22)
    if structural >= 0.65 and match_score < 0.4:
        topic = min(topic, 0.25)

    novelty = 0.6 if not is_duplicate else 0.15
    if "minor" in low and "version" in low:
        novelty = 0.15
        kernel_delta = min(kernel_delta, 0.15)
        topic = min(topic, 0.25)

    actionability = 0.7 if decision >= 0.6 or bottleneck >= 0.6 else 0.35
    temporal = 0.7 if extraction.future_plans else 0.4
    cost = 8.0 if match_score >= 0.6 else 2.0

    threatened = threatens_active_work
    if threatened is None:
        threatened = any(
            p in low
            for p in (
                "invalidates novelty",
                "overlaps the active submission",
                "overlaps user's active submission",
                "nearly identical to the active paper",
            )
        )

    high_quality = (
        not marketing
        and (bool(extraction.technical_claims) or "paper" in low or "arxiv" in low)
        and credibility >= 0.65
    )
    foundational = any(p in low for p in ("foundational", "survey of", "textbook", "principles of"))

    features = SchedulerFeatures(
        topic_relevance=round(topic, 3),
        structural_relevance=round(structural, 3),
        decision_relevance=round(decision, 3),
        novelty=round(novelty, 3),
        credibility=round(min(credibility, 1.0), 3),
        kernel_delta=round(kernel_delta, 3),
        bottleneck_alignment=round(bottleneck, 3),
        disagreement=round(disagreement, 3),
        actionability=round(actionability, 3),
        temporal_value=round(temporal, 3),
        cognitive_cost=cost,
        is_duplicate=is_duplicate,
        evidence_maturity=extraction.evidence_maturity,
        threatens_active_work=bool(threatened),
        marketing_heavy=marketing,
        sources_conflict=conflict,
        evidence_links_present=links_present,
        evidence_stage_skipped=bool(extraction.evidence_stage_skipped),
        evidence_skip_reason=extraction.evidence_skip_reason,
        independent_source_count=independent_source_count,
        secondary_report_count=secondary_report_count,
        high_quality_technical=high_quality,
        foundational_paper=foundational,
    )
    return ground_features_to_matches(features, matches)


def estimate_features(
    text: str,
    extraction: ExtractionResult,
    matches: list[KernelMatch],
    *,
    is_duplicate: bool = False,
    independent_source_count: int = 1,
    secondary_report_count: int = 0,
    threatens_active_work: bool | None = None,
) -> SchedulerFeatures:
    from app.services.cognitive_impact import assess_impact_from_rules

    return assess_impact_from_rules(
        text,
        extraction,
        matches,
        is_duplicate=is_duplicate,
        independent_source_count=independent_source_count,
        secondary_report_count=secondary_report_count,
        threatens_active_work=threatens_active_work,
    ).features


def _budget(disposition: Disposition) -> int:
    return {
        Disposition.DROP: 0,
        Disposition.AWARE: 1,
        Disposition.WATCH: 2,
        Disposition.ENGAGE: 15,
    }[disposition]


def _projection_assessment(features: SchedulerFeatures):
    """Compatibility placeholder when a frozen CognitiveImpactAssessment is missing.

    Legacy SchedulerFeatures are not a Cognitive Transition source of truth.
    Missing frozen judgment → empty assessment (NONE), never inferred OPEN_NEW /
    REINFORCE / CHALLENGE from exploration, disagreement, conflict, or kernel_delta.
    """
    from app.services.cognitive_impact import CognitiveImpactAssessment

    cost = features.attention_cost or features.cognitive_cost
    return CognitiveImpactAssessment(
        effects=[],
        attention_cost=cost,
        exploration_candidate=False,
        features=features,
    )


def matches_from_debug(raw) -> list[KernelMatch]:
    if not raw:
        return []
    out: list[KernelMatch] = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("node_id"):
            continue
        from uuid import UUID

        try:
            nid = UUID(str(item["node_id"]))
        except (TypeError, ValueError):
            continue
        out.append(
            KernelMatch(
                node_id=nid,
                node_type=str(item.get("node_type") or ""),
                title=item.get("title"),
                score=float(item.get("score") or 0.0),
                reason=str(item.get("reason") or ""),
                structural=bool(item.get("structural")),
                relevance_type=str(item.get("relevance_type") or "TOPIC"),
            )
        )
    return out


def route(
    features: SchedulerFeatures,
    runtime: RuntimeView | None = None,
    assessment=None,
    matches: list[KernelMatch] | None = None,
) -> PlanDraft:
    """Attention Policy. Canonical Δ is the cognitive authority.

    Runtime may raise urgency or defer existing ENGAGE. It cannot invent
    AWARE/WATCH/ENGAGE from Δ=NONE. exploration_candidate is not an authority.
    Missing frozen CognitiveImpactAssessment is fail-closed to NONE.
    """
    from app.services.cognitive_impact import (
        normalize_frozen_transition,
        select_primary_effect,
    )

    runtime = runtime or RuntimeView()
    if assessment is None:
        assessment = _projection_assessment(features)
    matches = matches or []
    assessment = normalize_frozen_transition(assessment, matches).assessment
    primary = select_primary_effect(assessment)

    # --- Source identity (not cognitive value). Duplicate policy is unchanged. ---
    if features.is_duplicate:
        return PlanDraft(
            disposition=Disposition.DROP,
            urgency=Urgency.BACKGROUND,
            expected_output=ExpectedOutput.NONE,
            reason="Duplicate or secondary reprint of an already covered event; independent confirmation count does not increase.",
            cognitive_budget_minutes=_budget(Disposition.DROP),
        )

    draft = _cognitive_disposition(features, primary, matches)
    return _apply_runtime_overlays(draft, features, runtime, primary=primary, matches=matches)


def _cognitive_disposition(features: SchedulerFeatures, primary, matches: list[KernelMatch]) -> PlanDraft:
    """Disposition from canonical Δ only. Runtime and source-quality flags cannot invent value."""
    from app.enums import CognitiveEffectKind
    from app.services.cognitive_impact import (
        MATERIAL_CHANGE_MIN,
        MEANINGFUL_CHANGE,
        effect_target_match,
    )

    if primary is None:
        return PlanDraft(
            disposition=Disposition.DROP,
            expected_output=ExpectedOutput.NONE,
            reason="No canonical cognitive effect. Δ=NONE is DROP; topic/quality/threat cannot invent attention.",
            cognitive_budget_minutes=_budget(Disposition.DROP),
        )

    op = primary.operation
    if not isinstance(op, CognitiveEffectKind):
        op = CognitiveEffectKind(str(getattr(op, "value", op)))
    change = float(primary.change_magnitude)
    epi = float(primary.epistemic_strength)
    importance = float(primary.target_importance)
    match = effect_target_match(primary, matches)
    targeted = primary.target_kernel_node_id is not None and op in {
        CognitiveEffectKind.REINFORCE,
        CognitiveEffectKind.CHALLENGE,
    }
    challenge = op == CognitiveEffectKind.CHALLENGE and targeted
    open_new = op == CognitiveEffectKind.OPEN_NEW
    node_type = str(getattr(match, "node_type", "") or "").upper()
    rel = str(getattr(match, "relevance_type", "") or "").upper()
    structural = bool(match is not None and (getattr(match, "structural", False) or rel == "STRUCTURAL"))
    synth = node_type in {"MODEL", "BELIEF", "QUESTION", "BOTTLENECK", "DECISION", "HYPOTHESIS"}

    if targeted and node_type == "DECISION":
        return PlanDraft(
            disposition=Disposition.ENGAGE,
            urgency=Urgency.NORMAL,
            expected_output=ExpectedOutput.DECISION_REVIEW,
            reason="Material cognitive effect on an active Decision; do not DROP solely because the source topic is not AI.",
            cognitive_budget_minutes=_budget(Disposition.ENGAGE),
        )

    meaningful = change >= MEANINGFUL_CHANGE
    important = importance >= 0.55 or synth or challenge
    if targeted and meaningful and important:
        reason_parts: list[str] = [
            "Material cognitive effect with meaningful change magnitude on an important Kernel target."
        ]
        low_epi = epi < 0.45
        if challenge or features.sources_conflict:
            reason_parts.append(
                "CHALLENGE / conflicting evidence raises verification value; disagreement is not low relevance."
            )
        elif low_epi and not features.foundational_paper:
            reason_parts.append(
                "Change magnitude is meaningful but epistemic strength is low; absorb carefully before belief revision."
            )
        elif features.evidence_maturity < 0.5 and not features.foundational_paper:
            reason_parts.append("Evidence maturity is low; attributed claims need care before belief update.")
        if features.foundational_paper or (
            features.high_quality_technical and not challenge and not low_epi and features.disagreement < 0.4
        ):
            reason_parts.append("Foundational / high-quality technical treatment of a mechanism.")
        if synth or challenge:
            reason_parts.append("Integrate against an existing Model, Belief, Question, Bottleneck, or Decision.")
        expected = ExpectedOutput.KERNEL_PATCH if change >= MEANINGFUL_CHANGE else ExpectedOutput.SUMMARY
        if features.evidence_maturity < 0.45 and expected != ExpectedOutput.KERNEL_PATCH:
            expected = ExpectedOutput.WATCH
        urgency = Urgency.PRIORITY if node_type == "BOTTLENECK" and change >= MEANINGFUL_CHANGE else Urgency.NORMAL
        return PlanDraft(
            disposition=Disposition.ENGAGE,
            urgency=urgency,
            expected_output=expected,
            reason=" ".join(reason_parts),
            watch_after_processing=features.evidence_maturity < 0.5,
            watch_triggers=_default_watch_triggers(features, primary=primary, matches=matches),
            cognitive_budget_minutes=_budget(Disposition.ENGAGE),
        )

    if targeted and structural and change >= 0.4:
        expected = ExpectedOutput.DECISION_REVIEW if node_type == "DECISION" else ExpectedOutput.KERNEL_PATCH
        return PlanDraft(
            disposition=Disposition.ENGAGE,
            expected_output=expected,
            reason="Meaningful CognitiveEffect on a STRUCTURAL Kernel match; low topic similarity does not DROP.",
            cognitive_budget_minutes=_budget(Disposition.ENGAGE),
        )

    if targeted and change >= MATERIAL_CHANGE_MIN:
        return PlanDraft(
            disposition=Disposition.WATCH,
            expected_output=ExpectedOutput.WATCH,
            reason="Potentially important cognitive effect with insufficient current evidence; transfer future attention to the system.",
            watch_after_processing=True,
            watch_triggers=_default_watch_triggers(features, primary=primary, matches=matches),
            cognitive_budget_minutes=_budget(Disposition.WATCH),
        )

    if open_new:
        low_epi = epi < 0.45
        conflict = features.sources_conflict or features.disagreement >= 0.55
        if change >= 0.65 and importance >= 0.7 and (not low_epi or conflict):
            return PlanDraft(
                disposition=Disposition.ENGAGE,
                expected_output=ExpectedOutput.SUMMARY,
                reason=(
                    "High-value OPEN_NEW direction; ENGAGE to absorb a new cognitive branch."
                    if not conflict
                    else "Claims and observations conflict on a new branch; verification is the cognitive work."
                ),
                cognitive_budget_minutes=_budget(Disposition.ENGAGE),
            )
        if change >= MEANINGFUL_CHANGE:
            reason = "Material OPEN_NEW branch is worth keeping in view, but not immediately diving into."
            if low_epi or features.marketing_heavy:
                reason += " Source framing / low epistemic strength caps confidence, not cognitive change."
            return PlanDraft(
                disposition=Disposition.WATCH,
                expected_output=ExpectedOutput.WATCH,
                reason=reason,
                watch_after_processing=True,
                watch_triggers=_default_watch_triggers(features, primary=primary, matches=matches),
                cognitive_budget_minutes=_budget(Disposition.WATCH),
            )
        return PlanDraft(
            disposition=Disposition.AWARE,
            expected_output=ExpectedOutput.SUMMARY,
            reason="Canonical OPEN_NEW: missing Kernel localization is not automatic DROP.",
            cognitive_budget_minutes=_budget(Disposition.AWARE),
        )

    return PlanDraft(
        disposition=Disposition.AWARE,
        expected_output=ExpectedOutput.SUMMARY,
        reason="Default AWARE: no ENGAGE-grade cognitive effect.",
        cognitive_budget_minutes=_budget(Disposition.AWARE),
    )


def _apply_runtime_overlays(
    draft: PlanDraft,
    features: SchedulerFeatures,
    runtime: RuntimeView,
    *,
    primary,
    matches: list[KernelMatch],
) -> PlanDraft:
    """Runtime may raise urgency or defer existing attention. It cannot invent Δ."""
    if draft.disposition == Disposition.DROP:
        return draft

    if features.threatens_active_work:
        draft.urgency = Urgency.PREEMPT
        if "preempt" not in draft.reason.lower() and "interrupt" not in draft.reason.lower():
            draft.reason = (
                f"{draft.reason} PREEMPT is justified: interrupting current work is cheaper "
                "than discovering a novelty collision after submission."
            ).strip()

    tight_deadline = runtime.deadline_minutes is not None and runtime.deadline_minutes <= 120
    low_interrupt = (runtime.interruptibility or "MEDIUM") == "LOW"
    if (
        draft.disposition == Disposition.ENGAGE
        and tight_deadline
        and low_interrupt
        and not features.threatens_active_work
    ):
        draft.disposition = Disposition.WATCH
        draft.urgency = Urgency.BACKGROUND
        draft.expected_output = ExpectedOutput.WATCH
        draft.watch_after_processing = True
        draft.watch_triggers = draft.watch_triggers or _default_watch_triggers(
            features, primary=primary, matches=matches
        )
        draft.cognitive_budget_minutes = _budget(Disposition.WATCH)
        draft.reason = (
            f"{draft.reason} RuntimeContext: camera-ready/deadline is imminent and interruptibility is LOW. "
            "Defer existing ENGAGE to WATCH. Runtime cannot invent attention from Δ=NONE."
        ).strip()
    return draft


def _default_watch_triggers(features: SchedulerFeatures, assessment=None, matches=None, primary=None) -> list[str]:
    from app.services.cognitive_impact import effect_target_match

    triggers = ["PAPER_RELEASE", "CODE_RELEASE", "INDEPENDENT_REPLICATION"]
    match = effect_target_match(primary, matches) if primary is not None else None
    bottleneck = str(getattr(match, "node_type", "") or "").upper() == "BOTTLENECK"
    if bottleneck or features.bottleneck_alignment >= 0.4:
        triggers.extend(["BENCHMARK_UPDATE", "NEW_EVIDENCE"])
    return triggers


def validate_plan(draft: PlanDraft) -> PlanDraft:
    if draft.cognitive_budget_minutes is not None and draft.cognitive_budget_minutes < 0:
        raise ValueError("budget must be >= 0")
    if draft.disposition == Disposition.WATCH and not draft.watch_triggers:
        draft.watch_triggers = ["NEW_EVIDENCE"]
    if draft.urgency == Urgency.PREEMPT and "interrupt" not in draft.reason.lower() and "preempt" not in draft.reason.lower():
        raise ValueError("PREEMPT requires explicit interruption justification")
    return draft
