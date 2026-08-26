"""Deterministic gates for evidence reasoning and conflict flags.

Heavy Evidence LLM is for evidential structure (observations vs claims,
independent sources, contradictions), not for the mere presence of AI inferences.
"""

from __future__ import annotations

from app.enums import Stance
from app.services.extraction import CONTRADICTION_PAIRS, ExtractionResult

SKIP_NO_CLAIMS = "no_claims"
SKIP_SINGLE_SOURCE_NO_STRUCTURE = "single_source_no_observation_no_contradiction"
RUN_OBSERVATIONS_VS_CLAIMS = "observations_vs_claims"
RUN_INDEPENDENT_SOURCES = "independent_sources"
RUN_CONFLICTING_CLAIMS = "conflicting_claims"
RUN_VERIFICATION_CASES = "verification_cases"


def _stance_value(stance) -> str:
    if hasattr(stance, "value"):
        return str(stance.value).upper()
    return str(stance).upper()


def has_conflict_stance(extraction: ExtractionResult) -> bool:
    return any(_stance_value(item.stance) in {Stance.WEAKENS.value, Stance.REFUTES.value} for item in extraction.evidence)


def has_lexical_contradiction(extraction: ExtractionResult, *, independent_source_count: int = 1) -> bool:
    claim_blob = " ".join(c.text.lower() for c in extraction.claims)
    obs_blob = " ".join(o.text.lower() for o in extraction.observations)
    for pos, neg in CONTRADICTION_PAIRS:
        pos_in_claims = any(p in claim_blob for p in pos)
        if not pos_in_claims:
            continue
        if any(n in obs_blob for n in neg):
            return True
        if independent_source_count >= 2 and any(n in claim_blob for n in neg):
            return True
    return False


def evidence_conflict_flags(
    extraction: ExtractionResult,
    *,
    independent_source_count: int = 1,
) -> tuple[bool, bool]:
    """Return (evidence_links_present, sources_conflict).

    sources_conflict is true only when evidence WEAKENS/REFUTES a claim,
    or independent sources lexically conflict. SUPPORTS-only links are not conflict.
    """
    links_present = bool(extraction.evidence)
    conflict = has_conflict_stance(extraction) or has_lexical_contradiction(
        extraction, independent_source_count=independent_source_count
    )
    return links_present, conflict


def should_run_heavy_evidence(
    extraction: ExtractionResult,
    *,
    independent_source_count: int = 1,
) -> tuple[bool, str]:
    """Whether the expensive reasoning-enabled evidence stage should run."""
    if not extraction.claims:
        return False, SKIP_NO_CLAIMS
    if extraction.observations:
        return True, RUN_OBSERVATIONS_VS_CLAIMS
    if independent_source_count >= 2:
        return True, RUN_INDEPENDENT_SOURCES
    if has_conflict_stance(extraction):
        return True, RUN_VERIFICATION_CASES
    if has_lexical_contradiction(extraction, independent_source_count=independent_source_count):
        return True, RUN_CONFLICTING_CLAIMS
    return False, SKIP_SINGLE_SOURCE_NO_STRUCTURE
