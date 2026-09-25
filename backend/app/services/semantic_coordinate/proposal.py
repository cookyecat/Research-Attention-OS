"""Phase17.3-KS Semantic Coordinate proposal construction.

Proposal does not classify raw evidence. Primitive family and state question
must already come from the upstream semantic normalization/key-resolution path.
"""
from __future__ import annotations

from app.services.semantic_primitives import PrimitiveFamily

from .models import CoordinateProposal, SemanticCoordinate


def propose_coordinate(
    *,
    proposition: str,
    primitive_family: PrimitiveFamily,
    state_question: str,
    coordinate_label: str | None = None,
    aliases: tuple[str, ...] = (),
    domain_hints: tuple[str, ...] = (),
    entity_type_hints: tuple[str, ...] = (),
    value_type: str = "unknown",
    temporal_behavior: str = "mutable",
    confidence: float = 0.5,
) -> CoordinateProposal:
    """Construct a provisional coordinate without reclassifying evidence."""
    coordinate = SemanticCoordinate(
        primitive_family=primitive_family,
        state_question=state_question,
        coordinate_label=coordinate_label,
        aliases=aliases,
        domain_hints=domain_hints,
        entity_type_hints=entity_type_hints,
        value_type=value_type,
        temporal_behavior=temporal_behavior,
        confidence=confidence,
    )
    return CoordinateProposal(
        proposition=proposition,
        candidates=(coordinate,),
    )
