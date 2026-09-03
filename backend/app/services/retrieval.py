from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from uuid import UUID

from app.cognitive.client import EmbeddingDimensionError, LLMError, embed_texts
from app.config import settings
from app.models.kernel import KernelNode
from app.services.matching import expand_locate_query, node_text, tokenize, _overlap

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
    candidates: tuple[dict, ...] = ()

    def as_dict(self) -> dict:
        data = asdict(self)
        data["candidates"] = list(self.candidates)
        return data


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


def _lexical_scored(query_text: str, active: list[KernelNode]) -> list[tuple[float, KernelNode]]:
    qtokens = tokenize(query_text)
    scored = [(_overlap(qtokens, tokenize(node_text(node))), node) for node in active]
    scored.sort(key=lambda x: (-x[0], str(x[1].id)))
    return scored


def _candidate_row(node: KernelNode, rank: int, score: float, method: str) -> dict:
    return {
        "node_id": str(node.id),
        "title": node.title,
        "node_type": node.node_type,
        "rank": rank,
        "score": round(float(score), 4),
        "method": method,
    }


def _merge_retrieval_lists(
    parts: list[tuple[str, list[tuple[float, KernelNode]]]],
    *,
    top_k: int,
) -> tuple[list[KernelNode], tuple[dict, ...]]:
    """Union of each retriever's top_k. Locate prefers recall; Impact filters false positives."""
    best: dict[UUID, dict] = {}
    for method, scored in parts:
        for score, node in scored[:top_k]:
            prev = best.get(node.id)
            if prev is None:
                best[node.id] = {"node": node, "score": float(score), "methods": {method}}
                continue
            prev["methods"].add(method)
            if float(score) > prev["score"]:
                prev["score"] = float(score)
    ordered = sorted(best.values(), key=lambda rec: (-rec["score"], str(rec["node"].id)))
    cap = max(top_k, min(len(ordered), top_k * 2))
    hits: list[KernelNode] = []
    rows: list[dict] = []
    for rank, rec in enumerate(ordered[:cap], start=1):
        methods = rec["methods"]
        method = "hybrid" if len(methods) > 1 else next(iter(methods))
        hits.append(rec["node"])
        rows.append(_candidate_row(rec["node"], rank, rec["score"], method))
    return hits, tuple(rows)


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
    """Locate candidates for the LLM matcher. Embedding ∪ lexical. Not a truth judgment."""
    query_text = expand_locate_query(query_text)
    instruct = query_instruct_enabled()
    had_embedding = query_embedding is not None or bool(ranked_ids)
    active = [n for n in nodes if n.deleted_at is None]
    empty = RetrievalTrace(
        embedding_used=False,
        lexical_fallback=True,
        method="lexical",
        embedding_model=embedding_model,
        query_instruct_applied=instruct,
        candidates=(),
    )
    if not active:
        return [], empty
    by_id = {n.id: n for n in active}
    lexical = _lexical_scored(query_text, active)
    parts: list[tuple[str, list[tuple[float, KernelNode]]]] = []
    dense_method = None
    if ranked_ids:
        ordered = [by_id[i] for i in ranked_ids if i in by_id]
        if ordered:
            decay = [(max(0.0, 1.0 - i / max(len(ordered), 1)), n) for i, n in enumerate(ordered)]
            parts.append(("pgvector", decay))
            dense_method = "pgvector"
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
        scored.sort(key=lambda x: (-x[0], str(x[1].id)))
        if scored:
            parts.append(("embedding", scored))
            dense_method = dense_method or "embedding"
    parts.append(("lexical", lexical))
    hits, candidates = _merge_retrieval_lists(parts, top_k=top_k)
    used_dense = dense_method is not None
    lexical_only = any(row["method"] == "lexical" for row in candidates)
    if used_dense and lexical_only:
        overall = "hybrid"
        lexical_fallback = False
    elif used_dense:
        overall = dense_method
        lexical_fallback = False
    else:
        overall = "lexical"
        lexical_fallback = True
    return hits, RetrievalTrace(
        embedding_used=used_dense or had_embedding,
        lexical_fallback=lexical_fallback,
        method=overall,
        embedding_model=embedding_model,
        query_instruct_applied=instruct,
        candidates=candidates,
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
