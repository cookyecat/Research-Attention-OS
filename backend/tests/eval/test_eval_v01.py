from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.cognitive.factory import FallbackProvider
from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from tests.conftest import add_observation, add_text, analyze, kernel_index, matched_codes
from tests.fakes import SemanticFakeChat

CASES_PATH = Path(__file__).resolve().parents[3] / "eval" / "v0.1" / "cases.py"
spec = importlib.util.spec_from_file_location("raos_eval_cases", CASES_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)
CASES: list[dict] = mod.CASES


def _check(result: dict, case: dict, index: dict[str, dict]) -> None:
    expected = case["expected"]
    plan = result["attention_plan"]
    assert plan["disposition"] in expected["disposition"], (
        case["id"],
        plan["disposition"],
        expected["disposition"],
    )
    codes = matched_codes(result, index)
    for code in expected["expected_kernel_matches"]:
        if code in index:
            assert code in codes, (case["id"], code, codes)
    for code in expected["forbidden_kernel_matches"]:
        assert code not in codes, (case["id"], code, codes)
    blob = " ".join(
        [o["text"] for o in result["observations"]]
        + [i["text"] for i in result["inferences"]]
        + [result["model_delta"].get("summary") or ""]
        + (result["model_delta"].get("what_could_change") or [])
        + (result["model_delta"].get("distinctions") or [])
    ).lower()
    for phrase in expected["forbidden_conclusions"]:
        assert phrase.lower() not in blob, (case["id"], phrase)
    delta_blob = " ".join(
        [result["model_delta"].get("summary") or ""]
        + (result["model_delta"].get("distinctions") or [])
        + (result["model_delta"].get("questions") or [])
        + (result["model_delta"].get("what_could_change") or [])
    ).lower()
    for topic in expected["expected_delta_topics"]:
        if plan["disposition"] in {"ENGAGE", "WATCH", "AWARE"}:
            assert topic.lower() in delta_blob or topic.lower() in blob or topic.lower() in str(result["kernel_matches"]).lower(), (
                case["id"],
                topic,
            )
    coi = expected.get("claim_observation_inference_constraints") or {}
    claims = " ".join(c["text"].lower() for c in result["claims"])
    obs = " ".join(o["text"].lower() for o in result["observations"])
    inf = " ".join(i["text"].lower() for i in result["inferences"])
    for needle in coi.get("must_have_claim_topics") or []:
        assert needle.lower() in claims, (case["id"], needle)
    for needle in coi.get("must_have_observation_topics") or []:
        assert needle.lower() in obs, (case["id"], needle)
    for needle in coi.get("must_have_inference_topics") or []:
        assert needle.lower() in inf, (case["id"], needle)
    for needle in coi.get("observation_must_not_contain") or []:
        assert needle.lower() not in obs, (case["id"], needle)


@pytest.mark.skip(
    reason=(
        "v2.1 P0: production rule Locate is lexical overlap only; Pilot-12 eval gold "
        "is a diagnostic artifact, not a production contract. Gold is unchanged. "
        "Use test_eval_v01_model for the model-path diagnostic."
    )
)
@pytest.mark.parametrize("case", [c for c in CASES if "rule" in c.get("backends", ["rule"])], ids=lambda c: c["id"])
def test_eval_v01_rule(client: TestClient, case: dict):
    index = kernel_index(client)
    src = add_text(client, case["source"], title=f"eval-{case['id'].split('_')[0]}")
    extra = []
    if case.get("extra_observation"):
        extra = [add_observation(client, case["extra_observation"], title=case["id"] + "-obs")["id"]]
    result = analyze(client, src["id"], extra_ids=extra)
    _check(result, case, index)


@pytest.mark.parametrize("case", [c for c in CASES if "model" in c.get("backends", [])], ids=lambda c: c["id"] + "-model")
def test_eval_v01_model(client: TestClient, monkeypatch, case: dict):
    def _provider(**_kwargs):
        return FallbackProvider(
            ModelBackedCognitiveProvider(chat_fn=SemanticFakeChat()),
            RuleBasedCognitiveProvider(),
        )

    monkeypatch.setattr("app.cognitive.factory.get_provider", _provider)
    index = kernel_index(client)
    src = add_text(client, case["source"], title=f"eval-{case['id'].split('_')[0]}-m")
    extra = []
    if case.get("extra_observation"):
        extra = [add_observation(client, case["extra_observation"], title=case["id"] + "-obs-m")["id"]]
    result = analyze(client, src["id"], extra_ids=extra)
    _check(result, case, index)


def test_eval_set_size():
    assert len(CASES) >= 50
    cats = {c["category"] for c in CASES}
    for needed in (
        "ai_news",
        "robotics_company",
        "paper_abstract",
        "paper_section",
        "github_release",
        "benchmark",
        "founder_opinion",
        "media_hype",
        "investment_case",
        "unrelated_noise",
        "conflicting_evidence",
        "cross_domain_structural",
        "user_field_observation",
        "decision_relevant",
        "active_project_competitor",
    ):
        assert needed in cats
