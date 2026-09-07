"""Explicit-max-token JSON chat transport for the open-stop development probe.

Kept separate from the production client so the experiment can raise completion headroom
without changing production defaults.
"""
from __future__ import annotations

import time
from typing import Any

import httpx


def chat_json_with_max_tokens(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    timeout: float = 120.0,
    thinking=None,
    reasoning_effort=None,
    max_tokens: int = 16384,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from app.config import settings
    from app.cognitive.client import (
        LLMError,
        LLMTimeoutError,
        _parse_json_object,
        estimate_cost_usd,
        thinking_request_fields,
    )

    if not settings.llm_api_key:
        raise LLMError("RAOS_LLM_API_KEY is not set")
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model or settings.llm_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": messages,
        "max_tokens": int(max_tokens),
    }
    payload.update(thinking_request_fields(thinking, reasoning_effort))
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
    except httpx.TimeoutException as exc:
        raise LLMTimeoutError(timeout, f"timeout after {timeout}s: {exc}") from exc
    except Exception as exc:
        raise LLMError(str(exc)) from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    choice = body["choices"][0]
    content = choice["message"]["content"]
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
        "thinking": thinking,
        "reasoning_effort": reasoning_effort,
        "timeout": timeout,
        "finish_reason": choice.get("finish_reason"),
        "max_tokens": int(max_tokens),
        "raw_content_chars": len(content or ""),
    }
    return parsed, meta
