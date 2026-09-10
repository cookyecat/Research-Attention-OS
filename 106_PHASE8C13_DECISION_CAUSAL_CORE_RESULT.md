# Phase 8C.13 — Decision-Causal Core Result

**Status:** EXPERIMENTALLY COMPLETE  
**Canonical measurement SHA:** `c77ad268948671bd193467f12b8433443c12c2c7`  
**Artifact:** `eval/live/results/phase8c13_decision_causal_core_v0_1/phase8c13_decision_causal_core_v0.1_20260910T073058Z.json`  
**SHA256:** `dfb1c2b8ca9cef464f9f272b4e8fe784a68615251d374efcb094bd712a1b1407`

## Measurement correction

An earlier exploratory artifact at `20260910T072925Z` exposed a definition bug through the D negative control: `alone == baseline == DROP` was incorrectly counted as sufficient. That artifact is invalid for inference. The chip was corrected so sufficiency additionally requires `baseline != null_decision`; contract regression passed before the canonical rerun above.

## Core definitions

First-order necessary core: removing relation `r` changes Article Attention disposition. First-order sufficient support: relation `r` alone reproduces the baseline disposition and the baseline differs from the empty-relation decision. This distinguishes singular load-bearing relations from redundant load-bearing supports without power-set search.

## Findings

- RS05: `CHALLENGE(CF-B-PERF)` occurs 6/6, is sufficient 6/6 and necessary 5/6. It is the strongest stable load-bearing relation. One realization has an OPEN_NEW branch that redundantly sustains ENGAGE.
- RS15: current ENGAGE realizations are redundantly sustained by `CHALLENGE(B1)` and `CHALLENGE(Q1)`; `CHALLENGE(BT1)` occurs 6/6 but is peripheral 6/6. Historical semantic sentinels Q2/B2 remain frequent but are not the current ENGAGE load-bearing core.
- RS11: the relation class `OPEN_NEW(null)` is singular load-bearing 6/6 for current WATCH. All other measured relation classes are peripheral to the Article disposition.
- RS12: `REINFORCE(BT1)` is sufficient 6/6 and necessary in the one realization without a redundant OPEN_NEW support. This explains why topology can vary while WATCH remains stable.
- D: free-floating OPEN_NEW remains peripheral under Anchored admission, including the prior burst realization.

## Interpretation

`Semantic Core != Decision-Causal Core`. Relation frequency, semantic importance and Jaccard similarity cannot substitute for policy counterfactuals. Phase 8C.13 also shows why singleton necessity alone is insufficient under Pareto: redundant load-bearing relations can each be sufficient while neither is individually necessary.

RS11 exposes the next attribution boundary. `OPEN_NEW(null)` is stable at the coarse decision-relation level, but inspection shows its free-text branch meaning varies across realizations. Therefore branch identity must be measured before redesigning admission or entering probabilistic modeling.

Production default remains `one-delta-v1`.
