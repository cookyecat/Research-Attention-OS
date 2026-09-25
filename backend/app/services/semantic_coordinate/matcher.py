"""Phase17.3-KS-D Semantic Coordinate compatibility matcher.

The matcher is advisory and side-effect free. It never mutates the registry
or performs MERGE/SPLIT operations.
"""
from __future__ import annotations

from app.cognitive.client import embed_texts

from .models import CoordinateMatch, SemanticCoordinate
from app.cognitive.embedding_math import cosine_similarity

class CoordinateSimilarityEngine:
    def __init__(self, embed_fn=embed_texts):
        self.embed_fn = embed_fn

    def _semantic_similarity(
        self,
        a: SemanticCoordinate,
        b: SemanticCoordinate,
    ) -> float:
        vectors, _model = self.embed_fn([
            a.embedding_text(),
            b.embedding_text(),
        ])
        if len(vectors) != 2:
            raise ValueError(
                "embedding provider returned unexpected vector count"
            )
        return cosine_similarity(vectors[0], vectors[1])
    def compare(
        self,
        a: SemanticCoordinate,
        b: SemanticCoordinate,
        *,
        semantic_similarity: float | None = None,
    ) -> CoordinateMatch:
        if a.primitive_family != b.primitive_family:
            return CoordinateMatch(
                left_id=a.coordinate_id,
                right_id=b.coordinate_id,
                compatibility="TYPE_MISMATCH",
                score=0.0,
                semantic_similarity=0.0,
                requires_semantic_resolution=False,
                rationale="primitive-family hard guard mismatch",
            )

        if a.coordinate_id == b.coordinate_id:
            return CoordinateMatch(
                left_id=a.coordinate_id,
                right_id=b.coordinate_id,
                compatibility="EXACT_MATCH",
                score=1.0,
                semantic_similarity=1.0,
                requires_semantic_resolution=False,
                rationale="same canonical coordinate identity",
            )

        semantic = (
            self._semantic_similarity(a, b)
            if semantic_similarity is None
            else semantic_similarity
        )
        semantic01 = max(0.0, min(1.0, semantic))
        value_type_compatible = (
            None
            if "unknown" in {a.value_type, b.value_type}
            else a.value_type == b.value_type
        )
        temporal_behavior_compatible = (
            a.temporal_behavior == b.temporal_behavior
        )

        return CoordinateMatch(
            left_id=a.coordinate_id,
            right_id=b.coordinate_id,
            compatibility="CANDIDATE",
            score=semantic01,
            semantic_similarity=semantic,
            value_type_compatible=value_type_compatible,
            temporal_behavior_compatible=temporal_behavior_compatible,
            requires_semantic_resolution=True,
            rationale=(
                "same primitive family; score is only normalized embedding "
                "similarity. Value/temporal compatibility is exposed as "
                "separate evidence and cannot decide REUSE/CREATE by itself."
            ),
        )
