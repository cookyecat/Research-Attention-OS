# Phase 8C.12 — Locate vs Relation Mapping Longitudinal Attribution Preregistration

**Status:** PREREGISTERED / NOT YET MEASURED  
**Changed variable:** execution epoch only; source semantics, Kernel and historical fixtures are frozen  
**Production default:** unchanged (`one-delta-v1`)

## Question

Phase 8C.8 established a historical downstream basin on frozen audited semantic worlds. Later same-world experiments suggested current Cognitive Mapping may occupy a different basin. Phase 8C.12 asks where that longitudinal drift enters:

1. `L` — Locate / Kernel jurisdiction selection; or
2. `R` — Relation Mapping / CognitiveEffect generation after Locate is frozen.

This is causal-stage attribution, not a claim that `L` and `R` are statistically independent.

## Gate 8C.12A — Locate longitudinal replay

Cases: RS05, RS15, RS11, RS12.

Freeze the exact Phase 8C.8 admitted semantic units and the same Kernel fixtures. Re-run current `native_locate` 6 times per case using the declared model configuration. Compare historical and current distributions separately for:

- target-set topology;
- `(target, relevance_type)` detail topology;
- exact mode rate, pairwise Jaccard, entropy;
- historical-modal vs current-modal Jaccard.

No Sensor or Auditor calls are permitted.

## Gate 8C.12B — Relation Mapping longitudinal replay

For each case, reconstruct the exact historical Phase 8C.8 modal Locate fixture from stored `target / relevance_type / score / reason` fields and the frozen Kernel UUID mapping. Then freeze:

- exact audited semantic units;
- exact Kernel;
- exact historical modal Locate fixture.

Re-run only `native_assess` 6 times. Compare current decision-relation topology against the historical Phase 8C.8 Impact distribution using `topology-stability-metrics-v0.1`.

Historical Attention is taken from the Phase 8C.9 deterministic replay under `Anchored OPEN_NEW + Magnitude-Free + Pareto`; current Attention uses the same strategy stack.

## Guardrails

- No policy, prompt, threshold, Sensor or Auditor tuning after outcomes.
- `change_magnitude` has zero decision authority in the experimental downstream.
- Jaccard measures representation/topology similarity only; it is not a proxy for Decision Fidelity.
- OPEN_NEW identity at decision-topology level is `(OPEN_NEW, null)`; branch-text identity remains a separate diagnostic.
- Historical-vs-current difference is evidence of longitudinal distribution change, not proof of provider weight drift.

## Exit

Classify each case as: primarily Locate drift, Relation Mapping drift, both, neither, or unresolved. Only after this attribution is frozen may Phase 8C.13 Decision-Causal Core construction begin.
