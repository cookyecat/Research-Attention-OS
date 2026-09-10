# Phase 10D.3 — Real-Web Static Cognitive Map Result

Status: COMPLETE / FIVE MAPS + ONE RETAINED SENSOR TECHNICAL FAILURE

## Frozen measurement

Measurement SHA: `4251f1bb294553cdb46f7a7d1851f2f6f41d576e`

Artifact:
`eval/live/results/phase10d3_real_web_static_cognitive_map_v0_1/phase10d3_real_web_static_cognitive_map_v0.1_20260910T151143Z.json`

SHA256: `a40f2a6e4690a34552232c7e63c473e87ad7d5b846304a5a89108544b8b63f89`

Acquisition-only preflight artifact:
`eval/live/results/phase10d3_acquisition_preflight_v0_1/phase10d3_acquisition_preflight_v0.1_20260910T145307Z.json`

Preflight SHA256: `5d707a6bafd3558e9d2ba86232e9e468485776a43a4cccbd430e4b867df81ebf`

Decision stack remained frozen as `Anchored OPEN_NEW Admission + Magnitude-Free + Pareto`; production default remained `one-delta-v1`.
## Source selection and technical outcome

Batch-3 used an acquisition-only preflight over 12 ordered candidates. Eleven were fetchable; USGS returned `403`. The first two fetchable candidates in each preregistered stratum were selected without observing any Sensor, Auditor, Relation, or Attention outcome.

Selected: N3/N4 Near-Kernel, B3/B4 Boundary, F3/F4 Far-Control.

N3 (Anthropic multiagent systems) failed on its first and only Sensor pass with malformed/truncated JSON (`Unterminated string ... char 32928`). The failure was retained without retry or substitution.

The remaining five sources completed full frozen-world probability maps. All six selected URLs re-fetched with exact preflight hash and character-count continuity before model calls.

## Successful static maps

| Label | Stratum | N | Attention distribution | H(Topology) | H(Load-bearing) | H(Attention) |
|---|---|---:|---|---:|---:|---:|
| N4 | Near-Kernel | 24 | ENGAGE 15 / WATCH 9 | 3.939 | 2.551 | 0.954 |
| B3 | Boundary | 12 | DROP 12/12 | 0.000 | 0.000 | 0.000 |
| B4 | Boundary | 12 | DROP 12/12 | 0.000 | 0.000 | 0.000 |
| F3 | Far-Control | 12 | DROP 12/12 | 0.000 | 0.000 | 0.000 |
| F4 | Far-Control | 12 | DROP 12/12 | 0.000 | 0.000 | 0.000 |
## Structural findings

N4 is a genuine real-web two-basin case. At N=12 it was exactly `ENGAGE 6 / WATCH 6`, triggering the preregistered Wilson precision expansion. At N=24 it remained non-degenerate: `ENGAGE 15 / WATCH 9` (dominant concentration 0.625; Wilson 95% for ENGAGE approximately `[0.427, 0.788]`). The distribution did not collapse to a single deterministic label with additional sampling.

The WATCH basin is mainly supported by stable `REINFORCE(BT1/Q1)` plus OPEN_NEW branches. The ENGAGE basin is associated with additional decision-causal CHALLENGE relations, most often `CHALLENGE(BT1)` and `CHALLENGE(B1)`. Their load-bearing probabilities are approximately 0.542 and 0.458 respectively; no single relation dominates the whole map.

N4 therefore exhibits high internal structural uncertainty while retaining a more concentrated product-level distribution: `H(Topology)=3.939 bits > H(Load-bearing)=2.551 bits > H(Attention)=0.954 bits`.

B3 and B4 are useful Boundary controls. Locate often nominated many Kernel targets, yet Relation Mapping produced no admitted material CognitiveEffect in 12/12 samples for each article. This preserves the distinction `possible relevance != cognitive change`.

F3 and F4 are clean Far-Control controls: Locate was empty 3/3 and Relation Mapping remained empty 12/12 for each source.
## Cumulative distributional evidence

Across Phase 10A + 10D.1 + 10D.2 + 10D.3 there are now `16` successful cognitive maps and `252` frozen-world Relation Mapping realizations.

Fourteen of sixteen maps have dominant Attention concentration at least 0.8. Nine maps have non-empty cognitive topology; all `9/9` satisfy `H(Topology) > H(Attention)` in the observed sample. The empirical pattern therefore remains: internal cognitive structure is typically more variable than final Attention.

Within the preregistered successful Near/Boundary/Far samples from Batch-2 and Batch-3, the two Near-Kernel maps are non-DROP (`N2 ENGAGE 12/12`; `N4 ENGAGE/WATCH`), while all three Boundary maps and all three Far-Control maps are DROP 12/12. This is supportive external evidence only, not a population-level accuracy estimate.

## Bounded conclusion

The enlarged sample continues to support static probabilistic cognitive maps as a useful representation. N4 independently reproduces a non-degenerate real-web decision basin similar in spirit to RS15, while the Boundary/Far controls show that topic-word overlap or broad AI relevance need not create material CognitiveDelta.

No theory or production-policy change is justified from this batch alone. The highest-value next experiment is persistence validation on real-web non-degenerate maps: re-sample the same exact frozen semantic world and Locate fixture at an independent checkpoint, then compare distributions using the existing JSD + permutation-null machinery.

Production default remains `one-delta-v1`.
## Regression

Full backend regression: `615 passed / 63 skipped / 1 failed`.

The sole failure remains historical Case K: expected urgency `PREEMPT`, actual `PRIORITY`. No new regression was introduced by Phase 10D.3.
