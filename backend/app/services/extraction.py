from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.enums import (
    AttributionType,
    AuthorType,
    ClaimType,
    ObservationType,
    ObserverType,
    Stance,
    Strength,
)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“])|\n+")

INFERENCE_CUES = (
    "this probably means",
    "this means",
    "probably means",
    "this suggests",
    "suggests that",
    "therefore",
    "implying",
    "which means",
    "so the system is",
    "closed-loop bandwidth is low",
    "the system is robust",
)

OBSERVATION_CUES = (
    "in the video",
    "the video shows",
    "video shows",
    "demo contains",
    "demo shows",
    "demo visibly",
    "i saw",
    "i observed",
    "succeeds once",
    "one successful",
    "contains repeated",
    "move-pause-move",
    "move → pause",
    "move -> pause",
    "measured",
)

CLAIM_CUES = (
    "says",
    "said",
    "claims",
    "claimed",
    "announces",
    "announced",
    "according to",
    "argues",
    "argued",
    "we introduce",
    "the company",
    "the founder",
)

THEORETICAL_CUES = (
    "may face",
    "may be",
    "should",
    "if all",
    "i believe",
    "hypothesis",
    "counter",
)

PREDICTIVE_CUES = (
    "will be released",
    "will eventually",
    "is planned",
    "are planned",
    "planned",
    "will replace",
    "going to",
    "upcoming",
    "first in-orbit",
    "will be",
)

PROMOTIONAL_CUES = (
    "revolutionary",
    "world's first",
    "worlds first",
    "game-changing",
    "game changing",
    "seamless",
    "cutting-edge",
    "cutting edge",
    "unprecedented",
    "breakthrough experience",
    "unleash",
    "reimagine",
    "next-generation delight",
)

TECHNICAL_CUES = (
    "architecture",
    "latency",
    "energy",
    "world model",
    "end-to-end",
    "hierarchical",
    "control loop",
    "benchmark",
    "motor",
    "multi-agent",
    "shared world",
)

FUTURE_AS_PRESENT_FORBIDDEN = (
    "orbitbench is released",
    "orbitbench has been released",
    "already released",
)

CONTRADICTION_PAIRS = (
    (("continuous", "stable"), ("pause", "intermittent", "move-pause", "move → pause", "move -> pause")),
    (("zero-shot", "generalizes"), ("succeeds once", "one successful", "single run", "once")),
)


def split_sentences(text: str) -> list[str]:
    if not text:
        return []
    parts = [p.strip() for p in SENTENCE_SPLIT.split(text) if p.strip()]
    if len(parts) <= 1:
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    return parts


def _contains_any(text: str, cues: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(cue in low for cue in cues)


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


def _contains_unnegated_any(text: str, cues: tuple[str, ...]) -> bool:
    low = (text or "").lower()
    return any(_unnegated(low, cue) for cue in cues)


@dataclass
class ExtractedClaim:
    text: str
    claim_type: ClaimType
    attributed_to: str | None = None
    attribution_type: AttributionType = AttributionType.UNKNOWN
    confidence_extraction: float = 0.7
    temporal_status: str = "CURRENT"
    source_span_text: str | None = None
    source_start_offset: int | None = None
    source_end_offset: int | None = None
    chunk_id: str | None = None


@dataclass
class ExtractedObservation:
    text: str
    observer_type: ObserverType
    observation_type: ObservationType
    confidence: float = 0.8
    source_span_text: str | None = None
    source_start_offset: int | None = None
    source_end_offset: int | None = None
    chunk_id: str | None = None


@dataclass
class ExtractedInference:
    text: str
    author_type: AuthorType
    confidence: float = 0.5
    source_roles: list[str] = field(default_factory=list)
    source_span_text: str | None = None
    source_start_offset: int | None = None
    source_end_offset: int | None = None
    chunk_id: str | None = None


@dataclass
class ExtractedEvidence:
    source_role: str
    source_index: int
    target_role: str
    target_index: int
    stance: Stance
    strength: Strength
    confidence: float
    scope: str | None = None


@dataclass
class ExtractionResult:
    claims: list[ExtractedClaim] = field(default_factory=list)
    observations: list[ExtractedObservation] = field(default_factory=list)
    inferences: list[ExtractedInference] = field(default_factory=list)
    evidence: list[ExtractedEvidence] = field(default_factory=list)
    event_title: str | None = None
    event_summary: str | None = None
    marketing_heavy: bool = False
    evidence_maturity: float = 0.4
    current_facts: list[str] = field(default_factory=list)
    future_plans: list[str] = field(default_factory=list)
    technical_claims: list[str] = field(default_factory=list)
    promotional_framing: list[str] = field(default_factory=list)
    evidence_stage_skipped: bool = False
    evidence_skip_reason: str | None = None


def _claim_type_for(sentence: str) -> ClaimType:
    if _contains_any(sentence, PROMOTIONAL_CUES):
        return ClaimType.PROMOTIONAL
    if _contains_any(sentence, PREDICTIVE_CUES):
        return ClaimType.PREDICTIVE
    if _contains_any(sentence, TECHNICAL_CUES):
        return ClaimType.TECHNICAL
    if "should" in sentence.lower() or "will eventually" in sentence.lower():
        return ClaimType.OPINION
    return ClaimType.FACTUAL


def _attribution(sentence: str, source_type: str) -> tuple[str | None, AttributionType]:
    low = sentence.lower()
    if "founder" in low:
        return "founder", AttributionType.FOUNDER
    if "company" in low:
        return "company", AttributionType.COMPANY
    if source_type == "MANUAL_OBSERVATION" and _contains_any(sentence, THEORETICAL_CUES):
        return "user", AttributionType.USER
    if source_type == "MANUAL_OBSERVATION":
        return "user", AttributionType.USER
    return None, AttributionType.UNKNOWN


def _is_inference(sentence: str) -> bool:
    return _contains_any(sentence, INFERENCE_CUES)


def _is_observation(sentence: str, source_type: str) -> bool:
    if _is_inference(sentence):
        return False
    if _contains_any(sentence, OBSERVATION_CUES):
        return True
    if source_type == "MANUAL_OBSERVATION" and not _contains_any(sentence, THEORETICAL_CUES):
        return True
    return False


def _is_user_claim(sentence: str, source_type: str) -> bool:
    return source_type == "MANUAL_OBSERVATION" and _contains_any(sentence, THEORETICAL_CUES)


def extract_from_text(text: str, source_type: str = "TEXT", title: str | None = None) -> ExtractionResult:
    result = ExtractionResult()
    sentences = split_sentences(text)
    if title:
        result.event_title = title
    result.event_summary = (text or "")[:400]
    result.marketing_heavy = _contains_any(text or "", PROMOTIONAL_CUES) and not _contains_unnegated_any(
        text or "", TECHNICAL_CUES
    )

    search_from = 0

    def _span_for(sentence: str) -> tuple[str, int | None, int | None]:
        nonlocal search_from
        if not text:
            return sentence, None, None
        idx = text.find(sentence, search_from)
        if idx < 0:
            idx = text.find(sentence)
        if idx >= 0:
            search_from = idx + len(sentence)
            return sentence, idx, idx + len(sentence)
        return sentence, None, None

    for sentence in sentences:
        span_text, start, end = _span_for(sentence)
        if _is_inference(sentence):
            # Source-authored derived conclusion: attributed Claim, not RAOS Inference.
            result.claims.append(
                ExtractedClaim(
                    text=sentence,
                    claim_type=ClaimType.OPINION,
                    attributed_to="source",
                    attribution_type=AttributionType.UNKNOWN,
                    temporal_status="CURRENT",
                    confidence_extraction=0.6,
                    source_span_text=span_text,
                    source_start_offset=start,
                    source_end_offset=end,
                )
            )
            continue
        if _is_observation(sentence, source_type):
            obs_type = ObservationType.USER_FIELD_NOTE if source_type == "MANUAL_OBSERVATION" else ObservationType.DIRECT_VISUAL
            if "measured" in sentence.lower():
                obs_type = ObservationType.MEASUREMENT
            observer = ObserverType.USER if source_type == "MANUAL_OBSERVATION" else ObserverType.SYSTEM_EXTRACTED
            result.observations.append(
                ExtractedObservation(
                    text=sentence,
                    observer_type=observer,
                    observation_type=obs_type,
                    confidence=0.85,
                    source_span_text=span_text,
                    source_start_offset=start,
                    source_end_offset=end,
                )
            )
            continue
        if _is_user_claim(sentence, source_type) or _contains_any(sentence, CLAIM_CUES) or len(sentence) > 20:
            ctype = _claim_type_for(sentence)
            attributed_to, attr_type = _attribution(sentence, source_type)
            if _is_user_claim(sentence, source_type):
                attr_type = AttributionType.USER
                attributed_to = "user"
            temporal = "FUTURE" if ctype == ClaimType.PREDICTIVE else "CURRENT"
            claim = ExtractedClaim(
                text=sentence,
                claim_type=ctype,
                attributed_to=attributed_to,
                attribution_type=attr_type,
                temporal_status=temporal,
                source_span_text=span_text,
                source_start_offset=start,
                source_end_offset=end,
            )
            result.claims.append(claim)
            if ctype == ClaimType.PREDICTIVE:
                result.future_plans.append(sentence)
            elif ctype == ClaimType.PROMOTIONAL:
                result.promotional_framing.append(sentence)
            elif ctype == ClaimType.TECHNICAL:
                result.technical_claims.append(sentence)
            elif ctype != ClaimType.OPINION:
                result.current_facts.append(sentence)

    if source_type == "MANUAL_OBSERVATION" and not result.observations and not result.claims:
        span_text, start, end = _span_for(text.strip())
        result.observations.append(
            ExtractedObservation(
                text=text.strip(),
                observer_type=ObserverType.USER,
                observation_type=ObservationType.USER_FIELD_NOTE,
                confidence=0.9,
                source_span_text=span_text,
                source_start_offset=start,
                source_end_offset=end,
            )
        )

    result.evidence.extend(_link_contradictions(result))
    result.evidence_maturity = _evidence_maturity(result)
    return result


def _link_contradictions(result: ExtractionResult) -> list[ExtractedEvidence]:
    links = []
    for oi, obs in enumerate(result.observations):
        obs_l = obs.text.lower()
        for ci, claim in enumerate(result.claims):
            claim_l = claim.text.lower()
            for pos, neg in CONTRADICTION_PAIRS:
                if any(p in claim_l for p in pos) and any(n in obs_l for n in neg):
                    links.append(
                        ExtractedEvidence(
                            source_role="OBSERVATION",
                            source_index=oi,
                            target_role="CLAIM",
                            target_index=ci,
                            stance=Stance.WEAKENS,
                            strength=Strength.MODERATE,
                            confidence=0.7,
                            scope="surface behavior vs claimed continuity/generalization",
                        )
                    )
    return links


def _evidence_maturity(result: ExtractionResult) -> float:
    if any(o.observation_type == ObservationType.MEASUREMENT for o in result.observations):
        return 0.75
    if result.observations and result.claims:
        return 0.45
    if result.technical_claims:
        return 0.4
    if result.promotional_framing and not result.technical_claims:
        return 0.1
    return 0.3


def merge_extractions(*parts: ExtractionResult) -> ExtractionResult:
    merged = ExtractionResult()
    for part in parts:
        merged.claims.extend(part.claims)
        merged.observations.extend(part.observations)
        merged.inferences.extend(part.inferences)
        merged.current_facts.extend(part.current_facts)
        merged.future_plans.extend(part.future_plans)
        merged.technical_claims.extend(part.technical_claims)
        merged.promotional_framing.extend(part.promotional_framing)
        merged.marketing_heavy = merged.marketing_heavy or part.marketing_heavy
        if part.event_title and not merged.event_title:
            merged.event_title = part.event_title
        if part.event_summary and not merged.event_summary:
            merged.event_summary = part.event_summary
    merged = dedup_extraction(merged)
    merged.evidence = _link_contradictions(merged)
    merged.evidence_maturity = _evidence_maturity(merged)
    return merged


def _norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def dedup_extraction(result: ExtractionResult) -> ExtractionResult:
    """Keep first occurrence so source_span / chunk_id survive merge."""

    def _uniq(items, keyfn):
        seen: set[str] = set()
        out = []
        for item in items:
            key = keyfn(item)
            if key in seen:
                continue
            if key:
                seen.add(key)
            out.append(item)
        return out

    result.claims = _uniq(result.claims, lambda c: _norm_text(c.text))
    result.observations = _uniq(result.observations, lambda o: _norm_text(o.text))
    result.inferences = _uniq(result.inferences, lambda i: _norm_text(i.text))
    result.current_facts = _uniq(result.current_facts, _norm_text)
    result.future_plans = _uniq(result.future_plans, _norm_text)
    result.technical_claims = _uniq(result.technical_claims, _norm_text)
    result.promotional_framing = _uniq(result.promotional_framing, _norm_text)
    return result


FORBIDDEN_OBSERVATION_PATTERNS = (
    "closed-loop bandwidth is low",
    "the system is robust",
    "system is robust",
)


def observation_is_forbidden_inference(text: str) -> bool:
    low = text.lower()
    return any(p in low for p in FORBIDDEN_OBSERVATION_PATTERNS)
