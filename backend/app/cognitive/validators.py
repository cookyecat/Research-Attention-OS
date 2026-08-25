from __future__ import annotations

import re

from app.enums import ClaimType, ObservationType
from app.services.extraction import (
    ExtractedClaim,
    ExtractedInference,
    ExtractedObservation,
    ExtractionResult,
    FORBIDDEN_OBSERVATION_PATTERNS,
    observation_is_forbidden_inference,
)

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
)


def _is_inference_language(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in INFERENCE_MARKERS) or observation_is_forbidden_inference(text)


def validate_extraction(result: ExtractionResult) -> ExtractionResult:
    """Deterministic constitution guard: Claim != Observation != Inference."""
    clean_obs: list[ExtractedObservation] = []
    for obs in result.observations:
        if _is_inference_language(obs.text) or observation_is_forbidden_inference(obs.text):
            result.inferences.append(
                ExtractedInference(
                    text=obs.text,
                    author_type=obs.observer_type if hasattr(obs, "observer_type") else "AI",  # type: ignore[arg-type]
                    confidence=min(obs.confidence, 0.45),
                    source_roles=["demoted-from-observation"],
                )
            )
            continue
        if any(p in obs.text.lower() for p in FORBIDDEN_OBSERVATION_PATTERNS):
            continue
        clean_obs.append(obs)
    result.observations = clean_obs

    # Attributed company/founder speech must stay Claims
    still_obs = []
    for obs in result.observations:
        low = obs.text.lower()
        if any(p in low for p in ("the company says", "the founder says", "claims that", "we announce")):
            result.claims.append(
                ExtractedClaim(
                    text=obs.text,
                    claim_type=ClaimType.TECHNICAL,
                    attributed_to="speaker",
                    confidence_extraction=0.6,
                )
            )
            continue
        still_obs.append(obs)
    result.observations = still_obs

    # Normalize inference author_type if validator stuffed a string enum mismatch
    fixed_inf = []
    from app.enums import AuthorType

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
