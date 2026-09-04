from __future__ import annotations

from fastapi.testclient import TestClient

from app.cognitive.factory import FallbackProvider, get_provider
from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.cognitive.validators import validate_evidence_strength, validate_extraction
from app.enums import ObservationType, ObserverType
from app.services.extraction import ExtractedObservation, ExtractionResult
from tests.conftest import add_text, analyze, kernel_index
from tests.fakes import BoomChat, SemanticFakeChat


def test_default_provider_is_rule():
    assert isinstance(get_provider(), RuleBasedCognitiveProvider)


def test_validator_demotes_inference_language_from_observations():
    result = ExtractionResult(
        observations=[
            ExtractedObservation(
                text="This probably means the robot is scripted",
                observer_type=ObserverType.SYSTEM_EXTRACTED,
                observation_type=ObservationType.OTHER,
                confidence=0.9,
            )
        ]
    )
    cleaned = validate_extraction(result)
    assert cleaned.observations == []
    assert any("probably" in i.text.lower() for i in cleaned.inferences)


def test_validator_demotes_chinese_inference_and_attribution():
    inferred = validate_extraction(
        ExtractionResult(
            observations=[
                ExtractedObservation(
                    text="这表明系统已经鲁棒",
                    observer_type=ObserverType.SYSTEM_EXTRACTED,
                    observation_type=ObservationType.OTHER,
                    confidence=0.9,
                )
            ]
        )
    )
    assert inferred.observations == []
    assert any("表明" in i.text for i in inferred.inferences)

    attributed = validate_extraction(
        ExtractionResult(
            observations=[
                ExtractedObservation(
                    text="公司称机器人已实现零样本泛化",
                    observer_type=ObserverType.SYSTEM_EXTRACTED,
                    observation_type=ObservationType.OTHER,
                    confidence=0.9,
                )
            ]
        )
    )
    assert not any("零样本" in o.text for o in attributed.observations)
    assert any("零样本" in c.text for c in attributed.claims)


def test_company_claim_is_not_an_observation():
    result = ExtractionResult(
        observations=[
            ExtractedObservation(
                text="The company says the robot generalizes zero-shot",
                observer_type=ObserverType.SYSTEM_EXTRACTED,
                observation_type=ObservationType.OTHER,
                confidence=0.9,
            )
        ]
    )
    cleaned = validate_extraction(result)
    assert not any("zero-shot" in o.text.lower() for o in cleaned.observations)
    assert any("zero-shot" in c.text.lower() for c in cleaned.claims)


def test_refutes_demoted_without_mature_evidence():
    stance, strength = validate_evidence_strength("REFUTES", "STRONG", 0.3)
    assert stance == "WEAKENS"
    assert strength != "STRONG"


def test_model_provider_structured_parse_and_constitution():
    chat = SemanticFakeChat()
    provider = ModelBackedCognitiveProvider(chat_fn=chat)
    extraction = provider.extract_information(
        "The founder says the robot generalizes zero-shot. In the video, it succeeds once. This probably means the system is robust.",
        "TEXT",
        "demo",
    )
    assert any("zero-shot" in c.text.lower() for c in extraction.claims)
    assert any("succeeds once" in o.text.lower() or "pause" in o.text.lower() or "dwell" in o.text.lower() for o in extraction.observations)
    assert not any("robust" in o.text.lower() for o in extraction.observations)
    assert any("robust" in c.text.lower() or "probably" in c.text.lower() for c in extraction.claims)
    assert not any("probably means the system is robust" in i.text.lower() for i in extraction.inferences)


def test_model_failure_falls_back_to_rule(client: TestClient, monkeypatch):
    def _provider(**_kwargs):
        return FallbackProvider(ModelBackedCognitiveProvider(chat_fn=BoomChat()), RuleBasedCognitiveProvider())

    monkeypatch.setattr("app.cognitive.factory.get_provider", _provider)
    src = add_text(
        client,
        "The founder says the robot generalizes zero-shot. In the video, it succeeds once. This probably means the system is robust.",
        title="fallback",
    )
    result = analyze(client, src["id"])
    assert result["attention_plan"]
    assert result["analysis_run"]["fallback_used"] is True
    got = client.get(f"/sources/{src['id']}")
    assert got.status_code == 200


def test_disagreement_is_not_low_relevance(client: TestClient):
    src = add_text(
        client,
        """A high-quality technical paper on arXiv argues the opposite of the belief that large
        unified models may be unsuitable for the fastest embodied-control loop.
        It argues that large unified models are necessary for high-frequency embodied motor control
        and reports latency measurements from a control architecture study.""",
        title="disagree",
    )
    result = analyze(client, src["id"])
    plan = result["attention_plan"]
    assert plan["disposition"] != "DROP"


def test_structural_relevance_can_be_high_with_low_topic(client: TestClient, monkeypatch):
    def _provider(**_kwargs):
        return FallbackProvider(
            ModelBackedCognitiveProvider(chat_fn=SemanticFakeChat()),
            RuleBasedCognitiveProvider(),
        )

    monkeypatch.setattr("app.cognitive.factory.get_provider", _provider)
    index = kernel_index(client)
    src = add_text(
        client,
        """A celebrity invested in a consumer beverage brand and retained minority equity
        while remaining outside day-to-day employment. Ownership of shares did not imply
        an operating role.""",
        title="structural",
    )
    result = analyze(client, src["id"])
    assert result["features"]["topic_relevance"] <= 0.35
    assert result["features"]["structural_relevance"] >= 0.65
    assert index["D1"]["id"] in {m["node_id"] for m in result["kernel_matches"]}
    assert result["attention_plan"]["disposition"] != "DROP"


def test_model_delta_is_proposal_only(client: TestClient):
    index = kernel_index(client)
    before = next(n for nodes in client.get("/kernel").json().values() for n in nodes if n["id"] == index["B1"]["id"])
    src = add_text(
        client,
        """A high-quality technical paper on arXiv argues the opposite of the belief that large
        unified models may be unsuitable for the fastest embodied-control loop.
        It argues that large unified models are necessary for high-frequency embodied motor control.""",
        title="delta",
    )
    result = analyze(client, src["id"])
    after = next(n for nodes in client.get("/kernel").json().values() for n in nodes if n["id"] == index["B1"]["id"])
    assert after["current_version"] == before["current_version"]
    assert after["payload"] == before["payload"]
    if result["kernel_patches"]:
        assert all(p["status"] == "PROPOSED" for p in result["kernel_patches"])


def test_modify_commits_edited_proposition(client: TestClient):
    index = kernel_index(client)
    created = client.post(
        "/kernel/patches",
        json={
            "target_object_type": "BELIEF",
            "target_object_id": index["B1"]["id"],
            "change_type": "REVISE",
            "proposed_state": {
                "status": "CONTESTED",
                "title": index["B1"]["title"],
                "payload": index["B1"]["payload"],
            },
            "reasoning": "proposal",
        },
    )
    pid = created.json()["id"]
    modified = client.post(
        f"/kernel/patches/{pid}/modify",
        json={
            "modified_state": {
                "status": "CONTESTED",
                "title": "Edited proposition",
                "payload": {
                    **index["B1"]["payload"],
                    "proposition": "Edited proposition",
                    "confidence": 0.41,
                    "scope": "edited-scope",
                    "rationale": "human rewrite",
                },
            }
        },
    )
    assert modified.status_code == 200
    assert modified.json()["status"] == "MODIFIED"
    node = next(n for nodes in client.get("/kernel").json().values() for n in nodes if n["id"] == index["B1"]["id"])
    assert node["payload"]["proposition"] == "Edited proposition"
    assert node["payload"]["confidence"] == 0.41
    assert node["payload"]["scope"] == "edited-scope"
