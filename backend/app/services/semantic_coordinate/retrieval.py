"""Phase17.3-KS-D Semantic Coordinate candidate retrieval.

Retrieval is side-effect free. Primitive-family filtering is a hard gate;
embeddings are candidate evidence only, never schema-mutation authority.
"""
from __future__ import annotations

from app.cognitive.client import embed_texts, format_embedding_query

from app.cognitive.embedding_math import cosine_similarity

from .models import (
    CoordinateCandidate,
    CoordinateRetrievalQuery,
    SemanticCoordinate,
)

CoordinateQuery = SemanticCoordinate | CoordinateRetrievalQuery

COORDINATE_QUERY_EMBED_INSTRUCT = (
    "Given a semantic state question, retrieve existing state dimensions "
    "that could represent the same underlying mutable world coordinate."
)
PROPOSITION_QUERY_EMBED_INSTRUCT = (
    "Given a typed semantic proposition about the world, retrieve existing "
    "state dimensions whose current value this proposition could update."
)


def format_coordinate_query_for_embedding(
    text: str,
    *,
    query_kind: str = "STATE_QUESTION",
) -> str:
    instruction = (
        PROPOSITION_QUERY_EMBED_INSTRUCT
        if query_kind == "PROPOSITION"
        else COORDINATE_QUERY_EMBED_INSTRUCT
    )
    return format_embedding_query(text, instruction)


def _query_embedding_text(query: CoordinateQuery) -> str:
    kind = (
        query.query_kind
        if isinstance(query, CoordinateRetrievalQuery)
        else "STATE_QUESTION"
    )
    return format_coordinate_query_for_embedding(
        query.embedding_text(),
        query_kind=kind,
    )


def _rank_candidates(
    *,
    query_vector: list[float],
    candidates: list[SemanticCoordinate],
    vectors: list[list[float]],
    model: str | None,
    top_k: int,
) -> list[CoordinateCandidate]:
    if len(candidates) != len(vectors):
        raise ValueError("candidate/vector cardinality mismatch")
    ranked = [
        CoordinateCandidate(
            coordinate=candidate,
            semantic_similarity=cosine_similarity(query_vector, vector),
            embedding_model=model,
        )
        for candidate, vector in zip(candidates, vectors)
    ]
    ranked.sort(
        key=lambda item: item.semantic_similarity,
        reverse=True,
    )
    return ranked[:top_k]
class CoordinateCandidateRetriever:
    """One-shot retrieval for small candidate sets and controlled evals."""

    def __init__(self, embed_fn=embed_texts):
        self.embed_fn = embed_fn

    def retrieve(
        self,
        query: CoordinateQuery,
        candidates: list[SemanticCoordinate],
        *,
        top_k: int = 5,
    ) -> list[CoordinateCandidate]:
        if top_k <= 0:
            return []

        exclude_id = (
            query.coordinate_id
            if isinstance(query, SemanticCoordinate)
            else query.exclude_coordinate_id
        )
        eligible = [
            candidate
            for candidate in candidates
            if candidate.primitive_family == query.primitive_family
            and candidate.coordinate_id != exclude_id
        ]
        if not eligible:
            return []

        texts = [
            _query_embedding_text(query),
            *[candidate.embedding_text() for candidate in eligible],
        ]
        vectors, model = self.embed_fn(texts)
        if len(vectors) != len(texts):
            raise ValueError(
                "embedding provider returned unexpected vector count"
            )
        return _rank_candidates(
            query_vector=vectors[0],
            candidates=eligible,
            vectors=vectors[1:],
            model=model,
            top_k=top_k,
        )
class InMemoryCoordinateIndex:
    """Cached-vector reference index.

    This is the Phase17.3-KS-D reference implementation. A future pgvector/ANN
    backend should preserve the same retrieve contract and family filter.
    """

    def __init__(self, embed_fn=embed_texts):
        self.embed_fn = embed_fn
        self._coordinates: dict[str, SemanticCoordinate] = {}
        self._vectors: dict[str, list[float]] = {}
        self._embedding_text: dict[str, str] = {}
        self.embedding_model: str | None = None

    def rebuild(self, coordinates: list[SemanticCoordinate]) -> None:
        unique = {
            coordinate.coordinate_id: coordinate
            for coordinate in coordinates
        }
        ordered = sorted(unique.values(), key=lambda row: row.coordinate_id)
        if not ordered:
            self._coordinates.clear()
            self._vectors.clear()
            self._embedding_text.clear()
            self.embedding_model = None
            return

        texts = [coordinate.embedding_text() for coordinate in ordered]
        vectors, model = self.embed_fn(texts)
        if len(vectors) != len(ordered):
            raise ValueError(
                "embedding provider returned unexpected vector count"
            )
        self._coordinates = {
            coordinate.coordinate_id: coordinate
            for coordinate in ordered
        }
        self._vectors = {
            coordinate.coordinate_id: vector
            for coordinate, vector in zip(ordered, vectors)
        }
        self._embedding_text = {
            coordinate.coordinate_id: text
            for coordinate, text in zip(ordered, texts)
        }
        self.embedding_model = model

    def upsert(self, coordinates: list[SemanticCoordinate]) -> int:
        changed = []
        for coordinate in coordinates:
            text = coordinate.embedding_text()
            if self._embedding_text.get(coordinate.coordinate_id) != text:
                changed.append((coordinate, text))
            else:
                self._coordinates[coordinate.coordinate_id] = coordinate
        if not changed:
            return 0

        vectors, model = self.embed_fn([text for _, text in changed])
        if len(vectors) != len(changed):
            raise ValueError(
                "embedding provider returned unexpected vector count"
            )
        if self.embedding_model is not None and model != self.embedding_model:
            raise ValueError(
                "embedding model changed; rebuild coordinate index"
            )
        self.embedding_model = model
        for (coordinate, text), vector in zip(changed, vectors):
            cid = coordinate.coordinate_id
            self._coordinates[cid] = coordinate
            self._embedding_text[cid] = text
            self._vectors[cid] = vector
        return len(changed)
    def retrieve(
        self,
        query: CoordinateQuery,
        *,
        top_k: int = 5,
    ) -> list[CoordinateCandidate]:
        if top_k <= 0:
            return []
        exclude_id = (
            query.coordinate_id
            if isinstance(query, SemanticCoordinate)
            else query.exclude_coordinate_id
        )
        eligible = [
            coordinate
            for coordinate in self._coordinates.values()
            if coordinate.primitive_family == query.primitive_family
            and coordinate.coordinate_id != exclude_id
        ]
        if not eligible:
            return []

        vectors, model = self.embed_fn([
            _query_embedding_text(query)
        ])
        if len(vectors) != 1:
            raise ValueError(
                "embedding provider returned unexpected vector count"
            )
        if self.embedding_model is not None and model != self.embedding_model:
            raise ValueError(
                "embedding model changed; rebuild coordinate index"
            )
        candidate_vectors = [
            self._vectors[coordinate.coordinate_id]
            for coordinate in eligible
        ]
        return _rank_candidates(
            query_vector=vectors[0],
            candidates=eligible,
            vectors=candidate_vectors,
            model=model,
            top_k=top_k,
        )

    def __len__(self) -> int:
        return len(self._coordinates)
