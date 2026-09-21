# Phase 17 — Event-State Cognition Input V0.1 Preregistration

Status: **HISTORICAL PREREGISTRATION / EVAL COMPLETED / PRODUCTION DESIGN SUPERSEDED BY 269 + 271**  
Date: 2026-09-21

## 1. Motivation

Phase16C closed Event identity and current Attention identity:

```text
N Sources
-> 1 Event
-> 1 current Event Attention decision
```

but the canonical cognition computation is still primarily formed from the newly arrived Source extraction.

That leaves a mainline semantic gap:

```text
Attention object = Event
cognition input   = latest Source
```

The target theory is:

```text
new Source
-> Event Processor
-> updated Event representation/evidence
-> cognition over the updated Event
-> Event decision
-> Attention lifecycle
```

Phase17 asks whether the existing frozen cognition engine can consume a legal Event-level evidence projection without creating a second cognition ontology or weakening Support Binding / Grounding.

## 2. Non-goal

Phase17 does NOT:

- redesign Phase10 cognition;
- feed SAME_EVENT probability into cognition;
- introduce an Event score;
- treat Source count as independent evidence count;
- infer Event cognition from Event summary text alone;
- change production pipeline before the eval gate passes;
- reopen general multi-news digest / 0..N Event decisions.

## 3. Event cognition input contract

Candidate contract:

```text
event-cognition-input-v0.1
```

Input authority:

```text
Event
-> active decision-authorized member Sources
-> each member Source's latest audited EventEvidenceFrame batch
-> audited_semantic_units + explicit supports
-> existing ExtractionResult shape
-> existing frozen cognition provider
```

Materialized Event title/summary/state may be supplied for retrieval/context, but it is not a substitute for audited semantic evidence.

If any active member Source lacks a usable audited EventEvidenceFrame with support-bound semantic units, the adapter fails closed for V0.1.

## 4. Evidence merge semantics

Aggregation is by semantic evidence identity, not prose text.

Rules:

1. Different semantic_unit_id values remain distinct even if statements are text-identical.
2. Exact duplicate semantic_unit_id + same normalized payload may collapse once.
3. Same semantic_unit_id with conflicting statement/support payload is an integrity error.
4. Source ordering must not change the Event cognition input digest.
5. Support pointers/excerpts are preserved unchanged.
6. No summary-only fallback is permitted.

This deliberately differs from whole-Source merge logic that may deduplicate equal prose.

## 5. Source independence

SAME_EVENT is orthogonal to provenance dependence.

Event member Sources are passed through the existing decision-authorized SourceGraph independence projection:

```text
freeze_analysis_relational_context(member_source_ids)
```

Therefore:

```text
2 SAME_EVENT independent reports
-> independent_source_count = 2

2 SAME_EVENT where B REPOSTS / DERIVED_FROM A
-> independent_source_count = 1
-> secondary_report_count = 1
```

Event membership count is never used as an independence proxy.

## 6. Event cognition identity

The Event cognition input digest is deterministic over:

- Event V1 materialized decision-relevant state;
- sorted active authorized member Source ids;
- sorted frame semantic_input_digest/frame_digest identities;
- SourceGraph independence digest;
- adapter contract version.

It excludes incidental ordering and non-semantic runtime timestamps.

A material Event/evidence change must change the digest. Reordering the same evidence must not.

## 7. Fixed controlled A/B cases

Before observing outputs, fix three cases.

### Case A — independent corroboration

Source A contains a decision-bearing profiler result:

> Profiler evidence shows kernel launch overhead dominates runtime for a small 64x64 bf16 matrix multiplication with bias.

Source B independently reports the same profiler result for the same Event.

Compare:

```text
LATEST_SOURCE_B
vs
EVENT_AGGREGATED_A_PLUS_B
```

Expected structural outcome:

- Event aggregate contains both support-bound semantic units;
- independent_source_count = 2;
- no unit/support provenance is lost merely because the statement text is similar.

No disposition change is required for success.

### Case B — material correction/update

Source A reports the same profiler result that directly challenges the frozen Kernel belief.

Source B, in the same coarse Event lifecycle, reports a material correction:

> The authors corrected the profiler interpretation: the earlier launch-overhead conclusion applied only to setup-heavy measurements; in the steady-state 64x64 bf16 matmul run, computation remains dominant.

Compare:

```text
LATEST_SOURCE_B
vs
EVENT_AGGREGATED_A_PLUS_B
```

This case tests whether Event cognition can preserve the prior claim and the later correction simultaneously rather than pretending the Event state is only the last article.

Expected structural outcome:

- aggregated input contains both A and B audited units/supports;
- digest differs from A-only and B-only;
- existing frozen cognition can run without a new ontology.

No post-result rewriting of case text is allowed.

### Case C — provenance dependence positive control

Source B repeats Source A but has a decision-authorized REPOSTS/DERIVED_FROM relation.

Expected:

```text
member Sources = 2
independent_source_count = 1
secondary_report_count = 1
```

This must hold regardless of SAME_EVENT membership.

## 8. Decision probe

Use the existing frozen decision-sensitive Kernel belief used in Phase16B:

> For a small 64x64 bf16 matrix multiplication with bias, computation dominates runtime rather than kernel preparation and launch overhead.

Reuse:

- `ResearchAlignedCognitiveProvider`;
- existing Relation -> Support Binding -> Grounding/Jurisdiction -> Authority contract;
- existing decision strategy and route;
- controlled fake model transport only for deterministic stage outputs.

The fake transport may vary only according to the preregistered semantic units visible in each input. It must not inspect case labels to force a desired disposition.

## 9. Success criteria

Adapter gate:

1. builds Event input only from decision-authorized member Sources;
2. requires audited semantic units with supports;
3. preserves duplicate-text independent evidence as distinct units;
4. detects conflicting duplicate unit ids;
5. computes independence through SourceGraph, not Event membership count;
6. digest is ordering-stable and evidence-sensitive.

Cognition gate:

7. frozen provider accepts the aggregated Event input without a new cognition schema;
8. Case A retains both corroborating supports;
9. Case B retains prior + correction evidence simultaneously;
10. Case C keeps independent count at one under secondary provenance.

Production gate:

11. no production wiring until adapter + controlled A/B pass;
12. any later production switch must include Event cognition input digest in AnalysisRun identity so new Event evidence cannot reuse stale cognition.

## 10. Interpretation boundary

A successful Phase17 V0.1 establishes a legal Event-level cognition input projection and bounded decision sensitivity.

It does NOT establish:

- calibrated Event-state probability;
- perfect contradiction resolution;
- optimal resurfacing policy;
- multi-event digest handling;
- general benchmark accuracy.

Those remain later questions.
