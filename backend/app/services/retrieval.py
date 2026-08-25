from __future__ import annotations

import math
from uuid import UUID

from app.cognitive.client import LLMError, embed_texts
from app.config import settings
from app.models.kernel import KernelNode
from app.services.matching import KernelMatch, node_text, tokenize, _overlap


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def retrieve_kernel_candidates(
    query_text: str,
    nodes: list[KernelNode],
    *,
    top_k: int = 12,
    query_embedding: list[float] | None = None,
    node_embeddings: dict[UUID, list[float]] | None = None,
) -> list[KernelNode]:
    """Embedding retrieval when available; lexical overlap otherwise. Not a truth judgment."""
    active = [n for n in nodes if n.deleted_at is None]
    if not active:
        return []
    if query_embedding and node_embeddings:
        scored = []
        for node in active:
            vec = node_embeddings.get(node.id)
            if not vec:
                continue
            scored.append((cosine(query_embedding, vec), node))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for s, n in scored[:top_k] if s > 0.15]
    qtokens = tokenize(query_text)
    scored = []
    for node in active:
        score = _overlap(qtokens, tokenize(node_text(node)))
        scored.append((score, node))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [n for s, n in scored[:top_k]]


def try_embed_query(text: str) -> tuple[list[float] | None, str]:
    if not (settings.embedding_api_key or settings.llm_api_key) or not settings.embedding_model:
        return None, "none"
    try:
        vecs, model = embed_texts([text])
        return (vecs[0] if vecs else None), model
    except LLMError:
        return None, "none"
