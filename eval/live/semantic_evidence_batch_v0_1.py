"""Semantic Extraction Batch v0.1.

A raw source is not assumed to correspond to exactly one event.
This source-level container routes event-like semantic units into one or more
SemanticEvidenceFrame objects while preserving non-event epistemic content for
RAOS's cognitive path.

It contains no D/S/P labels or Attention Actions.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from eval.live.semantic_evidence_frame_v0_1 import (
    Confidence,
    EpistemicStatus,
    SemanticEvidenceFrameV0_1,
)

BATCH_INTERFACE_VERSION = "semantic-evidence-batch-v0.1"


class NonEventSemanticUnitV0_1(BaseModel):
    """Epistemic content that should not be forced into an event frame."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    unit_id: str = Field(min_length=1, max_length=300)
    statement: str = Field(min_length=1, max_length=4000)
    epistemic_status: EpistemicStatus
    confidence: Confidence = "UNKNOWN"
    source_id: str = Field(min_length=1, max_length=300)
    support_pointer: str = Field(min_length=1, max_length=1000)
    support_excerpt: str = Field(default="", max_length=1200)
    note: str = Field(default="", max_length=2000)


class SemanticExtractionBatchV0_1(BaseModel):
    """Source-level output of the Semantic Sensor Front-End."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    interface_version: Literal["semantic-evidence-batch-v0.1"] = BATCH_INTERFACE_VERSION
    batch_id: str = Field(min_length=1, max_length=300)
    source_ids: list[str] = Field(min_length=1, max_length=100)
    event_frames: list[SemanticEvidenceFrameV0_1] = Field(default_factory=list, max_length=100)
    non_event_units: list[NonEventSemanticUnitV0_1] = Field(default_factory=list, max_length=500)
    notes: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_batch(self):
        if len(self.source_ids) != len(set(self.source_ids)):
            raise ValueError("duplicate source_id in batch")

        allowed_sources = set(self.source_ids)
        event_ids: list[str] = []

        for frame in self.event_frames:
            event_ids.append(frame.event.event_id)
            frame_source_ids = {source.source_id for source in frame.sources}
            if not frame_source_ids.issubset(allowed_sources):
                missing = sorted(frame_source_ids - allowed_sources)
                raise ValueError(f"event frame references source(s) outside batch: {missing}")

        if len(event_ids) != len(set(event_ids)):
            raise ValueError("duplicate event_id across event_frames")

        unit_ids = [u.unit_id for u in self.non_event_units]
        if len(unit_ids) != len(set(unit_ids)):
            raise ValueError("duplicate unit_id across non_event_units")

        missing_unit_sources = sorted(
            {u.source_id for u in self.non_event_units if u.source_id not in allowed_sources}
        )
        if missing_unit_sources:
            raise ValueError(
                f"non-event units reference source(s) outside batch: {missing_unit_sources}"
            )

        return self
