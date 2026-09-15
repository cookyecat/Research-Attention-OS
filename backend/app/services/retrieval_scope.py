from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from app.cognitive.client import chat_json
from app.config import settings
from app.services.acquisition_types import DiscoveredExternalItem

RETRIEVAL_SCOPE_VERSION = "retrieval-scope-guard-v0.1"

_SYSTEM = """You are a retrieval-scope guard, not an importance or attention judge.
Given one monitoring intent and search candidates, decide only whether each candidate is substantially about that monitored subject.
Do not judge usefulness, novelty, importance, D/S/P, or Attention.
Reject incidental mentions, broad courses/lists/news roundups that merely contain the words, and neighboring topics that do not instantiate the monitored subject.
For role/agent intents, require the candidate's central subject to actually instantiate that role. Example: for "AI research agents conducting scientific discovery", accept systems/agents/audits where agents perform research/discovery; reject courses about agentic AI, generic AI-for-science methods, search tools for human researchers, or scientific papers that use LLMs but do not center on research agents.
Accept semantic paraphrases even when exact keywords differ.
Return JSON only: {"decisions":[{"id":"...","in_scope":true,"reason":"short"}]}.
"""


@dataclass(frozen=True)
class ScopeGuardResult:
    accepted_ids: frozenset[str]
    status: str
    version: str = RETRIEVAL_SCOPE_VERSION
    model_meta: dict | None = None
    reasons: dict[str, str] | None = None
    error: str | None = None


def _candidate_text(item: DiscoveredExternalItem) -> str:
    metadata = item.metadata or {}
    return "\n".join(
        part for part in [
            str(item.title or "").strip(),
            str(metadata.get("content_text") or "").strip(),
            str(metadata.get("fallback_content_text") or "").strip(),
        ] if part
    )[:1800]


def semantic_scope_guard(
    intent: str,
    candidates: Iterable[DiscoveredExternalItem],
    *,
    chat_fn: Callable = chat_json,
) -> ScopeGuardResult:
    rows = list(candidates)
    if not rows:
        return ScopeGuardResult(frozenset(), "EMPTY")
    payload = []
    id_to_item: dict[str, DiscoveredExternalItem] = {}
    for idx, item in enumerate(rows):
        key = f"c{idx}"
        id_to_item[key] = item
        payload.append({"id": key, "title": item.title, "text": _candidate_text(item)})
    user = f"Monitoring intent: {intent}\nCandidates: {payload}"
    try:
        obj, meta = chat_fn(
            [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
            model=settings.llm_model,
            timeout=30.0,
            thinking="disabled",
            reasoning_effort=None,
            temperature=0.0,
        )
        accepted: set[str] = set()
        reasons: dict[str, str] = {}
        for decision in obj.get("decisions") or []:
            key = str(decision.get("id") or "")
            if key not in id_to_item:
                continue
            if bool(decision.get("in_scope")):
                accepted.add(key)
            reasons[key] = str(decision.get("reason") or "")
        # Missing decisions fail closed for the active WATCH bundle, but the raw
        # platform observations remain visible in the adapter report.
        return ScopeGuardResult(frozenset(accepted), "OK", model_meta=meta, reasons=reasons)
    except Exception as exc:
        return ScopeGuardResult(
            frozenset(), "ERROR", error=f"{type(exc).__name__}: {exc}"
        )
