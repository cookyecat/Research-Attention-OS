"""Semantic Evidence Frame v0.1 — sensor-front-end research interface.

This module represents extracted semantic evidence only.
It must not contain D/S/P labels or Attention Actions.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

INTERFACE_VERSION = "semantic-evidence-frame-v0.1"

EpistemicStatus = Literal["SOURCE_CLAIM", "DIRECT_OBSERVATION", "EXTRACTOR_INFERENCE"]
Confidence = Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
TemporalStatus = Literal[
    "PROPOSED",
    "ANNOUNCED",
    "ENACTED",
    "EFFECTIVE",
    "OBSERVED",
    "HISTORICAL",
    "UNKNOWN",
]
UncertaintyKind = Literal[
    "UNKNOWN",
    "CONFLICTING_SOURCES",
    "UNCERTAIN_SCOPE",
    "UNCERTAIN_ACTOR_ROLE",
    "INSUFFICIENT_SUPPORT",
]


class EventV0_1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_id: str = Field(min_length=1, max_length=300)
    as_of: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=4000)


class SourceV0_1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(min_length=1, max_length=300)
    source_type: str = Field(default="unknown", max_length=200)
    published_at: str = Field(default="unknown", max_length=100)
    locator: str = Field(min_length=1, max_length=2000)


class EvidenceV0_1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    evidence_id: str = Field(min_length=1, max_length=300)
    source_id: str = Field(min_length=1, max_length=300)
    support_pointer: str = Field(min_length=1, max_length=1000)
    support_excerpt: str = Field(default="", max_length=1200)
    epistemic_status: EpistemicStatus
    confidence: Confidence = "UNKNOWN"


class SubstantiveActorObjectV0_1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=1000)
    role: str = Field(min_length=1, max_length=500)
    substantive_basis: str = Field(min_length=1, max_length=2000)
    support_ids: list[str] = Field(min_length=1, max_length=50)


class ActionChangeV0_1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Field(min_length=1, max_length=3000)
    temporal_status: TemporalStatus = "UNKNOWN"
    support_ids: list[str] = Field(min_length=1, max_length=50)


class AffectedSystemPopulationV0_1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Field(min_length=1, max_length=2500)
    reference_scope: str = Field(default="unknown", max_length=1000)
    support_ids: list[str] = Field(min_length=1, max_length=50)


class TemporalContextV0_1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_time: str = Field(default="unknown", max_length=200)
    effective_time: str = Field(default="unknown", max_length=200)
    as_of: str = Field(min_length=1, max_length=100)
    notes: str = Field(default="", max_length=2000)


class UncertaintyV0_1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    field: str = Field(min_length=1, max_length=500)
    kind: UncertaintyKind
    note: str = Field(min_length=1, max_length=2000)
    support_ids: list[str] = Field(default_factory=list, max_length=50)


class SemanticEvidenceFrameV0_1(BaseModel):
    """Minimal provenance-preserving sensor reading for downstream RAOS estimators."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    interface_version: Literal["semantic-evidence-frame-v0.1"] = INTERFACE_VERSION
    event: EventV0_1
    sources: list[SourceV0_1] = Field(min_length=1, max_length=100)
    evidence: list[EvidenceV0_1] = Field(min_length=1, max_length=500)
    substantive_actors_objects: list[SubstantiveActorObjectV0_1] = Field(default_factory=list, max_length=100)
    actions_changes: list[ActionChangeV0_1] = Field(default_factory=list, max_length=200)
    affected_systems_populations: list[AffectedSystemPopulationV0_1] = Field(default_factory=list, max_length=200)
    temporal_context: TemporalContextV0_1
    uncertainties: list[UncertaintyV0_1] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_provenance_graph(self):
        source_ids = [s.source_id for s in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("duplicate source_id")

        evidence_ids = [e.evidence_id for e in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("duplicate evidence_id")

        source_set = set(source_ids)
        evidence_set = set(evidence_ids)

        missing_sources = sorted({e.source_id for e in self.evidence if e.source_id not in source_set})
        if missing_sources:
            raise ValueError(f"evidence references missing source_id(s): {missing_sources}")

        supported_objects = [
            *(self.substantive_actors_objects or []),
            *(self.actions_changes or []),
            *(self.affected_systems_populations or []),
        ]
        for obj in supported_objects:
            missing = sorted(set(obj.support_ids) - evidence_set)
            if missing:
                raise ValueError(f"semantic object references missing evidence_id(s): {missing}")

        for uncertainty in self.uncertainties:
            missing = sorted(set(uncertainty.support_ids) - evidence_set)
            if missing:
                raise ValueError(f"uncertainty references missing evidence_id(s): {missing}")

        if self.temporal_context.as_of != self.event.as_of:
            raise ValueError("temporal_context.as_of must equal event.as_of")

        return self
