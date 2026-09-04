"""Locally-controlled AnalysisRun execution fingerprint.

Not a version system and not a config dump. Hash effective E_t / L_t / Δ_t inputs
that existing component versions do not already cover.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import urlsplit

from app.cognitive.client import thinking_request_fields
from app.cognitive.runtime import STAGE_RUNTIME, StageRuntime
from app.config import settings
from app.services.retrieval import query_instruct_enabled

_MODEL_STAGES = ("extraction", "matching", "evidence", "impact")


def sanitized_endpoint_identity(url: str | None) -> str | None:
    """Scheme + host + port + path. No userinfo, query, fragment, or credential."""
    if not url or not str(url).strip():
        return None
    parts = urlsplit(str(url).strip())
    if not parts.scheme or not parts.hostname:
        return None
    host = parts.hostname
    netloc = f"{host}:{parts.port}" if parts.port else host
    path = (parts.path or "").rstrip("/")
    return f"{parts.scheme.lower()}://{netloc}{path}"


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _model_backend(provider) -> Any | None:
    if provider is None:
        return None
    primary = getattr(provider, "primary", None)
    if primary is not None and getattr(primary, "provider_type", None) == "model":
        return primary
    if getattr(provider, "provider_type", None) == "model" and not hasattr(provider, "fallback"):
        return provider
    if type(provider).__name__ == "ModelBackedCognitiveProvider":
        return provider
    return None


def _uses_model_llm(provider) -> bool:
    return _model_backend(provider) is not None


def uses_embedding_retrieval(provider) -> bool:
    """Model/fallback Locate consumes embeddings. Rule matching is lexical-only."""
    return _model_backend(provider) is not None


def _llm_available() -> bool:
    return bool(settings.llm_api_key)


def _embedding_available() -> bool:
    return bool(settings.embedding_api_key or settings.llm_api_key) and bool(settings.embedding_model)


def _stage_budget(model_backend, stage: str) -> StageRuntime:
    if stage == "impact":
        override = getattr(model_backend, "_impact_runtime", None)
        if override is not None:
            return override
    return STAGE_RUNTIME.get(stage) or StageRuntime(thinking=None, reasoning_effort=None, timeout=45.0)


def _stage_execution(model_backend, stage: str) -> dict[str, Any]:
    budget = _stage_budget(model_backend, stage)
    return {
        "timeout": budget.timeout,
        "thinking_fields": thinking_request_fields(budget.thinking, budget.reasoning_effort),
    }


def _llm_execution(model_backend) -> dict[str, Any]:
    if not _llm_available():
        return {"available": False}
    impact_model = getattr(model_backend, "_impact_model", None) or settings.llm_model
    return {
        "available": True,
        "model": settings.llm_model,
        "impact_model": impact_model,
        "endpoint": sanitized_endpoint_identity(settings.llm_base_url),
        "stages": {stage: _stage_execution(model_backend, stage) for stage in _MODEL_STAGES},
    }


def _retrieval_execution() -> dict[str, Any]:
    if not _embedding_available():
        return {"available": False}
    embedding_url = settings.embedding_base_url or settings.llm_base_url
    return {
        "available": True,
        "model": settings.embedding_model,
        "endpoint": sanitized_endpoint_identity(embedding_url),
        "query_instruct_applied": query_instruct_enabled(),
        "dimensions": settings.embedding_dimensions,
    }


def analysis_execution_snapshot(provider=None) -> dict[str, Any]:
    from app.cognitive.versions import IMPACT_ASSESSOR_VERSION

    snapshot: dict[str, Any] = {
        "impact_assessor_version": IMPACT_ASSESSOR_VERSION,
        "chunking": {
            "max_chars": settings.long_source_chunk_chars,
            "overlap": settings.long_source_chunk_overlap,
        },
    }
    if _uses_model_llm(provider):
        snapshot["llm"] = _llm_execution(_model_backend(provider))
    if uses_embedding_retrieval(provider):
        snapshot["retrieval"] = _retrieval_execution()
    return snapshot


def analysis_execution_digest(provider=None, *, snapshot: dict[str, Any] | None = None) -> str:
    raw = _canonical_json(snapshot if snapshot is not None else analysis_execution_snapshot(provider))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
