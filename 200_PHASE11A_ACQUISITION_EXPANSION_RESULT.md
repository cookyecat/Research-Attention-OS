# Phase 11A — Acquisition Expansion Result

Status: **CLOSED / 11B NEXT**
Date: 2026-09-15
Preregistration: `199_PHASE11A_ACQUISITION_EXPANSION_PREREGISTRATION.md`

## 1. Result

Phase 11A expands the existing Acquisition Plane without changing cognition semantics or the four-object acquisition ontology.

Implemented source types:

- `HACKERNEWS_SEARCH`
- `BILIBILI_SEARCH`
- `BILIBILI_CREATOR`
- `SOGOU_SEARCH`

All dispatch through the existing `SourceDefinition → AcquisitionObservation → ExternalInformationItem → InformationSnapshot → RAOS Source` path.

## 2. Live dogfood

Hacker News Algolia search is live and fetchable. A baseline query `AI agent` persisted 5/5 external items with zero item failures. Web discoveries prefer the existing URL ingestion path and preserve HN points/comments in Acquisition Observation metadata.

Bilibili public search is live after adopting an anonymous visitor `buvid3` cookie pattern; no authenticated/personal account cookie is used. A baseline query `AI Agent` persisted 5/5 videos with zero item failures.
Bilibili search currently exposes listing metadata rather than full video semantics/transcript. Therefore every acquired video is explicitly marked `content_scope=METADATA_ONLY` and `cognition_deferred=true`; acquisition succeeds without pretending the full information object has been understood.

Repeated polls of both enabled dogfood Sources were idempotent: `new_items=0`, `new_observations=0`, `new_snapshots=0`.

Initial baseline snapshots produced zero AnalysisRuns, preserving the present-time baseline invariant.

## 3. Explicit residuals

`BILIBILI_CREATOR` is implemented and deterministic parsing is tested, but the current anonymous creator-feed endpoint returns platform code `-799` for live dogfood. The Source is registered disabled rather than bypassing platform controls.

`SOGOU_SEARCH` is implemented with explicit protection-page detection. Current live requests return HTTP 200 but no result DOM, consistent with a shell/protection response. This is treated as a technical failure, never as a valid empty result. The Source is registered disabled.

These residuals do not block 11A closure because the preregistered close criteria required live HN + Bilibili search coverage and explicit handling of Sogou blocking, not forced success for every adapter.

## 4. Authority result

Raw platform observations such as HN points/comments and Bilibili views/likes/comments/danmaku are preserved with provenance only.

```text
raw engagement ≠ P
raw engagement ≠ D/S
raw engagement ≠ Attention
```

No new adapter contains cognition or Attention policy logic.
## 5. Validation

Focused regression:

```text
21 passed
1 existing Starlette/httpx deprecation warning
0 failures
```

Covered:

- new adapter parsers and API source-type management;
- Acquisition idempotency;
- first-poll baseline behavior;
- sibling source/item failure isolation;
- RSS fallback compatibility;
- public social adapters;
- arXiv paper connector compatibility.

Frontend route smoke after backend/worker restart:

```text
/          200
/inbox     200
/attention 200
/kernel    200
/watch     200
/system    200
```

## 6. Close decision

Phase 11A is **CLOSED**. The external-world observation surface is broader, raw attention-related telemetry is now preserved for future P work, and no semantic authority moved out of canonical RAOS cognition.

Next: **Phase 11B — Query Expansion / Active Acquisition**.
