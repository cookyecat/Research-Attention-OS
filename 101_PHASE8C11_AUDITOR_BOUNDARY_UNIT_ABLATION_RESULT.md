# Phase 8C.11 — Auditor Boundary-Unit Causal Ablation Result

**Status:** EXPERIMENTALLY COMPLETE — 2026-09-10  
**Measurement SHA:** `043da08846e2d208db5f9f070d674af1429b48e0`  
**Artifact:** `eval/live/results/phase8c11_auditor_boundary_unit_ablation_v0_1/phase8c11_auditor_boundary_unit_ablation_v0.1_20260910T035325Z.json`  
**Artifact SHA256:** `111bf7222d0ae653515fd6b1f87d4edea5cf0e4d9a82892af028885df467d6ce`

## Question

Gate 2B showed historical→current Attention shifts after Auditor admitted one or more boundary units. This experiment asks the stricter causal question: **is the newly admitted boundary unit itself necessary for the Attention shift?**

The intervention is same-SHA and paired: `full admitted world` versus `same world - designated boundary unit(s)`. Locate is repeated to choose a modal arm-specific realization; Impact calls are then interleaved `full -> ablated -> full -> ablated` to reduce temporal confounding. Downstream is frozen to Anchored OPEN_NEW + Magnitude-Free + Pareto.

## Results

| Case | Ablation | Full Attention | Ablated Attention | Causal reading |
|---|---|---|---|---|
| RS05 | remove U06,U08 | ENGAGE 6/6 | ENGAGE 6/6 | negative propagation control; core CHALLENGE preserved |
| RS15 | remove NEU4 | ENGAGE 5/6, WATCH 1/6 | ENGAGE 6/6 | NEU4 is not necessary for current ENGAGE basin |
| RS11 | remove N1 | ENGAGE 6/6 | ENGAGE 6/6 | N1 is not necessary for current ENGAGE basin |
| RS12 | remove N11 | WATCH 6/6 | WATCH 6/6 | N11 is not necessary for current WATCH outcome |

RS15 critical `REINFORCE(Q2)` and `REINFORCE(B2)` recall remained 1.0 in both arms. RS05 critical `CHALLENGE(CF-B-PERF)` recall remained 1.0 in both arms.

## Conclusion

The Gate 2B historical→current Attention differences **cannot be attributed to the designated Auditor boundary units as necessary single-unit causes**. In RS15 and RS11, removing the suspected newly admitted unit did not restore the historical WATCH/AWARE basin. RS12 similarly remained WATCH after removing N11.

The stronger remaining hypothesis is therefore **longitudinal Cognitive Mapping basin drift**: the same or nearly identical audited semantic world may map to a different distribution of CognitiveEffects at a later time. This must be measured directly before redesigning Auditor policy.

This result also reinforces a measurement rule: high admitted-set similarity (e.g. Jaccard) is descriptive only; decision-causal influence must be tested by intervention under the actual downstream policy.

## Next gate

Phase 8C.12 should isolate longitudinal stability of the downstream cognitive mapping itself, separating Locate from relation/effect mapping wherever possible. No production default changes are justified by this experiment.
