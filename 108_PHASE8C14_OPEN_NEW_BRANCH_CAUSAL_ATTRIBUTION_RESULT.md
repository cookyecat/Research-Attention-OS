# Phase 8C.14 — OPEN_NEW Branch-Level Causal Attribution Result

**Status:** EXPERIMENTALLY COMPLETE  
**Measurement SHA:** `34a97da46b4e7249657e9dc1c014eadc253f9443`  
**Artifact:** `eval/live/results/phase8c14_open_new_branch_causal_attribution_v0_1/phase8c14_open_new_branch_causal_attribution_v0.1_20260910T073517Z.json`  
**SHA256:** `1327abc2899acf7c93a936dd824c2ea139ae17e6b081fb9057678bdc342583f2`

## Question

Does coarse `OPEN_NEW(null)` causal stability correspond to a stable underlying branch, or can different source-grounded branches take turns carrying the same Article Attention action?

## Findings

RS11 is the key result. Coarse OPEN_NEW is load-bearing for WATCH in every Phase 8C.13 realization, but branch-aware attribution shows different supports:

- `OPEN_NEW[RS11-N11]` appears 5/6, is sufficient whenever present, and is singularly necessary 4/6;
- `OPEN_NEW[RS11-N10]` appears once and is singularly load-bearing in that realization;
- `OPEN_NEW[RS11-N9,N10]` appears once as a redundant load-bearing support;
- `OPEN_NEW[RS11-N9]` appears once but is peripheral.

Therefore stable Article Attention and stable coarse operation type can hide unstable load-bearing branch identity.

RS12 shows a more robust regime: `REINFORCE(BT1)` remains the stable sufficient WATCH support, while N12 / N6-N7 / N7 / N8 OPEN_NEW branches are redundant when present. RS15's OPEN_NEW branch is consistently grounded in NEU9/NEU10 but is only a WATCH-level redundant support; current ENGAGE is carried by challenge relations. RS05 retains `CHALLENGE(CF-B-PERF)` as the main load-bearing relation, with U05/U07/U09 branches only becoming redundant ENGAGE supports in one realization.

## Boundary exposed

`anchored-open-new-v0.1` checks only global jurisdiction presence. It does not bind each OPEN_NEW effect to a specific Kernel jurisdiction. Phase 8C.14 does not redesign admission, but establishes that effect/branch identity matters before probabilistic modeling or any v0.2 anchor proposal.

## Decision

Proceed to a static empirical probabilistic cognitive-map chip. The first pilot must report topology distribution, branch-aware causal-core/support distribution, and Attention distribution separately. No stochastic-process model yet; temporal dynamics remain gated on evidence of distribution shift across repeated epochs.

Production default remains `one-delta-v1`.
