# Phase 10A — Static Probabilistic Cognitive Map Preregistration

Status: PREREGISTERED / IMPLEMENTATION GATE

## Question

Given fixed source semantics, Kernel, Locate fixture, model/prompt/configuration and the frozen experimental downstream (`Anchored OPEN_NEW + Magnitude-Free + Pareto`), what empirical cognitive distribution is produced inside one bounded epoch?

This phase does **not** model temporal dynamics. It estimates one static empirical map.

## Frozen map

For relation identity `r`, Cognitive Topology `T`, Necessary Core `N_pi(T)`, Sufficient Supports `S_pi(T)`, and Attention action `A`:

```math
B_\pi(T)=N_\pi(T)\cup S_\pi(T)
```

`B_pi` is the load-bearing set and includes redundant supports that are sufficient but not individually necessary.

The v0.1 Cognitive Map is:

```math
\mathcal M_t(E,K)=\left(P_t(r\in T),\;P_t(r\in B_\pi(T)),\;P_t(A)\right)
```

Also report `P(r in N_pi)` and `P(r in S_pi)` separately for diagnosis.

## Relation identity

Targeted effects use `(operation, target)`. `OPEN_NEW` uses the Phase 8C.14 explicit source-unit branch signature. `OPEN_NEW(null)` alone is not an acceptable probabilistic identity.

## Measurement

- empirical frequency, not LLM-estimated probability;
- Wilson 95% interval for Bernoulli relation/core probabilities and dominant Attention proportion;
- exact-topology entropy and load-bearing-set entropy in bits;
- four-way Attention counts/proportions and Shannon entropy;
- no continuous `change_magnitude` authority.

## Sampling

Initial canonical target is `N=12` per case for RS05 / RS15 / RS11 / RS12 inside one bounded measurement epoch. The first six exact Phase 8C.12 Relation realizations may seed this epoch because they share the same frozen semantic world, historical modal Locate fixture, prompt/configuration and downstream strategy. Collect six additional samples under the same frozen contract.

Precision expansion rule: after N=12, expand to N=24 only if either (a) the dominant Attention Wilson-95 half-width is >0.20, or (b) a relation observed as load-bearing in at least 25% and at most 75% of samples has load-bearing Wilson-95 half-width >0.20. Expansion is precision-triggered, not outcome-selected.

## Guardrails

- Static probability is a measurement chip, not production policy.
- No HMM, Markov model, change-point model, or temporal transition matrix in Phase 10A.
- Jaccard remains representation similarity; it is not replaced by causal-core probability.
- High `P(r in T)` does not imply high `P(r in B_pi)`.
- Stability is not correctness.
- Production default remains `one-delta-v1`.
