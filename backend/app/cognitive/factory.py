from __future__ import annotations

from app.cognitive.client import LLMTimeoutError, SchemaValidationError, estimate_cost_usd
from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.config import settings


def _runtime_fields(primary) -> dict:
    runtime = getattr(primary, "last_stage_runtime", None) or {}
    return {
        "thinking": runtime.get("thinking"),
        "reasoning_effort": runtime.get("reasoning_effort"),
        "timeout": runtime.get("timeout"),
        "llm_called": runtime.get("llm_called"),
    }


def _error_type(exc: Exception) -> str:
    if isinstance(exc, LLMTimeoutError):
        return "timeout"
    if isinstance(exc, SchemaValidationError):
        return "schema"
    return type(exc).__name__

STAGE_NAMES = {
    "extract_information": "extraction",
    "match_kernel": "matching",
    "reason_evidence": "evidence",
    "judge_features": "judgment",
    "propose_model_delta": "delta",
    "propose_patches": "patches",
}


class FallbackProvider:
    """Model-backed with sticky deterministic rule fallback. Stage provenance is recorded."""

    def __init__(self, primary: ModelBackedCognitiveProvider, fallback: RuleBasedCognitiveProvider):
        self.primary = primary
        self.fallback = fallback
        self.provider_type = "model"
        self.fallback_used = False
        self.stage_provenance: dict = {}
        self.last_retrieval: dict | None = None

    def _call(self, name: str, *args, **kwargs):
        stage = STAGE_NAMES.get(name, name)
        before = {
            "latency_ms": int(getattr(self.primary, "last_meta", {}).get("latency_ms") or 0),
            "prompt_tokens": int(getattr(self.primary, "last_meta", {}).get("prompt_tokens") or 0),
            "completion_tokens": int(getattr(self.primary, "last_meta", {}).get("completion_tokens") or 0),
        }
        if self.fallback_used:
            result = getattr(self.fallback, name)(*args, **kwargs)
            self.stage_provenance[stage] = {
                "provider": "rule",
                "model": None,
                "status": "rule-after-fallback",
                "fallback_from": "model",
                "thinking": None,
                "reasoning_effort": None,
                "timeout": None,
                "note": "sticky fallback; not a model prediction",
            }
            return result
        try:
            result = getattr(self.primary, name)(*args, **kwargs)
            after = getattr(self.primary, "last_meta", {}) or {}
            events = list(getattr(self.primary, "last_validation_events", []) or [])
            retry = 1 if any(e.get("retry") == 1 and e.get("status") == "repaired" for e in events) else 0
            rec = {
                "provider": "model",
                "model": after.get("model") or settings.llm_model,
                "status": "success",
                "retry": retry,
                "latency_ms": int(after.get("latency_ms") or 0) - before["latency_ms"],
                "prompt_tokens": int(after.get("prompt_tokens") or 0) - before["prompt_tokens"],
                "completion_tokens": int(after.get("completion_tokens") or 0) - before["completion_tokens"],
                "estimated_cost_usd": estimate_cost_usd(
                    int(after.get("prompt_tokens") or 0) - before["prompt_tokens"],
                    int(after.get("completion_tokens") or 0) - before["completion_tokens"],
                ),
                "validation_events": events,
            }
            rec.update(_runtime_fields(self.primary))
            self.stage_provenance[stage] = rec
            return result
        except Exception as exc:
            self.fallback_used = True
            self.provider_type = "model+rule-fallback"
            result = getattr(self.fallback, name)(*args, **kwargs)
            after = getattr(self.primary, "last_meta", {}) or {}
            rec = {
                "provider": "rule",
                "model": None,
                "status": "fallback",
                "fallback_from": "model",
                "error": str(exc)[:2000],
                "error_type": _error_type(exc),
                "retry": 1 if isinstance(exc, SchemaValidationError) and exc.retry_used else 0,
                "latency_ms": int(after.get("latency_ms") or 0) - before["latency_ms"],
                "prompt_tokens": int(after.get("prompt_tokens") or 0) - before["prompt_tokens"],
                "completion_tokens": int(after.get("completion_tokens") or 0) - before["completion_tokens"],
            }
            rec.update(_runtime_fields(self.primary))
            if isinstance(exc, SchemaValidationError):
                rec["validation_error"] = exc.errors
            if isinstance(exc, LLMTimeoutError):
                rec["timeout"] = rec.get("timeout") if rec.get("timeout") is not None else exc.timeout
            self.stage_provenance[stage] = rec
            return result

    @property
    def last_meta(self) -> dict:
        return getattr(self.primary, "last_meta", {}) or {}

    def extract_information(self, *args, **kwargs):
        return self._call("extract_information", *args, **kwargs)

    def match_kernel(self, *args, **kwargs):
        result = self._call("match_kernel", *args, **kwargs)
        rec = self.stage_provenance.get("matching") or {}
        if rec.get("status") in {"fallback", "rule-after-fallback"}:
            self.last_retrieval = {
                "embedding_used": False,
                "lexical_fallback": True,
                "method": "lexical",
                "embedding_model": None,
                "query_instruct_applied": False,
            }
        else:
            self.last_retrieval = getattr(self.primary, "last_retrieval", None)
        return result

    def reason_evidence(self, *args, **kwargs):
        return self._call("reason_evidence", *args, **kwargs)

    def judge_features(self, *args, **kwargs):
        return self._call("judge_features", *args, **kwargs)

    def propose_model_delta(self, *args, **kwargs):
        return self._call("propose_model_delta", *args, **kwargs)

    def propose_patches(self, *args, **kwargs):
        return self._call("propose_patches", *args, **kwargs)


def get_provider(*, chat_fn=None):
    kind = (settings.cognitive_provider or "rule").lower()
    rule = RuleBasedCognitiveProvider()
    if kind == "rule":
        rule.stage_provenance = {
            "extraction": {"provider": "rule", "status": "success"},
            "matching": {"provider": "rule", "status": "success"},
            "evidence": {"provider": "rule", "status": "success"},
            "judgment": {"provider": "rule", "status": "success"},
            "delta": {"provider": "rule", "status": "success"},
            "patches": {"provider": "deterministic", "status": "success"},
        }
        return rule
    model = ModelBackedCognitiveProvider(chat_fn=chat_fn) if chat_fn else ModelBackedCognitiveProvider()
    if kind == "model":
        return FallbackProvider(model, rule)
    return rule
