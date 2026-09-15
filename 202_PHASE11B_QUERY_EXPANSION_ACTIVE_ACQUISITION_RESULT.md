# Phase 11B — Query Expansion / Active Acquisition Result

Status: **CLOSED / 11C NEXT**
Date: 2026-09-15
Preregistration: `201_PHASE11B_QUERY_EXPANSION_ACTIVE_ACQUISITION_PREREGISTRATION.md`

## 1. Result

Phase 11B implemented a bounded WATCH-driven active acquisition loop:

```text
WATCH
→ Observation Intent Projection
→ Query Expansion Plan
→ ACTIVE_QUERY_BUNDLE
→ HN / Bilibili discovery
→ Retrieval Scope Guard
→ existing Acquisition ontology
```

Query Expansion changes only where RAOS looks. Retrieval Scope Guard changes only whether a search hit remains inside the declared observation scope. Neither has D/S/P, cognition, or Attention authority.

## 2. Core implementation

- `query-expansion-v0.1`: model-backed bounded query expansion with original-query preservation and fail-safe original-only fallback.
- `active-query-bundle-v0.1`: one upserted Acquisition SourceDefinition per WATCH, not one database record per query.
- child-query failures are isolated.
- same URL discovered by multiple queries/adapters is one item with merged query provenance.
- generic legacy WATCH labels without origin context are rejected as `INSUFFICIENT_CONTEXT` rather than broadly searched.
## 3. Dogfood calibration

The first real WATCH A/B used:

> `Can shared world models reduce explicit multi-agent communication?`

Naive expansion increased apparent recall from 0 to 4, but all 4 were generic world-model results. This was recorded as semantic drift, not success.

A lexical scope guard then removed the noise but proved too brittle: it rejected semantic paraphrases and accepted some incidental keyword matches. Phase 11B therefore added `retrieval-scope-guard-v0.1`, a cheap batch semantic admission layer whose sole question is whether a candidate is substantially about the monitoring intent.

A second real WATCH (`latency × energy × task-success / high-frequency embodied control`) correctly returned no admitted candidates. Zero is a valid active-acquisition output; the system did not loosen scope to manufacture activity.
## 4. Closing A/B

A temporary research-only semantic WATCH was created for:

> `AI research agents conducting open-ended scientific discovery`

It was cancelled after the A/B and its query bundle was left disabled.

Final A/B, same child platforms and per-query budget:

```text
original admitted refs:    0
expanded admitted refs:    7
incremental admitted refs: 7
raw expanded refs:        26
scope rejected:           19
child failures:            0
```

Representative admitted results included autonomous agents for scientific tasks, autonomous goal-evolving agents for AI4S, Deep Research Max autonomous research agents, and Magellan autonomous cross-disciplinary scientific discovery. Earlier false-positive course/roundup results were removed by the calibrated semantic scope guard.

The final expansion call used `deepseek-flash`; the observed expansion latency was about 1.7s in dogfood. Scope guarding is explicitly cheaper retrieval admission, not canonical cognition.
## 5. Frozen invariants

```text
Query Expansion → observation recall only.
Retrieval Scope Guard → observation-scope admission only.
Neither defines D, S, P, Delta, or Attention.
Zero admitted results is valid.
One WATCH owns one upserted active query bundle.
Duplicate refs merge provenance rather than duplicate facts.
Generic WATCH labels without enough origin context are not activated.
```

Phase 11B is closed. Phase 11C now consumes the raw platform evidence preserved by 11A/11B and asks whether event-level observable attention signals can estimate the frozen theoretical P variable without redefining it.