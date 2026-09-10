# Phase 10D.4 — Real-Web Basin Persistence Preregistration

Status: PREREGISTERED / BEFORE T2 RELATION SAMPLING

## Question

Do non-degenerate real-web static cognitive maps reproduce as distributions when the exact audited semantic world, Kernel, Locate fixture, admission/calibration/decision stack, and prompt are held fixed?

This phase tests distribution persistence, not web acquisition, Sensor stability, Auditor stability, or Locate stability.

## Objective case-selection rule

Include every successful real-web static map from Phase 10D.1/10D.2/10D.3 whose observed Attention distribution contains at least two distinct actions.

Applying this rule before T2 sampling selects exactly: `A`, `D`, `X`, `N4`.

No case is selected by whether its dominant action or theoretical story is desirable.
## Frozen controls

For each selected case, replay exactly the previously persisted `frozen_units` and the previously selected modal Locate match realization. Do not re-run acquisition, Sensor, Auditor, or Locate.

Decision stack remains `Anchored OPEN_NEW Admission + Magnitude-Free + Pareto`; raw `change_magnitude` has no decision authority. Production default remains `one-delta-v1`.

T2 sample size is fixed to the original T1 sample size per case: A=24, D=24, X=12, N4=24. No outcome-dependent expansion or early stopping is allowed.

## Persistence metrics

Compare T1 vs T2 using the existing `cognitive-map-distance-v0.1` at three levels: Attention-state JSD, load-bearing-state JSD, and topology-state JSD. Also retain relation-frequency drift diagnostics.

For each JSD statistic run `5000` fixed-seed permutation-null reallocations using `cognitive-map-permutation-null-v0.1`.

A dimension is called `same-basin-compatible-v0.1` when the permutation gate does **not** support drift. It is called `distribution-shift-supported-v0.1` only when observed JSD exceeds the permutation-null p95 and upper-tail probability is <=0.05.

This is a same-day independent persistence checkpoint, not evidence for a long-horizon stochastic process or a dynamical-system attractor.
