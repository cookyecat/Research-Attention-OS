"""Phase17.3-KS canonical Semantic Coordinate contracts.

A coordinate is a reusable semantic state dimension, not an Event-local slot
and not a raw fact. Its identity is primitive family + canonical state question.
"""
from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.services.semantic_primitives import (
    PrimitiveFamily,
    referent_scope_for_family,
)


def normalize_semantic_text(value: str) -> str:
    return " ".join(str(value).strip().split())


def make_coordinate_id(
    primitive_family: PrimitiveFamily,
    state_question: str,
) -> str:
    identity = (
        f"{primitive_family}\n"
        f"{normalize_semantic_text(state_question).casefold()}"
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    return f"sc_{digest}"
class SemanticCoordinate(BaseModel):
    coordinate_id: str = Field(min_length=8)
    primitive_family: PrimitiveFamily
    state_question: str = Field(min_length=1, max_length=1000)
    coordinate_label: str | None = Field(default=None, max_length=200)
    value_type: str = "unknown"
    temporal_behavior: str = "mutable"
    aliases: tuple[str, ...] = ()
    domain_hints: tuple[str, ...] = ()
    entity_type_hints: tuple[str, ...] = ()
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @model_validator(mode="before")
    @classmethod
    def populate_coordinate_id(cls, data):
        if isinstance(data, dict) and not data.get("coordinate_id"):
            family = data.get("primitive_family")
            question = data.get("state_question")
            if family and question:
                data = dict(data)
                data["coordinate_id"] = make_coordinate_id(family, question)
        return data

    @model_validator(mode="after")
    def normalize_and_validate_identity(self):
        question = normalize_semantic_text(self.state_question)
        object.__setattr__(self, "state_question", question)
        expected = make_coordinate_id(self.primitive_family, question)
        if self.coordinate_id != expected:
            raise ValueError(
                "coordinate_id must be derived only from primitive_family "
                "and canonical state_question"
            )

        label = (
            normalize_semantic_text(self.coordinate_label)
            if self.coordinate_label
            else None
        )
        object.__setattr__(self, "coordinate_label", label)
        object.__setattr__(
            self,
            "aliases",
            tuple(sorted({
                normalize_semantic_text(v)
                for v in self.aliases
                if normalize_semantic_text(v)
            }, key=str.casefold)),
        )
        for field_name in ("domain_hints", "entity_type_hints"):
            values = getattr(self, field_name)
            object.__setattr__(
                self,
                field_name,
                tuple(sorted({
                    normalize_semantic_text(v)
                    for v in values
                    if normalize_semantic_text(v)
                }, key=str.casefold)),
            )
        return self
    @property
    def referent_scope(self):
        return referent_scope_for_family(self.primitive_family)

    def identity_signature(self) -> tuple[str, str]:
        return (
            self.primitive_family,
            normalize_semantic_text(self.state_question).casefold(),
        )

    def embedding_text(self) -> str:
        """Stable semantic retrieval text; contextual hints are excluded."""
        parts = [
            f"primitive_family: {self.primitive_family}",
            f"state_question: {self.state_question}",
            f"value_type: {self.value_type}",
            f"temporal_behavior: {self.temporal_behavior}",
        ]
        if self.coordinate_label:
            parts.append(f"coordinate_label: {self.coordinate_label}")
        if self.aliases:
            parts.append(f"aliases: {', '.join(self.aliases)}")
        return "; ".join(parts)


CoordinateQueryKind = Literal["PROPOSITION", "STATE_QUESTION"]


class CoordinateRetrievalQuery(BaseModel):
    """Typed query for locating candidate semantic coordinates."""

    primitive_family: PrimitiveFamily
    text: str = Field(min_length=1, max_length=6000)
    query_kind: CoordinateQueryKind = "PROPOSITION"
    exclude_coordinate_id: str | None = None

    @model_validator(mode="after")
    def normalize_query(self):
        object.__setattr__(self, "text", normalize_semantic_text(self.text))
        return self

    @classmethod
    def from_coordinate(cls, coordinate: SemanticCoordinate):
        return cls(
            primitive_family=coordinate.primitive_family,
            text=coordinate.state_question,
            query_kind="STATE_QUESTION",
            exclude_coordinate_id=coordinate.coordinate_id,
        )

    def embedding_text(self) -> str:
        field = (
            "proposition"
            if self.query_kind == "PROPOSITION"
            else "state_coordinate"
        )
        return (
            f"primitive_family: {self.primitive_family}; "
            f"{field}: {self.text}"
        )


class CoordinateProposal(BaseModel):
    proposition: str
    candidates: tuple[SemanticCoordinate, ...]


class CoordinateCandidate(BaseModel):
    coordinate: SemanticCoordinate
    semantic_similarity: float = Field(ge=-1.0, le=1.0)
    embedding_model: str | None = None


CoordinateCompatibility = Literal[
    "EXACT_MATCH",
    "CANDIDATE",
    "TYPE_MISMATCH",
]


class CoordinateMatch(BaseModel):
    left_id: str
    right_id: str
    compatibility: CoordinateCompatibility
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized retrieval signal; not a merge/reuse probability.",
    )
    semantic_similarity: float = Field(ge=-1.0, le=1.0)
    value_type_compatible: bool | None = None
    temporal_behavior_compatible: bool | None = None
    requires_semantic_resolution: bool
    rationale: str


class CoordinateRelation(BaseModel):
    source_id: str
    target_id: str
    relation: Literal["MERGE", "SPLIT", "ALIAS", "REKEY", "RETIRE"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str | None = None
