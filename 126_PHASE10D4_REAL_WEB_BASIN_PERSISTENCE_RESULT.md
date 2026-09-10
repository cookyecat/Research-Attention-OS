# Phase 10D.4 — Real-Web Basin Persistence Result

Status: COMPLETE / REAL-WEB PROBABILITY-BASIN PERSISTENCE SUPPORTED

## Frozen measurement

Measurement SHA: `484eda0299c1699247a1a5181501519ce0640cf9`

Artifact:
`eval/live/results/phase10d4_real_web_basin_persistence_v0_1/phase10d4_real_web_basin_persistence_v0.1_20260910T160403Z.json`

SHA256: `5299cab0607779989b896148765f5c6ef9873b001449b73f51cba6b67e7438a7`

Selection rule was frozen before t2 sampling: every existing real-web static map with at least two observed Attention actions was included. This selected A, D, X, and N4.

For each case, the exact previously frozen admitted semantic world, Kernel, historical modal Locate, Anchored OPEN_NEW admission, Magnitude-Free calibration, Pareto strategy, and Decision-Causal Core machinery were reused. Only Relation Mapping was freshly sampled at t2.
## Persistence results

| Case | t1 Attention | t2 Attention | Attention JSD | Load-bearing JSD | Topology JSD | Null-calibrated basin result |
|---|---|---|---:|---:|---:|---|
| A | WATCH 14 / DROP 6 / AWARE 4 | WATCH 8 / DROP 10 / AWARE 6 | 0.046 | 0.105 | 0.076 | same basin on all three layers |
| D | WATCH 22 / AWARE 2 | WATCH 23 / AWARE 1 | 0.005 | 0.108 | 0.428 | Attention/core same basin; raw topology drift supported |
| X | ENGAGE 11 / WATCH 1 | ENGAGE 7 / WATCH 5 | 0.114 | 0.194 | 0.044 | same basin on all three layers |
| N4 | ENGAGE 15 / WATCH 9 | ENGAGE 14 / WATCH 10 | 0.001 | 0.219 | 0.508 | same basin on all three layers |

All JSD values were calibrated with 5000 fixed-seed permutations using the existing `cognitive-map-permutation-null-v0.1` gate. “Same basin” means the observed distance did not exceed the preregistered null threshold; it does not mean the empirical frequencies are literally equal.

N4 is the strongest persistence example. Its non-degenerate real-web Attention distribution reproduced from `15/24 ENGAGE, 9/24 WATCH` to `14/24 ENGAGE, 10/24 WATCH`; Attention JSD was only `0.00131`, with permutation tail probability `1.0`. Load-bearing and topology distances were also within their null distributions.
D provides a complementary robustness example. Its exact topology-state distribution changed enough to exceed the permutation-null gate (`JSD=0.42811`, tail probability approximately `0.04999`), but its load-bearing distribution and final Attention distribution remained in the same basin. This supports the distinction between internal semantic-topology drift and product-level decision drift.

A also reproduced its three-action basin (`WATCH/AWARE/DROP`) despite visibly different empirical counts across checkpoints. X remained a high-attention basin: its ENGAGE/WATCH ratio moved from `11/1` to `7/5`, but the observed Attention JSD landed exactly at the permutation null p95 and therefore did not pass the strict `observed > p95` drift gate.

## Bounded conclusion

Across all four objectively selected non-degenerate real-web maps, `4/4` showed no null-calibrated Attention-basin shift at t2. Three also retained the same load-bearing and topology basins; D retained the same load-bearing and Attention basins despite supported raw-topology drift.

This is evidence that the static probabilistic cognitive-map representation is not merely a one-checkpoint artifact. In particular, a non-degenerate distribution such as N4 can reappear at an independent Relation-Mapping checkpoint while individual realizations remain stochastic.

The result does **not** establish a stationary stochastic process, a dynamical attractor, or population-level generality. It supports a weaker and currently justified claim: under frozen perception/Kernel/Locate and frozen decision machinery, some real-web Relation-Mapping distributions exhibit repeatable basin-level structure.

Production default remains `one-delta-v1`; no production policy was changed.
## Regression and cumulative sampling

Focused decision/probability-map contracts: `36 passed / 1 warning`.

Full backend regression: `615 passed / 63 skipped / 1 failed`. The sole failure remains historical Case K (`PREEMPT` expected, `PRIORITY` actual); no new regression was introduced.

Phase 10D.4 adds `84` fresh Relation-Mapping realizations over four exact frozen real-web worlds (`24 + 24 + 12 + 24`). Combined with the prior `252` static-map realizations, the distributional research corpus now contains `336` Relation-Mapping realizations across the established maps/checkpoints, while the count of distinct successful static Cognitive Maps remains `16`.