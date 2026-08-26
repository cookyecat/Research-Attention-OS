from __future__ import annotations

import re

from app.enums import AuthorType, ClaimType, ObservationType
from app.services.extraction import (
    ExtractedClaim,
    ExtractedInference,
    ExtractedObservation,
    ExtractionResult,
    FORBIDDEN_OBSERVATION_PATTERNS,
    observation_is_forbidden_inference,
)

# Constitution guardrail only — not the Cognitive Engine.
# Markers in English and Chinese; attribution speech is a Claim, not an Observation.
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


def validate_extraction(result: ExtractionResult) -> ExtractionResult:
    """Deterministic constitution guard: Claim != Observation != Inference."""
    clean_obs: list[ExtractedObservation] = []
    for obs in result.observations:
        if _is_inference_language(obs.text) or observation_is_forbidden_inference(obs.text):
            result.inferences.append(
                ExtractedInference(
                    text=obs.text,
                    author_type=AuthorType.AI,
                    confidence=min(obs.confidence, 0.45),
                    source_roles=["demoted-from-observation"],
                    source_span_text=obs.source_span_text,
                    source_start_offset=obs.source_start_offset,
                    source_end_offset=obs.source_end_offset,
                    chunk_id=obs.chunk_id,
                )
            )
            continue
        if any(p in obs.text.lower() for p in FORBIDDEN_OBSERVATION_PATTERNS):
            continue
        clean_obs.append(obs)
    result.observations = clean_obs

    still_obs = []
    for obs in result.observations:
        if _is_attribution_language(obs.text):
            result.claims.append(
                ExtractedClaim(
                    text=obs.text,
                    claim_type=ClaimType.TECHNICAL,
                    attributed_to="speaker",
                    confidence_extraction=0.6,
                    source_span_text=obs.source_span_text,
                    source_start_offset=obs.source_start_offset,
                    source_end_offset=obs.source_end_offset,
                    chunk_id=obs.chunk_id,
                )
            )
            continue
        still_obs.append(obs)
    result.observations = still_obs

    fixed_inf = []
    for inf in result.inferences:
        author = inf.author_type
        if not isinstance(author, AuthorType):
            author = AuthorType.AI
        fixed_inf.append(
            ExtractedInference(
                text=inf.text,
                author_type=author,
                confidence=inf.confidence,
                source_roles=inf.source_roles,
                source_span_text=inf.source_span_text,
                source_start_offset=inf.source_start_offset,
                source_end_offset=inf.source_end_offset,
                chunk_id=inf.chunk_id,
            )
        )
    result.inferences = fixed_inf
    return result


def validate_evidence_strength(stance: str, strength: str, evidence_maturity: float) -> tuple[str, str]:
    stance = stance.upper()
    strength = strength.upper()
    if stance == "REFUTES" and evidence_maturity < 0.7:
        return "WEAKENS", "MODERATE"
    if strength == "STRONG" and evidence_maturity < 0.55:
        strength = "MODERATE"
    return stance, strength
