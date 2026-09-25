"""Phase17.3-KS-D coordinate evolution proposal ledger.

This module records low-frequency schema-evolution proposals. It deliberately
does not mutate coordinate identity or automatically apply matcher decisions.
"""
from __future__ import annotations

from .models import CoordinateRelation


class CoordinateEvolutionEngine:
    def __init__(self, registry):
        self.registry = registry
        self.history: list[CoordinateRelation] = []

    def propose_merge(
        self,
        source_id: str,
        target_id: str,
        *,
        confidence: float,
        rationale: str | None = None,
    ) -> CoordinateRelation:
        source = self._get(source_id)
        target = self._get(target_id)
        if source.primitive_family != target.primitive_family:
            raise ValueError(
                "MERGE proposal cannot cross primitive-family boundary"
            )
        relation = CoordinateRelation(
            source_id=source_id,
            target_id=target_id,
            relation="MERGE",
            confidence=confidence,
            rationale=rationale,
        )
        self.history.append(relation)
        return relation

    def propose_split(
        self,
        parent_id: str,
        child_ids: list[str],
        *,
        confidence: float,
        rationale: str | None = None,
    ) -> list[CoordinateRelation]:
        self._get(parent_id)
        relations = []
        for child_id in child_ids:
            child = self._get(child_id)
            relation = CoordinateRelation(
                source_id=parent_id,
                target_id=child.coordinate_id,
                relation="SPLIT",
                confidence=confidence,
                rationale=rationale,
            )
            self.history.append(relation)
            relations.append(relation)
        return relations

    def _get(self, coordinate_id):
        coordinate = self.registry.get(coordinate_id)
        if coordinate is None:
            raise KeyError(coordinate_id)
        return coordinate
