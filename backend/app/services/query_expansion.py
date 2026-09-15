from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.cognitive.client import chat_json
from app.config import settings

QUERY_EXPANSION_VERSION = "query-expansion-v0.1"

_SYSTEM = """You expand a standing monitoring intent into a small set of search queries.
The purpose is retrieval recall, not importance judgment.
Rules:
1. Preserve the original intent exactly as the first query.
2. Add only aliases, concise entity/topic combinations, spelling variants, or natural cross-language equivalents that preserve the same intent.
3. Do not broaden to generic domain terms just to increase result count.
4. Prefer queries likely to retrieve genuinely different phrasings of the same monitored concept.
5. Return JSON only: {\"queries\": [\"...\"], \"anchor_groups\": [[\"term A\", \"synonym A\"], [\"term B\", \"synonym B\"]], \"note\": \"short rationale\"}.\n6. anchor_groups are the minimum SUBJECT concepts every retrieved candidate must still express. Each inner group lists lexical/cross-language equivalents for one required entity/technology/object concept; every candidate must match at least one term from every group. Keep 1-3 groups, few and discriminative. Do NOT make question/stance/effect words such as reduce, improve, replace, lack, prove, increase, effect, or their translations into required anchor groups; those are relations to investigate, not retrieval subjects.
"""


@dataclass(frozen=True)
class QueryExpansionPlan:
    version: str
    intent: str
    queries: tuple[str, ...]
    status: str
    note: str | None = None
    anchor_groups: tuple[tuple[str, ...], ...] = ()
    model_meta: dict | None = None
    error: str | None = None

    def as_dict(self) -> dict:
        return {
            "version": self.version,
            "intent": self.intent,
            "queries": list(self.queries),
            "status": self.status,
            "note": self.note,
            "anchor_groups": [list(group) for group in self.anchor_groups],
            "model_meta": self.model_meta,
            "error": self.error,
        }


def _clean_queries(intent: str, values, *, max_queries: int) -> tuple[str, ...]:
    limit = max(1, min(int(max_queries), 12))
    candidates = [intent]
    if isinstance(values, list):
        candidates.extend(str(value) for value in values)
    seen: set[str] = set()
    out: list[str] = []
    for raw in candidates:
        query = " ".join(str(raw or "").strip().split())
        if not query or len(query) > 180:
            continue
        key = query.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(query)
        if len(out) >= limit:
            break
    return tuple(out or [intent])



def _clean_anchor_groups(values) -> tuple[tuple[str, ...], ...]:
    groups: list[tuple[str, ...]] = []
    if not isinstance(values, list):
        return ()
    for raw_group in values[:4]:
        if not isinstance(raw_group, list):
            continue
        seen: set[str] = set()
        terms: list[str] = []
        for raw in raw_group[:8]:
            term = " ".join(str(raw or "").strip().split())
            if not term or len(term) > 100 or term.casefold() in seen:
                continue
            seen.add(term.casefold())
            terms.append(term)
        if terms:
            groups.append(tuple(terms))
    return tuple(groups)

def expand_query_intent(
    intent: str,
    *,
    context: str | None = None,
    max_queries: int = 6,
    chat_fn: Callable = chat_json,
) -> QueryExpansionPlan:
    normalized = " ".join((intent or "").strip().split())
    if not normalized:
        raise ValueError("Query expansion intent must be non-empty")
    user = f"Monitoring intent: {normalized}"
    if context:
        user += f"\nContext for disambiguation only: {context[:1200]}"
    try:
        obj, meta = chat_fn(
            [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
            model=settings.llm_model,
            timeout=25.0,
            thinking="disabled",
            reasoning_effort=None,
            temperature=0.1,
        )
        queries = _clean_queries(normalized, obj.get("queries"), max_queries=max_queries)
        return QueryExpansionPlan(
            version=QUERY_EXPANSION_VERSION,
            intent=normalized,
            queries=queries,
            status="OK",
            note=str(obj.get("note") or "").strip() or None,
            anchor_groups=_clean_anchor_groups(obj.get("anchor_groups")),
            model_meta=meta,
        )
    except Exception as exc:
        return QueryExpansionPlan(
            version=QUERY_EXPANSION_VERSION,
            intent=normalized,
            queries=(normalized,),
            status="FALLBACK_ORIGINAL_ONLY",
            error=f"{type(exc).__name__}: {exc}",
        )
