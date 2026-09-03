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

# Type priors only. Not "every BELIEF outranks every PROJECT."
# Resolution: explicit Kernel payload importance/priority > type prior > LLM estimate > neutral.
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
NEUTRAL_IMPORTANCE = 0.5
MATERIAL_CHANGE_MIN = 0.35
MEANINGFUL_CHANGE = 0.55
LOW_EPISTEMIC = 0.45

# Single promotional / media source without first-hand evidence cannot justify strong revision.
SINGLE_SOURCE_EPISTEMIC_CAP = 0.35
MARKETING_EPISTEMIC_CAP = 0.25


KNOWN_OPERATIONS = frozenset({"REINFORCE", "CHALLENGE", "OPEN_NEW"})

# Kernel Match localizes work context. These types are not automatic update targets.
LOCATION_NODE_TYPES = frozenset({"GOAL", "PROJECT"})
# Nodes whose content can actually be reinforced or challenged.
UPDATE_ELIGIBLE_NODE_TYPES = frozenset(
    {"BELIEF", "MODEL", "QUESTION", "HYPOTHESIS", "DECISION", "BOTTLENECK"}
)
# Shared topical words that must not by themselves justify REINFORCE / CHALLENGE.
GENERIC_TOPIC_TOKENS = frozenset(
    {
        "model",
        "models",
        "motor",
        "intelligence",
        "embodied",
        "control",
        "robot",
        "robots",
        "robotics",
        "ai",
        "unified",
        "system",
        "systems",
        "agent",
        "agents",
        "learning",
        "paper",
        "large",
        "high",
        "frequency",
    }
)


@dataclass
class CognitiveEffect:
    target_kernel_node_id: UUID | None
    operation: CognitiveEffectKind
    change_magnitude: float
    epistemic_strength: float
    target_importance: float
    reason: str
    exploration_candidate: bool = False

    def as_dict(self) -> dict:
        kind = self.operation.value if hasattr(self.operation, "value") else str(self.operation)
        return {
            "target_kernel_node_id": str(self.target_kernel_node_id) if self.target_kernel_node_id else None,
            "operation": kind,
            "change_magnitude": round(float(self.change_magnitude), 3),
            "epistemic_strength": round(float(self.epistemic_strength), 3),
            "target_importance": round(float(self.target_importance), 3),
            "reason": self.reason,
            "exploration_candidate": bool(self.exploration_candidate),
        }


@dataclass
class CognitiveImpactAssessment:
    """Semantic source of truth for Attention Policy. SchedulerFeatures is a debug projection."""

    effects: list[CognitiveEffect] = field(default_factory=list)
    attention_cost: float = 2.0
    exploration_candidate: bool = False
    features: object | None = None
    raw_effects: list[CognitiveEffect] = field(default_factory=list)

    def as_dict(self) -> dict:
        primary = select_primary_effect(self)
        return {
            "effects": [e.as_dict() for e in self.effects],
            "primary_effect": primary.as_dict() if primary is not None else None,
            "attention_cost": round(float(self.attention_cost), 3),
            "exploration_candidate": bool(self.exploration_candidate),
        }

    def material_effects(self) -> list[CognitiveEffect]:
        return [e for e in self.effects if _is_operation(e.operation)]


def _kind(value) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _is_operation(value) -> bool:
    return _kind(value) in KNOWN_OPERATIONS


def is_location_node(node_type) -> bool:
    return str(node_type or "").upper() in LOCATION_NODE_TYPES


def is_update_eligible_node(node_type) -> bool:
    return str(node_type or "").upper() in UPDATE_ELIGIBLE_NODE_TYPES


def epistemic_text(extraction: ExtractionResult) -> str:
    """Claim / Observation / Inference text — the Impact stage's primary input."""
    parts: list[str] = []
    for item in getattr(extraction, "claims", None) or []:
        text = getattr(item, "text", None)
        if text:
            parts.append(str(text))
    for item in getattr(extraction, "observations", None) or []:
        text = getattr(item, "text", None)
        if text:
            parts.append(str(text))
    for item in getattr(extraction, "inferences", None) or []:
        text = getattr(item, "text", None)
        if text:
            parts.append(str(text))
    for item in getattr(extraction, "technical_claims", None) or []:
        if item:
            parts.append(str(item))
    return "\n".join(parts)


def node_proposition(node_or_match) -> str:
    payload = getattr(node_or_match, "payload", None) or {}
    if isinstance(payload, dict):
        for key in ("proposition", "text", "description", "rationale", "scope"):
            if payload.get(key):
                return str(payload[key])
    return str(getattr(node_or_match, "title", None) or "")


def distinctive_target_tokens(match: KernelMatch) -> set[str]:
    from app.services.matching import tokenize

    target_tokens = tokenize(node_proposition(match)) | tokenize(str(match.title or ""))
    return {t for t in target_tokens if t not in GENERIC_TOPIC_TOKENS}


def claim_scope_aligned(extraction: ExtractionResult, match: KernelMatch) -> bool:
    """True only when epistemic objects overlap the target's distinctive scope.

    Generic topical words (motor / model / unified / robot) are not enough.
    STRUCTURAL matches are analogical, not keyword overlap, and count as aligned.
    """
    if getattr(match, "structural", False) or str(getattr(match, "relevance_type", "") or "").upper() == "STRUCTURAL":
        return True
    from app.services.matching import tokenize

    distinctive = distinctive_target_tokens(match)
    if len(distinctive) < 2:
        return False
    source_tokens = tokenize(epistemic_text(extraction))
    overlap = distinctive & source_tokens
    # Beliefs/questions need two distinctive tokens so "loop" or "unified" cannot
    # alone attach an update. Models/bottlenecks may align on one technical term.
    need = 2 if str(match.node_type or "").upper() in {"BELIEF", "QUESTION"} else 1
    return len(overlap) >= need


# Comparative / exclusive / counterexample / causal cues. Not route names.
CONTRASTIVE_EVIDENCE_CUES = (
    "unlike",
    "rather than",
    "instead of",
    "compared to",
    "compared with",
    "as opposed to",
    "not necessary",
    "unnecessary",
    "unsuitable",
    "does not require",
    "do not need",
    "cannot",
    "is false",
    "are false",
    "refute",
    "contradict",
    "counterexample",
    "opposite",
    "fails when",
    "insufficient",
    "invalidates",
    "no longer",
    "no separate",
    "不适合",
    "不需要",
    "无法",
    "而不是",
    "相比",
    "反例",
)


NEGATIVE_PROPOSITION_CUES = (
    "unsuitable",
    "unnecessary",
    "cannot",
    "is false",
    "are false",
    "should not",
    "does not",
    "not sufficient",
    "不适合",
    "不需要",
)


def source_addresses_proposition_polarity(extraction: ExtractionResult, match: KernelMatch) -> bool:
    """A success/existence claim about another route does not confirm a negative proposition."""
    if getattr(match, "structural", False) or str(getattr(match, "relevance_type", "") or "").upper() == "STRUCTURAL":
        return True
    text = epistemic_text(extraction)
    if not (text or "").strip():
        return True
    prop = f"{node_proposition(match)} {match.title or ''}".lower()
    cues = [c for c in NEGATIVE_PROPOSITION_CUES if c in prop]
    if not cues:
        return True
    return any(c in text.lower() for c in cues)


def direct_challenge_evidence(extraction: ExtractionResult, match: KernelMatch) -> bool:
    """CHALLENGE needs evidence that addresses the target proposition itself.

    Evidence that some other route works, exists, or succeeds is not enough.
    STRUCTURAL matches already carry analogical challenge structure.
    Empty epistemic text cannot disprove an already-judged CHALLENGE (caps only).
    """
    if getattr(match, "structural", False) or str(getattr(match, "relevance_type", "") or "").upper() == "STRUCTURAL":
        return True
    text = epistemic_text(extraction)
    if not (text or "").strip():
        return True
    if not claim_scope_aligned(extraction, match):
        exclusive = any(cue in text.lower() for cue in CONTRASTIVE_EVIDENCE_CUES)
        return exclusive
    distinctive = distinctive_target_tokens(match)
    if not distinctive:
        return any(cue in text.lower() for cue in CONTRASTIVE_EVIDENCE_CUES)
    from app.services.extraction import split_sentences
    from app.services.matching import tokenize

    for sentence in split_sentences(text) or [text]:
        low = sentence.lower()
        if not any(cue in low for cue in CONTRASTIVE_EVIDENCE_CUES):
            continue
        if distinctive & tokenize(sentence):
            return True
        # Exclusive/comparative syntax can challenge even when distinctive tokens
        # sit in the title rather than the same sentence.
        if any(cue in low for cue in ("rather than", "instead of", "compared to", "no separate", "as opposed to")):
            return True
    return False


def _unnegated(low: str, cue: str) -> bool:
    """True when `cue` occurs at least once without a local negation."""
    if cue not in low:
        return False
    remnants = low
    for neg in (
        f"no {cue}",
        f"not {cue}",
        f"without {cue}",
        f"without a {cue}",
        f"without an {cue}",
        f"lacks {cue}",
        f"lack of {cue}",
    ):
        remnants = remnants.replace(neg, " ")
    return cue in remnants


def _parse_operation(raw) -> CognitiveEffectKind | None:
    value = _kind(raw)
    if value not in KNOWN_OPERATIONS:
        return None
    return CognitiveEffectKind(value)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def explicit_node_importance(node) -> float | None:
    """Read KernelNode.payload importance or priority. Clamp to [0, 1]."""
    payload = getattr(node, "payload", None) or {}
    if not isinstance(payload, dict):
        return None
    for key in ("importance", "priority"):
        raw = payload.get(key)
        if raw is None:
            continue
        try:
            return _clamp01(float(raw))
        except (TypeError, ValueError):
            continue
    return None


def resolve_target_importance(*, node=None, node_type: str | None = None, llm_estimate: float | None = None) -> float:
    """explicit Kernel importance > stable type prior > LLM estimate > neutral.

    Does not raise an LLM estimate to a type minimum.
    """
    if node is not None:
        explicit = explicit_node_importance(node)
        if explicit is not None:
            return explicit
        node_type = node_type or getattr(node, "node_type", None)
    if node_type:
        prior = TARGET_IMPORTANCE.get(str(node_type))
        if prior is not None:
            return prior
    if llm_estimate is not None:
        try:
            return _clamp01(float(llm_estimate))
        except (TypeError, ValueError):
            pass
    return NEUTRAL_IMPORTANCE


def material_effects(assessment: CognitiveImpactAssessment | None, *, min_change: float = MATERIAL_CHANGE_MIN) -> list[CognitiveEffect]:
    if assessment is None:
        return []
    return [
        e
        for e in assessment.effects
        if _is_operation(e.operation) and float(e.change_magnitude) >= min_change
    ]


def _legal_public_effect(effect: CognitiveEffect) -> bool:
    """REINFORCE/CHALLENGE require an existing node. OPEN_NEW requires none."""
    op = _kind(effect.operation)
    if op == CognitiveEffectKind.OPEN_NEW:
        return True
    if op in {CognitiveEffectKind.REINFORCE, CognitiveEffectKind.CHALLENGE}:
        return effect.target_kernel_node_id is not None
    return False


def _primary_sort_key(effect: CognitiveEffect) -> tuple:
    """Order-independent rank: maximum useful cognitive change.

    Existing-target REINFORCE/CHALLENGE and OPEN_NEW compete on the same
    value: how much cognition could change × how much that change matters.
    Having an existing node is not a bonus. Operation type is not a bonus.
    Epistemic strength is a tie-break, not the definition of the update.
    Node id is a stable last key so list order never decides.
    """
    change = round(float(effect.change_magnitude), 6)
    importance = round(float(effect.target_importance), 6)
    epi = round(float(effect.epistemic_strength), 6)
    nid = str(effect.target_kernel_node_id) if effect.target_kernel_node_id else ""
    useful = round(change * importance, 6)
    return (useful, change, importance, epi, nid)


def select_primary_effect(assessment: CognitiveImpactAssessment | None) -> CognitiveEffect | None:
    """The one CognitiveEffect that public Update and Attention Policy both use.

    Primary = the coherent effect that best represents the largest useful
    cognitive change after absorbing the information.
    """
    legal = [e for e in material_effects(assessment) if _legal_public_effect(e)]
    if not legal:
        return None
    return max(legal, key=_primary_sort_key)


def primary_update(assessment: CognitiveImpactAssessment | None) -> dict:
    """Single Cognitive Update for the public contract: operation × target_node_id."""
    chosen = select_primary_effect(assessment)
    if chosen is None:
        return {"operation": None, "target_node_id": None}
    op = _kind(chosen.operation)
    nid = str(chosen.target_kernel_node_id) if chosen.target_kernel_node_id else None
    if op == CognitiveEffectKind.OPEN_NEW:
        nid = None
    return {"operation": chosen.operation if isinstance(chosen.operation, CognitiveEffectKind) else CognitiveEffectKind(op), "target_node_id": nid}


def max_change_magnitude(assessment: CognitiveImpactAssessment | None) -> float:
    pool = material_effects(assessment) or (list(assessment.effects) if assessment else [])
    return max((float(e.change_magnitude) for e in pool), default=0.0)


def max_epistemic_strength(assessment: CognitiveImpactAssessment | None) -> float:
    pool = material_effects(assessment) or (list(assessment.effects) if assessment else [])
    return max((float(e.epistemic_strength) for e in pool), default=0.0)


def max_target_importance(assessment: CognitiveImpactAssessment | None) -> float:
    pool = material_effects(assessment) or (list(assessment.effects) if assessment else [])
    return max((float(e.target_importance) for e in pool), default=0.0)


def has_effect(assessment: CognitiveImpactAssessment | None, kind) -> bool:
    want = _kind(kind)
    if assessment is None:
        return False
    for effect in assessment.effects:
        if _kind(effect.operation) != want:
            continue
        if want in {CognitiveEffectKind.REINFORCE, CognitiveEffectKind.CHALLENGE} and effect.target_kernel_node_id is None:
            continue
        return True
    return False


def has_exploration_effect(assessment: CognitiveImpactAssessment | None) -> bool:
    if assessment is None:
        return False
    if assessment.exploration_candidate:
        return True
    return any(
        e.exploration_candidate or _kind(e.operation) == CognitiveEffectKind.OPEN_NEW for e in assessment.effects
    )


def _match_index(matches) -> dict:
    return {m.node_id: m for m in (matches or [])}


def effect_target_match(effect: CognitiveEffect, matches):
    if effect.target_kernel_node_id is None:
        return None
    return _match_index(matches).get(effect.target_kernel_node_id)


def has_target_type(assessment: CognitiveImpactAssessment | None, matches, node_type: str) -> bool:
    wanted = str(node_type).upper()
    for effect in material_effects(assessment):
        match = effect_target_match(effect, matches)
        if match is not None and str(match.node_type).upper() == wanted:
            return True
    return False


def material_effects_on_type(assessment: CognitiveImpactAssessment | None, matches, *node_types: str) -> list[CognitiveEffect]:
    wanted = {t.upper() for t in node_types}
    found: list[CognitiveEffect] = []
    for effect in material_effects(assessment):
        match = effect_target_match(effect, matches)
        if match is not None and str(match.node_type).upper() in wanted:
            found.append(effect)
    return found


def material_structural_effects(assessment: CognitiveImpactAssessment | None, matches) -> list[CognitiveEffect]:
    found: list[CognitiveEffect] = []
    for effect in material_effects(assessment):
        match = effect_target_match(effect, matches)
        if match is None:
            continue
        rel = str(getattr(match, "relevance_type", "") or "").upper()
        if match.structural or rel == "STRUCTURAL" or str(match.node_type).upper() == "DECISION":
            found.append(effect)
    return found


def assessment_from_dict(data: dict | None) -> CognitiveImpactAssessment | None:
    if not data:
        return None
    effects: list[CognitiveEffect] = []
    for item in data.get("effects") or []:
        nid = item.get("target_kernel_node_id")
        try:
            target = UUID(str(nid)) if nid else None
        except (TypeError, ValueError):
            target = None
        raw = item.get("operation") if item.get("operation") is not None else item.get("effect")
        operation = _parse_operation(raw)
        if operation is None:
            continue
        effects.append(
            CognitiveEffect(
                target_kernel_node_id=target,
                operation=operation,
                change_magnitude=float(item.get("change_magnitude") or 0.0),
                epistemic_strength=float(item.get("epistemic_strength") or 0.0),
                target_importance=float(item.get("target_importance") or 0.0),
                reason=str(item.get("reason") or ""),
                exploration_candidate=bool(item.get("exploration_candidate")),
            )
        )
    return CognitiveImpactAssessment(
        effects=effects,
        attention_cost=float(data.get("attention_cost") or 2.0),
        exploration_candidate=bool(data.get("exploration_candidate")),
    )


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


def _targeted_effect_is_valid(
    operation: CognitiveEffectKind,
    match: KernelMatch,
    extraction: ExtractionResult,
) -> bool:
    """REINFORCE/CHALLENGE must pass scope, location, and epistemic grounding."""
    if is_location_node(match.node_type) and not claim_scope_aligned(extraction, match):
        return False
    if operation == CognitiveEffectKind.CHALLENGE:
        if (epistemic_text(extraction) or "").strip() and not direct_challenge_evidence(extraction, match):
            return False
    if operation == CognitiveEffectKind.REINFORCE:
        if (epistemic_text(extraction) or "").strip() and not source_addresses_proposition_polarity(
            extraction, match
        ):
            return False
    return True


def ground_effects(
    effects: list[CognitiveEffect],
    matches: list[KernelMatch],
    extraction: ExtractionResult,
    *,
    independent_source_count: int = 1,
) -> list[CognitiveEffect]:
    """Deterministic caps plus Location ≠ Update.

    Invalid targeted REINFORCE/CHALLENGE effects are discarded — not rewritten
    as OPEN_NEW. OPEN_NEW must come from positive new-branch recognition.
    """
    allowed = {m.node_id for m in matches}
    cap = epistemic_cap(extraction, independent_source_count=independent_source_count)
    grounded: list[CognitiveEffect] = []
    for effect in effects:
        operation = _parse_operation(effect.operation)
        if operation is None:
            continue
        target = effect.target_kernel_node_id
        if operation == CognitiveEffectKind.OPEN_NEW:
            target = None
        elif target is None or target not in allowed:
            continue
        else:
            match = next((m for m in matches if m.node_id == target), None)
            if match is None:
                continue
            if not _targeted_effect_is_valid(operation, match, extraction):
                continue
        epi = min(float(effect.epistemic_strength), cap)
        change = max(0.0, min(1.0, float(effect.change_magnitude)))
        importance = max(0.0, min(1.0, float(effect.target_importance)))
        explore = bool(effect.exploration_candidate) or operation == CognitiveEffectKind.OPEN_NEW
        grounded.append(
            CognitiveEffect(
                target_kernel_node_id=target,
                operation=operation,
                change_magnitude=change,
                epistemic_strength=epi,
                target_importance=importance,
                reason=effect.reason,
                exploration_candidate=explore,
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
    """Compatibility/debug projection. Not the source of truth for Attention Policy."""
    from app.services.scheduler import SchedulerFeatures, ground_features_to_matches

    if isinstance(assessment_or_effects, CognitiveImpactAssessment):
        effects = assessment_or_effects.effects
        attention_cost = assessment_or_effects.attention_cost
        exploration_candidate = assessment_or_effects.exploration_candidate or exploration_candidate
        assessment = assessment_or_effects
    else:
        effects = list(assessment_or_effects)
        assessment = CognitiveImpactAssessment(effects=effects, attention_cost=attention_cost)

    links_present, conflict = evidence_conflict_flags(
        extraction, independent_source_count=independent_source_count
    )
    primary = select_primary_effect(assessment)
    if primary is not None:
        max_change = float(primary.change_magnitude)
        max_epi = float(primary.epistemic_strength)
        max_importance = float(primary.target_importance)
        challenge = max_change if _kind(primary.operation) == CognitiveEffectKind.CHALLENGE else 0.0
    else:
        max_change = 0.0
        max_epi = 0.2
        max_importance = 0.0
        challenge = 0.0
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
        _kind(e.operation) == CognitiveEffectKind.OPEN_NEW for e in effects
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
    nodes=None,
) -> CognitiveImpactAssessment:
    """Deterministic impact assessment used by the rule provider and as fallback."""
    from app.services.matching import EQUITY_STRUCTURE, tokenize
    from app.services.scheduler import _compatibility_features

    nodes_by_id = {n.id: n for n in (nodes or [])}

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

    for match in matches:
        if is_location_node(match.node_type):
            # GOAL / PROJECT localize where the information sits. They are not
            # automatic REINFORCE / CHALLENGE targets.
            continue
        if not is_update_eligible_node(match.node_type):
            continue
        if not claim_scope_aligned(extraction, match):
            continue
        importance = resolve_target_importance(node=nodes_by_id.get(match.node_id), node_type=match.node_type)
        change = match.score
        epi = min(probe.credibility, cap)
        if "minor" in low and "version" in low:
            continue
        if match.node_type == "BELIEF":
            if direct_challenge_evidence(extraction, match):
                kind = CognitiveEffectKind.CHALLENGE
                change = max(change, 0.7)
            elif not source_addresses_proposition_polarity(extraction, match):
                continue
            else:
                kind = CognitiveEffectKind.REINFORCE
        elif match.node_type == "DECISION" or match.structural or match.relevance_type == "STRUCTURAL":
            kind = CognitiveEffectKind.REINFORCE
        elif match.node_type in {"MODEL", "QUESTION", "BOTTLENECK", "HYPOTHESIS"}:
            kind = CognitiveEffectKind.REINFORCE
        else:
            continue
        if probe.marketing_heavy:
            epi = min(epi, MARKETING_EPISTEMIC_CAP)
        effects.append(
            CognitiveEffect(
                target_kernel_node_id=match.node_id,
                operation=kind,
                change_magnitude=change,
                epistemic_strength=epi,
                target_importance=importance,
                reason=match.reason or f"{kind} on {match.title or match.node_type}",
            )
        )
    if not effects:
        from app.services.extraction import PROMOTIONAL_CUES, _contains_any

        equity_only = bool(EQUITY_STRUCTURE & tokens) and not ({"robot", "embodied", "motor", "agent"} & tokens)
        promo = probe.marketing_heavy or bool(extraction.promotional_framing) or _contains_any(text, PROMOTIONAL_CUES)
        paperish = _unnegated(low, "paper") or _unnegated(low, "arxiv") or "foundational" in low
        technical = bool(extraction.technical_claims) or paperish
        located = any(is_location_node(m.node_type) for m in matches)
        conflict = probe.disagreement >= 0.55 or probe.sources_conflict
        media_hype = "unsourced" in low or (
            "video" in low and any(w in low for w in ("magical", "inspiring", "hype"))
        )
        shallow_news = (
            ("minor" in low and "version" in low)
            or "leaderboard" in low
            or "changelog" in low
            or "funding recap" in low
            or "tweeted" in low
            or media_hype
        )
        if conflict:
            epi = min(0.35, cap)
            if promo:
                epi = min(epi, MARKETING_EPISTEMIC_CAP)
            effects.append(
                CognitiveEffect(
                    target_kernel_node_id=None,
                    operation=CognitiveEffectKind.OPEN_NEW,
                    change_magnitude=max(0.65, probe.kernel_delta, 0.55),
                    epistemic_strength=epi,
                    target_importance=0.75,
                    reason="Claims and observations conflict, but no existing Kernel node is the right update target.",
                    exploration_candidate=True,
                )
            )
        elif technical and not equity_only and not shallow_news:
            material_branch = (
                paperish
                or _unnegated(low, "architecture")
                or any(k in low for k in ("introduces", "we propose", "abstraction"))
            )
            # Promotional framing without a real new method/paper/architecture is
            # source quality, not a cognitive branch.
            if promo and not material_branch:
                pass
            else:
                reason = (
                    "Located near an existing Goal/Project, but no existing cognition is actually updated."
                    if located and material_branch
                    else "No current Kernel target; possible new question or model candidate."
                )
                epi = min(0.3, cap)
                if promo:
                    epi = min(epi, MARKETING_EPISTEMIC_CAP)
                effects.append(
                    CognitiveEffect(
                        target_kernel_node_id=None,
                        operation=CognitiveEffectKind.OPEN_NEW,
                        change_magnitude=0.55 if material_branch else 0.4,
                        epistemic_strength=epi,
                        target_importance=0.55 if material_branch else 0.4,
                        reason=reason,
                        exploration_candidate=True,
                    )
                )

    if probe.disagreement >= 0.55 or probe.sources_conflict:
        if not any(_kind(e.operation) == CognitiveEffectKind.CHALLENGE for e in effects):
            belief = next(
                (
                    m
                    for m in matches
                    if m.node_type == "BELIEF" and claim_scope_aligned(extraction, m)
                ),
                None,
            )
            if belief is not None and direct_challenge_evidence(extraction, belief):
                effects.append(
                    CognitiveEffect(
                        target_kernel_node_id=belief.node_id,
                        operation=CognitiveEffectKind.CHALLENGE,
                        change_magnitude=max(0.75, probe.kernel_delta),
                        epistemic_strength=min(0.45, cap),
                        target_importance=resolve_target_importance(
                            node=nodes_by_id.get(belief.node_id),
                            node_type="BELIEF",
                            llm_estimate=0.5,
                        ),
                        reason="Attributed claims conflict with observations or an active Belief.",
                    )
                )
            elif not any(_kind(e.operation) == CognitiveEffectKind.OPEN_NEW for e in effects):
                effects.append(
                    CognitiveEffect(
                        target_kernel_node_id=None,
                        operation=CognitiveEffectKind.OPEN_NEW,
                        change_magnitude=max(0.55, probe.kernel_delta),
                        epistemic_strength=min(0.35, cap),
                        target_importance=0.55,
                        reason="Conflicting claims/observations with no existing Kernel node to challenge.",
                        exploration_candidate=True,
                    )
                )

    raw_effects = list(effects)
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
    primary = select_primary_effect(
        CognitiveImpactAssessment(effects=effects, attention_cost=float(attention_cost), exploration_candidate=explore)
    )
    if primary is None:
        features.kernel_delta = min(probe.kernel_delta, 0.1)
        features.change_magnitude = 0.0
        features.epistemic_strength = 0.2
        features.target_importance = 0.0
    else:
        features.kernel_delta = float(primary.change_magnitude)
        features.change_magnitude = round(float(primary.change_magnitude), 3)
        features.epistemic_strength = round(float(primary.epistemic_strength), 3)
        features.target_importance = round(float(primary.target_importance), 3)
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
        raw_effects=raw_effects,
    )
