from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings


class LLMError(RuntimeError):
    pass


class SchemaValidationError(LLMError):
    """Model output failed the structural schema after optional repair."""

    def __init__(self, message: str, *, errors: Any = None, retry_used: bool = False, raw: Any = None):
        super().__init__(message)
        self.errors = errors
        self.retry_used = retry_used
        self.raw = raw


class EmbeddingDimensionError(ValueError):
    pass


def estimate_cost_usd(prompt_tokens: int, completion_tokens: int) -> float | None:
    """Configured $/1M tokens. Unknown prices must be null — never a fake-precise default."""
    inp = settings.llm_input_cost_per_1m
    out = settings.llm_output_cost_per_1m
    if inp is None or out is None:
        return None
    return round((prompt_tokens * inp + completion_tokens * out) / 1_000_000, 8)


def merge_usage_meta(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = dict(a or {})
    out["latency_ms"] = int(out.get("latency_ms") or 0) + int(b.get("latency_ms") or 0)
    out["prompt_tokens"] = int(out.get("prompt_tokens") or 0) + int(b.get("prompt_tokens") or 0)
    out["completion_tokens"] = int(out.get("completion_tokens") or 0) + int(b.get("completion_tokens") or 0)
    out["model"] = b.get("model") or out.get("model")
    cost = estimate_cost_usd(out["prompt_tokens"], out["completion_tokens"])
    out["estimated_cost_usd"] = cost
    return out


def chat_json(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    timeout: float = 45.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """OpenAI-compatible chat completion expecting a JSON object."""
    if not settings.llm_api_key:
        raise LLMError("RAOS_LLM_API_KEY is not set")
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model or settings.llm_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": messages,
    }
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            body = resp.json()
    except Exception as exc:
        raise LLMError(str(exc)) from exc
    latency_ms = int((time.perf_counter() - started) * 1000)
    content = body["choices"][0]["message"]["content"]
    usage = body.get("usage") or {}
    parsed = _parse_json_object(content)
    meta = {
        "latency_ms": latency_ms,
        "prompt_tokens": usage.get("prompt_tokens") or 0,
        "completion_tokens": usage.get("completion_tokens") or 0,
        "model": body.get("model") or (model or settings.llm_model),
        "estimated_cost_usd": estimate_cost_usd(
            int(usage.get("prompt_tokens") or 0),
            int(usage.get("completion_tokens") or 0),
        ),
    }
    return parsed, meta


def chat_json_schema(
    messages: list[dict[str, str]],
    schema_cls: type[BaseModel],
    *,
    chat_fn=None,
    model: str | None = None,
) -> tuple[BaseModel, dict[str, Any], list[dict[str, Any]]]:
    """Parse JSON, validate with Pydantic, repair once, then fail closed."""
    fn = chat_fn or chat_json
    events: list[dict[str, Any]] = []
    parsed, meta = fn(messages, model=model)
    try:
        obj = schema_cls.model_validate(parsed)
        return obj, meta, events
    except ValidationError as exc:
        events.append(
            {
                "retry": 0,
                "status": "invalid",
                "error": exc.errors(include_url=False),
                "schema": schema_cls.__name__,
            }
        )
        repair_messages = list(messages) + [
            {"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)[:12000]},
            {
                "role": "user",
                "content": (
                    "Your JSON failed structural schema validation.\n"
                    f"Schema: {schema_cls.__name__}\n"
                    f"Errors: {exc.json()}\n"
                    "Return a corrected JSON object only. Do not omit required fields. "
                    "Do not invent values for missing evidence."
                ),
            },
        ]
        parsed2, meta2 = fn(repair_messages, model=model)
        meta = merge_usage_meta(meta, meta2)
        try:
            obj = schema_cls.model_validate(parsed2)
            events.append({"retry": 1, "status": "repaired", "schema": schema_cls.__name__})
            meta["schema_repaired"] = True
            return obj, meta, events
        except ValidationError as exc2:
            events.append(
                {
                    "retry": 1,
                    "status": "invalid",
                    "error": exc2.errors(include_url=False),
                    "schema": schema_cls.__name__,
                }
            )
            raise SchemaValidationError(
                f"{schema_cls.__name__} invalid after repair",
                errors=exc2.errors(include_url=False),
                retry_used=True,
                raw=parsed2,
            ) from exc2


def embed_texts(texts: list[str], *, timeout: float = 30.0) -> tuple[list[list[float]], str]:
    if not texts:
        return [], settings.embedding_model
    key = settings.embedding_api_key or settings.llm_api_key
    if not key:
        raise LLMError("embedding API key is not set")
    base = (settings.embedding_base_url or settings.llm_base_url).rstrip("/")
    url = base + "/embeddings"
    payload = {"model": settings.embedding_model, "input": texts}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            body = resp.json()
    except Exception as exc:
        raise LLMError(str(exc)) from exc
    vectors = [item["embedding"] for item in sorted(body["data"], key=lambda x: x["index"])]
    if settings.embedding_dimensions is not None:
        for vec in vectors:
            if len(vec) != settings.embedding_dimensions:
                raise EmbeddingDimensionError(
                    f"embedding dimension {len(vec)} != configured {settings.embedding_dimensions}"
                )
    return vectors, settings.embedding_model


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(f"model did not return JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMError("model JSON must be an object")
    return data
