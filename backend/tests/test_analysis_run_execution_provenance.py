"""Frozen relational snapshot + analysis execution fingerprint invariants."""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.enums import SourceEdgeRelationship
from app.models.kernel import KernelEmbedding, KernelNode
from app.services.analysis_execution import (
    analysis_execution_digest,
    analysis_execution_snapshot,
    sanitized_endpoint_identity,
)
from app.services.analysis_runs import compute_identity, kernel_snapshot_hash
from app.services.source_graph import freeze_analysis_relational_context, persist_source_edge
from tests.conftest import add_text, analyze


_IDENTITY = dict(
    input_digest="in",
    kernel_digest="k",
    provider_type="rule",
    model_name=None,
    embedding_model_version="none",
)


def _dummy_chat(*_a, **_k):
    return {}, {}


def _model_provider(**kwargs):
    from app.cognitive.model_provider import ModelBackedCognitiveProvider

    return ModelBackedCognitiveProvider(chat_fn=_dummy_chat, **kwargs)


def _fallback_provider(primary=None):
    from app.cognitive.factory import FallbackProvider
    from app.cognitive.rule_provider import RuleBasedCognitiveProvider

    return FallbackProvider(primary or _model_provider(), RuleBasedCognitiveProvider())


def _rule_provider():
    from app.cognitive.rule_provider import RuleBasedCognitiveProvider

    return RuleBasedCognitiveProvider()


def test_identity_includes_execution_digest():
    assert compute_identity(**_IDENTITY) != compute_identity(**_IDENTITY, execution_digest="abc")
    assert compute_identity(**_IDENTITY, execution_digest="abc") == compute_identity(
        **_IDENTITY, execution_digest="abc"
    )


def test_frozen_digest_and_independence_share_facts(db, client: TestClient):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="frz-src")
    extra = add_text(client, "Derived reprint of the motor intelligence latency paper.", title="frz-ex")
    persist_source_edge(db, UUID(extra["id"]), UUID(src["id"]), SourceEdgeRelationship.DERIVED_FROM)
    db.commit()
    ctx = freeze_analysis_relational_context(db, [UUID(src["id"]), UUID(extra["id"])])
    assert ctx.digest == hashlib.sha256(
        json.dumps(list(ctx.facts), separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert ctx.facts == ((str(extra["id"]), "DERIVED_FROM", str(src["id"])),)
    assert ctx.independent_sources == 1
    assert ctx.secondary_reports == 1
    assert ctx.independent_source_ids == (str(src["id"]),)
    assert str(extra["id"]) in ctx.secondary_source_ids


def test_cites_does_not_change_relational_digest(db, client: TestClient):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="frz-cites")
    other = add_text(client, "Cited work.", title="frz-cited")
    before = freeze_analysis_relational_context(db, [UUID(src["id"])])
    persist_source_edge(db, UUID(src["id"]), UUID(other["id"]), SourceEdgeRelationship.CITES)
    db.commit()
    after = freeze_analysis_relational_context(db, [UUID(src["id"])])
    assert before.digest == after.digest
    assert before.facts == after.facts


def test_evidence_and_impact_use_frozen_independence_not_extra_count(client: TestClient, db, monkeypatch):
    from app.cognitive.rule_provider import RuleBasedCognitiveProvider

    seen: dict = {}

    class Spy(RuleBasedCognitiveProvider):
        def reason_evidence(self, extraction, **kwargs):
            seen["count"] = kwargs.get("independent_source_count")
            return super().reason_evidence(extraction, **kwargs)

    monkeypatch.setattr("app.cognitive.factory.get_provider", lambda **_k: Spy())
    primary = add_text(client, "A technical paper about motor intelligence latency.", title="frz-pri")
    extra = add_text(client, "Derived reprint of the motor intelligence latency paper.", title="frz-extra")
    persist_source_edge(
        db, UUID(extra["id"]), UUID(primary["id"]), SourceEdgeRelationship.DERIVED_FROM
    )
    db.commit()
    result = analyze(client, primary["id"], extra_ids=[extra["id"]])
    assert seen["count"] == 1
    independence = result["attention_plan"]["score_debug"]["independence"]
    assert independence["independent_sources"] == 1
    assert independence["secondary_reports"] == 1
    assert result["impact_input"]["independence"]["independent_source_count"] == 1
    assert result["impact_input"]["independence"]["secondary_report_count"] == 1
    frozen = result["relational_context"]["independence"]
    assert frozen["independent_sources"] == independence["independent_sources"]
    assert frozen["secondary_reports"] == independence["secondary_reports"]


def test_mid_run_sourcegraph_mutation_keeps_frozen_run_then_new_identity(client: TestClient, db, monkeypatch):
    primary = add_text(client, "A technical paper about motor intelligence latency.", title="frz-mid-p")
    extra = add_text(client, "Derived motor intelligence latency reprint.", title="frz-mid-e")
    other = add_text(client, "Unrelated target used only for the new edge.", title="frz-mid-t")
    persist_source_edge(
        db, UUID(extra["id"]), UUID(primary["id"]), SourceEdgeRelationship.DERIVED_FROM
    )
    db.commit()

    import app.services.pipeline as pipeline_mod

    original = pipeline_mod.extract_source

    def mutating_extract(session, *args, **kwargs):
        persist_source_edge(
            session, UUID(primary["id"]), UUID(other["id"]), SourceEdgeRelationship.REPOSTS
        )
        session.flush()
        return original(session, *args, **kwargs)

    monkeypatch.setattr(pipeline_mod, "extract_source", mutating_extract)
    first = analyze(client, primary["id"], extra_ids=[extra["id"]])
    assert first["attention_plan"]["score_debug"]["independence"]["independent_sources"] == 1
    assert first["relational_context"]["independence"]["is_duplicate"] is False
    g0 = first["relational_context"]["digest"]

    monkeypatch.undo()
    second = analyze(client, primary["id"], extra_ids=[extra["id"]])
    assert second["analysis_run"]["id"] != first["analysis_run"]["id"]
    assert second["relational_context"]["digest"] != g0


def test_impact_assessor_version_changes_execution_digest_and_run(client: TestClient, monkeypatch):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="exec-impact")
    first = analyze(client, src["id"])
    d1 = analysis_execution_digest(_rule_provider())
    monkeypatch.setattr("app.cognitive.versions.IMPACT_ASSESSOR_VERSION", "raos-impact-CHANGED")
    d2 = analysis_execution_digest(_rule_provider())
    assert d1 != d2
    second = analyze(client, src["id"])
    assert second["analysis_run"]["id"] != first["analysis_run"]["id"]
    assert second["execution_digest"] != first["execution_digest"]


def test_chunk_settings_change_execution_digest(monkeypatch):
    rule = _rule_provider()
    base = analysis_execution_digest(rule)
    monkeypatch.setattr(settings, "long_source_chunk_chars", 1234)
    assert analysis_execution_digest(rule) != base
    monkeypatch.setattr(settings, "long_source_chunk_chars", 6000)
    monkeypatch.setattr(settings, "long_source_chunk_overlap", 17)
    assert analysis_execution_digest(rule) != base


def test_thinking_fields_hash_effective_wire_not_spelling(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "usable-key")
    provider = _model_provider()
    monkeypatch.setattr(settings, "llm_thinking_protocol", "none")
    none_digest = analysis_execution_digest(provider)
    monkeypatch.setattr(settings, "llm_thinking_protocol", "off")
    assert analysis_execution_digest(provider) == none_digest
    monkeypatch.setattr(settings, "llm_thinking_protocol", "deepseek")
    assert analysis_execution_digest(provider) != none_digest


def test_query_instruct_hashes_effective_behavior(monkeypatch):
    monkeypatch.setattr(settings, "embedding_api_key", "emb-key")
    monkeypatch.setattr(settings, "embedding_model", "Qwen3-Embedding-8B")
    provider = _model_provider()
    monkeypatch.setattr(settings, "embedding_query_protocol", "auto")
    auto = analysis_execution_digest(provider)
    monkeypatch.setattr(settings, "embedding_query_protocol", "qwen")
    assert analysis_execution_digest(provider) == auto
    monkeypatch.setattr(settings, "embedding_query_protocol", "none")
    assert analysis_execution_digest(provider) != auto


def test_embedding_model_and_dimensions_change_digest(monkeypatch):
    monkeypatch.setattr(settings, "embedding_api_key", "emb-key")
    monkeypatch.setattr(settings, "embedding_model", "text-embedding-3-small")
    monkeypatch.setattr(settings, "embedding_dimensions", None)
    provider = _model_provider()
    base = analysis_execution_digest(provider)
    monkeypatch.setattr(settings, "embedding_model", "text-embedding-3-large")
    assert analysis_execution_digest(provider) != base
    monkeypatch.setattr(settings, "embedding_model", "text-embedding-3-small")
    monkeypatch.setattr(settings, "embedding_dimensions", 1024)
    assert analysis_execution_digest(provider) != base


def test_runtime_context_does_not_change_execution_digest_or_run(client: TestClient):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="exec-runtime")
    first = analyze(client, src["id"])
    planned = client.post(
        "/scheduler/plan",
        json={
            "source_id": src["id"],
            "runtime_context": {
                "current_task": "camera-ready",
                "interruptibility": "LOW",
                "cognitive_capacity": "LOW",
            },
        },
    )
    assert planned.status_code == 200, planned.text
    body = planned.json()
    assert body["analysis_run"]["id"] == first["analysis_run"]["id"]
    assert body["attention_plan"]["id"] != first["attention_plan"]["id"]
    assert body["execution_digest"] == first["execution_digest"]


def test_token_price_does_not_change_execution_digest(monkeypatch):
    provider = _model_provider()
    monkeypatch.setattr(settings, "llm_api_key", "usable-key")
    base = analysis_execution_digest(provider)
    monkeypatch.setattr(settings, "llm_input_cost_per_1m", 12.0)
    monkeypatch.setattr(settings, "llm_output_cost_per_1m", 36.0)
    assert analysis_execution_digest(provider) == base
    snap = json.dumps(analysis_execution_snapshot(provider))
    assert "12.0" not in snap
    assert "36.0" not in snap


def test_credential_availability_not_secret_value(monkeypatch):
    provider = _model_provider()
    monkeypatch.setattr(settings, "llm_api_key", "secret-aaa")
    d1 = analysis_execution_digest(provider)
    snap1 = analysis_execution_snapshot(provider)
    monkeypatch.setattr(settings, "llm_api_key", "secret-bbb")
    d2 = analysis_execution_digest(provider)
    snap2 = analysis_execution_snapshot(provider)
    assert d1 == d2
    dumped = json.dumps(snap1) + json.dumps(snap2)
    assert "secret-aaa" not in dumped
    assert "secret-bbb" not in dumped
    monkeypatch.setattr(settings, "llm_api_key", None)
    d3 = analysis_execution_digest(provider)
    assert d3 != d1
    assert analysis_execution_snapshot(provider)["llm"]["available"] is False


def test_embedding_credential_availability_changes_digest(monkeypatch):
    provider = _model_provider()
    monkeypatch.setattr(settings, "llm_api_key", None)
    monkeypatch.setattr(settings, "embedding_model", "text-embedding-3-small")
    monkeypatch.setattr(settings, "embedding_api_key", None)
    unavailable = analysis_execution_digest(provider)
    assert analysis_execution_snapshot(provider)["retrieval"]["available"] is False
    monkeypatch.setattr(settings, "embedding_api_key", "emb-secret")
    available = analysis_execution_digest(provider)
    snap = analysis_execution_snapshot(provider)
    assert available != unavailable
    assert snap["retrieval"]["available"] is True
    assert "emb-secret" not in json.dumps(snap)


def test_rule_ignores_unused_llm_thinking_but_model_does_not(monkeypatch):
    monkeypatch.setattr(settings, "llm_thinking_protocol", "none")
    rule = _rule_provider()
    model = _model_provider()
    monkeypatch.setattr(settings, "llm_api_key", "usable-key")
    rule_none = analysis_execution_digest(rule)
    model_none = analysis_execution_digest(model)
    monkeypatch.setattr(settings, "llm_thinking_protocol", "deepseek")
    assert analysis_execution_digest(rule) == rule_none
    assert analysis_execution_digest(model) != model_none


def test_rule_does_not_fingerprint_unused_embedding_settings(monkeypatch):
    rule = _rule_provider()
    monkeypatch.setattr(settings, "embedding_api_key", "emb-key")
    monkeypatch.setattr(settings, "embedding_model", "text-embedding-3-small")
    base = analysis_execution_digest(rule)
    monkeypatch.setattr(settings, "embedding_model", "other-embed")
    monkeypatch.setattr(settings, "embedding_query_protocol", "qwen")
    assert analysis_execution_digest(rule) == base


def test_impact_runtime_override_and_fallback_primary(monkeypatch):
    from app.cognitive.runtime import StageRuntime

    monkeypatch.setattr(settings, "llm_api_key", "usable-key")
    default = _model_provider()
    override = _model_provider(
        impact_runtime=StageRuntime(thinking="disabled", reasoning_effort=None, timeout=9.0)
    )
    assert analysis_execution_digest(default) != analysis_execution_digest(override)
    fallback = _fallback_provider(override)
    assert analysis_execution_digest(fallback) == analysis_execution_digest(override)


def test_sanitized_endpoint_strips_userinfo_and_query(monkeypatch):
    assert (
        sanitized_endpoint_identity("https://user:token@api.example.com:8443/v1/chat?api_key=x#frag")
        == "https://api.example.com:8443/v1/chat"
    )
    monkeypatch.setattr(settings, "llm_api_key", "usable-key")
    monkeypatch.setattr(settings, "llm_base_url", "https://user:secret@api.example.com/v1")
    snap = analysis_execution_snapshot(_model_provider())
    dumped = json.dumps(snap)
    assert "secret" not in dumped
    assert "user:" not in dumped
    assert snap["llm"]["endpoint"] == "https://api.example.com/v1"


def test_disabled_llm_endpoint_change_does_not_invalidate(monkeypatch):
    provider = _model_provider()
    monkeypatch.setattr(settings, "llm_api_key", None)
    monkeypatch.setattr(settings, "llm_base_url", "https://a.example/v1")
    d1 = analysis_execution_digest(provider)
    monkeypatch.setattr(settings, "llm_base_url", "https://b.example/v1")
    assert analysis_execution_digest(provider) == d1


def test_persisted_embedding_rewrite_without_kernel_version_is_not_production_path(client: TestClient, db):
    nodes = db.execute(select(KernelNode).where(KernelNode.deleted_at.is_(None))).scalars().all()
    before = kernel_snapshot_hash(nodes)
    node = nodes[0]
    row = db.get(KernelEmbedding, node.id)
    if row is None:
        row = KernelEmbedding(
            kernel_node_id=node.id,
            embedding=[0.1, 0.2, 0.3],
            embedding_model="manual-test",
            dimensions=3,
        )
        db.add(row)
    else:
        row.embedding = [0.1, 0.2, 0.3]
        row.embedding_model = "manual-test"
        row.dimensions = 3
    db.commit()
    after_write = kernel_snapshot_hash(
        db.execute(select(KernelNode).where(KernelNode.deleted_at.is_(None))).scalars().all()
    )
    assert after_write == before

    src = add_text(client, "A technical paper about motor intelligence latency.", title="emb-audit")
    first = analyze(client, src["id"])
    row = db.get(KernelEmbedding, node.id)
    row.embedding = [9.9, 8.8, 7.7]
    db.commit()
    second = analyze(client, src["id"])
    assert second["analysis_run"]["id"] == first["analysis_run"]["id"]


def test_kernel_create_changes_snapshot_when_embedding_refresh_can_run(client: TestClient, db):
    db.expire_all()
    nodes = db.execute(select(KernelNode).where(KernelNode.deleted_at.is_(None))).scalars().all()
    before = kernel_snapshot_hash(nodes)
    created = client.post(
        "/kernel/nodes",
        json={"node_type": "QUESTION", "title": "emb-audit-q", "status": "OPEN", "payload": {"text": "q"}},
    )
    assert created.status_code == 200
    db.expire_all()
    after = kernel_snapshot_hash(
        db.execute(select(KernelNode).where(KernelNode.deleted_at.is_(None))).scalars().all()
    )
    assert after != before
