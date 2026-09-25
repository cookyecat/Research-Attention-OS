"""Shared embedding-vector math for RAOS retrieval layers."""
from __future__ import annotations

import math

from app.cognitive.client import EmbeddingDimensionError


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        raise EmbeddingDimensionError("empty embedding")
    if len(a) != len(b):
        raise EmbeddingDimensionError(
            f"dimension mismatch: {len(a)} vs {len(b)}"
        )
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
