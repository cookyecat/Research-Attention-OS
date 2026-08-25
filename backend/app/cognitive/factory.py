from __future__ import annotations

from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.config import settings


class FallbackProvider:
    """Model-backed with deterministic rule fallback. Never loses the Source."""

    def __init__(self, primary: ModelBackedCognitiveProvider, fallback: RuleBasedCognitiveProvider):
        self.primary = primary
        self.fallback = fallback
        self.provider_type = "model"
        self.fallback_used = False

    def _call(self, name: str, *args, **kwargs):
        if self.fallback_used:
            return getattr(self.fallback, name)(*args, **kwargs)
        try:
            return getattr(self.primary, name)(*args, **kwargs)
        except Exception:
            self.fallback_used = True
            self.provider_type = "model+rule-fallback"
            return getattr(self.fallback, name)(*args, **kwargs)

    @property
    def last_meta(self) -> dict:
        return getattr(self.primary, "last_meta", {}) or {}

    def extract_information(self, *args, **kwargs):
        return self._call("extract_information", *args, **kwargs)

    def match_kernel(self, *args, **kwargs):
        return self._call("match_kernel", *args, **kwargs)

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
        return rule
    model = ModelBackedCognitiveProvider(chat_fn=chat_fn) if chat_fn else ModelBackedCognitiveProvider()
    if kind == "model":
        return FallbackProvider(model, rule)
    return rule
