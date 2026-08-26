from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from app.cognitive.client import LLMTimeoutError, chat_json, thinking_request_fields
from app.cognitive.factory import FallbackProvider
from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.cognitive.runtime import STAGE_RUNTIME
from app.config import settings
from app.models.kernel import KernelNode
from tests.fakes import SemanticFakeChat


EXTRACT_TEXT = "The founder says the robot generalizes zero-shot. In the video, it succeeds once."


class RecordingChat(SemanticFakeChat):
    def __init__(self):
        super().__init__()
        self.kwargs: list[dict] = []
        self.by_stage: dict[str, dict] = {}

    def __call__(self, messages, **kwargs):
        self.kwargs.append(dict(kwargs))
        system = (messages[0].get("content") or "").lower()
        if "extraction stage" in system:
            self.by_stage["extraction"] = dict(kwargs)
        elif "match extracted" in system or "embedding retrieval" in system:
            self.by_stage["matching"] = dict(kwargs)
        elif "relate claims" in system or "stances:" in system:
            self.by_stage["evidence"] = dict(kwargs)
        elif "model delta" in system or "what this information could change" in system:
            self.by_stage["delta"] = dict(kwargs)
        elif "judge scheduler" in system or "you do not choose drop" in system:
            self.by_stage["judgment"] = dict(kwargs)
        return super().__call__(messages, **kwargs)


class TimeoutChat:
    def __call__(self, messages, **kwargs):
        raise LLMTimeoutError(float(kwargs.get("timeout") or 60.0))


class _FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [{"message": {"content": '{"ok": true}'}}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 6},
            "model": "captured",
        }


class _CapturingClient:
    last_payload = None
    last_timeout = None

    def __init__(self, timeout=None):
        type(self).last_timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, json=None, headers=None):
        type(self).last_payload = json
        return _FakeResponse()


class _TimeoutClient:
    def __init__(self, timeout=None):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, *args, **kwargs):
        raise httpx.TimeoutException("timed out")


def test_stage_runtime_defaults():
    assert STAGE_RUNTIME["extraction"].thinking == "disabled"
    assert STAGE_RUNTIME["extraction"].timeout == 60.0
    assert STAGE_RUNTIME["matching"].thinking == "disabled"
    assert STAGE_RUNTIME["judgment"].thinking == "disabled"
    assert STAGE_RUNTIME["evidence"].thinking == "enabled"
    assert STAGE_RUNTIME["evidence"].reasoning_effort == "low"
    assert STAGE_RUNTIME["evidence"].timeout == 120.0
    assert STAGE_RUNTIME["delta"].thinking == "enabled"
    assert STAGE_RUNTIME["delta"].reasoning_effort == "low"
    assert STAGE_RUNTIME["delta"].timeout == 120.0


def test_extraction_disables_thinking():
    chat = RecordingChat()
    provider = ModelBackedCognitiveProvider(chat_fn=chat)
    result = provider.extract_information(EXTRACT_TEXT, "TEXT")
    assert result.claims
    kw = chat.by_stage["extraction"]
    assert kw["thinking"] == "disabled"
    assert kw["reasoning_effort"] is None
    assert kw["timeout"] == 60.0


def test_evidence_and_delta_enable_reasoning():
    chat = RecordingChat()
    provider = ModelBackedCognitiveProvider(chat_fn=chat)
    extraction = provider.extract_information(EXTRACT_TEXT, "TEXT")
    extraction = provider.reason_evidence(extraction)
    assert chat.by_stage["evidence"]["thinking"] == "enabled"
    assert chat.by_stage["evidence"]["reasoning_effort"] == "low"
    assert chat.by_stage["evidence"]["timeout"] == 120.0

    node = KernelNode(node_type="BELIEF", title="motor intelligence", status="ACTIVE", payload={"text": "embodied latency"})
    node.id = uuid4()
    matches = provider.match_kernel(extraction, [node])
    assert chat.by_stage["matching"]["thinking"] == "disabled"
    assert chat.by_stage["matching"]["timeout"] == 60.0

    features = provider.judge_features(EXTRACT_TEXT, extraction, matches)
    assert chat.by_stage["judgment"]["thinking"] == "disabled"
    assert chat.by_stage["judgment"]["timeout"] == 60.0

    provider.propose_model_delta(EXTRACT_TEXT, extraction, matches, features, [node])
    assert chat.by_stage["delta"]["thinking"] == "enabled"
    assert chat.by_stage["delta"]["reasoning_effort"] == "low"
    assert chat.by_stage["delta"]["timeout"] == 120.0


def test_timeout_fallback_provenance():
    provider = FallbackProvider(
        ModelBackedCognitiveProvider(chat_fn=TimeoutChat()),
        RuleBasedCognitiveProvider(),
    )
    result = provider.extract_information("A technical paper about motor intelligence latency.", "TEXT")
    rec = provider.stage_provenance["extraction"]
    assert rec["status"] == "fallback"
    assert rec["provider"] == "rule"
    assert rec["fallback_from"] == "model"
    assert rec["error_type"] == "timeout"
    assert rec["thinking"] == "disabled"
    assert rec["timeout"] == 60.0
    assert rec["reasoning_effort"] is None
    assert provider.fallback_used is True

    provider.match_kernel(result, [])
    later = provider.stage_provenance["matching"]
    assert later["status"] == "rule-after-fallback"
    assert later["fallback_from"] == "model"
    assert later["note"]


def test_thinking_omitted_for_openai_compatible_protocol(monkeypatch):
    monkeypatch.setattr(settings, "llm_thinking_protocol", "none")
    assert thinking_request_fields("disabled", None) == {}
    assert thinking_request_fields("enabled", "low") == {}

    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr("app.cognitive.client.httpx.Client", _CapturingClient)
    chat_json(
        [{"role": "user", "content": "hi"}],
        thinking="enabled",
        reasoning_effort="low",
        timeout=12.0,
    )
    payload = _CapturingClient.last_payload
    assert "thinking" not in payload
    assert "reasoning_effort" not in payload
    assert _CapturingClient.last_timeout == 12.0


def test_deepseek_protocol_sends_thinking_fields(monkeypatch):
    monkeypatch.setattr(settings, "llm_thinking_protocol", "deepseek")
    assert thinking_request_fields("disabled", None) == {"thinking": {"type": "disabled"}}
    assert thinking_request_fields("enabled", "low") == {
        "thinking": {"type": "enabled"},
        "reasoning_effort": "low",
    }

    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr("app.cognitive.client.httpx.Client", _CapturingClient)
    chat_json([{"role": "user", "content": "hi"}], thinking="disabled", timeout=60.0)
    assert _CapturingClient.last_payload["thinking"] == {"type": "disabled"}
    assert "reasoning_effort" not in _CapturingClient.last_payload

    chat_json(
        [{"role": "user", "content": "hi"}],
        thinking="enabled",
        reasoning_effort="low",
        timeout=120.0,
    )
    assert _CapturingClient.last_payload["thinking"] == {"type": "enabled"}
    assert _CapturingClient.last_payload["reasoning_effort"] == "low"


def test_chat_json_timeout_becomes_llm_timeout_error(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr("app.cognitive.client.httpx.Client", _TimeoutClient)
    with pytest.raises(LLMTimeoutError) as exc:
        chat_json([{"role": "user", "content": "hi"}], timeout=7.5)
    assert exc.value.timeout == 7.5
