# Phase 10C — Temporal Regime Classifier Preregistration

Status: PREREGISTERED

## Goal

Convert null-calibrated three-checkpoint pairwise drift results into a minimal deterministic regime label. This is a descriptive topology over checkpoint relations, not a stochastic-process model.

For each metric use the three booleans `d01`, `d02`, `d12`, where `dij=true` means the permutation-calibrated drift gate is supported between checkpoints i and j.

## v0.1 labels

- `STABLE`: 000
- `PERSISTENT_SHIFT`: 110 — t0 differs from both later checkpoints; t1 and t2 are compatible.
- `TRANSIENT_RETURN`: 101 — t1 differs, then t2 returns to a t0-compatible basin.
- `LATE_SHIFT`: 011 — t0 and t1 are compatible; t2 differs from both.
- `CONTINUING_OR_MULTI_REGIME_DRIFT`: 111 — all checkpoints are pairwise separated.
- `INDETERMINATE`: any other pattern, typically reflecting limited power, finite-sample inconsistency, or a boundary result.

Classify Attention, Load-Bearing state, and Topology state separately. Do not collapse them into one scalar stability score.

Production default remains `one-delta-v1`.
