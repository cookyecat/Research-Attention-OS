# Phase 10D.4 — Production Promotion and Phase 9 Handoff

Status: COMPLETE / LOCAL PRODUCTION DOGFOOD ROLLOUT VERIFIED
Date: 2026-09-11

## Decision

Promote the experimentally validated decision stack `Anchored OPEN_NEW Admission + Magnitude-Free Calibration + Pareto Multi-Delta` from research-only use to the active local production dogfood configuration.

The repository compatibility default remains `one-delta-v1`, while the Mac dogfood runtime selects `pareto-multidelta-magnitude-free-anchored-open-new` through `RAOS_DECISION_STRATEGY_ID`. Historical AnalysisRuns continue to resolve against their recorded strategy fingerprints.

## Why now

Phase 8C.5–8C.9 isolated three distinct failure modes and corresponding interventions: lossy single-winner compression -> Pareto; pseudo-cardinal `change_magnitude` authority -> Magnitude-Free; free-floating OPEN_NEW -> Anchored admission. Phase 10A–10D.4 then showed repeatable decision-bearing probability structure under the combined research stack, including 4/4 real-web non-degenerate cases remaining Attention-basin compatible at the second checkpoint.

This promotion is a product-dogfood decision, not proof that the strategy is globally optimal or universally calibrated.
## Promotion verification

Focused strategy / identity / policy-contract regression passed `78 passed / 1 warning`. Full backend regression passed `616` tests with `63` skipped and only the historical Case K residual failing (`PREEMPT` expected, `PRIORITY` actual); no new regression was introduced. A previously missing tracked Phase 6A measurement artifact was restored before the final full regression.

The running Mac backend was launched with the project `.env`, and a fresh real API smoke analysis recorded `pareto-multidelta-magnitude-free-anchored-open-new-v0.1` in `AnalysisRun.execution_snapshot.decision_strategy`, with `magnitude-free-v0.1` and `anchored-open-new-v0.1` recorded explicitly. The frontend is available at `http://localhost:3000` and backend health at `http://127.0.0.1:8000/health`.

No Sensor, Auditor, Locate, D/S/P, Cognitive Transition semantics, WATCH semantics, or Kernel authorization rule is changed by this rollout.

## Phase 9 handoff

After promotion and tagging, open Phase 9A as **Kernel Causal Alignment**: compare `M(E,K0)` against `M(E,K1)` after an explicit human-authorized Kernel change, using the existing fixed-K probability basin as the stochastic null baseline. The objective is to distinguish legitimate cognition-induced basin shift from internal RAOS stochastic drift.

Do not introduce Markov/HMM/attractor machinery at Phase 9A. Start with controlled Kernel interventions and the existing static probability-map / JSD / permutation-null chips.
## Rollback contract

Rollback is a strategy selection change, not a semantic rewrite: explicitly select `one-delta-v1` or check out the promotion tag. Historical result artifacts and their execution snapshots remain immutable.

The production promotion must be recorded in the roadmap and tagged only after focused tests and the full backend regression establish that no new regression was introduced.
## Implementation scope

The code change adds a versioned production-selection setting only. `one-delta-v1` remains the repository compatibility default and the fallback for historical snapshots with no strategy fingerprint. The local dogfood runtime selects `pareto-multidelta-magnitude-free-anchored-open-new-v0.1` through configuration; explicit strategy injection remains available for controlled A/B and rollback.