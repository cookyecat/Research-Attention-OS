"""Phase17.3-KS in-memory Semantic Coordinate Registry.

This is an experimental registry contract, not durable canonical storage.
Coordinate identity is immutable after registration.
"""
from __future__ import annotations

from app.services.semantic_primitives import PrimitiveFamily

from .models import SemanticCoordinate, normalize_semantic_text


class SemanticCoordinateRegistry:
    def __init__(self):
        self._coordinates: dict[str, SemanticCoordinate] = {}

    def register(self, coordinate: SemanticCoordinate) -> SemanticCoordinate:
        existing = self._coordinates.get(coordinate.coordinate_id)
        if existing is None:
            self._coordinates[coordinate.coordinate_id] = coordinate
            return coordinate

        if existing.identity_signature() != coordinate.identity_signature():
            raise ValueError(
                "coordinate_id collision with different semantic identity"
            )
        if (
            existing.value_type != "unknown"
            and coordinate.value_type != "unknown"
            and existing.value_type != coordinate.value_type
        ):
            raise ValueError("coordinate value_type conflict")
        if existing.temporal_behavior != coordinate.temporal_behavior:
            raise ValueError("coordinate temporal_behavior conflict")

        canonical_label = (
            existing.coordinate_label or coordinate.coordinate_label
        )
        alternate_labels = {
            label
            for label in (
                existing.coordinate_label,
                coordinate.coordinate_label,
            )
            if label and label != canonical_label
        }
        merged = existing.model_copy(update={
            "coordinate_label": canonical_label,
            "value_type": (
                existing.value_type
                if existing.value_type != "unknown"
                else coordinate.value_type
            ),
            "aliases": tuple(sorted(
                set(existing.aliases)
                | set(coordinate.aliases)
                | alternate_labels,
                key=str.casefold,
            )),
            "domain_hints": tuple(sorted(
                set(existing.domain_hints) | set(coordinate.domain_hints),
                key=str.casefold,
            )),
            "entity_type_hints": tuple(sorted(
                set(existing.entity_type_hints)
                | set(coordinate.entity_type_hints),
                key=str.casefold,
            )),
            "confidence": max(existing.confidence, coordinate.confidence),
        })
        self._coordinates[coordinate.coordinate_id] = merged
        return merged

    def get(self, coordinate_id: str) -> SemanticCoordinate | None:
        return self._coordinates.get(coordinate_id)
    def candidates_for_family(
        self,
        primitive_family: PrimitiveFamily,
        *,
        exclude_coordinate_id: str | None = None,
    ) -> list[SemanticCoordinate]:
        return [
            coordinate
            for coordinate in self._coordinates.values()
            if coordinate.primitive_family == primitive_family
            and coordinate.coordinate_id != exclude_coordinate_id
        ]

    def resolve_alias(
        self,
        alias: str,
        *,
        primitive_family: PrimitiveFamily | None = None,
    ) -> SemanticCoordinate | None:
        target = normalize_semantic_text(alias).casefold()
        matches = []
        for coordinate in self._coordinates.values():
            if primitive_family and coordinate.primitive_family != primitive_family:
                continue
            terms = [coordinate.coordinate_label, *coordinate.aliases]
            if any(
                normalize_semantic_text(term).casefold() == target
                for term in terms
                if term
            ):
                matches.append(coordinate)
        return matches[0] if len(matches) == 1 else None
    def all(
        self,
        *,
        primitive_family: PrimitiveFamily | None = None,
    ) -> list[SemanticCoordinate]:
        rows = list(self._coordinates.values())
        if primitive_family is not None:
            rows = [
                row for row in rows
                if row.primitive_family == primitive_family
            ]
        return sorted(rows, key=lambda row: row.coordinate_id)

    def __len__(self) -> int:
        return len(self._coordinates)


registry = SemanticCoordinateRegistry()
