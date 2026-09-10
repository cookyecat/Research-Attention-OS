# Phase 10D.1 — Real-Web Static Probabilistic Cognitive Map Preregistration

Status: PREREGISTERED

## Question

Does the Static Probabilistic Cognitive Map observed on canonical fixtures generalize to frozen real-web semantic worlds?

## Cases

Reuse the same four Phase 8C.7 real-web URLs. Continuity is recorded per source rather than required globally:

- A — Microsoft Azure / Astra;
- C — OpenAI Safety / Astra;
- D — The Verge / Astra;
- X — Google Research / AgentHands.

A/X previously produced non-empty cognitive effects; C/D previously acted as empty-topology controls. Those historical outcomes are context only, not frozen gold labels.

## Controlled pipeline

For each source, run fresh real-web acquisition and exactly one Sensor v0.2.6 + Auditor v0.1.1 perception pass. Persist the complete admitted canonical units, including unit ids and supports. Then freeze that admitted world for all downstream sampling.

Run Locate three times on the frozen admitted world; choose the modal target-set realization with deterministic earliest-repeat tie break. Freeze that Locate fixture.

Then sample only Relation Mapping under the frozen world + frozen Locate:

- initial N = 12 per source;
- expand to N = 24 only under the same preregistered Wilson precision gate used by Phase 10A;
- downstream strategy = `pareto-multidelta-magnitude-free-anchored-open-new`;
- Decision-Causal Core is computed deterministically for every realization;
- OPEN_NEW branch identity uses explicit admitted-unit ids when referenced; unresolved branches remain `UNRESOLVED` rather than being semantically guessed.

## Primary map

For each source estimate the empirical map:

`M(E,K) = [ P(r in T), P(r in B_pi(T)), P(Attention) ]`

where `B_pi(T)` is the union of necessary and individually sufficient load-bearing relations under the frozen decision strategy.

## Precision gate

Use Wilson 95% intervals exactly as Phase 10A. Expand 12 -> 24 when either:

1. dominant Attention probability half-width > 0.20; or
2. a load-bearing relation with empirical p in [0.25, 0.75] has Wilson half-width > 0.20.

No expansion may depend on whether the result looks favorable.

## Guardrails

- No production promotion.
- No raw `change_magnitude` decision authority.
- No Sensor/Auditor repetition in this phase; perception variance is intentionally frozen out.
- No temporal/stochastic-process model.
- Do not interpret AWARE/WATCH/ENGAGE as accuracy gold without human labels.
- Acquisition continuity is classified per source before model calls. A hash/length mismatch may proceed only as an explicitly labeled `NEW_SNAPSHOT`, never as a longitudinal replay of the old page.
- If complete admitted units cannot be serialized/replayed exactly, fail closed rather than reconstructing an approximate semantic world.
- Production default remains `one-delta-v1`.

## Pre-measurement acquisition amendment — 2026-09-10

The first formal attempt stopped before any model call because source C no longer matched the Phase 8C.7 snapshot. Inspection showed this was not parser noise: the same `/gpt-6-astra/vision` URL now yields the full Astra System Card (~184k chars) rather than the earlier ~5.95k-char narrow extraction.

Therefore v0.1 records two acquisition classes before perception:

- `CONTINUITY_PRESERVED`: current hash and char count both match Phase 8C.7;
- `NEW_SNAPSHOT`: current page differs and is treated as a new real-web sample, with no longitudinal claim against the old snapshot.

Observed before any model call: A/D/X are continuity-preserved; C is a new snapshot. This amendment changes only source-snapshot interpretation, not the downstream sampling or precision rules.
