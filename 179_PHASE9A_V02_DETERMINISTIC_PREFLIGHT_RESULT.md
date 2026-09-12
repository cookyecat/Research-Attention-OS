# Phase 9A v0.2 — Deterministic Instrument Preflight

**Status:** CLOSED / FEASIBILITY CONFIRMED / NO LLM OUTCOME SAMPLED
**Date:** 2026-09-13
**Parent preregistration:** `177_PHASE9A_POST_10D6L_INSTRUMENT_AMENDMENT.md`

## Purpose

Before implementing or running the stochastic Relation-Mapping measurement, verify that the preregistered causal design is representable by the current repaired RAOS stack without semantic workarounds.

## Deterministic checks

Using the isolated production KernelPatch -> KernelVersion materialization path and frozen RS05 evidence:

- The Relation-Mapping payload for K0 and K1-I is byte-equivalent when importance/version metadata is excluded as preregistered: `True`.
- The Relation-Mapping payload for K0 and K1-S differs because the target proposition changes: `True`.
- Materialized explicit importance is K0=`0.9`, K1-S=`0.9`, K1-I=`0.2`.
With manually constructed cardinal-free, directly grounded targeted relations routed through `pareto-multidelta-cardinal-free-anchored-open-new`:

- K0 `CHALLENGE + HIGH importance + SUFFICIENT` -> `ENGAGE / KERNEL_PATCH`.
- K1-S `REINFORCE + HIGH importance + SUFFICIENT` -> `AWARE / SUMMARY`.
- K1-I `CHALLENGE + LOW importance + SUFFICIENT` -> `AWARE / SUMMARY`.

No model call, stochastic sample, Sensor/Auditor rerun, or Phase 9A outcome was produced by this preflight.

## Interpretation

The preregistered interventions are executable as two orthogonal causal manipulations:

1. K0 -> K1-S changes semantic proposition and therefore may change Relation Mapping polarity.
2. K0 -> K1-I can reuse the identical Relation-Mapping realization and isolate standing-importance propagation downstream.

This preflight validates instrumentation feasibility only. It is not evidence that the stochastic semantic endpoint will pass.