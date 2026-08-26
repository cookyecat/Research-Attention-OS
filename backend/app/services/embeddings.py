from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.cognitive.client import EmbeddingDimensionError, LLMError, embed_texts
from app.config import settings
from app.models.kernel import KernelEmbedding, KernelNode
from app.services.matching import node_text

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def embedding_model_label() -> str:
    if not (settings.embedding_api_key or settings.llm_api_key):
        return "none"
    return settings.embedding_model or "none"


def upsert_node_embedding(db: Session, node: KernelNode, *, vectors_fn=None) -> KernelEmbedding | None:
    """Persist an embedding for a Kernel node. Failure must not raise to callers of commit."""
    fn = vectors_fn or embed_texts
    try:
        vecs, model = fn([node_text(node)[:8000]])
    except LLMError as exc:
        if "API key" in str(exc):
            return None
        logger.warning("kernel embedding skipped for %s: %s", node.id, exc)
        return None
    except (EmbeddingDimensionError, Exception) as exc:
        logger.warning("kernel embedding skipped for %s: %s", node.id, exc)
        return None
    if not vecs or not vecs[0]:
        return None
    vector = list(vecs[0])
    dim = len(vector)
    if settings.embedding_dimensions is not None and dim != settings.embedding_dimensions:
        logger.warning(
            "kernel embedding dimension mismatch for %s: got %s expected %s",
            node.id,
            dim,
            settings.embedding_dimensions,
        )
        return None
    row = db.get(KernelEmbedding, node.id)
    if row is None:
        row = KernelEmbedding(kernel_node_id=node.id, embedding=vector, embedding_model=model, dimensions=dim)
        db.add(row)
    else:
        row.embedding = vector
        row.embedding_model = model
        row.dimensions = dim
        row.updated_at = _utcnow()
    db.flush()
    _write_pgvector(db, node.id, vector)
    return row


def refresh_node_embedding(db: Session, node: KernelNode) -> None:
    """Best-effort. Never blocks Kernel commit/create."""
    try:
        upsert_node_embedding(db, node)
    except Exception as exc:
        logger.warning("embedding refresh failed for %s: %s", node.id, exc)


def load_node_embeddings(
    db: Session,
    *,
    expected_model: str | None = None,
    expected_dim: int | None = None,
) -> dict[UUID, list[float]]:
    rows = db.execute(select(KernelEmbedding)).scalars().all()
    out: dict[UUID, list[float]] = {}
    for row in rows:
        vec = list(row.embedding or [])
        if not vec:
            continue
        if expected_model and row.embedding_model not in {expected_model, "none"} and row.embedding_model != expected_model:
            continue
        if expected_dim is not None and row.dimensions not in {None, expected_dim} and len(vec) != expected_dim:
            if all((r.dimensions or len(r.embedding or [])) != expected_dim for r in rows if r.embedding):
                raise EmbeddingDimensionError(
                    f"stored embedding dimensions do not match query dim {expected_dim}"
                )
            continue
        if expected_dim is not None and len(vec) != expected_dim:
            continue
        out[row.kernel_node_id] = vec
    if expected_dim is not None and rows:
        stored_dims = {len(r.embedding) for r in rows if r.embedding}
        if stored_dims and expected_dim not in stored_dims and out == {}:
            raise EmbeddingDimensionError(
                f"dimension mismatch: query={expected_dim} stored={sorted(stored_dims)}"
            )
    return out


def retrieve_ids_pgvector(
    db: Session,
    query: list[float],
    *,
    model: str,
    top_k: int = 12,
) -> list[UUID] | None:
    """Use pgvector when the unbounded embedding_vec column exists. None = caller should fallback."""
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return None
    dim = len(query)
    literal = "[" + ",".join(str(float(x)) for x in query) + "]"
    try:
        rows = db.execute(
            text(
                """
                SELECT kernel_node_id
                FROM kernel_embeddings
                WHERE dimensions = :dim
                  AND embedding_model = :model
                  AND embedding_vec IS NOT NULL
                ORDER BY embedding_vec <=> CAST(:q AS vector)
                LIMIT :k
                """
            ),
            {"dim": dim, "model": model, "q": literal, "k": top_k},
        ).fetchall()
    except Exception:
        try:
            rows = db.execute(
                text(
                    """
                    SELECT kernel_node_id
                    FROM kernel_embeddings
                    WHERE dimensions = :dim
                      AND embedding IS NOT NULL
                    ORDER BY CAST(embedding::text AS vector) <=> CAST(:q AS vector)
                    LIMIT :k
                    """
                ),
                {"dim": dim, "q": literal, "k": top_k},
            ).fetchall()
        except Exception as exc:
            logger.info("pgvector retrieval unavailable: %s", exc)
            return None
    return [row[0] for row in rows]


def _write_pgvector(db: Session, node_id: UUID, vector: list[float]) -> None:
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    literal = "[" + ",".join(str(float(x)) for x in vector) + "]"
    try:
        db.execute(
            text(
                """
                UPDATE kernel_embeddings
                SET embedding_vec = CAST(:q AS vector),
                    dimensions = :dim
                WHERE kernel_node_id = CAST(:id AS uuid)
                """
            ),
            {"q": literal, "dim": len(vector), "id": str(node_id)},
        )
    except Exception as exc:
        logger.info("pgvector write skipped: %s", exc)
