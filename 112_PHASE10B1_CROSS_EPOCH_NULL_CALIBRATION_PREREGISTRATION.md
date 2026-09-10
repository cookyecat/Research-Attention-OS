# Phase 10B.1 — Cross-Epoch Empirical Null Calibration Preregistration

Status: PREREGISTERED

## Why this gate exists

Exact topology/load-bearing state spaces are high-dimensional and current samples are small. A raw cross-epoch JSD near 1 can occur simply because two finite samples from the same broad distribution contain few exact duplicate states.

Before calling a cross-epoch distance a basin-shift signal, calibrate it against a no-epoch-shift empirical null.

## Null construction

For each canonical case, pool the frozen `t0` and `t1` samples from Phase 10B, randomly permute epoch labels while preserving original group sizes, and recompute the same distance. Use 5000 Monte Carlo permutations with fixed seed `20260910`.

Calibrate separately:

- Attention JSD;
- exact branch-level Topology-state JSD;
- exact Load-Bearing-set JSD.

## v0.1 descriptive gate

A distance is marked `drift_supported_v0_1` only when:

1. observed distance exceeds the permutation-null 95th percentile; and
2. Monte Carlo upper-tail probability is <= 0.05.

This is a research gate, not a multiple-comparison-corrected confirmatory hypothesis test.

## Interpretation

- Attention gate supported: product decision basin moved.
- Load-Bearing gate supported: decision-causal structural basin moved.
- Topology-only gate supported: cognitive shape moved but may be absorbed downstream.
- Raw JSD high but null-calibrated gate false: do not call it a basin shift.

## Guardrails

- no LLM calls;
- fixed seed and permutation count;
- no tuning after outcomes;
- exchangeability is an assumption of the empirical null;
- historical requested-model identity remains incompletely observed;
- no stochastic-process model is fitted;
- production default remains `one-delta-v1`.
