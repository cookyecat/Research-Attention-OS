# Phase 9A — Kernel Causal Alignment Preregistration

Status: **PREREGISTERED — DO NOT TUNE AFTER OUTCOME**  
Date: 2026-09-11  
Parent checkpoint: `phase10d4-production-dogfood-v1` / `7054029599b5e3302e6748c3dc7e90ef0473b278`

## Frozen question

Can an explicit human-authorized Kernel change cause a reproducible, directionally interpretable change in the same information interaction that exceeds fixed-K stochastic variation?

Phase 9A treats the Phase 10 fixed-`E,K` Cognitive Probability Map as the null baseline and intentionally changes only `K`:

```math
M(E,K_0) \rightarrow M(E,K_1)
```

The first pilot uses RS05 because Phase 10A established a concentrated baseline: `CHALLENGE(CF-B-PERF)` load-bearing `12/12` and article Attention `ENGAGE 12/12`.
## Experimental arms

All arms use the exact frozen RS05 audited semantic units, the same historical modal Locate target identity, the same Relation-Mapping prompt/model/configuration, and the Phase 10D.4 decision stack.

**K0 — fixed-K control.** Keep `CF-B-PERF` unchanged:

> For a small 64x64 bf16 matrix multiplication with bias, computation dominates runtime rather than kernel preparation and launch overhead.

with explicit `importance=0.9`.

**K1-S — semantic assimilation.** Starting from K0, apply a production `KernelPatch` MODIFY to the same node identity, replacing the proposition with:

> For a small 64x64 bf16 matrix multiplication with bias, kernel preparation and launch overhead dominate useful GPU computation.

Keep `importance=0.9`. The intervention changes belief content, not target identity or standing importance.
**K1-I — importance downshift.** Starting from K0, apply a production `KernelPatch` MODIFY to the same node identity, preserving the original proposition exactly but changing explicit Kernel `importance` from `0.9` to `0.2`.

This intervention changes standing importance only; it must not be interpreted as a semantic belief update.

Both K1 arms must be created through the production `create_patch -> commit_patch(action="accept") -> KernelVersion` path in an isolated temporary database. The experiment must not mutate the user's live Kernel. Embedding refresh may be disabled because Locate is frozen and embeddings are outside the measured causal path.

## Preregistered directional expectations

For **K1-S**, the target relation to `CF-B-PERF` should move away from `CHALLENGE` and toward `REINFORCE`. The primary success claim is a Kernel-content-induced topology/load-bearing shift; an Attention shift is allowed but not required.

For **K1-I**, the target relation polarity/topology should remain materially unchanged, while Magnitude-Free policy should reduce the Attention allocated to the low-importance CHALLENGE. The expected article-level direction is `ENGAGE -> AWARE` when epistemic support remains sufficient.
## Sampling and ordering

Initial target: `N=12` fresh Relation-Mapping realizations per arm. Sample in rotating/interleaved arm order so short-term provider drift is not confounded with one arm.

If an intervention is directionally consistent but the preregistered permutation gate is not resolved at N=12, expand that comparison to `N=24` per arm. Do not expand an arm merely because its observed effect is inconvenient.

Frozen: RS05 audited units/artifact, node identity, modal Locate matches, Relation-Mapping prompt, model alias/configuration, thinking disabled, temperature 0.1, Anchored OPEN_NEW admission, Magnitude-Free calibration, Pareto aggregation, Decision-Causal Core definition, probability-map chip and distance chip.

The only intended differences are the accepted KernelVersion contents described above.

## Measurements

For each arm construct:

```math
M(E,K)=\left(P(r\in T), P(r\in B_\pi(T)), P(A)\right)
```

Compare K0 vs each K1 using topology-state JSD, load-bearing-state JSD, Attention JSD, target-relation frequencies, and the existing 5000-permutation null calibration.
A distributional difference is called supported only when the existing Phase 10 gate holds:

```text
observed JSD > permutation null p95
AND
tail_probability <= 0.05
```

Intervention-specific interpretation gates:

- **K1-S semantic alignment supported:** the modal target polarity flips away from CHALLENGE toward REINFORCE and topology or load-bearing drift is permutation-supported in the preregistered direction.
- **K1-I allocation alignment supported:** target polarity remains CHALLENGE-dominant, topology drift is not required, and Attention moves materially downward with permutation-supported Attention drift toward AWARE.
- If topology shifts under K1-I, treat that as a failure of the intended isolation, not as a success.
- If K1-S changes topology but not Attention, record this as legitimate internal cognitive evolution absorbed by downstream Attention stability.

## Guardrails / stop rules

1. Do not tune prompts, thresholds, Kernel wording, or sample selection after observing outcomes.
2. Do not claim correctness from stability alone; this phase tests causal alignment to an explicit Kernel intervention.
3. Do not mutate the live user Kernel or live dogfood database.
4. Do not introduce Markov/HMM/attractor machinery.
5. Do not rerun Sensor or Auditor in v0.1; they remain frozen so the causal variable is Kernel state.
6. If the production patch/KernelVersion path cannot reproduce the intended K1 snapshots exactly, stop before Relation sampling and repair instrumentation only.