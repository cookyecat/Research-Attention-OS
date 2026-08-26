from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from tests.conftest import add_text, analyze


pytestmark = pytest.mark.skipif(
    not os.environ.get("RAOS_TEST_DATABASE_URL"),
    reason="RAOS_TEST_DATABASE_URL not set",
)


def test_postgres_pgvector_distance(engine):
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        value = conn.execute(text("SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector")).scalar()
        conn.commit()
    assert value is not None
    assert float(value) > 0


def test_postgres_pipeline_smoke(client):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="pg-smoke")
    result = analyze(client, src["id"])
    assert result["analysis_run"]["id"]
    assert result["attention_plan"]["attention_state"]


def test_postgres_pgvector_kernel_retrieval(engine, db):
    from uuid import uuid4

    from app.models.kernel import KernelEmbedding, KernelNode
    from app.services.embeddings import retrieve_ids_pgvector
    from app.services.retrieval import retrieve_kernel_candidates

    n1 = KernelNode(node_type="BELIEF", title="alpha node", status="ACTIVE", payload={"proposition": "alpha"})
    n2 = KernelNode(node_type="BELIEF", title="beta node", status="ACTIVE", payload={"proposition": "beta"})
    db.add_all([n1, n2])
    db.flush()
    db.add_all(
        [
            KernelEmbedding(
                kernel_node_id=n1.id,
                embedding=[1.0, 0.0, 0.0],
                embedding_model="test-emb",
                dimensions=3,
            ),
            KernelEmbedding(
                kernel_node_id=n2.id,
                embedding=[0.0, 1.0, 0.0],
                embedding_model="test-emb",
                dimensions=3,
            ),
        ]
    )
    db.flush()
    db.execute(
        text(
            "UPDATE kernel_embeddings SET embedding_vec = CAST(embedding::text AS vector) "
            "WHERE embedding_vec IS NULL"
        )
    )
    db.flush()
    ranked = retrieve_ids_pgvector(db, [0.99, 0.01, 0.0], model="test-emb", top_k=2)
    assert ranked is not None
    assert ranked[0] == n1.id
    hits = retrieve_kernel_candidates(
        "alpha",
        [n1, n2],
        query_embedding=[0.99, 0.01, 0.0],
        node_embeddings={n1.id: [1.0, 0.0, 0.0], n2.id: [0.0, 1.0, 0.0]},
        ranked_ids=ranked,
    )
    assert hits[0].id == n1.id
