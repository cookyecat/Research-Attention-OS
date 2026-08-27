"""Authoritative Pydantic v2 schemas for model structured output.

Structural validation is a separate layer from the epistemic constitution validator.
Malformed items fail the whole response; they are never silently dropped.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from app.enums import (
    AttributionType,
    ClaimType,
    KernelNodeType,
    ObservationType,
    ObserverType,
    Stance,
    Strength,
)

# Kernel node statuses actually used in seed, bootstrap, patches, and the active-kernel filter.
# Not a new state machine — a closed set of values already present in the codebase.
KernelNodeStatus = Literal["ACTIVE", "OPEN", "CONTESTED", "DEPRECATED", "ABANDONED", "COMPLETED"]


class StrictModel(BaseModel):
    """Fail-closed LLM structured output. Unexpected fields are rejected, not dropped."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _require_string_list(value: Any) -> Any:
    """Reject object/number coercion. These fields must already be arrays of strings."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("must be an array of strings")
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise ValueError(f"must be an array of strings; index {i} is {type(item).__name__}, not str")
    return value


StringList = Annotated[list[str], BeforeValidator(_require_string_list)]


class ClaimItem(StrictModel):
    text: str = Field(min_length=1)
    claim_type: ClaimType
    attributed_to: str | None = None
    attribution_type: AttributionType = AttributionType.UNKNOWN
    temporal_status: Literal["CURRENT", "FUTURE"] = "CURRENT"
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    source_span: str | None = None
    source_start_offset: int | None = None
    source_end_offset: int | None = None
    chunk_id: str | None = None


class ObservationItem(StrictModel):
    text: str = Field(min_length=1)
    observer: ObserverType
    observation_type: ObservationType
    confidence: float = Field(ge=0.0, le=1.0)
    source_span: str | None = None
    source_start_offset: int | None = None
    source_end_offset: int | None = None
    chunk_id: str | None = None


class InferenceItem(StrictModel):
    text: str = Field(min_length=1)
    derived_from: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractionResponse(StrictModel):
    claims: list[ClaimItem]
    observations: list[ObservationItem]
    inferences: list[InferenceItem]
    event_title: str | None = None
    event_summary: str | None = None
    current_facts: StringList = Field(default_factory=list)
    future_plans: StringList = Field(default_factory=list)
    technical_claims: StringList = Field(default_factory=list)
    promotional_framing: StringList = Field(default_factory=list)
    marketing_heavy: bool = False


class KernelMatchItem(StrictModel):
    kernel_node_id: UUID
    relevance_type: Literal["TOPIC", "STRUCTURAL", "DECISION", "BOTTLENECK", "EVIDENCE"]
    score: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)


class KernelMatchResponse(StrictModel):
    matches: list[KernelMatchItem]


class EvidenceLinkItem(StrictModel):
    source_role: Literal["OBSERVATION", "CLAIM", "INFERENCE"]
    source_index: int = Field(ge=0)
    target_role: Literal["CLAIM", "OBSERVATION", "INFERENCE"]
    target_index: int = Field(ge=0)
    stance: Stance
    strength: Strength
    confidence: float = Field(ge=0.0, le=1.0)
    scope: str | None = None


class EvidenceReasoningResponse(StrictModel):
    links: list[EvidenceLinkItem] = Field(default_factory=list)


class CognitiveEffectItem(StrictModel):
    target_kernel_node_id: UUID | None = None
    operation: Literal["REINFORCE", "CHALLENGE", "OPEN_NEW"]
    change_magnitude: float = Field(ge=0.0, le=1.0)
    epistemic_strength: float = Field(ge=0.0, le=1.0)
    target_importance: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)
    exploration_candidate: bool = False


class CognitiveImpactResponse(StrictModel):
    effects: list[CognitiveEffectItem]
    attention_cost: float = Field(ge=0.0, le=100.0)
    exploration_candidate: bool = False
    evidence_maturity: float = Field(ge=0.0, le=1.0)
    threatens_active_work: bool = False
    marketing_heavy: bool = False
    high_quality_technical: bool = False
    foundational_paper: bool = False


class AffectedKernelNode(StrictModel):
    id: str
    impact: Literal["SUPPORT", "WEAKEN", "CONTEST", "REFINE", "REFRAME", "OPEN_NEW_QUESTION", "DECISION_REVIEW"] | None = None


class ModelDeltaResponse(StrictModel):
    summary: str = Field(min_length=1)
    affected_kernel_nodes: list[AffectedKernelNode] = Field(default_factory=list)
    distinctions: list[str] = Field(default_factory=list)
    new_questions: list[str] = Field(default_factory=list)
    possible_hypotheses: list[str] = Field(default_factory=list)
    decision_implications: list[str] = Field(default_factory=list)
    epistemic_risk: str = ""
    evidence_maturity: float = Field(default=0.4, ge=0.0, le=1.0)
    admission_allowed: bool = False
    rationale: str = ""
    what_could_change: list[str] = Field(default_factory=list)


class BootstrapProposal(StrictModel):
    target_object_type: KernelNodeType | Literal["GOAL", "PROJECT", "QUESTION", "BELIEF", "MODEL", "BOTTLENECK", "DECISION"]
    title: str = Field(min_length=1)
    status: KernelNodeStatus = "ACTIVE"
    payload: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = Field(min_length=1)


class BootstrapResponse(StrictModel):
    proposals: list[BootstrapProposal]


# Kept for prompt documentation / older callers that still mention dict schemas.
EXTRACT_SCHEMA = ExtractionResponse.model_json_schema()
MATCH_SCHEMA = KernelMatchResponse.model_json_schema()
DELTA_SCHEMA = ModelDeltaResponse.model_json_schema()
