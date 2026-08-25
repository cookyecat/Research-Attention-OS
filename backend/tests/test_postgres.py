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
