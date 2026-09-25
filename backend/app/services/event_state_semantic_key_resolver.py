"""Phase17.3-KS semantic key-resolution boundary.

Two deliberately separate operations live here.

1. resolve_exact_coordinate is a deterministic compatibility shortcut for
   already-normalized coordinate proposals carrying a state_question.
2. retrieve_key_candidates accepts the real WorldProposition boundary
   (statement + primitive_family) and returns Event-local Top-K slot candidates.

Candidate retrieval is not REUSE/CREATE authority.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.services.semantic_coordinate.models import (
    CoordinateRetrievalQuery,
    SemanticCoordinate,
    normalize_semantic_text,
)
from app.services.semantic_coordinate.retrieval import CoordinateCandidateRetriever

ResolutionDecision = Literal["REUSE", "CREATE"]


class SemanticKeyResolution(BaseModel):
    decision: ResolutionDecision
    slot_key: str | None = None
    coordinate: SemanticCoordinate
    rationale: str | None = None


class EventSlotCandidate(BaseModel):
    slot_key: str
    slot_label: str | None = None
    state_question: str
    primitive_family: str
    semantic_similarity: float = Field(ge=-1.0, le=1.0)
    embedding_model: str | None = None


class SemanticKeyCandidateSet(BaseModel):
    query: CoordinateRetrievalQuery
    candidates: tuple[EventSlotCandidate, ...]
    total_current_slots: int
    same_family_slot_count: int
    top_k: int
    rationale: str
def _field(value, name: str):
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _slot_key(slot) -> str | None:
    return _field(slot, "slot_id") or _field(slot, "slot_key")


def _slot_coordinate(slot) -> SemanticCoordinate | None:
    family = _field(slot, "primitive_family")
    question = _field(slot, "state_question")
    key = _slot_key(slot)
    if not family or not question or not key:
        return None
    return SemanticCoordinate(
        primitive_family=family,
        state_question=question,
        coordinate_label=_field(slot, "slot_label"),
        temporal_behavior="mutable",
    )


def retrieve_key_candidates(
    *,
    event_identity,
    current_slots,
    proposition,
    top_k: int = 2,
    retriever: CoordinateCandidateRetriever | None = None,
) -> SemanticKeyCandidateSet:
    """Retrieve Event-local candidate slots for a real typed World proposition.

    event_identity remains in the contract because entity/referent scoping
    belongs before final semantic adjudication. KS-D currently applies only the
    machine-checkable primitive-family guard plus embedding retrieval.
    """
    del event_identity

    family = _field(proposition, "primitive_family")
    statement = (
        _field(proposition, "statement")
        or _field(proposition, "proposition")
        or _field(proposition, "text")
    )
    if not family or not statement:
        raise ValueError(
            "candidate retrieval requires primitive_family and proposition statement"
        )
    query = CoordinateRetrievalQuery(
        primitive_family=family,
        text=statement,
        query_kind="PROPOSITION",
    )

    entries = []
    for slot in current_slots:
        coordinate = _slot_coordinate(slot)
        if coordinate is None:
            continue
        entries.append((slot, coordinate))

    same_family = [
        (slot, coordinate)
        for slot, coordinate in entries
        if coordinate.primitive_family == family
    ]
    engine = retriever or CoordinateCandidateRetriever()
    rows = engine.retrieve(
        query,
        [coordinate for _, coordinate in same_family],
        top_k=top_k,
    )
    by_coordinate: dict[str, list] = {}
    for slot, coordinate in same_family:
        by_coordinate.setdefault(coordinate.coordinate_id, []).append(slot)

    candidates = []
    used_slot_keys = set()
    for row in rows:
        for slot in by_coordinate.get(row.coordinate.coordinate_id, []):
            key = _slot_key(slot)
            if not key or key in used_slot_keys:
                continue
            used_slot_keys.add(key)
            candidates.append(EventSlotCandidate(
                slot_key=key,
                slot_label=_field(slot, "slot_label"),
                state_question=row.coordinate.state_question,
                primitive_family=row.coordinate.primitive_family,
                semantic_similarity=row.semantic_similarity,
                embedding_model=row.embedding_model,
            ))

    return SemanticKeyCandidateSet(
        query=query,
        candidates=tuple(candidates),
        total_current_slots=len(current_slots),
        same_family_slot_count=len(same_family),
        top_k=top_k,
        rationale=(
            "primitive-family hard filter + semantic embedding retrieval; "
            "candidate order is evidence only and does not decide REUSE/CREATE"
        ),
    )


def resolve_exact_coordinate(
    *,
    event_identity,
    current_slots,
    proposition,
) -> SemanticKeyResolution:
    """Exact deterministic shortcut for an already-normalized state_question.

    This function is retained for historical KS-C compatibility. A raw
    WorldProposition must use retrieve_key_candidates first and then a
    separate semantic adjudication stage.
    """
    del event_identity

    family = _field(proposition, "primitive_family")
    question = _field(proposition, "state_question")
    if not family or not question:
        raise ValueError(
            "exact resolver requires primitive_family and state_question; "
            "raw WorldProposition must use candidate retrieval"
        )

    coordinate = SemanticCoordinate(
        primitive_family=family,
        state_question=question,
        coordinate_label=str(family).lower(),
        temporal_behavior="mutable",
    )
    normalized_question = normalize_semantic_text(question).casefold()
    for slot in current_slots:
        slot_family = _field(slot, "primitive_family")
        slot_question = _field(slot, "state_question")
        if not slot_question:
            continue
        if (
            slot_family == family
            and normalize_semantic_text(slot_question).casefold()
            == normalized_question
        ):
            key = _slot_key(slot)
            return SemanticKeyResolution(
                decision="REUSE",
                slot_key=key,
                coordinate=coordinate,
                rationale=(
                    "same primitive family and canonical state question"
                ),
            )

    return SemanticKeyResolution(
        decision="CREATE",
        coordinate=coordinate,
        rationale="no existing Event-local coordinate matches exactly",
    )


def resolve_key(
    *,
    event_identity,
    current_slots,
    proposition,
) -> SemanticKeyResolution:
    """Backward-compatible alias for historical KS-C exact-coordinate tests."""
    return resolve_exact_coordinate(
        event_identity=event_identity,
        current_slots=current_slots,
        proposition=proposition,
    )
