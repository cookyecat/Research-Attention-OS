from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.cognitive.factory import FallbackProvider
from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from tests.acceptance.paraphrases import PARAPHRASES
from tests.conftest import add_observation, add_text, analyze, kernel_index, matched_codes
from tests.fakes import SemanticFakeChat


@pytest.fixture
def model_client(client: TestClient, monkeypatch) -> TestClient:
    def _provider(**_kwargs):
        return FallbackProvider(
            ModelBackedCognitiveProvider(chat_fn=SemanticFakeChat()),
            RuleBasedCognitiveProvider(),
        )

    monkeypatch.setattr("app.cognitive.factory.get_provider", _provider)
    return client


def test_paraphrase_a_weakens_not_refutes(model_client: TestClient):
    index = kernel_index(model_client)
    for i, variant in enumerate(PARAPHRASES["A"]):
        src = add_text(model_client, variant["article"], title=f"A-{i}")
        extra = []
        if variant.get("obs"):
            extra = [add_observation(model_client, variant["obs"], title=f"A-obs-{i}")["id"]]
        result = analyze(model_client, src["id"], extra_ids=extra)
        plan = result["attention_plan"]
        assert plan["attention_state"] != "DROP", variant["article"][:80]
        blob = " ".join(
            [plan["reason"]]
            + [o["text"] for o in result["observations"]]
            + [i["text"] for i in result["inferences"]]
            + [result["model_delta"].get("summary") or ""]
        ).lower()
        assert "scripted" not in blob or "without independent" in blob
        stances = {e["stance"] for e in result["evidence_links"]}
        assert "REFUTES" not in stances
        if result["evidence_links"]:
            assert "WEAKENS" in stances
        codes = matched_codes(result, index)
        assert "P1" in codes or "B1" in codes or "M1" in codes


def test_paraphrase_c_reframes_layers(model_client: TestClient):
    for i, variant in enumerate(PARAPHRASES["C"]):
        src = add_text(model_client, variant["article"], title=f"C-{i}")
        extra = [add_observation(model_client, variant["obs"], title=f"C-obs-{i}")["id"]] if variant.get("obs") else []
        result = analyze(model_client, src["id"], extra_ids=extra)
        assert result["attention_plan"]["attention_state"] == "ENGAGE"
        assert "VERIFY" in result["attention_plan"]["processing_modes"]
        questions = " ".join(result["model_delta"].get("questions") or []).lower()
        distinctions = " ".join(result["model_delta"].get("distinctions") or []).lower()
        joined = questions + " " + distinctions
        assert "layer" in joined or "temporal" in joined
        assert "good/bad" not in questions


def test_paraphrase_d_structural(model_client: TestClient):
    index = kernel_index(model_client)
    for i, variant in enumerate(PARAPHRASES["D"]):
        src = add_text(model_client, variant["article"], title=f"D-{i}")
        result = analyze(model_client, src["id"])
        assert result["attention_plan"]["attention_state"] != "DROP", variant["article"][:80]
        assert "D1" in matched_codes(result, index) or result["features"]["structural_relevance"] >= 0.65


def test_paraphrase_m_constitution(model_client: TestClient):
    for i, variant in enumerate(PARAPHRASES["M"]):
        src = add_text(model_client, variant["article"], title=f"M-{i}")
        result = analyze(model_client, src["id"])
        claims = " ".join(c["text"].lower() for c in result["claims"])
        obs = " ".join(o["text"].lower() for o in result["observations"])
        inf = " ".join(i["text"].lower() for i in result["inferences"])
        assert "zero-shot" in claims
        assert "robust" not in obs
        assert "probably" not in obs
        assert "robust" in inf or "probably" in inf


def test_paraphrase_n_drop(model_client: TestClient):
    for i, variant in enumerate(PARAPHRASES["N"]):
        src = add_text(model_client, variant["article"], title=f"N-{i}")
        result = analyze(model_client, src["id"])
        assert result["attention_plan"]["attention_state"] == "DROP"


def test_paraphrase_i_verify_not_drop(model_client: TestClient):
    for i, variant in enumerate(PARAPHRASES["I"]):
        src = add_text(model_client, variant["article"], title=f"I-{i}")
        result = analyze(model_client, src["id"])
        assert result["attention_plan"]["attention_state"] != "DROP"
        assert "VERIFY" in result["attention_plan"]["processing_modes"]


def test_paraphrase_o_news_no_silent_kernel(model_client: TestClient):
    for i, variant in enumerate(PARAPHRASES["O_NEWS"]):
        src = add_text(model_client, variant["article"], title=f"Onews-{i}")
        result = analyze(model_client, src["id"])
        assert result["kernel_patches"] == []
