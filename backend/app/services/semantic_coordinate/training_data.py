"""Phase17.3-KS-F versioned Direct-Answer learning-data contracts."""
from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.services.semantic_coordinate.models import normalize_semantic_text
from app.services.semantic_primitives import (
    PrimitiveFamily,
    ReferentScope,
    referent_scope_for_family,
)

DIRECT_ANSWER_TRAINING_CONTRACT = (
    "semantic-direct-answer-training-example-v0.1"
)

TrainingLabel = Literal["DIRECT", "NOT_DIRECT"]
LabelAuthority = Literal[
    "HUMAN_REVIEWED",
    "LLM_CONSENSUS",
    "HISTORICAL_PROXY",
    "UNREVIEWED",
]


def make_training_example_id(
    *,
    event_group: str,
    primitive_family: PrimitiveFamily,
    referent_scope: ReferentScope,
    proposition: str,
    state_question: str,
) -> str:
    identity = "\n".join([
        normalize_semantic_text(event_group).casefold(),
        primitive_family,
        referent_scope,
        normalize_semantic_text(proposition).casefold(),
        normalize_semantic_text(state_question).casefold(),
    ])
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    return f"da_{digest}"


class DirectAnswerTrainingExampleV01(BaseModel):
    contract: str = DIRECT_ANSWER_TRAINING_CONTRACT
    example_id: str | None = None

    event_group: str = Field(min_length=1, max_length=300)
    domain_group: str = Field(min_length=1, max_length=200)
    split_group: str = Field(min_length=1, max_length=300)

    ordinal: int | None = Field(default=None, ge=1)
    proposition_key: str | None = None
    slot_key: str | None = None

    proposition: str = Field(min_length=1, max_length=6000)
    primitive_family: PrimitiveFamily
    referent_scope: ReferentScope
    state_question: str = Field(min_length=1, max_length=1000)
    slot_label: str | None = Field(default=None, max_length=200)

    label: TrainingLabel
    label_authority: LabelAuthority
    hard_negative: bool = False
    note: str | None = Field(default=None, max_length=1000)

    provenance_artifact: str = Field(min_length=1, max_length=1000)
    source_contract: str | None = Field(default=None, max_length=200)

    @model_validator(mode="before")
    @classmethod
    def populate_id(cls, data):
        if isinstance(data, dict) and not data.get("example_id"):
            required = (
                "event_group",
                "primitive_family",
                "referent_scope",
                "proposition",
                "state_question",
            )
            if all(data.get(key) for key in required):
                data = dict(data)
                data["example_id"] = make_training_example_id(
                    event_group=data["event_group"],
                    primitive_family=data["primitive_family"],
                    referent_scope=data["referent_scope"],
                    proposition=data["proposition"],
                    state_question=data["state_question"],
                )
        return data

    @model_validator(mode="after")
    def normalize_and_validate(self):
        for field_name in (
            "event_group",
            "domain_group",
            "split_group",
            "proposition",
            "state_question",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_semantic_text(getattr(self, field_name)),
            )

        if self.slot_label:
            object.__setattr__(
                self,
                "slot_label",
                normalize_semantic_text(self.slot_label),
            )
        if self.note:
            object.__setattr__(
                self,
                "note",
                normalize_semantic_text(self.note),
            )

        expected_scope = referent_scope_for_family(self.primitive_family)
        if self.referent_scope != expected_scope:
            raise ValueError(
                "referent_scope must match frozen primitive-family semantics"
            )

        expected_id = make_training_example_id(
            event_group=self.event_group,
            primitive_family=self.primitive_family,
            referent_scope=self.referent_scope,
            proposition=self.proposition,
            state_question=self.state_question,
        )
        if self.example_id != expected_id:
            raise ValueError(
                "example_id must be derived from semantic pair identity"
            )

        if self.label == "DIRECT" and self.hard_negative:
            raise ValueError("DIRECT example cannot be marked hard_negative")
        return self


class DirectAnswerDatasetV01(BaseModel):
    contract: str = "semantic-direct-answer-dataset-v0.1"
    dataset_id: str
    status: Literal["DEVELOPMENT_ONLY", "EVAL_READY", "TRAIN_READY"]
    examples: tuple[DirectAnswerTrainingExampleV01, ...]
    review_queue: tuple[dict, ...] = ()

    @model_validator(mode="after")
    def validate_dataset(self):
        ids = [row.example_id for row in self.examples]
        if len(ids) != len(set(ids)):
            raise ValueError("dataset contains duplicate example_id values")
        if not self.examples:
            raise ValueError("dataset must contain at least one example")
        return self

    def label_counts(self) -> dict[str, int]:
        counts = {"DIRECT": 0, "NOT_DIRECT": 0}
        for row in self.examples:
            counts[row.label] += 1
        return counts

    def authority_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in self.examples:
            counts[row.label_authority] = (
                counts.get(row.label_authority, 0) + 1
            )
        return counts

    def event_groups(self) -> tuple[str, ...]:
        return tuple(sorted({row.event_group for row in self.examples}))
