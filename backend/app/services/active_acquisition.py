from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from app.services.acquisition_types import DiscoveredExternalItem
from app.services.discovery_adapters import BilibiliSearchAdapter, HackerNewsSearchAdapter
from app.services.retrieval_scope import semantic_scope_guard

ACTIVE_QUERY_BUNDLE_VERSION = "active-query-bundle-v0.1"
_SUPPORTED_CHILDREN = {
    "HACKERNEWS_SEARCH": HackerNewsSearchAdapter,
    "BILIBILI_SEARCH": BilibiliSearchAdapter,
}


@dataclass(frozen=True)
class ActiveQueryBundleSpec:
    watch_id: str
    intent: str
    queries: tuple[str, ...]
    child_adapters: tuple[str, ...] = ("HACKERNEWS_SEARCH", "BILIBILI_SEARCH")
    per_query_limit: int = 10
    expansion_version: str = "query-expansion-v0.1"
    expansion_status: str = "OK"
    anchor_groups: tuple[tuple[str, ...], ...] = ()

    def as_dict(self) -> dict:
        return {
            "version": ACTIVE_QUERY_BUNDLE_VERSION,
            "watch_id": self.watch_id,
            "intent": self.intent,
            "queries": list(self.queries),
            "child_adapters": list(self.child_adapters),
            "per_query_limit": self.per_query_limit,
            "expansion_version": self.expansion_version,
            "expansion_status": self.expansion_status,
            "anchor_groups": [list(group) for group in self.anchor_groups],
        }

    def to_locator(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, separators=(",", ":"))


def parse_bundle_locator(locator: str) -> ActiveQueryBundleSpec:
    try:
        obj = json.loads(locator)
    except Exception as exc:
        raise ValueError("ACTIVE_QUERY_BUNDLE locator must be valid JSON") from exc
    if obj.get("version") != ACTIVE_QUERY_BUNDLE_VERSION:
        raise ValueError(f"Unsupported active query bundle version: {obj.get('version')}")
    watch_id = str(obj.get("watch_id") or "").strip()
    intent = " ".join(str(obj.get("intent") or "").split())
    queries = tuple(dict.fromkeys(" ".join(str(q or "").split()) for q in (obj.get("queries") or []) if str(q or "").strip()))
    children = tuple(str(x).upper() for x in (obj.get("child_adapters") or []))
    if not watch_id or not intent or not queries:
        raise ValueError("ACTIVE_QUERY_BUNDLE requires watch_id, intent, and queries")
    unsupported = [child for child in children if child not in _SUPPORTED_CHILDREN]
    if unsupported:
        raise ValueError(f"Unsupported active query child adapters: {unsupported}")
    limit = max(1, min(int(obj.get("per_query_limit") or 10), 50))
    return ActiveQueryBundleSpec(
        watch_id=watch_id,
        intent=intent,
        queries=queries,
        child_adapters=children or tuple(_SUPPORTED_CHILDREN),
        per_query_limit=limit,
        expansion_version=str(obj.get("expansion_version") or "unknown"),
        expansion_status=str(obj.get("expansion_status") or "unknown"),
        anchor_groups=tuple(tuple(str(term) for term in group) for group in (obj.get("anchor_groups") or []) if isinstance(group, list)),
    )


def _copy_with_provenance(item: DiscoveredExternalItem, *, spec: ActiveQueryBundleSpec, child: str, query: str) -> DiscoveredExternalItem:
    metadata = dict(item.metadata or {})
    metadata["active_query_bundle"] = {
        "version": ACTIVE_QUERY_BUNDLE_VERSION,
        "watch_id": spec.watch_id,
        "intent": spec.intent,
        "matches": [{"child_adapter": child, "query": query}],
        "expansion_version": spec.expansion_version,
        "expansion_status": spec.expansion_status,
    }
    return DiscoveredExternalItem(
        ref=item.ref,
        external_id=item.external_id,
        title=item.title,
        published_at=item.published_at,
        metadata=metadata,
    )


def _merge_duplicate(existing: DiscoveredExternalItem, incoming: DiscoveredExternalItem) -> DiscoveredExternalItem:
    metadata = dict(existing.metadata or {})
    bundle = dict(metadata.get("active_query_bundle") or {})
    matches = list(bundle.get("matches") or [])
    for match in ((incoming.metadata or {}).get("active_query_bundle") or {}).get("matches") or []:
        if match not in matches:
            matches.append(match)
    bundle["matches"] = matches
    metadata["active_query_bundle"] = bundle
    return DiscoveredExternalItem(
        ref=existing.ref,
        external_id=existing.external_id or incoming.external_id,
        title=existing.title or incoming.title,
        published_at=existing.published_at or incoming.published_at,
        metadata=metadata,
    )


def _within_scope(item: DiscoveredExternalItem, anchor_groups: tuple[tuple[str, ...], ...]) -> bool:
    if not anchor_groups:
        return True
    metadata = item.metadata or {}
    haystack = " ".join([str(item.title or ""), str(metadata.get("content_text") or ""), str(metadata.get("fallback_content_text") or "")]).casefold()
    return all(any(term.casefold() in haystack for term in group if term.strip()) for group in anchor_groups)


class ActiveQueryBundleAdapter:
    source_type = "ACTIVE_QUERY_BUNDLE"

    def __init__(self, *, scope_fn=semantic_scope_guard) -> None:
        self.last_report: dict = {}
        self._scope_fn = scope_fn

    def discover(self, locator: str) -> list[DiscoveredExternalItem]:
        spec = parse_bundle_locator(locator)
        merged: dict[str, DiscoveredExternalItem] = {}
        attempts: list[dict] = []
        for child in spec.child_adapters:
            adapter = _SUPPORTED_CHILDREN[child]()
            for query in spec.queries:
                try:
                    rows = adapter.discover(query)[: spec.per_query_limit]
                    attempts.append({"child_adapter": child, "query": query, "status": "OK", "raw_count": len(rows)})
                    for row in rows:
                        key = (row.ref or f"{child}:{row.external_id or row.title}").rstrip("/")
                        with_prov = _copy_with_provenance(row, spec=spec, child=child, query=query)
                        if key in merged:
                            merged[key] = _merge_duplicate(merged[key], with_prov)
                        else:
                            merged[key] = with_prov
                except Exception as exc:
                    attempts.append({
                        "child_adapter": child,
                        "query": query,
                        "status": "ERROR",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    })
        raw_values = list(merged.values())
        raw_values.sort(key=lambda item: item.published_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        guard = self._scope_fn(spec.intent, raw_values)
        if guard.status == "OK":
            accepted = [row for idx, row in enumerate(raw_values) if f"c{idx}" in guard.accepted_ids]
            scope_status = "SEMANTIC"
        elif guard.status == "EMPTY":
            accepted = []
            scope_status = "EMPTY"
        else:
            accepted = [row for row in raw_values if _within_scope(row, spec.anchor_groups)]
            scope_status = "LEXICAL_FALLBACK"
        self.last_report = {
            "version": ACTIVE_QUERY_BUNDLE_VERSION,
            "watch_id": spec.watch_id,
            "intent": spec.intent,
            "query_count": len(spec.queries),
            "child_count": len(spec.child_adapters),
            "attempts": attempts,
            "raw_unique_refs": len(raw_values),
            "unique_refs": len(accepted),
            "scope_rejected": len(raw_values) - len(accepted),
            "scope_guard": {
                "status": scope_status,
                "version": guard.version,
                "model_meta": guard.model_meta,
                "error": guard.error,
            },
            "failed_attempts": sum(1 for x in attempts if x["status"] == "ERROR"),
        }
        return accepted


@dataclass(frozen=True)
class WatchObservationIntent:
    status: str
    intent: str | None
    context: str | None
    reason: str | None = None


def project_watch_observation_intent(db, watch) -> WatchObservationIntent:
    target = " ".join(str(watch.target_ref or "").split())
    if not target:
        return WatchObservationIntent("INSUFFICIENT_CONTEXT", None, None, "WATCH target_ref is empty")
    # Long/question-like targets are self-contained enough to monitor. Generic
    # trigger labels such as `code release` require origin context.
    self_contained = len(target) >= 48 or "?" in target or len(target.split()) >= 7
    context_parts = [f"WATCH type: {watch.target_type}", f"Reason: {watch.created_reason}"]
    source = None
    if getattr(watch, "analysis_run_id", None):
        from app.models.analysis import AnalysisRun
        from app.models.source import Source
        run = db.get(AnalysisRun, watch.analysis_run_id)
        if run is not None and getattr(run, "source_id", None):
            source = db.get(Source, run.source_id)
    if source is not None:
        if source.title:
            context_parts.append(f"Origin source: {source.title}")
        if source.content_text:
            context_parts.append(f"Origin evidence: {source.content_text[:1600]}")
    if not self_contained and source is None:
        return WatchObservationIntent(
            "INSUFFICIENT_CONTEXT", None, "\n".join(context_parts),
            "Generic WATCH target has no origin Source/AnalysisRun context",
        )
    intent = target if self_contained else f"{source.title}: {target}"
    return WatchObservationIntent("READY", intent, "\n".join(context_parts))

def upsert_watch_query_bundle(
    db,
    *,
    watch,
    max_queries: int = 6,
    child_adapters: Iterable[str] = ("HACKERNEWS_SEARCH", "BILIBILI_SEARCH"),
    per_query_limit: int = 10,
    enabled: bool = True,
    chat_fn=None,
):
    from sqlalchemy import select
    from app.models.acquisition import SourceDefinition
    from app.services.query_expansion import expand_query_intent

    projection = project_watch_observation_intent(db, watch)
    if projection.status != "READY" or not projection.intent:
        raise ValueError(projection.reason or "WATCH does not contain a self-contained observation intent")
    kwargs = {}
    if chat_fn is not None:
        kwargs["chat_fn"] = chat_fn
    plan = expand_query_intent(
        projection.intent,
        context=projection.context,
        max_queries=max_queries,
        **kwargs,
    )
    spec = ActiveQueryBundleSpec(
        watch_id=str(watch.id),
        intent=plan.intent,
        queries=plan.queries,
        child_adapters=tuple(str(x).upper() for x in child_adapters),
        per_query_limit=max(1, min(int(per_query_limit), 50)),
        expansion_version=plan.version,
        expansion_status=plan.status,
        anchor_groups=plan.anchor_groups,
    )
    existing = None
    rows = db.execute(
        select(SourceDefinition).where(SourceDefinition.source_type == "ACTIVE_QUERY_BUNDLE")
    ).scalars().all()
    for row in rows:
        try:
            if parse_bundle_locator(row.locator).watch_id == str(watch.id):
                existing = row
                break
        except Exception:
            continue
    if existing is None:
        existing = SourceDefinition(
            name=f"WATCH · {watch.target_ref[:80]}",
            source_type="ACTIVE_QUERY_BUNDLE",
            locator=spec.to_locator(),
            enabled=enabled,
            poll_interval_seconds=1800,
        )
        db.add(existing)
    else:
        existing.name = f"WATCH · {watch.target_ref[:80]}"
        existing.locator = spec.to_locator()
        existing.enabled = enabled
    db.flush()
    return existing, plan, spec


def compare_original_vs_expanded(
    *,
    watch_id: str,
    intent: str,
    queries: Iterable[str],
    child_adapters: Iterable[str] = ("HACKERNEWS_SEARCH", "BILIBILI_SEARCH"),
    per_query_limit: int = 10,
    anchor_groups: Iterable[Iterable[str]] = (),
) -> dict:
    queries = tuple(dict.fromkeys(" ".join(str(x).split()) for x in queries if str(x).strip()))
    if not queries:
        queries = (intent,)
    normalized_anchor_groups = tuple(tuple(str(term) for term in group) for group in anchor_groups)
    original_spec = ActiveQueryBundleSpec(
        watch_id=watch_id,
        intent=intent,
        queries=(intent,),
        child_adapters=tuple(child_adapters),
        per_query_limit=per_query_limit,
        expansion_status="ORIGINAL_ONLY",
        anchor_groups=normalized_anchor_groups,
    )
    expanded_spec = ActiveQueryBundleSpec(
        watch_id=watch_id,
        intent=intent,
        queries=queries,
        child_adapters=tuple(child_adapters),
        per_query_limit=per_query_limit,
        expansion_status="EXPANDED",
        anchor_groups=normalized_anchor_groups,
    )
    a = ActiveQueryBundleAdapter()
    b = ActiveQueryBundleAdapter()
    a_rows = a.discover(original_spec.to_locator())
    b_rows = b.discover(expanded_spec.to_locator())
    a_refs = {row.ref for row in a_rows}
    b_refs = {row.ref for row in b_rows}
    incremental = [row for row in b_rows if row.ref not in a_refs]
    return {
        "intent": intent,
        "queries": list(queries),
        "original_unique_refs": len(a_refs),
        "expanded_unique_refs": len(b_refs),
        "incremental_unique_refs": len(b_refs - a_refs),
        "overlap_refs": len(a_refs & b_refs),
        "incremental_examples": [
            {"title": row.title, "ref": row.ref, "published_at": row.published_at.isoformat() if row.published_at else None}
            for row in incremental[:20]
        ],
        "original_report": a.last_report,
        "expanded_report": b.last_report,
    }
