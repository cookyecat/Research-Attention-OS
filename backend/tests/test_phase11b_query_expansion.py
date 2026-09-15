from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import select

from app.models.acquisition import SourceDefinition
from app.models.watch import Watch
from app.services import active_acquisition
from app.services.acquisition_types import DiscoveredExternalItem
from app.services.active_acquisition import (
    ActiveQueryBundleAdapter,
    ActiveQueryBundleSpec,
    parse_bundle_locator,
    upsert_watch_query_bundle,
)
from app.services.query_expansion import expand_query_intent


def test_query_expansion_preserves_original_first_and_deduplicates():
    def fake_chat(messages, **kwargs):
        return ({"queries": ["shared world model", "共享世界模型", "shared world model"], "note": "aliases"}, {"model": "fake", "prompt_tokens": 10, "completion_tokens": 4})

    plan = expand_query_intent(
        "Can shared world models reduce explicit multi-agent communication?",
        max_queries=5,
        chat_fn=fake_chat,
    )
    assert plan.status == "OK"
    assert plan.queries[0] == "Can shared world models reduce explicit multi-agent communication?"
    assert plan.queries.count("shared world model") == 1
    assert "共享世界模型" in plan.queries


def test_query_expansion_failure_falls_back_to_original_only():
    def broken(*args, **kwargs):
        raise RuntimeError("model unavailable")

    plan = expand_query_intent("Motor Intelligence Foundation Model", chat_fn=broken)
    assert plan.status == "FALLBACK_ORIGINAL_ONLY"
    assert plan.queries == ("Motor Intelligence Foundation Model",)
    assert "model unavailable" in plan.error


def test_active_bundle_deduplicates_refs_and_merges_query_provenance(monkeypatch):
    def fake_hn(self, query):
        return [DiscoveredExternalItem(ref="https://example.com/same", title=f"same via {query}")]

    def fake_bili(self, query):
        return [DiscoveredExternalItem(ref=f"https://example.com/{query.replace(' ', '-')}", title=query)]

    monkeypatch.setattr(active_acquisition.HackerNewsSearchAdapter, "discover", fake_hn)
    monkeypatch.setattr(active_acquisition.BilibiliSearchAdapter, "discover", fake_bili)
    spec = ActiveQueryBundleSpec(
        watch_id="w1",
        intent="shared world models",
        queries=("shared world models", "shared latent world model"),
        per_query_limit=5,
    )
    adapter = ActiveQueryBundleAdapter()
    rows = adapter.discover(spec.to_locator())
    same = next(row for row in rows if row.ref == "https://example.com/same")
    matches = same.metadata["active_query_bundle"]["matches"]
    assert len(matches) == 2
    assert {m["query"] for m in matches} == {"shared world models", "shared latent world model"}
    assert adapter.last_report["unique_refs"] == 3


def test_active_bundle_child_failure_is_isolated(monkeypatch):
    monkeypatch.setattr(
        active_acquisition.HackerNewsSearchAdapter,
        "discover",
        lambda self, query: [DiscoveredExternalItem(ref="https://example.com/good", title="good")],
    )
    monkeypatch.setattr(
        active_acquisition.BilibiliSearchAdapter,
        "discover",
        lambda self, query: (_ for _ in ()).throw(RuntimeError("blocked")),
    )
    spec = ActiveQueryBundleSpec(watch_id="w1", intent="AI agent", queries=("AI agent",))
    adapter = ActiveQueryBundleAdapter()
    rows = adapter.discover(spec.to_locator())
    assert [row.ref for row in rows] == ["https://example.com/good"]
    assert adapter.last_report["failed_attempts"] == 1


def test_watch_bundle_upsert_reuses_one_source_definition(db):
    watch = Watch(
        target_type="KERNEL",
        target_ref="Can shared world models reduce explicit multi-agent communication?",
        status="ACTIVE",
        created_reason="Keep monitoring new evidence",
        kernel_target_ids=[],
    )
    db.add(watch)
    db.flush()

    def fake_chat(messages, **kwargs):
        return ({"queries": ["shared world models multi-agent communication", "共享世界模型 多智能体通信"]}, {"model": "fake"})

    first, plan1, spec1 = upsert_watch_query_bundle(db, watch=watch, chat_fn=fake_chat)
    second, plan2, spec2 = upsert_watch_query_bundle(db, watch=watch, chat_fn=fake_chat)
    rows = db.execute(select(SourceDefinition).where(SourceDefinition.source_type == "ACTIVE_QUERY_BUNDLE")).scalars().all()
    assert first.id == second.id
    assert len(rows) == 1
    parsed = parse_bundle_locator(rows[0].locator)
    assert parsed.watch_id == str(watch.id)
    assert parsed.queries[0] == watch.target_ref
