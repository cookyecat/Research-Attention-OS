"""Phase17.3-KS-E deterministic candidate-adjudication planning.

This module does not call an LLM and does not mutate EventState. It converts
typed propositions + Event-local CurrentSlots into a bounded candidate plan.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .models import CoordinateRetrievalQuery, SemanticCoordinate
from .retrieval import CoordinateCandidateRetriever


class CandidateSlotScore(BaseModel):
    slot_id: str
    semantic_similarity: float = Field(ge=-1.0, le=1.0)


class PropositionCandidatePlan(BaseModel):
    proposition_id: str
    primitive_family: str
    candidate_slots: tuple[CandidateSlotScore, ...]
    same_family_slot_ids: tuple[str, ...]
    hidden_same_family_slot_ids: tuple[str, ...]

    @property
    def candidate_slot_ids(self) -> tuple[str, ...]:
        return tuple(row.slot_id for row in self.candidate_slots)

    @property
    def create_requires_expansion(self) -> bool:
        return bool(self.hidden_same_family_slot_ids)


class CandidateAdjudicationPlan(BaseModel):
    top_k: int = Field(ge=1)
    propositions: tuple[PropositionCandidatePlan, ...]
    visible_slot_ids: tuple[str, ...]
    total_slot_count: int
    visible_slot_count: int

    @property
    def compression_ratio(self) -> float:
        if self.total_slot_count == 0:
            return 1.0
        return self.visible_slot_count / self.total_slot_count
def _field(value, name: str):
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _slot_coordinate(slot) -> SemanticCoordinate | None:
    slot_id = _field(slot, "slot_id") or _field(slot, "slot_key")
    family = _field(slot, "primitive_family")
    question = _field(slot, "state_question")
    if not slot_id or not family or not question:
        return None
    return SemanticCoordinate(
        primitive_family=family,
        state_question=question,
        coordinate_label=_field(slot, "slot_label"),
        temporal_behavior="mutable",
    )


def build_candidate_adjudication_plan(
    *,
    propositions,
    current_slots,
    top_k: int = 2,
    retriever: CoordinateCandidateRetriever | None = None,
) -> CandidateAdjudicationPlan:
    if top_k < 1:
        raise ValueError("top_k must be >= 1")

    slot_entries = []
    for slot in current_slots:
        coordinate = _slot_coordinate(slot)
        if coordinate is not None:
            slot_id = _field(slot, "slot_id") or _field(slot, "slot_key")
            slot_entries.append((str(slot_id), coordinate))

    engine = retriever or CoordinateCandidateRetriever()
    proposition_plans = []
    visible_slot_ids = set()
    for index, proposition in enumerate(propositions, start=1):
        proposition_id = (
            _field(proposition, "proposition_id")
            or _field(proposition, "proposition_key")
            or f"P{index:03d}"
        )
        family = _field(proposition, "primitive_family")
        statement = (
            _field(proposition, "statement")
            or _field(proposition, "proposition")
            or _field(proposition, "text")
        )
        if not family or not statement:
            raise ValueError(
                "candidate planning requires proposition_id, primitive_family, "
                "and statement/text"
            )

        same_family = [
            (slot_id, coordinate)
            for slot_id, coordinate in slot_entries
            if coordinate.primitive_family == family
        ]
        query = CoordinateRetrievalQuery(
            primitive_family=family,
            text=statement,
            query_kind="PROPOSITION",
        )
        rows = engine.retrieve(
            query,
            [coordinate for _, coordinate in same_family],
            top_k=min(top_k, len(same_family)) if same_family else top_k,
        )

        ids_by_coordinate: dict[str, list[str]] = {}
        for slot_id, coordinate in same_family:
            ids_by_coordinate.setdefault(
                coordinate.coordinate_id,
                [],
            ).append(slot_id)

        candidate_slots = []
        used_slot_ids = set()
        for row in rows:
            for slot_id in ids_by_coordinate.get(
                row.coordinate.coordinate_id,
                [],
            ):
                if slot_id in used_slot_ids:
                    continue
                used_slot_ids.add(slot_id)
                candidate_slots.append(
                    CandidateSlotScore(
                        slot_id=slot_id,
                        semantic_similarity=row.semantic_similarity,
                    )
                )
                visible_slot_ids.add(slot_id)
        same_family_ids = tuple(
            sorted(slot_id for slot_id, _ in same_family)
        )
        hidden_ids = tuple(
            slot_id
            for slot_id in same_family_ids
            if slot_id not in used_slot_ids
        )
        proposition_plans.append(
            PropositionCandidatePlan(
                proposition_id=str(proposition_id),
                primitive_family=family,
                candidate_slots=tuple(candidate_slots),
                same_family_slot_ids=same_family_ids,
                hidden_same_family_slot_ids=hidden_ids,
            )
        )

    visible = tuple(sorted(visible_slot_ids))
    return CandidateAdjudicationPlan(
        top_k=top_k,
        propositions=tuple(proposition_plans),
        visible_slot_ids=visible,
        total_slot_count=len(slot_entries),
        visible_slot_count=len(visible),
    )
