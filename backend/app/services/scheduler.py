from __future__ import annotations

from dataclasses import dataclass, field

from app.enums import AttentionState, CandidateType, ExpectedOutput, ProcessingMode, Urgency
from app.services.evidence_gate import evidence_conflict_flags
from app.services.extraction import ExtractionResult
from app.services.matching import EQUITY_STRUCTURE, KernelMatch, tokenize

SCHEDULER_VERSION = "raos-scheduler-0.2.0"
# Below Attention Policy HIGH (0.65). Do not change route() thresholds to match this cap.
UNSUPPORTED_RELEVANCE_CAP = 0.34


@dataclass
class SchedulerFeatures:
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
    attention_state: AttentionState
    processing_modes: list[ProcessingMode] = field(default_factory=list)
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
    """Deterministic consistency cap before Attention Policy.

    LLM remains the feature judge. Unsupported HIGH scores cannot fire Decision /
    Structural / Bottleneck branches. route() thresholds are unchanged.
    """
    if not _match_supported(matches, node_types=("DECISION",), relevance_types=("DECISION",)):
        features.decision_relevance = min(features.decision_relevance, UNSUPPORTED_RELEVANCE_CAP)
    if not _match_supported(matches, relevance_types=("STRUCTURAL",), structural=True):
        features.structural_relevance = min(features.structural_relevance, UNSUPPORTED_RELEVANCE_CAP)
    if not _match_supported(matches, node_types=("BOTTLENECK",), relevance_types=("BOTTLENECK",)):
        features.bottleneck_alignment = min(features.bottleneck_alignment, UNSUPPORTED_RELEVANCE_CAP)
    return features


def _level(value: float) -> str:
    if value >= 0.65:
        return "HIGH"
    if value <= 0.35:
        return "LOW"
    return "MEDIUM"


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
    tokens = tokenize(text)
    match_score = max((m.score for m in matches), default=0.0)
    structural = max((m.score for m in matches if m.structural), default=0.0)
    decision = max((m.score for m in matches if m.node_type == "DECISION"), default=0.0)
    bottleneck = max((m.score for m in matches if m.node_type == "BOTTLENECK"), default=0.0)
    belief_match = max((m.score for m in matches if m.node_type == "BELIEF"), default=0.0)

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
    # Conflict with "large unified models may be unsuitable"
    if any(p in low for p in ("end-to-end will eventually replace", "unified model", "one large model")):
        if belief_match >= 0.28 or any(k in low for k in ("embodied", "motor", "humanoid", "control")):
            disagreement = max(disagreement, 0.85)
    if "opposite" in low or "unsuitable" in low and "suitable" in low:
        disagreement = max(disagreement, 0.8)
    if "argues opposite" in low or "contradicts the belief" in low or "large unified models are necessary" in low:
        disagreement = max(disagreement, 0.9)

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

    # Celebrity consumer brand vs robotics kernel: low topic if no AI/robot terms
    if (EQUITY_STRUCTURE & tokens) and not ({"robot", "embodied", "motor", "agent"} & tokens):
        topic = min(topic, 0.2)
        if decision >= 0.5:
            structural = max(structural, 0.85)
            decision = max(decision, 0.85)

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


def _budget(state: AttentionState, modes: list[ProcessingMode]) -> int:
    if state == AttentionState.DROP:
        return 0
    if state == AttentionState.AWARE:
        return 1
    if state == AttentionState.WATCH:
        return 2
    minutes = 0
    for mode in modes:
        minutes += {
            ProcessingMode.SCAN: 2,
            ProcessingMode.LEARN: 12,
            ProcessingMode.VERIFY: 15,
            ProcessingMode.DEEP_DIVE: 40,
            ProcessingMode.SYNTHESIZE: 18,
        }[mode]
    return minutes


def route(features: SchedulerFeatures, runtime: RuntimeView | None = None, assessment=None) -> PlanDraft:
    runtime = runtime or RuntimeView()
    reason_parts: list[str] = []

    if features.is_duplicate:
        return PlanDraft(
            attention_state=AttentionState.DROP,
            urgency=Urgency.BACKGROUND,
            expected_output=ExpectedOutput.NONE,
            reason="Duplicate or secondary reprint of an already covered event; independent confirmation count does not increase.",
            cognitive_budget_minutes=0,
        )

    if features.credibility < 0.4 and features.topic_relevance < 0.35 and features.structural_relevance < 0.5:
        return PlanDraft(
            attention_state=AttentionState.DROP,
            urgency=Urgency.BACKGROUND,
            reason="Low credibility and low Kernel relevance.",
            cognitive_budget_minutes=0,
        )

    if features.marketing_heavy and features.kernel_delta < 0.3 and features.structural_relevance < 0.5:
        return PlanDraft(
            attention_state=AttentionState.DROP,
            urgency=Urgency.BACKGROUND,
            reason="Marketing-heavy article with no primary technical evidence and no Kernel or structural relevance.",
            cognitive_budget_minutes=0,
        )

    # Runtime: imminent deadline + low interruptibility, unless threat to submission
    tight_deadline = runtime.deadline_minutes is not None and runtime.deadline_minutes <= 120
    low_interrupt = (runtime.interruptibility or "MEDIUM") == "LOW"
    if tight_deadline and low_interrupt and not features.threatens_active_work:
        modes: list[ProcessingMode] = []
        return PlanDraft(
            attention_state=AttentionState.WATCH,
            processing_modes=modes,
            urgency=Urgency.BACKGROUND,
            expected_output=ExpectedOutput.WATCH,
            reason=(
                "RuntimeContext: camera-ready/deadline is imminent and interruptibility is LOW. "
                "Importance is not urgency; park as WATCH/BACKGROUND unless the item threatens the current submission."
            ),
            watch_after_processing=True,
            watch_triggers=["NEW_EVIDENCE"],
            cognitive_budget_minutes=1,
        )

    if features.threatens_active_work:
        reason = (
            "This item highly overlaps the active submission and may invalidate novelty. "
            "PREEMPT is justified: interrupting current work is cheaper than discovering a novelty collision after submission."
        )
        modes = [ProcessingMode.VERIFY, ProcessingMode.SYNTHESIZE]
        return PlanDraft(
            attention_state=AttentionState.ENGAGE,
            processing_modes=modes,
            urgency=Urgency.PREEMPT,
            expected_output=ExpectedOutput.KERNEL_PATCH,
            reason=reason,
            cognitive_budget_minutes=_budget(AttentionState.ENGAGE, modes),
        )

    if features.decision_relevance >= 0.65:
        modes = [ProcessingMode.SYNTHESIZE]
        state = AttentionState.ENGAGE
        expected = ExpectedOutput.DECISION_REVIEW
        reason_parts.append(
            f"Topic relevance {_level(features.topic_relevance)}; "
            f"structural relevance {_level(features.structural_relevance)}; "
            f"decision relevance {_level(features.decision_relevance)}."
        )
        reason_parts.append("Active Decision may change; do not DROP solely because the source topic is not AI.")
        return PlanDraft(
            attention_state=state,
            processing_modes=modes,
            urgency=Urgency.NORMAL,
            expected_output=expected,
            reason=" ".join(reason_parts),
            cognitive_budget_minutes=_budget(state, modes),
        )

    if features.bottleneck_alignment >= 0.65 or (
        features.topic_relevance >= 0.55 and features.kernel_delta >= 0.55
    ):
        modes = []
        if features.disagreement >= 0.55 or features.sources_conflict:
            modes.append(ProcessingMode.VERIFY)
            reason_parts.append(
                "High relevance plus disagreement with an active Belief raises verification value; "
                "disagreement is not low relevance."
            )
        elif features.evidence_maturity < 0.5 and not features.foundational_paper:
            modes.append(ProcessingMode.VERIFY)
            reason_parts.append("Evidence maturity is low; VERIFY attributed claims before belief update.")
        if features.novelty >= 0.5 and "VERIFY" in [m.value for m in modes]:
            modes.append(ProcessingMode.SYNTHESIZE)
            reason_parts.append("Sources or observations materially conflict with attributed claims; synthesize against the Kernel.")
        elif features.foundational_paper or (features.high_quality_technical and features.disagreement < 0.4):
            modes.append(ProcessingMode.LEARN)
            reason_parts.append("High relevance introducing or explaining a mechanism; LEARN.")
        else:
            if ProcessingMode.SYNTHESIZE not in modes:
                modes.append(ProcessingMode.SYNTHESIZE)
            if ProcessingMode.VERIFY not in modes and features.high_quality_technical:
                modes.insert(0, ProcessingMode.VERIFY)
        if not modes:
            modes = [ProcessingMode.VERIFY, ProcessingMode.SYNTHESIZE]
        expected = ExpectedOutput.KERNEL_PATCH if features.kernel_delta >= 0.55 else ExpectedOutput.SUMMARY
        if features.evidence_maturity < 0.45:
            expected = ExpectedOutput.WATCH if expected != ExpectedOutput.KERNEL_PATCH else expected
        reason_parts.insert(0, "Candidate matches active Project/Bottleneck/Belief/Model state.")
        urgency = Urgency.PRIORITY if features.bottleneck_alignment >= 0.7 else Urgency.NORMAL
        return PlanDraft(
            attention_state=AttentionState.ENGAGE,
            processing_modes=modes,
            urgency=urgency,
            expected_output=expected,
            reason=" ".join(reason_parts),
            watch_after_processing=features.evidence_maturity < 0.5,
            watch_triggers=_default_watch_triggers(features),
            cognitive_budget_minutes=_budget(AttentionState.ENGAGE, modes),
        )

    if features.structural_relevance >= 0.65 and features.kernel_delta >= 0.4:
        modes = [ProcessingMode.SYNTHESIZE]
        return PlanDraft(
            attention_state=AttentionState.ENGAGE,
            processing_modes=modes,
            expected_output=ExpectedOutput.DECISION_REVIEW,
            reason="Structural relevance is high even if topic relevance is low.",
            cognitive_budget_minutes=_budget(AttentionState.ENGAGE, modes),
        )

    if features.topic_relevance >= 0.4 and features.evidence_maturity < 0.45 and features.kernel_delta >= 0.35:
        return PlanDraft(
            attention_state=AttentionState.WATCH,
            expected_output=ExpectedOutput.WATCH,
            reason="Strategic potential with insufficient current evidence; transfer future attention to the system.",
            watch_after_processing=True,
            watch_triggers=_default_watch_triggers(features),
            cognitive_budget_minutes=2,
        )

    if features.topic_relevance >= 0.25 and features.kernel_delta < 0.35:
        return PlanDraft(
            attention_state=AttentionState.AWARE,
            processing_modes=[ProcessingMode.SCAN],
            expected_output=ExpectedOutput.SUMMARY,
            reason="Relevant enough to know it happened, but no likely Kernel delta. Popularity is not importance; do not ENGAGE because a company is famous.",
            cognitive_budget_minutes=1,
        )

    if features.exploration_candidate and not features.marketing_heavy:
        return PlanDraft(
            attention_state=AttentionState.AWARE,
            processing_modes=[ProcessingMode.SCAN],
            expected_output=ExpectedOutput.SUMMARY,
            reason="OPEN_NEW exploration candidate: missing Kernel localization is not automatic DROP.",
            cognitive_budget_minutes=1,
        )

    if features.kernel_delta < 0.2 and features.topic_relevance < 0.3:
        return PlanDraft(
            attention_state=AttentionState.DROP,
            reason="No material Kernel relation and low topic relevance.",
            cognitive_budget_minutes=0,
        )

    return PlanDraft(
        attention_state=AttentionState.AWARE,
        processing_modes=[ProcessingMode.SCAN],
        expected_output=ExpectedOutput.SUMMARY,
        reason="Default AWARE: insufficient Kernel delta for ENGAGE.",
        cognitive_budget_minutes=1,
    )


def _default_watch_triggers(features: SchedulerFeatures) -> list[str]:
    triggers = ["PAPER_RELEASE", "CODE_RELEASE", "INDEPENDENT_REPLICATION"]
    if features.bottleneck_alignment >= 0.4:
        triggers.extend(["BENCHMARK_UPDATE", "NEW_EVIDENCE"])
    return triggers


def validate_plan(draft: PlanDraft) -> PlanDraft:
    if draft.cognitive_budget_minutes is not None and draft.cognitive_budget_minutes < 0:
        raise ValueError("budget must be >= 0")
    if draft.attention_state == AttentionState.ENGAGE and not draft.processing_modes:
        raise ValueError("ENGAGE requires at least one processing mode")
    if draft.attention_state == AttentionState.WATCH and not draft.watch_triggers:
        draft.watch_triggers = ["NEW_EVIDENCE"]
    if draft.urgency == Urgency.PREEMPT and "interrupt" not in draft.reason.lower() and "preempt" not in draft.reason.lower():
        raise ValueError("PREEMPT requires explicit interruption justification")
    return draft
