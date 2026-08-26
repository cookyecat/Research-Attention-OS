from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from uuid import UUID

from app.cognitive.client import EmbeddingDimensionError, LLMError, embed_texts
from app.config import settings
from app.models.kernel import KernelNode
from app.services.matching import node_text, tokenize, _overlap

RAOS_QUERY_EMBED_INSTRUCT = (
    "Given a new research information item, retrieve relevant Cognitive Kernel nodes "
    "that this item should be matched against."
)


@dataclass(frozen=True)
class RetrievalTrace:
    embedding_used: bool
    lexical_fallback: bool
    method: str
    embedding_model: str | None = None
    query_instruct_applied: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


def query_instruct_enabled() -> bool:
    protocol = (settings.embedding_query_protocol or "auto").strip().lower()
    if protocol in {"qwen", "instruct", "on", "true", "1"}:
        return True
    if protocol in {"none", "off", "openai"}:
        return False
    model = (settings.embedding_model or "").lower()
    return "qwen" in model


def format_query_for_embedding(text: str) -> str:
    """Qwen-style instruct prefix on the query side only. Document/Kernel text stays raw."""
    if not query_instruct_enabled():
        return text
    return f"Instruct: {RAOS_QUERY_EMBED_INSTRUCT}\nQuery: {text}"


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        raise EmbeddingDimensionError("empty embedding")
    if len(a) != len(b):
        raise EmbeddingDimensionError(f"dimension mismatch: {len(a)} vs {len(b)}")
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
    ranked_ids: list[UUID] | None = None,
) -> list[KernelNode]:
    hits, _trace = retrieve_kernel_candidates_traced(
        query_text,
        nodes,
        top_k=top_k,
        query_embedding=query_embedding,
        node_embeddings=node_embeddings,
        ranked_ids=ranked_ids,
    )
    return hits


def retrieve_kernel_candidates_traced(
    query_text: str,
    nodes: list[KernelNode],
    *,
    top_k: int = 12,
    query_embedding: list[float] | None = None,
    node_embeddings: dict[UUID, list[float]] | None = None,
    ranked_ids: list[UUID] | None = None,
    embedding_model: str | None = None,
) -> tuple[list[KernelNode], RetrievalTrace]:
    """Embedding retrieval when available; lexical overlap otherwise. Not a truth judgment."""
    instruct = query_instruct_enabled()
    had_embedding = query_embedding is not None or bool(ranked_ids)
    active = [n for n in nodes if n.deleted_at is None]
    if not active:
        return [], RetrievalTrace(
            embedding_used=False,
            lexical_fallback=True,
            method="lexical",
            embedding_model=embedding_model,
            query_instruct_applied=instruct,
        )
    by_id = {n.id: n for n in active}
    if ranked_ids:
        ordered = [by_id[i] for i in ranked_ids if i in by_id]
        if ordered:
            return ordered[:top_k], RetrievalTrace(
                embedding_used=True,
                lexical_fallback=False,
                method="pgvector",
                embedding_model=embedding_model,
                query_instruct_applied=instruct,
            )
    if query_embedding and node_embeddings:
        qdim = len(query_embedding)
        compatible = {nid: vec for nid, vec in node_embeddings.items() if vec and len(vec) == qdim}
        if node_embeddings and not compatible:
            stored = sorted({len(v) for v in node_embeddings.values() if v})
            raise EmbeddingDimensionError(f"dimension mismatch: query={qdim} stored={stored}")
        scored = []
        for node in active:
            vec = compatible.get(node.id)
            if not vec:
                continue
            scored.append((cosine(query_embedding, vec), node))
        scored.sort(key=lambda x: x[0], reverse=True)
        hits = [n for s, n in scored[:top_k] if s > 0.15]
        if hits:
            return hits, RetrievalTrace(
                embedding_used=True,
                lexical_fallback=False,
                method="embedding",
                embedding_model=embedding_model,
                query_instruct_applied=instruct,
            )
    qtokens = tokenize(query_text)
    scored = []
    for node in active:
        score = _overlap(qtokens, tokenize(node_text(node)))
        scored.append((score, node))
    scored.sort(key=lambda x: x[0], reverse=True)
    lexical = [n for s, n in scored[:top_k]]
    return lexical, RetrievalTrace(
        embedding_used=had_embedding,
        lexical_fallback=True,
        method="lexical",
        embedding_model=embedding_model,
        query_instruct_applied=instruct,
    )


def try_embed_query(text: str) -> tuple[list[float] | None, str]:
    if not (settings.embedding_api_key or settings.llm_api_key) or not settings.embedding_model:
        return None, "none"
    try:
        vecs, model = embed_texts([format_query_for_embedding(text)])
        vec = vecs[0] if vecs else None
        if vec and settings.embedding_dimensions is not None and len(vec) != settings.embedding_dimensions:
            raise EmbeddingDimensionError(
                f"query embedding dimension {len(vec)} != configured {settings.embedding_dimensions}"
            )
        return vec, model
    except EmbeddingDimensionError:
        raise
    except LLMError:
        return None, "none"
