# Phase 11A — Acquisition Expansion Preregistration

Status: **PREREGISTERED / IMPLEMENTATION ACTIVE**
Date: 2026-09-15
Parent plan: `198_PHASE11_EXTERNAL_ATTENTION_INFRASTRUCTURE_PLAN.md`

## 1. Question

Can RAOS expand from publisher feeds/public timelines to heterogeneous discovery platforms while preserving the existing Acquisition ontology and canonical cognition boundary?

## 2. Initial adapters

- `HACKERNEWS_SEARCH` — Algolia HN search API, query locator.
- `BILIBILI_SEARCH` — public Bilibili video search API, query locator.
- `BILIBILI_CREATOR` — public creator video feed when a numeric MID is explicitly configured.
- `SOGOU_SEARCH` — public HTML search, query locator; live success is not assumed.

11A deliberately permits explicit fixed query locators. Automatic query generation belongs to Phase 11B.

## 3. Frozen data path

```text
External platform
→ DiscoveredExternalItem
→ ExternalInformationItem
→ AcquisitionObservation
→ InformationSnapshot
→ canonical RAOS Source
→ existing automatic cognition policy
```
## 4. Delivery semantics

Two adapter families are allowed:

1. **Web-discovery item** — candidate points at an external article/page. RAOS first uses the existing `ingest_url()` path; source-provided title/snippet is an explicit fallback only when direct retrieval fails.
2. **Platform-native item** — candidate is itself the information object (for example a public Bilibili video listing). RAOS preserves platform text, author/media metadata, and raw engagement observations without using those signals to decide Attention.

Cross-source URL identity remains canonical where possible, so an HN result and an RSS feed pointing to the same article produce one external information item with multiple observations.

## 5. Raw signal rule

11A may preserve observable values such as views, likes, comments, danmaku, HN points, rank, author identity, and publication time. These values are **raw acquisition evidence only**.

```text
engagement metadata ≠ P
engagement metadata ≠ D/S
engagement metadata ≠ Attention
```

P modeling belongs to Phase 11C.

## 6. Baseline rule

A newly registered source still establishes a present-time baseline. Initial historical/search results may be persisted/read but must not masquerade as post-baseline cognitive arrivals. Subsequent genuinely new items enter the existing automatic canonical cognition path.
## 7. Live preflight frozen before implementation

2026-09-15 local preflight:

- Hacker News Algolia search: HTTP 200, current AI-agent stories returned.
- Bilibili public video search: HTTP 200 / API code 0, current videos returned with engagement fields.
- Sogou public web search: HTTP 200 but response was a shell/protection page with no result DOM. This is a live residual, not a zero-result success.

No authenticated personal cookies are permitted for this phase. Transparent public endpoints may be used; blocked adapters must fail explicitly.

## 8. Success criteria

11A can close when:

1. HN and Bilibili adapters pass deterministic parser/unit tests and at least one live dogfood probe each.
2. Search/platform adapters reuse the four-object Acquisition model and preserve first-poll baseline semantics.
3. One broken adapter/source and one broken discovered item cannot terminate independent siblings.
4. Cross-source URL dedup remains intact for web-discovery items.
5. Raw engagement metadata is preserved with provenance but never changes cognition/Attention directly.
6. Sogou is either live-validated or retained as an explicit blocked residual with no false success.
7. Focused regressions and existing Acquisition invariants pass.

## 9. Non-goals

- automatic Query Expansion (11B)
- Event-level P estimator or platform normalization (11C)
- notifications / Delivery Plane (11D)
- Agent API / Skill (11E)
- changing D/S/P or canonical Attention semantics
