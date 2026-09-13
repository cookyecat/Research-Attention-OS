# RAOS Acquisition Plane v0.1 — RSS Dogfood Result

Date: 2026-09-13
Status: **CLOSED / RSS DOGFOOD ACTIVE**

## 1. Scope

Top-level design is frozen in `182_ACQUISITION_PLANE_V01_TOP_LEVEL_DESIGN.md`. v0.1 intentionally proves only the semantic chain:

```text
Source
→ Observation
→ Information Object
→ Snapshot
→ existing RAOS Source ingestion
→ existing research-aligned cognition
```

RSS is the first transport. The implementation does not introduce acquisition-side relevance, importance, truth, Kernel, or Attention judgment.

## 2. Implemented objects

Four Acquisition objects are now persistent:

- `SourceDefinition`: a configured external observation point.
- `AcquisitionObservation`: a Source made an Information Object observable.
- `ExternalInformationItem`: identity of the external information object.
- `InformationSnapshot`: captured content state linked to the delivered RAOS Source.

The same external URL observed through multiple SourceDefinitions resolves to one Information Object while preserving distinct Observations.

## 3. Implementation path

```text
RSSAdapter
→ discovered external item
→ identity / observation persistence
→ existing ingest_url()
→ InformationSnapshot
→ existing run_pipeline()
```

Existing URL retrieval and Trafilatura normalization remain authoritative. Acquisition does not duplicate content extraction or cognition.

A separate `app.acquisition_worker` polls due Sources. It is deliberately separate from the RAOS Attention Scheduler.

## 4. Focused invariants

Tests confirm:

1. RSS and Atom both map into the same external-information abstraction.
2. Repeated polling is idempotent at Information Object / Observation / Snapshot / analysis delivery.
3. The same article seen through two Sources becomes one Information Object, two Observations, and one Snapshot.
4. SourceDefinitions can be enabled/disabled and have their polling cadence changed without touching cognition.

Focused Acquisition tests: `4 passed`.

## 5. Real network dogfood

The first real SourceDefinition is:

```text
name = The Verge RSS
source_definition_id = 159973c8-bc51-4c8b-be16-518ba152b145
locator = https://www.theverge.com/rss/index.xml
poll_interval = 1800 seconds
```

A real poll discovered the current article:

```text
OpenAI’s rogue AI tried to hack another company in May
https://www.theverge.com/ai-artificial-intelligence/994383/openais-rogue-ai-rubygems-hack
```

The live chain created:

```text
ExternalInformationItem = 33e46c1b-18f4-4f04-91f8-51433972fc00
RAOS Source              = cbaa3e6c-4b39-4421-b55a-2b5ab31f29c0
AnalysisRun              = 3b2ea02c-8c39-406a-b44c-208113676fe5
```

The AnalysisRun completed with `fallback_used=false` and execution identity:

```text
cognition = research-aligned-cognition-v1
decision strategy = pareto-multidelta-cardinal-free-effect-anchored-open-new-v0.2
extraction = phase8c2-production-sensor-bridge-v0.2
```

The article produced no authorized cognitive relation and therefore final disposition `DROP`. This is a useful end-to-end boundary check: Acquisition observed and delivered the item; downstream cognition, not Acquisition, decided it did not currently require attention.

A second real poll completed in about 0.4 seconds with:

```text
new_items = 0
new_observations = 0
new_snapshots = 0
```

so the live path is idempotent.

## 6. First real residual

OpenAI's RSS feed itself is publicly retrievable and parses correctly, but direct URL retrieval of a tested OpenAI article returned HTTP 403 with the current generic URL connector.

This does not change the Acquisition architecture. It is retained as the first real acquisition residual rather than being anticipated away in v0.1. Future dogfood can determine whether the correct response is RSS-carried content, an official API/adapter, authenticated retrieval, or another transport.

## 7. Regression

Final full backend regression after v0.1 implementation:

```text
705 passed
63 skipped
1 failed
1 warning
```

The sole failure remains historical `test_case_k_preempt` (`PREEMPT` expected vs `PRIORITY` actual). Zero new regression failures.

## 8. Closure

Acquisition Plane v0.1 is sufficient for real dogfood. The next development rule is the same as the RAOS cognition rule: use the system, collect concrete residuals, and evolve adapters/semantics only when actual use demonstrates a need.
