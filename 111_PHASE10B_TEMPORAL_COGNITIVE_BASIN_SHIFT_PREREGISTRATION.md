# Phase 10B — Temporal Cognitive Basin-Shift Preregistration

Status: PREREGISTERED / CROSS-EPOCH MEASUREMENT ONLY

## Question

Do two independently frozen execution epochs for the same audited semantic world, Kernel and historical modal Locate fixture produce materially different **distributions** of Cognitive Topology, Decision-Causal Load-Bearing structure, and Article Attention?

This phase measures cross-epoch drift. It does not fit a stochastic process.

## Epochs

`t0`: Phase 8C.8 Relation-Mapping realizations, six samples per canonical case. Historical effects are replayed offline through the same current `Anchored OPEN_NEW + Magnitude-Free + Pareto` decision stack and Decision-Causal Core chip. OPEN_NEW identity is reconstructed with the Phase 8C.14 explicit source-unit signature.

`t1`: Phase 10A bounded-epoch samples and final maps. RS05/RS11 N=12; RS15/RS12 N=24 after the preregistered precision expansion.

## Configuration identity gate

Historical metadata stored only provider `response model` in `meta.model`; it did not separately record the requested alias. Phase 8C.8 responses report `deepseek-v4-flash`; current responses report `deepseek-flash`. A 2026-09-10 instrumentation probe with the patched client proves that the current request alias is still `deepseek-v4-flash` while the provider response name is `deepseek-flash`.

Therefore this experiment may establish **RAOS system-level longitudinal distribution shift**, but must not attribute that shift purely to model-weight or serving drift. Historical requested-model identity is inferred, not directly recorded.

## Distances

For each case report:

- Jensen-Shannon divergence of Attention distributions;
- Jensen-Shannon divergence of exact branch-level Topology-state distributions;
- Jensen-Shannon divergence of exact Load-Bearing-set distributions;
- mean/max absolute drift in `P(r in T)`;
- mean/max absolute drift in `P(r in B_pi(T))`.

JSD is descriptive here and bounded in `[0,1]` bits. Small-sample empirical JSD is not treated as a calibrated hypothesis test.

## Interpretation hierarchy

1. Attention JSD answers whether the product decision basin moved.
2. Load-Bearing JSD answers whether the decision-causal structural basin moved.
3. Topology JSD answers whether the full cognitive shape moved.
4. Relation-frequency drift identifies which edges contribute.

A high Topology JSD with low Load-Bearing/Attention JSD is compatible with `peripheral drift under stable decision structure`.

## Guardrails

- no Sensor/Auditor/LLM calls;
- no threshold tuning after observing distances;
- no claim that drift implies incorrectness;
- no Markov/HMM/change-point model in Phase 10B;
- production default remains `one-delta-v1`.
