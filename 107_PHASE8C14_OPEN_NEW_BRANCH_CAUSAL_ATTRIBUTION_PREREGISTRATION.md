# Phase 8C.14 — OPEN_NEW Branch-Level Causal Attribution Preregistration

**Status:** PREREGISTERED / NOT YET MEASURED  
**Policy changes:** none  
**Input:** exact frozen Phase 8C.12 CognitiveEffect realizations

## Motivation

Phase 8C.13 found coarse `OPEN_NEW(null)` singularly load-bearing 6/6 for RS11 WATCH. Inspection shows the free-text branch meaning is not identical across runs. Coarse relation identity can therefore hide branch drift.

## Measurement-only branch identity

For OPEN_NEW only, derive a conservative support signature from explicit canonical source-unit references in the effect reason. Example: `RS11-N11` or shorthand `N9/N10` becomes `(OPEN_NEW, {RS11-N9, RS11-N10})`.

Targeted REINFORCE/CHALLENGE relations keep `(operation,target)` identity.

This signature is not a production semantic identifier and does not claim that two branches citing the same unit are semantically identical. If no source-unit reference can be resolved, mark the branch `UNRESOLVED`; do not invent identity from free-text similarity.

## Counterfactual

Reuse `decision-causal-core-v0.1` with the branch-aware relation key. Within each already frozen realization, perform deterministic `without-branch` and `branch-alone` replay under Anchored OPEN_NEW + Magnitude-Free + Pareto. No LLM calls.

Primary question: is coarse OPEN_NEW causal stability supported by stable source-grounded branch identity, or is the load-bearing branch itself changing across realizations?

No admission redesign is allowed until this attribution is frozen.
