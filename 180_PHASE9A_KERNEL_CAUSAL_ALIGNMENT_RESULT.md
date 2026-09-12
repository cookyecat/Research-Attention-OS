# Phase 9A — Kernel Causal Alignment Result

**Status:** CLOSED / CAUSAL ALIGNMENT SUPPORTED / PRODUCTION UNCHANGED
**Date:** 2026-09-13
**Preregistration:** `130_PHASE9A_KERNEL_CAUSAL_ALIGNMENT_PREREGISTRATION.md`, amended by `131_PHASE9A_INSTRUMENT_AUDIT_AND_PREREGISTRATION_AMENDMENT.md` and `177_PHASE9A_POST_10D6L_INSTRUMENT_AMENDMENT.md`
**Deterministic preflight:** `179_PHASE9A_V02_DETERMINISTIC_PREFLIGHT_RESULT.md`
**Measurement SHA:** `fcf684ad33fb3de3215ce6b163f6cdb5ded50d7c`

## Frozen question

With external evidence `E` fixed, does an explicit accepted Kernel intervention `K0 -> K1` cause the expected change in the same information interaction, beyond fixed-K stochastic variation?

The v0.2 experiment separates two orthogonal interventions:

- `K1-S` changes belief semantics while preserving target identity and high standing importance.
- `K1-I` preserves belief semantics and the exact K0 Relation-Mapping realization while reducing standing importance from `0.9` to `0.2`.

## Artifact

`eval/live/results/phase9a_kernel_causal_alignment_v0_2/phase9a_kernel_causal_alignment_v0.2_20260912T175705Z.json`

SHA256: `025e0777d1146ce3e2720bd9bd1b42bf34a969a9faa2fea13b5b36c8237860ea`

Frozen RS05 Auditor artifact SHA256: `aa594aab2b7b2f0e252dbf3ed8978865e03d9ddd1b905c8f38db0ae60ea5711f`

All 24 semantic LLM calls used requested/response model `deepseek-flash`, thinking disabled, temperature `0.1`. There were zero schema repairs and zero invalid effects. K1-I used no additional LLM calls; each sample replayed the exact paired K0 relation realization.

## Primary result 1 — semantic assimilation

K0 belief:

> For a small 64x64 bf16 matrix multiplication with bias, computation dominates runtime rather than kernel preparation and launch overhead.

K1-S accepted belief:

> For a small 64x64 bf16 matrix multiplication with bias, kernel preparation and launch overhead dominate useful GPU computation.

The external RS05 evidence was identical in both arms. Raw Relation Mapping produced:

```text
K0    CHALLENGE_ONLY  12/12
K1-S  REINFORCE_ONLY  12/12
```

The preregistered raw-polarity JSD was `1.0` bit. The 5000-permutation calibration gave:

```text
null median       0.0201312433
null p95          0.0817041659
null p99          0.1887218755
tail probability  0.0001999600
```

Therefore the preregistered semantic gate passes: observed JSD exceeds null p95, tail probability is <= 0.05, and the modal direction is exactly `CHALLENGE -> REINFORCE`.

This result is not manufactured by Grounding. The primary endpoint is the raw relation-only model output before deterministic Support Binding / Grounding / Authority. Grounding only filters opposite relations downstream.

## Primary result 2 — importance-only intervention

K1-I preserves the original K0 proposition byte-for-byte for Relation Mapping and reuses each exact K0 relation realization. Only authoritative Kernel importance changes:

```text
K0    importance = 0.9 / HIGH
K1-I  importance = 0.2 / LOW
```

All 12 paired samples preserved identical raw and authorized target topology. There were zero topology invariant violations.

For every retained CHALLENGE pair:

```text
K0    ENGAGE
K1-I  AWARE
```

Observed paired transition: `ENGAGE -> AWARE` in `12/12` eligible pairs. The preregistered importance gate passes.

## Secondary cognitive maps

The two interventions have sharply different internal signatures:

```text
K0 vs K1-S
  topology-state JSD      = 1.0
  load-bearing-state JSD  = 1.0
  Attention JSD           = 1.0

K0 vs K1-I
  topology-state JSD      = 0.0
  load-bearing-state JSD  = 0.0
  Attention JSD           = 1.0
```

Thus both K1 arms end at `AWARE 12/12`, but for different causal reasons:

- K1-S: the evidence no longer challenges the current belief; it reinforces an assimilated belief.
- K1-I: the evidence still challenges the unchanged belief, but that belief now has low standing importance.

This directly demonstrates that identical final Attention does not imply identical cognitive state or causal path.

## Interpretation

Phase 9A supports both preregistered causal-alignment claims.

First, RAOS relation semantics are state-conditioned: the same frozen evidence changes from `CHALLENGE` to `REINFORCE` when the receiver's accepted belief changes in the corresponding direction.

Second, standing importance can change Attention without changing semantic relation topology. This validates the separation between semantic cognition and attention allocation rather than collapsing both into one scalar update score.

The result is especially useful because the two interventions are mechanically isolated: K1-S changes proposition semantics, while K1-I shares the exact K0 Relation-Mapping realization and changes only Kernel importance downstream.

## Regression

Full backend regression after the valid result:

```text
693 passed
63 skipped
1 failed
1 warning
```

The sole failure remains the historical acceptance case `test_case_k_preempt`: expected urgency `PREEMPT`, actual `PRIORITY`. There are zero new regression failures.

## Decision

Phase 9A is CLOSED. No expansion to N=24 is permitted or needed because the N=12 semantic gate resolved decisively in the preregistered direction.

Production defaults remain unchanged. Phase 9A is evidence about the correctness of the state-conditioned research architecture, not an automatic production-promotion decision.

The result should be consumed by the parallel RAOS-CogEval benchmark paper as the first controlled Kernel counterfactual: `E fixed, K changed, correct relation changed`.
