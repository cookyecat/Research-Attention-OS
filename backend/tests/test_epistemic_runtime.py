from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.cognitive.schemas import ExtractionResponse
from app.cognitive.validators import validate_extraction
from app.config import settings
from app.enums import AuthorType, ObservationType, ObserverType
from app.models.kernel import KernelNode
from app.services.extraction import ExtractedInference, ExtractedObservation, ExtractionResult
from app.services.retrieval import (
    format_query_for_embedding,
    retrieve_kernel_candidates_traced,
    try_embed_query,
)


def test_extraction_string_lists_reject_objects():
    with pytest.raises(ValidationError):
        ExtractionResponse.model_validate(
            {
                "claims": [],
                "observations": [],
                "inferences": [],
                "current_facts": [{"text": "not a string", "claim_type": "FACTUAL"}],
            }
        )
    with pytest.raises(ValidationError):
        ExtractionResponse.model_validate(
            {
                "claims": [],
                "observations": [],
                "inferences": [],
                "future_plans": [{"text": "will ship"}],
            }
        )
    parsed = ExtractionResponse.model_validate(
        {
            "claims": [],
            "observations": [],
            "inferences": [],
            "current_facts": ["a fact"],
            "technical_claims": ["a technical claim"],
        }
    )
    assert parsed.current_facts == ["a fact"]


def test_media_report_is_claim_not_observation():
    cleaned = validate_extraction(
        ExtractionResult(
            observations=[
                ExtractedObservation(
                    text="据报道，银河通用发布了新一代折叠机器人。",
                    observer_type=ObserverType.SYSTEM_EXTRACTED,
                    observation_type=ObservationType.REPORTED_RESULT,
                    confidence=0.8,
                )
            ]
        )
    )
    assert cleaned.observations == []
    assert any("银河通用" in c.text for c in cleaned.claims)


def test_source_authored_inference_is_not_ai_inference():
    cleaned = validate_extraction(
        ExtractionResult(
            inferences=[
                ExtractedInference(
                    text="This probably means the system is robust.",
                    author_type=AuthorType.AI,
                    confidence=0.4,
                    source_roles=["model"],
                )
            ]
        )
    )
    assert not any("probably means the system is robust" in i.text.lower() for i in cleaned.inferences)
    assert any("robust" in c.text.lower() for c in cleaned.claims)


def test_first_hand_observation_is_kept():
    cleaned = validate_extraction(
        ExtractionResult(
            observations=[
                ExtractedObservation(
                    text="In the video, it succeeds once.",
                    observer_type=ObserverType.USER,
                    observation_type=ObservationType.DIRECT_VISUAL,
                    confidence=0.8,
                )
            ]
        )
    )
    assert any("succeeds once" in o.text.lower() for o in cleaned.observations)


def test_qwen_query_instruct_prefix(monkeypatch):
    monkeypatch.setattr(settings, "embedding_query_protocol", "qwen")
    formatted = format_query_for_embedding("new paper on motor intelligence")
    assert formatted.startswith("Instruct: Given a new research information item, retrieve")
    assert formatted.endswith("Query: new paper on motor intelligence") or "Query: new paper on motor intelligence" in formatted


def test_openai_compatible_query_has_no_instruct(monkeypatch):
    monkeypatch.setattr(settings, "embedding_query_protocol", "none")
    monkeypatch.setattr(settings, "embedding_model", "text-embedding-3-small")
    assert format_query_for_embedding("hello") == "hello"


def test_try_embed_query_uses_instruct_and_document_path_stays_raw(monkeypatch):
    monkeypatch.setattr(settings, "embedding_query_protocol", "qwen")
    monkeypatch.setattr(settings, "llm_api_key", "k")
    monkeypatch.setattr(settings, "embedding_model", "Qwen3-Embedding-8B")
    captured: list[str] = []

    def fake_embed(texts, **_k):
        captured.extend(texts)
        return [[0.1, 0.2, 0.3] for _ in texts], "Qwen3-Embedding-8B"

    monkeypatch.setattr("app.services.retrieval.embed_texts", fake_embed)
    vec, model = try_embed_query("kernel query")
    assert vec == [0.1, 0.2, 0.3]
    assert captured[0].startswith("Instruct:")
    assert "Query: kernel query" in captured[0]


def test_lexical_fallback_trace_when_no_embedding():
    node = KernelNode(node_type="BELIEF", title="Motor Intelligence", status="ACTIVE", payload={"text": "embodied"})
    node.id = uuid4()
    hits, trace = retrieve_kernel_candidates_traced("motor intelligence latency", [node])
    assert trace.lexical_fallback is True
    assert trace.embedding_used is False
    assert trace.method == "lexical"
    assert hits


def test_embedding_retrieval_trace_when_vectors_match():
    node = KernelNode(node_type="BELIEF", title="Motor Intelligence", status="ACTIVE", payload={"text": "embodied"})
    node.id = uuid4()
    q = [1.0, 0.0]
    hits, trace = retrieve_kernel_candidates_traced(
        "motor",
        [node],
        query_embedding=q,
        node_embeddings={node.id: [0.9, 0.1]},
        embedding_model="Qwen3-Embedding-8B",
    )
    assert hits
    assert trace.embedding_used is True
    assert trace.lexical_fallback is False
    assert trace.method == "embedding"
