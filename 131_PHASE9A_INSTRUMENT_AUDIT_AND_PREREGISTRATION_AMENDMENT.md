# Phase 9A — Instrument Audit and Preregistration Amendment

Status: **PRE-MEASUREMENT AMENDMENT — NO PHASE 9A OUTCOMES SAMPLED**  
Date: 2026-09-11  
Parent preregistration: `130_PHASE9A_KERNEL_CAUSAL_ALIGNMENT_PREREGISTRATION.md`

## Instrument gap discovered before measurement

The Phase 10 native research interface sends Kernel `type/title/proposition` into Relation Mapping, but its research conversion preserves the LLM-emitted `target_importance`. It does **not** bind explicit `KernelNode.payload.importance` back onto the effect.

Therefore the preregistered K1-I arm (`importance 0.9 -> 0.2`) would not actually expose the intervention to downstream Magnitude-Free policy if the Phase 10 conversion were reused unchanged.

This is an instrumentation failure, not an experimental result. No Phase 9A Relation-Mapping outcomes have been collected.
## Production semantic reference

Production cognitive impact already defines the intended authority order:

```text
explicit Kernel importance / priority
    > stable node-type prior
    > LLM estimate
    > neutral
```

via `resolve_target_importance(...)` in `backend/app/services/cognitive_impact.py`.

Phase 9A will therefore add a longitudinal Kernel-binding projection applied **identically to every arm** after Relation Mapping and before Decision-Causal analysis. For each targeted effect, `target_importance` is rebound with production `resolve_target_importance(node=<arm Kernel node>, node_type=..., llm_estimate=<raw LLM value>)`.

Operation polarity, target identity, epistemic strength, raw magnitude, and Relation-Mapping prompt remain unchanged by this projection.
## Consequences for interpretation

1. Phase 9A must construct a **fresh K0 map under this corrected longitudinal instrument**; Phase 10A RS05 remains the conceptual fixed-K precedent, not a numerically interchangeable baseline.
2. K1-S and K1-I remain valid preregistered interventions because the correction is arm-invariant and was specified before any Phase 9A outcome sampling.
3. K1-I is now an explicit positive control for the production rule that standing Kernel importance can alter Attention without requiring a semantic topology change.
4. If explicit importance rebinding itself changes K0 relative to the historical Phase 10A map, record that difference as measurement-interface drift, not Kernel evolution.

## Frozen amendment

This amendment is the only pre-measurement correction. After its commit, do not modify the binding rule, intervention wording, sample size, directional hypotheses, or permutation gate based on outcomes.
