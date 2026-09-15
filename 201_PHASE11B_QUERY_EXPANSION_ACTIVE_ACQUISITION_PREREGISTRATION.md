# Phase 11B — Query Expansion / Active Acquisition Preregistration

Status: **PREREGISTERED / IMPLEMENTATION ACTIVE**
Date: 2026-09-15
Parent plan: `198_PHASE11_EXTERNAL_ATTENTION_INFRASTRUCTURE_PLAN.md`
Depends on: Phase 11A closed result `200_PHASE11A_ACQUISITION_EXPANSION_RESULT.md`

## 1. Question

Can RAOS expand a standing WATCH / observation intent into bounded retrieval queries that improve external-world recall without turning retrieval similarity into cognition or Attention authority?

Frozen direction:

```text
WATCH / observation intent
→ Query Expansion Plan
→ Active Acquisition Query Bundle
→ discovery adapters
→ existing Acquisition ontology
→ canonical cognition only after acquisition
```

## 2. Authority invariant

```text
Query Expansion → where RAOS looks
Query Expansion ≠ D
Query Expansion ≠ S
Query Expansion ≠ P
Query Expansion ≠ Attention
```
## 3. v1 expansion contract

Input:

- semantic observation intent;
- optional WATCH target type / created reason;
- bounded max query count.

Output:

- original query preserved first;
- concise aliases / spelling variants;
- entity + topic combinations;
- cross-language variants only when they preserve the same intent;
- no generic broad-domain terms added merely to increase result volume.

The LLM may propose expansions, but the plan is retrieval metadata only. Failure falls back to the original query rather than blocking acquisition.

## 4. Active Query Bundle

One standing WATCH may own one `ACTIVE_QUERY_BUNDLE` SourceDefinition. Its locator is a versioned JSON observation-scope description containing `watch_id`, original intent, expanded queries, and enabled child adapters.

The bundle polls child discovery adapters independently, preserves the exact query + child adapter provenance on every discovered item, deduplicates identical refs, and returns a merged recency-ordered candidate set through the existing Acquisition path.

Child failure must not terminate successful child queries/adapters.
## 5. A/B dogfood protocol

Use at least one existing semantic WATCH target that is specific enough to monitor. Freeze the same child platforms and per-query fetch limit for both arms.

- **A — Original only:** search the literal WATCH intent.
- **B — Expanded:** search the frozen v1 expansion list including the original.

Measure:

- unique discovered refs;
- incremental unique refs beyond A;
- cross-query duplication;
- obvious semantic drift in returned titles/snippets;
- child technical failures;
- model latency / token cost for expansion.

Do not score downstream Attention outcomes as evidence that expansion itself is good or bad; 11B is a retrieval-recall study.

## 6. Initial child adapters

Live-validated Phase 11A adapters only:

- `HACKERNEWS_SEARCH`
- `BILIBILI_SEARCH`

`SOGOU_SEARCH` and `BILIBILI_CREATOR` remain excluded from the first A/B because their anonymous live paths are currently blocked/residual.

## 7. Close criteria

11B can close when query expansion is reproducible and bounded, bundle polling is idempotent/provenance-preserving, at least one real WATCH A/B demonstrates incremental useful recall without uncontrolled broadening, and no new cognition authority path is introduced.
