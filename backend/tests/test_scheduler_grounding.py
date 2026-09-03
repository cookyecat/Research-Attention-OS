"""Live Eval v0.1.2: scheduler match grounding, sources_conflict, evidence skip."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.cognitive.factory import FallbackProvider
from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.enums import AuthorType, ClaimType, ObservationType, ObserverType, Stance, Strength
from app.services.evidence_gate import (
    SKIP_SINGLE_SOURCE_NO_STRUCTURE,
    evidence_conflict_flags,
    should_run_heavy_evidence,
)
from app.services.extraction import (
    ExtractedClaim,
    ExtractedEvidence,
    ExtractedInference,
    ExtractedObservation,
    ExtractionResult,
)
from app.services.matching import KernelMatch
from app.services.scheduler import (
    UNSUPPORTED_RELEVANCE_CAP,
    SchedulerFeatures,
    estimate_features,
    ground_features_to_matches,
    route,
)
from tests.conftest import add_text, analyze, kernel_index, matched_codes
from tests.fakes import SemanticFakeChat
from tests.test_runtime_budget import EXTRACT_TEXT, RecordingChat


GALAXY_STYLE = """
Galaxy General unveiled a folding household robot at the World Robot Conference.
The company says the robot uses an agent brain and generalizes zero-shot.
Ordinary users without an algorithm background can teach it new motor skills.
This is a revolutionary seamless leap for embodied motor intelligence —
the ChatGPT moment of physical AI. This probably means the system is robust.
"""


def _features(**overrides) -> SchedulerFeatures:
    base = dict(
        topic_relevance=0.8,
        structural_relevance=0.8,
        decision_relevance=0.9,
        novelty=0.65,
        credibility=0.7,
        kernel_delta=0.75,
        bottleneck_alignment=0.8,
        disagreement=0.1,
        actionability=0.4,
        temporal_value=0.4,
        cognitive_cost=8.0,
    )
    base.update(overrides)
    return SchedulerFeatures(**base)


def _match(*, node_type: str, relevance_type: str = "TOPIC", structural: bool = False, score: float = 0.8) -> KernelMatch:
    return KernelMatch(
        node_id=uuid4(),
        node_type=node_type,
        title=node_type,
        score=score,
        reason="test",
        structural=structural,
        relevance_type=relevance_type,
    )


def _claim(text: str = "The company says the robot generalizes zero-shot.") -> ExtractedClaim:
    return ExtractedClaim(text=text, claim_type=ClaimType.TECHNICAL)


def _obs(text: str = "In the video, it succeeds once.") -> ExtractedObservation:
    return ExtractedObservation(
        text=text,
        observer_type=ObserverType.USER,
        observation_type=ObservationType.DIRECT_VISUAL,
    )


def _link(stance: Stance) -> ExtractedEvidence:
    return ExtractedEvidence(
        source_role="OBSERVATION",
        source_index=0,
        target_role="CLAIM",
        target_index=0,
        stance=stance,
        strength=Strength.MODERATE,
        confidence=0.6,
    )


class GalaxyInflatedChat(SemanticFakeChat):
    """Simulate an LLM that spuriously scores decision_relevance HIGH."""

    def __init__(self):
        super().__init__()
        self.evidence_calls = 0

    def __call__(self, messages, **kwargs):
        system = (messages[0].get("content") or "").lower()
        if "relate claims" in system or "stances:" in system:
            self.evidence_calls += 1
        parsed, meta = super().__call__(messages, **kwargs)
        if "judge scheduler" in system or "you do not choose drop" in system or "cognitive impact" in system:
            parsed = dict(parsed)
            parsed["marketing_heavy"] = True
            parsed["evidence_maturity"] = 0.4
            parsed.pop("decision_relevance", None)
            parsed.pop("topic_relevance", None)
            parsed.pop("kernel_delta", None)
            parsed.pop("structural_relevance", None)
        return parsed, meta


def test_grounding_caps_unsupported_decision_structural_bottleneck():
    features = _features()
    matches = [_match(node_type="PROJECT", relevance_type="TOPIC")]
    grounded = ground_features_to_matches(features, matches)
    assert grounded.decision_relevance == UNSUPPORTED_RELEVANCE_CAP
    assert grounded.structural_relevance == UNSUPPORTED_RELEVANCE_CAP
    assert grounded.bottleneck_alignment == UNSUPPORTED_RELEVANCE_CAP
    plan = route(grounded)
    assert plan.expected_output.value != "DECISION_REVIEW"


def test_grounding_keeps_supported_decision_and_structural():
    features = _features(topic_relevance=0.2)
    matches = [
        _match(node_type="DECISION", relevance_type="STRUCTURAL", structural=True, score=0.85),
    ]
    grounded = ground_features_to_matches(features, matches)
    assert grounded.decision_relevance == 0.9
    assert grounded.structural_relevance == 0.8
    assert grounded.bottleneck_alignment == UNSUPPORTED_RELEVANCE_CAP


def test_sources_conflict_false_for_supports_only_links():
    extraction = ExtractionResult(claims=[_claim()], evidence=[_link(Stance.SUPPORTS)])
    links_present, conflict = evidence_conflict_flags(extraction)
    assert links_present is True
    assert conflict is False
    features = estimate_features("embodied motor intelligence article", extraction, [])
    assert features.evidence_links_present is True
    assert features.sources_conflict is False


def test_sources_conflict_true_for_weakens_links():
    extraction = ExtractionResult(
        claims=[_claim("The company claims stable continuous movement.")],
        observations=[_obs("The demo contains repeated move-pause-move.")],
        evidence=[_link(Stance.WEAKENS)],
    )
    links_present, conflict = evidence_conflict_flags(extraction)
    assert links_present is True
    assert conflict is True


def test_heavy_evidence_skips_inferences_without_observations():
    extraction = ExtractionResult(
        claims=[_claim()],
        inferences=[ExtractedInference(text="RAOS notes zero-shot is unverified.", author_type=AuthorType.AI)],
    )
    run, reason = should_run_heavy_evidence(extraction, independent_source_count=1)
    assert run is False
    assert reason == SKIP_SINGLE_SOURCE_NO_STRUCTURE

    chat = RecordingChat()
    provider = ModelBackedCognitiveProvider(chat_fn=chat)
    out = provider.reason_evidence(extraction, independent_source_count=1)
    assert "evidence" not in chat.by_stage
    assert out.evidence_stage_skipped is True
    assert out.evidence_skip_reason == SKIP_SINGLE_SOURCE_NO_STRUCTURE
    assert provider.last_stage_runtime["llm_called"] is False


def test_heavy_evidence_runs_for_observations_vs_claims():
    chat = RecordingChat()
    provider = ModelBackedCognitiveProvider(chat_fn=chat)
    extraction = provider.extract_information(EXTRACT_TEXT, "TEXT")
    assert extraction.claims and extraction.observations
    extraction = provider.reason_evidence(extraction, independent_source_count=1)
    assert "evidence" in chat.by_stage
    assert extraction.evidence_stage_skipped is False


def test_galaxy_style_no_spurious_decision_or_conflict(client: TestClient, monkeypatch):
    chat = GalaxyInflatedChat()

    def _provider(**_kwargs):
        return FallbackProvider(
            ModelBackedCognitiveProvider(chat_fn=chat),
            RuleBasedCognitiveProvider(),
        )

    monkeypatch.setattr("app.cognitive.factory.get_provider", _provider)
    index = kernel_index(client)
    src = add_text(client, GALAXY_STYLE, title="Galaxy General WRC marketing")
    result = analyze(client, src["id"])

    assert chat.evidence_calls == 0
    assert result["observations"] == []
    assert result["evidence_stage_skipped"] is True
    assert result["evidence_skip_reason"] == SKIP_SINGLE_SOURCE_NO_STRUCTURE

    features = result["features"]
    assert features["sources_conflict"] is False
    assert features["decision_relevance"] < 0.65
    assert features["evidence_stage_skipped"] is True
    assert features["evidence_maturity"] <= 0.4

    codes = matched_codes(result, index)
    assert "P1" in codes
    assert "D1" not in codes
    assert not any(m.get("relevance_type") == "DECISION" for m in result["kernel_matches"])
    assert not any(m.get("node_type") == "DECISION" for m in result["kernel_matches"])

    plan = result["attention_plan"]
    assert plan["disposition"] != "DROP"
    assert plan["expected_output"] != "DECISION_REVIEW"

    impact = result.get("cognitive_impact") or {}
    effects = impact.get("effects") or []
    assert effects
    belief_effects = [e for e in effects if e.get("target_kernel_node_id") == index["B1"]["id"]]
    assert all(e.get("operation") != "CHALLENGE" for e in belief_effects)
    assert {e.get("operation") for e in belief_effects} <= {"REINFORCE"}
    assert all(float(e.get("epistemic_strength") or 0) <= 0.45 for e in effects)
    assert "topic relevance" not in (plan.get("reason") or "").lower()

    titles = " ".join((m.get("title") or "") for m in result["kernel_matches"]).lower()
    assert "motor intelligence" in titles

    prov = (result.get("analysis_run") or {}).get("stage_provenance") or {}
    evidence_rec = prov.get("evidence") or {}
    assert evidence_rec.get("llm_called") is False
    assert evidence_rec.get("evidence_stage_skipped") is True
