from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx

from app.config import settings


class LLMError(RuntimeError):
    pass


def estimate_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    """Rough OpenAI-mini-class estimate; recorded, not optimized."""
    return round((prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000, 8)


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
    }
    return parsed, meta


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
