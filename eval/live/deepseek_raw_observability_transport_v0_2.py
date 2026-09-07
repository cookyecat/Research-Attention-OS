"""Raw DeepSeek Chat Completions transport for thinking-mode diagnostics.

Development-only instrumentation. The key rule is observability before parsing:
we always collect provider response metadata / usage / cache / reasoning counters before
attempting to parse the final answer as JSON.

Reasoning text is never persisted by this module. Only presence, character count, and
SHA256 are recorded. Final answer content may be returned to the caller for normal schema
validation; malformed content is represented by parse diagnostics rather than raising away
provider metadata.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any, Literal

import httpx

ThinkingType = Literal["enabled", "disabled"]
ReasoningEffort = Literal["low", "high", "max"]


def _sha256_text(text: str) -> str | None:
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_json_object(content: str) -> tuple[dict[str, Any] | None, str | None]:
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except Exception as exc:
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "model JSON must be an object"
    return data, None


def chat_deepseek_raw_observable(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    timeout: float = 300.0,
    thinking: ThinkingType,
    reasoning_effort: ReasoningEffort | None = None,
    max_tokens: int = 32768,
    response_format: str = "json_object",
) -> dict[str, Any]:
    """Return raw provider observability plus optional parsed final JSON.

    This function intentionally does not use the generic RAOS chat_json helper because
    malformed final JSON is itself a first-class diagnostic outcome in this experiment.
    """
    from app.config import settings

    if not settings.llm_api_key:
        raise RuntimeError("RAOS_LLM_API_KEY is not set")

    payload: dict[str, Any] = {
        "model": model or settings.llm_model,
        "messages": messages,
        "stream": False,
        "response_format": {"type": response_format},
        "max_tokens": int(max_tokens),
        "thinking": {"type": thinking},
    }
    # DeepSeek documents sampling parameters as ignored in thinking mode, so this
    # diagnostic does not send temperature/top_p when thinking is enabled.
    if thinking == "disabled":
        payload["temperature"] = 0.1
    if thinking == "enabled" and reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort

    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    started = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            status_code = response.status_code
            response.raise_for_status()
            body = response.json()
    except httpx.TimeoutException as exc:
        raise RuntimeError(f"DeepSeek timeout after {timeout}s: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"DeepSeek request failed: {exc}") from exc
    latency_ms = int((time.perf_counter() - started) * 1000)

    choices = body.get("choices") or []
    choice = choices[0] if choices else {}
    message = choice.get("message") or {}
    content = message.get("content") or ""
    reasoning_content = message.get("reasoning_content") or ""
    usage = body.get("usage") or {}
    completion_details = usage.get("completion_tokens_details") or {}

    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    cache_hit_tokens = int(usage.get("prompt_cache_hit_tokens") or 0)
    cache_miss_tokens = int(usage.get("prompt_cache_miss_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    reasoning_tokens = int(completion_details.get("reasoning_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or 0)
    visible_output_tokens = max(0, completion_tokens - reasoning_tokens)

    parsed_json, parse_error = _parse_json_object(content)

    return {
        "http_status": status_code,
        "provider_response": {
            "id": body.get("id"),
            "model": body.get("model") or (model or settings.llm_model),
            "system_fingerprint": body.get("system_fingerprint"),
            "object": body.get("object"),
            "created": body.get("created"),
            "finish_reason": choice.get("finish_reason"),
        },
        "request": {
            "thinking": thinking,
            "reasoning_effort": reasoning_effort if thinking == "enabled" else None,
            "max_tokens": int(max_tokens),
            "response_format": response_format,
            "temperature_sent": 0.1 if thinking == "disabled" else None,
        },
        "usage": {
            "prompt_tokens": prompt_tokens,
            "prompt_cache_hit_tokens": cache_hit_tokens,
            "prompt_cache_miss_tokens": cache_miss_tokens,
            "cache_accounting_matches_prompt": (
                prompt_tokens == cache_hit_tokens + cache_miss_tokens
                if (cache_hit_tokens or cache_miss_tokens)
                else None
            ),
            "completion_tokens": completion_tokens,
            "reasoning_tokens": reasoning_tokens,
            "visible_output_tokens_derived": visible_output_tokens,
            "total_tokens": total_tokens,
            "raw_usage": usage,
        },
        "reasoning_observability": {
            "present": bool(reasoning_content),
            "chars": len(reasoning_content),
            "sha256": _sha256_text(reasoning_content),
            "content_persisted": False,
        },
        "final_content_observability": {
            "chars": len(content),
            "sha256": _sha256_text(content),
            "head": content[:600],
            "tail": content[-1200:],
            "json_parse_success": parsed_json is not None,
            "json_parse_error": parse_error,
        },
        "latency_ms": latency_ms,
        "parsed_json": parsed_json,
    }


__all__ = ["chat_deepseek_raw_observable"]
