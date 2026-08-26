from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from pydantic import ValidationError

from app.cognitive.client import EmbeddingDimensionError
from app.cognitive.factory import FallbackProvider
from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.cognitive.schemas import ExtractionResponse, ModelDeltaResponse
from app.models.analysis import AnalysisRun
from app.models.kernel import KernelEmbedding, KernelNode
from app.services.analysis_runs import compute_identity
from app.services.chunking import split_source
from app.services.extraction import ExtractedClaim, ExtractionResult, merge_extractions
from app.services.retrieval import cosine, retrieve_kernel_candidates
from app.enums import ClaimType
from tests.conftest import add_text, analyze
from tests.fakes import META, SemanticFakeChat


class RepairOnceChat:
    def __init__(self):
        self.n = 0
        self.inner = SemanticFakeChat()

    def __call__(self, messages, **_kwargs):
        self.n += 1
        system = (messages[0].get("content") or "").lower()
        if self.n == 1 and "extraction stage" in system:
            return {"ok": True}, META
        return self.inner(messages, **_kwargs)


class AlwaysInvalidChat:
    def __call__(self, messages, **_kwargs):
        return {"claims": "not-a-list"}, META


class ExtraFieldOnceChat:
    """Valid payload plus an unexpected field on the first extraction call only."""

    def __init__(self):
        self.n = 0
        self.inner = SemanticFakeChat()

    def __call__(self, messages, **_kwargs):
        self.n += 1
        parsed, meta = self.inner(messages, **_kwargs)
        system = (messages[0].get("content") or "").lower()
        if self.n == 1 and "extraction stage" in system:
            return {**parsed, "unexpected_field": "must-fail"}, meta
        return parsed, meta


class AlwaysExtraFieldChat:
    def __init__(self):
        self.inner = SemanticFakeChat()

    def __call__(self, messages, **_kwargs):
        parsed, meta = self.inner(messages, **_kwargs)
        return {**parsed, "unexpected_field": "must-fail"}, meta


class BadAffectedNodesChat:
    def __init__(self):
        self.inner = SemanticFakeChat()

    def __call__(self, messages, **_kwargs):
        parsed, meta = self.inner(messages, **_kwargs)
        system = (messages[0].get("content") or "").lower()
        if "produce a model delta" in system:
            parsed = dict(parsed)
            parsed["affected_kernel_nodes"] = ["not-an-object"]
        return parsed, meta


def test_schema_invalid_then_retry_valid():
    chat = RepairOnceChat()
    provider = ModelBackedCognitiveProvider(chat_fn=chat)
    result = provider.extract_information(
        "The founder says the robot generalizes zero-shot. In the video, it succeeds once.",
        "TEXT",
        "retry",
    )
    assert result.claims
    events = provider.last_meta.get("validation_events") or []
    assert any(e.get("status") == "repaired" for e in events)


def test_schema_invalid_twice_raises_then_fallback(client: TestClient, monkeypatch):
    def _provider(**_kwargs):
        return FallbackProvider(ModelBackedCognitiveProvider(chat_fn=AlwaysInvalidChat()), RuleBasedCognitiveProvider())

    monkeypatch.setattr("app.cognitive.factory.get_provider", _provider)
    src = add_text(client, "A technical paper about motor intelligence latency.", title="schema-fb")
    result = analyze(client, src["id"])
    assert result["analysis_run"]["fallback_used"] is True
    prov = result["analysis_run"]["stage_provenance"] or {}
    assert prov.get("extraction", {}).get("status") == "fallback"
    assert prov.get("extraction", {}).get("provider") == "rule"


def test_malformed_item_is_not_silently_dropped():
    with pytest.raises(ValidationError):
        ExtractionResponse.model_validate(
            {
                "claims": [{"text": "ok", "claim_type": "FACTUAL", "extraction_confidence": 0.4}, "bad-item"],
                "observations": [],
                "inferences": [],
            }
        )


def test_unexpected_field_is_rejected_not_silently_dropped():
    payload = {
        "claims": [{"text": "ok", "claim_type": "FACTUAL", "extraction_confidence": 0.4}],
        "observations": [],
        "inferences": [],
        "unexpected_field": "nope",
    }
    with pytest.raises(ValidationError) as exc:
        ExtractionResponse.model_validate(payload)
    assert any(e.get("type") == "extra_forbidden" for e in exc.value.errors())


def test_unexpected_field_retries_then_succeeds():
    chat = ExtraFieldOnceChat()
    provider = ModelBackedCognitiveProvider(chat_fn=chat)
    result = provider.extract_information(
        "The founder says the robot generalizes zero-shot. In the video, it succeeds once.",
        "TEXT",
        "extra-retry",
    )
    assert result.claims
    events = provider.last_meta.get("validation_events") or []
    assert any(e.get("status") == "repaired" for e in events)


def test_unexpected_field_twice_falls_back(client: TestClient, monkeypatch):
    def _provider(**_kwargs):
        return FallbackProvider(ModelBackedCognitiveProvider(chat_fn=AlwaysExtraFieldChat()), RuleBasedCognitiveProvider())

    monkeypatch.setattr("app.cognitive.factory.get_provider", _provider)
    src = add_text(client, "A technical paper about motor intelligence latency.", title="extra-fb")
    result = analyze(client, src["id"])
    assert result["analysis_run"]["fallback_used"] is True
    prov = result["analysis_run"]["stage_provenance"] or {}
    assert prov.get("extraction", {}).get("status") == "fallback"


def test_malformed_affected_kernel_nodes_fail_validation():
    with pytest.raises(ValidationError) as exc:
        ModelDeltaResponse.model_validate(
            {
                "summary": "A relevant distinction.",
                "affected_kernel_nodes": ["not-an-object"],
            }
        )
    assert exc.value.errors()
    with pytest.raises(ValidationError):
        ModelDeltaResponse.model_validate(
            {
                "summary": "A relevant distinction.",
                "affected_kernel_nodes": [{"impact": "REFINE"}],
            }
        )


def test_malformed_affected_kernel_nodes_follow_repair_fallback(client: TestClient, monkeypatch):
    def _provider(**_kwargs):
        return FallbackProvider(ModelBackedCognitiveProvider(chat_fn=BadAffectedNodesChat()), RuleBasedCognitiveProvider())

    monkeypatch.setattr("app.cognitive.factory.get_provider", _provider)
    src = add_text(
        client,
        "A high-quality technical paper on arXiv argues the opposite of the belief that large "
        "unified models may be unsuitable for the fastest embodied-control loop.",
        title="delta-bad-nodes",
    )
    result = analyze(client, src["id"])
    assert result["model_delta"]["summary"]
    prov = result["analysis_run"].get("stage_provenance") or {}
    delta_stage = prov.get("delta") or {}
    assert delta_stage.get("status") in {"fallback", "success"}
    if result["analysis_run"]["fallback_used"]:
        assert delta_stage.get("status") == "fallback"


def test_analysis_identity_changes_with_matcher_and_prompt(monkeypatch):
    base = dict(
        input_digest="in",
        kernel_digest="k",
        provider_type="model",
        model_name="gpt-x",
        embedding_model_version="none",
    )
    a = compute_identity(**base)
    monkeypatch.setattr("app.services.analysis_runs.MATCHER_VERSION", "raos-matcher-CHANGED")
    b = compute_identity(**base)
    assert a != b
    monkeypatch.setattr("app.services.analysis_runs.PROMPT_VERSION", "raos-prompts-CHANGED")
    c = compute_identity(**base)
    assert b != c
    d = compute_identity(**{**base, "model_name": "other-model"})
    assert a != d


def test_concurrency_identity_unique(engine, db):
    run = AnalysisRun(
        source_id=uuid4(),
        extra_source_ids=[],
        identity_key="same-identity",
        extractor_version="e",
        matcher_version="m",
        evidence_reasoner_version="ev",
        delta_version="d",
        scheduler_version="s",
        prompt_version="p",
        provider_version="pv",
        pipeline_version="pl",
        provider_type="rule",
        input_hash="i",
        kernel_snapshot_hash="k",
        status="COMPLETED",
        result_payload={"attention_plan": {"id": "orig"}},
    )
    db.add(run)
    db.commit()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    other = SessionLocal()
    dup = AnalysisRun(
        source_id=uuid4(),
        extra_source_ids=[],
        identity_key="same-identity",
        extractor_version="e",
        matcher_version="m",
        evidence_reasoner_version="ev",
        delta_version="d",
        scheduler_version="s",
        prompt_version="p",
        provider_version="pv",
        pipeline_version="pl",
        provider_type="rule",
        input_hash="i",
        kernel_snapshot_hash="k",
        status="RUNNING",
        result_payload={},
    )
    other.add(dup)
    with pytest.raises(IntegrityError):
        other.commit()
    other.rollback()
    other.close()


def test_failed_analysis_can_retry(client: TestClient, monkeypatch):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="fail-retry")

    def boom(*_a, **_k):
        raise RuntimeError("forced analysis failure")

    monkeypatch.setattr("app.services.pipeline.extract_source", boom)
    r = client.post("/analysis/extract", json={"source_id": src["id"]})
    assert r.status_code >= 500
    monkeypatch.undo()
    again = client.post("/analysis/extract", json={"source_id": src["id"]})
    assert again.status_code == 200, again.text
    assert again.json()["analysis_run"]["status"] == "COMPLETED"


def test_completed_analysis_immutable_and_reschedule_creates_plans(client: TestClient):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="immutable")
    first = analyze(client, src["id"])
    original_plan_id = first["attention_plan"]["id"]
    run_id = first["analysis_run"]["id"]
    planned = client.post(
        "/scheduler/plan",
        json={
            "source_id": src["id"],
            "runtime_context": {"current_task": "later", "interruptibility": "LOW", "cognitive_capacity": "LOW"},
        },
    )
    assert planned.status_code == 200, planned.text
    body = planned.json()
    assert body["analysis_run"]["id"] == run_id
    assert body["attention_plan"]["id"] != original_plan_id
    stored = client.get(f"/analysis/by-source/{src['id']}").json()
    assert stored["attention_plan"]["id"] == original_plan_id
    assert stored["analysis_run"]["id"] == run_id
    history = client.get(f"/analysis/{run_id}/attention-plans").json()
    assert len(history["attention_plans"]) >= 2
    assert history["latest_attention_plan"]["id"] == body["attention_plan"]["id"]


def test_stage_provenance_on_rule_run(client: TestClient):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="prov")
    result = analyze(client, src["id"])
    prov = result["analysis_run"]["stage_provenance"] or {}
    assert prov.get("extraction", {}).get("provider") == "rule"


def test_long_source_chunk_extraction_and_span_survives_merge(client: TestClient):
    padding = "padding word. " * 900
    text = (
        "# Section One\nThe founder says the robot generalizes zero-shot.\n"
        + padding
        + "\n# Section Two\nIn the video, it succeeds once.\n"
    )
    assert len(text) > 12000
    chunks = split_source(text)
    assert len(chunks) >= 2
    src = add_text(client, text, title="long-src")
    result = analyze(client, src["id"])
    claim_blob = " ".join(c["text"] for c in result["claims"]).lower()
    obs_blob = " ".join(o["text"] for o in result["observations"]).lower()
    assert "zero-shot" in claim_blob
    assert "succeeds once" in obs_blob or "succeeds once" in claim_blob
    assert any(c.get("chunk_id") for c in result["claims"] + result["observations"])
    assert any(c.get("source_span_text") for c in result["claims"] + result["observations"])


def test_source_span_survives_merge_unit():
    a = ExtractionResult(
        claims=[
            ExtractedClaim(
                text="unique claim A",
                claim_type=ClaimType.FACTUAL,
                source_span_text="unique claim A",
                source_start_offset=0,
                source_end_offset=14,
                chunk_id="c0",
            )
        ]
    )
    b = ExtractionResult(
        claims=[
            ExtractedClaim(
                text="unique claim A",
                claim_type=ClaimType.FACTUAL,
                source_span_text="should-not-win",
                chunk_id="c1",
            )
        ]
    )
    merged = merge_extractions(a, b)
    assert len(merged.claims) == 1
    assert merged.claims[0].chunk_id == "c0"
    assert merged.claims[0].source_span_text == "unique claim A"


def test_embedding_dimension_mismatch_raises():
    with pytest.raises(EmbeddingDimensionError):
        cosine([0.1, 0.2], [0.1, 0.2, 0.3])
    n1 = KernelNode(node_type="BELIEF", title="a", status="ACTIVE", payload={})
    n1.id = uuid4()
    n2 = KernelNode(node_type="BELIEF", title="b", status="ACTIVE", payload={})
    n2.id = uuid4()
    with pytest.raises(EmbeddingDimensionError):
        retrieve_kernel_candidates(
            "query",
            [n1, n2],
            query_embedding=[0.1, 0.2, 0.3, 0.4],
            node_embeddings={n1.id: [0.1, 0.2, 0.3], n2.id: [0.2, 0.1, 0.0]},
        )


def test_kernel_commit_refreshes_embedding_and_failure_does_not_block(client: TestClient, engine, monkeypatch):
    from uuid import UUID

    from app.cognitive.client import LLMError

    created = client.post(
        "/kernel/nodes",
        json={"node_type": "QUESTION", "title": "Emb test", "status": "OPEN", "payload": {"text": "q"}},
    )
    assert created.status_code == 200
    nid = created.json()["id"]

    def fake_embed(texts, **_k):
        return [[0.1, 0.2, 0.3] for _ in texts], "test-emb"

    monkeypatch.setattr("app.services.embeddings.embed_texts", fake_embed)
    patch = client.post(
        "/kernel/patches",
        json={
            "target_object_type": "QUESTION",
            "target_object_id": nid,
            "change_type": "REVISE",
            "proposed_state": {"title": "Emb test revised", "status": "OPEN", "payload": {"text": "q2"}},
            "reasoning": "human",
        },
    )
    pid = patch.json()["id"]
    acc = client.post(f"/kernel/patches/{pid}/accept")
    assert acc.status_code == 200
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    row = session.get(KernelEmbedding, UUID(nid))
    assert row is not None
    assert row.dimensions == 3
    assert row.embedding_model == "test-emb"
    session.close()

    def boom(*_a, **_k):
        raise LLMError("embed down")

    monkeypatch.setattr("app.services.embeddings.embed_texts", boom)
    patch2 = client.post(
        "/kernel/patches",
        json={
            "target_object_type": "QUESTION",
            "target_object_id": nid,
            "change_type": "REVISE",
            "proposed_state": {"title": "still commits", "status": "OPEN", "payload": {"text": "q3"}},
            "reasoning": "human",
        },
    )
    acc2 = client.post(f"/kernel/patches/{patch2.json()['id']}/accept")
    assert acc2.status_code == 200
    node = next(n for nodes in client.get("/kernel").json().values() for n in nodes if n["id"] == nid)
    assert node["title"] == "still commits"


def test_cost_unknown_is_null():
    from app.cognitive.client import estimate_cost_usd
    from app.config import settings

    assert settings.llm_input_cost_per_1m is None
    assert estimate_cost_usd(1000, 1000) is None
