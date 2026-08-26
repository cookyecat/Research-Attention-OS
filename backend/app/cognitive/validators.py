from __future__ import annotations

from app.enums import AuthorType, AttributionType, ClaimType, ObservationType
from app.services.extraction import (
    ExtractedClaim,
    ExtractedInference,
    ExtractedObservation,
    ExtractionResult,
    FORBIDDEN_OBSERVATION_PATTERNS,
    observation_is_forbidden_inference,
)

# Constitution guardrail only — not the Cognitive Engine.
INFERENCE_MARKERS = (
    "probably",
    "therefore",
    "suggests",
    "indicates",
    "we believe",
    "this means",
    "implies",
    "likely means",
    "appears that",
    "it follows that",
    "we conclude",
)

ZH_INFERENCE_MARKERS = (
    "可能",
    "说明",
    "意味着",
    "表明",
    "推测",
    "或许",
    "可以认为",
    "由此可见",
    "我们认为",
    "因此",
    "所以",
    "由此可知",
    "这意味着",
    "这表示",
    "似乎",
    "大概",
    "估计",
)

ATTRIBUTION_MARKERS = (
    "the company says",
    "the founder says",
    "claims that",
    "we announce",
    "according to the company",
    "the official statement",
    "the paper argues",
    "the author argues",
    "the article says",
    "the report says",
)

ZH_ATTRIBUTION_MARKERS = (
    "公司称",
    "创始人表示",
    "官方宣称",
    "官方表示",
    "公司表示",
    "创始人称",
    "发言人表示",
    "据公司称",
    "据官方",
    "宣布",
    "文章认为",
    "作者认为",
    "该文指出",
    "报道认为",
)

MEDIA_REPORT_MARKERS = (
    "according to a report",
    "according to the report",
    "the article reports",
    "media reported",
    "it was reported",
    "news reported",
    "press release",
    "the article says",
    "a report said",
)

ZH_MEDIA_REPORT_MARKERS = (
    "据报道",
    "文章称",
    "消息称",
    "记者",
    "发布会",
    "媒体报道",
    "有报道称",
)

SOURCE_CONCLUSION_MARKERS = (
    "this probably means",
    "this means the",
    "this suggests",
    "this indicates",
    "therefore the system",
    "probably means the system",
)

FIRST_HAND_TYPES = {
    ObservationType.DIRECT_VISUAL,
    ObservationType.MEASUREMENT,
    ObservationType.USER_FIELD_NOTE,
}

FIRST_HAND_CUES = (
    "in the video",
    "the video shows",
    "video shows",
    "i saw",
    "i observed",
    "i measured",
    "we measured",
    "measured",
    "field note",
    "demo shows",
    "demo contains",
    "demo visibly",
    "succeeds once",
    "one successful",
)


def _is_inference_language(text: str) -> bool:
    low = text.lower()
    if any(m in low for m in INFERENCE_MARKERS):
        return True
    if any(m in text for m in ZH_INFERENCE_MARKERS):
        return True
    return observation_is_forbidden_inference(text)


def _is_attribution_language(text: str) -> bool:
    low = text.lower()
    if any(p in low for p in ATTRIBUTION_MARKERS):
        return True
    return any(p in text for p in ZH_ATTRIBUTION_MARKERS)


def _is_media_report(text: str) -> bool:
    low = text.lower()
    if any(p in low for p in MEDIA_REPORT_MARKERS):
        return True
    return any(p in text for p in ZH_MEDIA_REPORT_MARKERS)


def _is_source_authored_conclusion(text: str) -> bool:
    low = text.lower()
    if _is_attribution_language(text) or _is_media_report(text):
        return True
    return any(p in low for p in SOURCE_CONCLUSION_MARKERS)


def _has_first_hand_cue(text: str) -> bool:
    low = text.lower()
    return any(p in low for p in FIRST_HAND_CUES)


def _is_first_hand(obs: ExtractedObservation) -> bool:
    if obs.observation_type in FIRST_HAND_TYPES:
        return True
    return _has_first_hand_cue(obs.text)


def _as_claim(text: str, *, claim_type: ClaimType, attributed_to: str | None, obs: ExtractedObservation | None = None) -> ExtractedClaim:
    return ExtractedClaim(
        text=text,
        claim_type=claim_type,
        attributed_to=attributed_to,
        attribution_type=AttributionType.UNKNOWN,
        confidence_extraction=0.6,
        source_span_text=obs.source_span_text if obs else None,
        source_start_offset=obs.source_start_offset if obs else None,
        source_end_offset=obs.source_end_offset if obs else None,
        chunk_id=obs.chunk_id if obs else None,
    )


def _as_raos_inference(text: str, obs: ExtractedObservation | None = None, source_roles: list[str] | None = None) -> ExtractedInference:
    return ExtractedInference(
        text=text,
        author_type=AuthorType.AI,
        confidence=min(obs.confidence, 0.45) if obs else 0.45,
        source_roles=source_roles or ["raos"],
        source_span_text=obs.source_span_text if obs else None,
        source_start_offset=obs.source_start_offset if obs else None,
        source_end_offset=obs.source_end_offset if obs else None,
        chunk_id=obs.chunk_id if obs else None,
    )


def validate_extraction(result: ExtractionResult) -> ExtractionResult:
    """Deterministic constitution guard: Claim ≠ Observation ≠ Inference.

    Source-authored opinions/predictions stay Claims. AI Inference is RAOS-only.
    """
    clean_obs: list[ExtractedObservation] = []
    for obs in result.observations:
        if _is_attribution_language(obs.text) or _is_media_report(obs.text):
            result.claims.append(_as_claim(obs.text, claim_type=ClaimType.FACTUAL, attributed_to="source", obs=obs))
            continue
        if _is_inference_language(obs.text) or observation_is_forbidden_inference(obs.text):
            result.inferences.append(
                _as_raos_inference(obs.text, obs, source_roles=["demoted-from-observation"])
            )
            continue
        if any(p in obs.text.lower() for p in FORBIDDEN_OBSERVATION_PATTERNS):
            result.inferences.append(_as_raos_inference(obs.text, obs, source_roles=["demoted-from-observation"]))
            continue
        if obs.observation_type == ObservationType.REPORTED_RESULT and not _has_first_hand_cue(obs.text):
            result.claims.append(_as_claim(obs.text, claim_type=ClaimType.FACTUAL, attributed_to="source", obs=obs))
            continue
        if obs.observation_type == ObservationType.OTHER and not _is_first_hand(obs):
            result.claims.append(_as_claim(obs.text, claim_type=ClaimType.FACTUAL, attributed_to="source", obs=obs))
            continue
        clean_obs.append(obs)
    result.observations = clean_obs

    kept_inf: list[ExtractedInference] = []
    for inf in result.inferences:
        demoted = "demoted-from-observation" in (inf.source_roles or [])
        if not demoted and (
            _is_attribution_language(inf.text) or _is_media_report(inf.text) or _is_source_authored_conclusion(inf.text)
        ):
            result.claims.append(
                ExtractedClaim(
                    text=inf.text,
                    claim_type=ClaimType.OPINION,
                    attributed_to="source",
                    attribution_type=AttributionType.UNKNOWN,
                    confidence_extraction=min(inf.confidence, 0.6),
                    source_span_text=inf.source_span_text,
                    source_start_offset=inf.source_start_offset,
                    source_end_offset=inf.source_end_offset,
                    chunk_id=inf.chunk_id,
                )
            )
            continue
        author = inf.author_type if isinstance(inf.author_type, AuthorType) else AuthorType.AI
        kept_inf.append(
            ExtractedInference(
                text=inf.text,
                author_type=AuthorType.AI if author == AuthorType.AI else author,
                confidence=inf.confidence,
                source_roles=inf.source_roles or ["raos"],
                source_span_text=inf.source_span_text,
                source_start_offset=inf.source_start_offset,
                source_end_offset=inf.source_end_offset,
                chunk_id=inf.chunk_id,
            )
        )
    result.inferences = kept_inf
    return result


def validate_evidence_strength(stance: str, strength: str, evidence_maturity: float) -> tuple[str, str]:
    stance = stance.upper()
    strength = strength.upper()
    if stance == "REFUTES" and evidence_maturity < 0.7:
        return "WEAKENS", "MODERATE"
    if strength == "STRONG" and evidence_maturity < 0.55:
        strength = "MODERATE"
    return stance, strength
