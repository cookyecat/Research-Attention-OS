"""Semantic Extraction Batch v0.2.

Development revision after the first RS02/RS09 source-level extraction.
Key change: one non-event semantic unit may cite multiple source supports,
allowing semantic aggregation instead of one-comment-per-unit transcription.

Contains semantic evidence only; no D/S/P labels or Attention Actions.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from eval.live.semantic_evidence_frame_v0_1 import (
    Confidence,
    EpistemicStatus,
    SemanticEvidenceFrameV0_1,
)

BATCH_INTERFACE_VERSION = "semantic-evidence-batch-v0.2"


class SourceSupportV0_2(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(min_length=1, max_length=300)
    support_pointer: str = Field(min_length=1, max_length=1000)
    support_excerpt: str = Field(min_length=1, max_length=600)


class NonEventSemanticUnitV0_2(BaseModel):
    """Non-event epistemic content with one or more source-grounding supports."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    unit_id: str = Field(min_length=1, max_length=300)
    statement: str = Field(min_length=1, max_length=4000)
    epistemic_status: EpistemicStatus
    # Confidence concerns source-grounded extraction/attribution, not claim truth.
    confidence: Confidence
    supports: list[SourceSupportV0_2] = Field(min_length=1, max_length=8)
    note: str = Field(default="", max_length=2000)


class SemanticExtractionBatchV0_2(BaseModel):
    """Source-level Semantic Sensor output with bounded semantic compression."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    interface_version: Literal["semantic-evidence-batch-v0.2"] = BATCH_INTERFACE_VERSION
    batch_id: str = Field(min_length=1, max_length=300)
    source_ids: list[str] = Field(min_length=1, max_length=100)
    event_frames: list[SemanticEvidenceFrameV0_1] = Field(default_factory=list, max_length=8)
    non_event_units: list[NonEventSemanticUnitV0_2] = Field(default_factory=list, max_length=20)
    notes: list[str] = Field(default_factory=list, max_length=20)

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

        missing_support_sources = sorted(
            {
                support.source_id
                for unit in self.non_event_units
                for support in unit.supports
                if support.source_id not in allowed_sources
            }
        )
        if missing_support_sources:
            raise ValueError(
                f"non-event supports reference source(s) outside batch: {missing_support_sources}"
            )

        return self
