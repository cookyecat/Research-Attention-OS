# Phase 10A — Static Probabilistic Cognitive Map Result

Status: EXPERIMENTALLY COMPLETE — STATIC BOUNDED-EPOCH PILOT

## Frozen question

Can repeated Relation-Mapping realizations under one frozen semantic world, Kernel, historical modal Locate fixture, prompt/configuration, and the experimental downstream (`Anchored OPEN_NEW + Magnitude-Free + Pareto`) be represented more faithfully as a stable empirical cognitive distribution than as one deterministic topology?

The v0.1 map is:

```math
\mathcal M_t(E,K)=\left(P_t(r\in T),\;P_t(r\in B_\pi(T)),\;P_t(A)\right)
```

with `B_pi(T)=NecessaryCore union SufficientSupports` so redundant Pareto load-bearing relations remain visible.

## Measurement

Formal measurement SHA: `04915bd8eea5a03388f6e0905bc84bcd98462e75`.

Canonical artifact: `eval/live/results/phase10a_static_probabilistic_cognitive_map_v0_1/phase10a_static_probabilistic_cognitive_map_v0.1_20260910T075824Z.json`.

SHA256: `f3a56fdd7a1d3c95a96b41ae1a282f3ae1c94218b4adc43e7ed23390f5be25b7`.

Initial target was N=12 per case. The preregistered Wilson precision gate expanded RS15 and RS12 to N=24; RS05 and RS11 stopped at N=12. Expansion was precision-triggered, not result-selected.

## Results

| Case | N | Attention distribution | Attention entropy | Key load-bearing structure |
|---|---:|---|---:|---|
| RS05 | 12 | ENGAGE 12/12 | 0 bits | `CHALLENGE(CF-B-PERF)` P(B)=1.00 |
| RS15 | 24 | ENGAGE 20/24; WATCH 4/24 | 0.650 bits | `CHALLENGE(B1)` P(B)=0.833; `CHALLENGE(Q1)` P(B)=0.833 |
| RS11 | 12 | WATCH 12/12 | 0 bits | `OPEN_NEW[RS11-N11]` P(B)=0.917 |
| RS12 | 24 | WATCH 24/24 | 0 bits | `REINFORCE(BT1)` P(B)=1.00 |

RS05 shows a concentrated decision-bearing basin despite peripheral OPEN_NEW variation. RS15 remains genuinely bimodal at the Attention layer after expansion, with redundant CHALLENGE supports carrying the ENGAGE basin. RS11 has stable product-level WATCH but non-zero branch-level core variation. RS12 has high topology/core-set entropy while one invariant load-bearing relation keeps Article Attention at WATCH 24/24.

## Main findings

1. `P(r in T)` and `P(r in B_pi(T))` are materially different objects. A relation may occur almost always while rarely carrying Attention.
2. High raw Topology entropy does not imply high Attention entropy. RS12 is the strongest current example.
3. The Decision-Causal Core representation exposes stable load-bearing structure that Exact Match/Jaccard alone cannot identify.
4. RS15 is not adequately represented as one deterministic answer. Its bounded-epoch empirical map contains at least two decision basins under the current Relation Mapping.
5. Static probability is useful without introducing a temporal stochastic-process model.

## Boundaries

This experiment measures distributional stability, not semantic correctness. The empirical probabilities are small-sample estimates with Wilson intervals, not calibrated world-truth probabilities. `Cognitive Attractor` remains a working analogy, not a formal dynamical-systems claim. No temporal transition model, HMM, Markov process, or change-point detector is introduced here.

Full backend regression: `598 passed, 63 skipped, 1 failed`; the sole failure remains the pre-existing Case K `PREEMPT` vs `PRIORITY` residual. No new regression was observed.

Production default remains `one-delta-v1`. Phase 10A is a measurement/modeling chip only.

## Next gate

The data justify Phase 10B only as a **cross-epoch distribution comparison**, not yet as a stochastic-process model. Reconstruct the same branch-level topology/load-bearing maps for an earlier frozen epoch where possible, then measure cross-epoch drift with distribution distances. If cross-epoch drift is not materially larger than within-epoch uncertainty, stop. If it is, only then consider change-point/regime-shift modeling.
