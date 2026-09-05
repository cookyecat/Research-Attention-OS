from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SourceCreate(BaseModel):
    source_type: str = "TEXT"
    title: str | None = None
    content_text: str | None = None
    url: str | None = None
    publisher: str | None = None


class SourceOut(BaseModel):
    id: UUID
    source_type: str
    title: str | None
    canonical_url: str | None
    content_text: str | None
    ingested_at: datetime
    fingerprint: str
    content_hash: str | None
    ingestion_method: str
    raw_metadata: dict
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}


class RuntimeContextIn(BaseModel):
    current_task: str | None = None
    session_topic: str | None = None
    available_attention_minutes: int | None = None
    interruptibility: str | None = "MEDIUM"
    cognitive_capacity: str | None = "NORMAL"
    deadline_at: datetime | None = None


class ExtractIn(BaseModel):
    source_id: UUID
    extra_source_ids: list[UUID] = Field(default_factory=list)
    # Explicit caller override. Ordinary analyze/plan paths must not use this to
    # bypass ExpectedOutput.WATCH authorization.
    persist_suggested_watches: bool = False


class PlanIn(BaseModel):
    source_id: UUID
    extra_source_ids: list[UUID] = Field(default_factory=list)
    runtime_context: RuntimeContextIn | None = None


class PatchModifyIn(BaseModel):
    modified_state: dict


class WatchCreate(BaseModel):
    target_type: str
    target_ref: str
    created_reason: str
    kernel_target_ids: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)


class KernelNodeCreate(BaseModel):
    node_type: str
    title: str | None = None
    status: str = "ACTIVE"
    payload: dict = Field(default_factory=dict)


class CognitiveUpdateFeedbackIn(BaseModel):
    """Partial Update patch. Omitted fields keep the system value; explicit null is a value."""

    operation: str | None = None
    target_node_id: UUID | None = None


class AttentionFeedbackIn(BaseModel):
    """Confirm or correct the public contract. Omitted fields ≠ explicit null.

    `update: null` means no cognitive update. Omitting `update` keeps the system Update.
    """

    kind: str
    disposition: str | None = None
    update: CognitiveUpdateFeedbackIn | None = None
    delta_content: str | None = None


class SourceEdgeCreate(BaseModel):
    source_id: UUID
    target_id: UUID
    relationship: str
    confidence: float = 1.0
    evidence: str | None = None


class ImpactReplayIn(BaseModel):
    """Override a single Impact runtime/model variable for a frozen replay."""

    provider: str | None = None
    model: str | None = None
    thinking: str | None = None
    reasoning_effort: str | None = None
    timeout: float | None = None
    label: str | None = None


class ImpactReplayAbIn(BaseModel):
    a: ImpactReplayIn = Field(default_factory=ImpactReplayIn)
    b: ImpactReplayIn = Field(default_factory=ImpactReplayIn)
