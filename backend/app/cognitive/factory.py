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
        "evidence_stage_skipped": runtime.get("evidence_stage_skipped"),
        "evidence_skip_reason": runtime.get("evidence_skip_reason"),
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
    "judge_features": "impact",
    "assess_cognitive_impact": "impact",
    "propose_model_delta": "delta",
    "propose_patches": "patches",
}

FALLBACK_STATUSES = frozenset({"fallback", "rule-after-fallback"})


class FallbackProvider:
    """Model-backed with stage-scoped deterministic rule fallback.

    Each stage tries the model independently. A later-stage failure must not
    skip or overwrite earlier stages. Repeated calls to the same stage
    (chunked extraction) keep the first failure's error/error_type.
    """

    def __init__(self, primary: ModelBackedCognitiveProvider, fallback: RuleBasedCognitiveProvider):
        self.primary = primary
        self.fallback = fallback
        self.provider_type = "model"
        self.fallback_used = False
        self.stage_provenance: dict = {}
        self.last_retrieval: dict | None = None

    def _attempt_record(self, rec: dict) -> dict:
        keys = ("status", "provider", "error", "error_type", "fallback_from")
        return {k: rec[k] for k in keys if rec.get(k) is not None}

    def _merge_stage_record(self, stage: str, rec: dict) -> None:
        prev = self.stage_provenance.get(stage)
        if prev is None:
            rec = dict(rec)
            rec["attempts"] = [self._attempt_record(rec)]
            self.stage_provenance[stage] = rec
            return
        merged = dict(prev)
        attempts = list(prev.get("attempts") or [self._attempt_record(prev)])
        attempts.append(self._attempt_record(rec))
        merged["attempts"] = attempts
        if not prev.get("error") and rec.get("error"):
            merged["error"] = rec["error"]
            merged["error_type"] = rec.get("error_type")
            merged["fallback_from"] = rec.get("fallback_from") or prev.get("fallback_from")
            if rec.get("validation_error") and not prev.get("validation_error"):
                merged["validation_error"] = rec["validation_error"]
        if rec.get("status") in FALLBACK_STATUSES or prev.get("status") in FALLBACK_STATUSES:
            merged["status"] = "fallback"
        providers = {prev.get("provider"), rec.get("provider")} - {None}
        if len(providers) > 1:
            merged["provider"] = "mixed"
        elif rec.get("provider") and not prev.get("provider"):
            merged["provider"] = rec["provider"]
        if rec.get("model") and not merged.get("model"):
            merged["model"] = rec["model"]
        for key in ("latency_ms", "prompt_tokens", "completion_tokens"):
            merged[key] = int(prev.get(key) or 0) + int(rec.get(key) or 0)
        if rec.get("estimated_cost_usd") is not None or prev.get("estimated_cost_usd") is not None:
            merged["estimated_cost_usd"] = float(prev.get("estimated_cost_usd") or 0) + float(
                rec.get("estimated_cost_usd") or 0
            )
        events = list(prev.get("validation_events") or [])
        events.extend(rec.get("validation_events") or [])
        if events:
            merged["validation_events"] = events
        self.stage_provenance[stage] = merged

    def _call(self, name: str, *args, **kwargs):
        stage = STAGE_NAMES.get(name, name)
        before = {
            "latency_ms": int(getattr(self.primary, "last_meta", {}).get("latency_ms") or 0),
            "prompt_tokens": int(getattr(self.primary, "last_meta", {}).get("prompt_tokens") or 0),
            "completion_tokens": int(getattr(self.primary, "last_meta", {}).get("completion_tokens") or 0),
        }
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
            self._merge_stage_record(stage, rec)
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
            self._merge_stage_record(stage, rec)
            return result

    @property
    def last_meta(self) -> dict:
        return getattr(self.primary, "last_meta", {}) or {}

    def extract_information(self, *args, **kwargs):
        return self._call("extract_information", *args, **kwargs)

    def match_kernel(self, *args, **kwargs):
        result = self._call("match_kernel", *args, **kwargs)
        rec = self.stage_provenance.get("matching") or {}
        trace = dict(getattr(self.primary, "last_retrieval", None) or {})
        if rec.get("status") in FALLBACK_STATUSES:
            if not trace:
                trace = {
                    "embedding_used": False,
                    "lexical_fallback": True,
                    "method": "lexical",
                    "embedding_model": None,
                    "query_instruct_applied": False,
                    "candidates": [],
                }
            trace["matcher_fallback"] = True
            self.last_retrieval = trace
        else:
            self.last_retrieval = trace or getattr(self.primary, "last_retrieval", None)
        return result

    def reason_evidence(self, *args, **kwargs):
        return self._call("reason_evidence", *args, **kwargs)

    def judge_features(self, *args, **kwargs):
        return self._call("judge_features", *args, **kwargs)

    def assess_cognitive_impact(self, *args, **kwargs):
        return self._call("assess_cognitive_impact", *args, **kwargs)

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
            "impact": {"provider": "rule", "status": "success"},
            "judgment": {"provider": "rule", "status": "success"},
            "delta": {"provider": "rule", "status": "success"},
            "patches": {"provider": "deterministic", "status": "success"},
        }
        return rule
    model = ModelBackedCognitiveProvider(chat_fn=chat_fn) if chat_fn else ModelBackedCognitiveProvider()
    if kind == "model":
        return FallbackProvider(model, rule)
    return rule
