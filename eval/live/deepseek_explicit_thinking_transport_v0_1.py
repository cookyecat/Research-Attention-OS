"""DeepSeek-specific explicit thinking transport for controlled development A/B.

This bypasses RAOS_LLM_THINKING_PROTOCOL so the wire-level thinking state is unambiguous.
It stores reasoning observability only (token count / presence / character count), never
reasoning text.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Literal

import httpx

ThinkingType = Literal["enabled", "disabled"]
ReasoningEffort = Literal["low", "high", "max"]


class DeepSeekJSONParseError(RuntimeError):
    """Final answer JSON failed parsing, while preserving provider diagnostics."""

    def __init__(self, message: str, *, meta: dict[str, Any], raw_content_tail: str):
        super().__init__(message)
        self.meta = meta
        self.raw_content_tail = raw_content_tail


def _parse_json_object(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("model JSON must be an object")
    return data


def chat_json_deepseek_explicit_thinking(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    timeout: float = 180.0,
    thinking: ThinkingType,
    reasoning_effort: ReasoningEffort | None = None,
    max_tokens: int = 16384,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from app.config import settings
    from app.cognitive.client import LLMError, LLMTimeoutError, estimate_cost_usd

    if not settings.llm_api_key:
        raise LLMError("RAOS_LLM_API_KEY is not set")

    payload: dict[str, Any] = {
        "model": model or settings.llm_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": messages,
        "max_tokens": int(max_tokens),
        "thinking": {"type": thinking},
    }
    if thinking == "enabled" and reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort

    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
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
    message = choice["message"]
    content = message.get("content") or ""
    reasoning_content = message.get("reasoning_content") or ""
    usage = body.get("usage") or {}
    completion_details = usage.get("completion_tokens_details") or {}

    # Construct diagnostics BEFORE parsing so malformed/truncated JSON remains observable.
    meta = {
        "latency_ms": latency_ms,
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "reasoning_tokens": int(completion_details.get("reasoning_tokens") or 0),
        "model": body.get("model") or (model or settings.llm_model),
        "estimated_cost_usd": estimate_cost_usd(
            int(usage.get("prompt_tokens") or 0),
            int(usage.get("completion_tokens") or 0),
        ),
        "thinking_wire": thinking,
        "reasoning_effort_wire": reasoning_effort if thinking == "enabled" else None,
        "reasoning_content_present": bool(reasoning_content),
        "reasoning_content_chars": len(reasoning_content),
        "timeout": timeout,
        "finish_reason": choice.get("finish_reason"),
        "max_tokens": int(max_tokens),
        "raw_content_chars": len(content),
        "temperature_requested": 0.1,
        "temperature_note": "DeepSeek documents temperature as ignored when thinking is enabled.",
    }

    try:
        parsed = _parse_json_object(content)
    except Exception as exc:
        raise DeepSeekJSONParseError(
            f"model did not return JSON: {exc}",
            meta=meta,
            raw_content_tail=content[-1200:],
        ) from exc

    return parsed, meta
