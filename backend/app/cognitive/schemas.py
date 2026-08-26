"""Authoritative Pydantic v2 schemas for model structured output.

Structural validation is a separate layer from the epistemic constitution validator.
Malformed items fail the whole response; they are never silently dropped.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import (
    AttributionType,
    ClaimType,
    KernelNodeType,
    ObservationType,
    ObserverType,
    Stance,
    Strength,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class Score01(BaseModel):
    model_config = ConfigDict(extra="ignore")


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
    current_facts: list[str] = Field(default_factory=list)
    future_plans: list[str] = Field(default_factory=list)
    technical_claims: list[str] = Field(default_factory=list)
    promotional_framing: list[str] = Field(default_factory=list)
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


class SchedulerJudgmentResponse(StrictModel):
    topic_relevance: float = Field(ge=0.0, le=1.0)
    structural_relevance: float = Field(ge=0.0, le=1.0)
    decision_relevance: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    credibility: float = Field(ge=0.0, le=1.0)
    kernel_delta: float = Field(ge=0.0, le=1.0)
    bottleneck_alignment: float = Field(ge=0.0, le=1.0)
    disagreement: float = Field(ge=0.0, le=1.0)
    actionability: float = Field(ge=0.0, le=1.0)
    temporal_value: float = Field(ge=0.0, le=1.0)
    cognitive_cost: float = Field(ge=0.0, le=100.0)
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
    affected_kernel_nodes: list[Any] = Field(default_factory=list)
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
    status: str = "ACTIVE"
    payload: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = Field(min_length=1)


class BootstrapResponse(StrictModel):
    proposals: list[BootstrapProposal]


# Kept for prompt documentation / older callers that still mention dict schemas.
EXTRACT_SCHEMA = ExtractionResponse.model_json_schema()
MATCH_SCHEMA = KernelMatchResponse.model_json_schema()
DELTA_SCHEMA = ModelDeltaResponse.model_json_schema()
