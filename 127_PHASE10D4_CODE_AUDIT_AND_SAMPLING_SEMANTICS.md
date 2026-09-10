# Phase 10D.4 Code Audit and Sampling Semantics

Status: VERIFIED / NO EVIDENCE OF ATTENTION-JSD IMPLEMENTATION BUG

## Question

Why can Cognitive Topology vary substantially while `JSD_Attention` remains small? Is this intended downstream absorption, or an implementation error?

## Audited execution chain

For every Relation-Mapping sample, `collect_relation_sample(...)` performs a fresh `native_assess(...)` call, then routes the resulting legal CognitiveEffects through the frozen research strategy:

`Anchored OPEN_NEW Admission -> Magnitude-Free Calibration -> Pareto Frontier -> Article Attention Join`.

Each sample stores exactly one article-level Attention disposition: `DROP`, `AWARE`, `WATCH`, or `ENGAGE`.

The Decision-Causal Core analyzer immediately recomputes the baseline article disposition from the same assessment. The runner fails closed if this recomputed baseline differs from the disposition already recorded for that sample.

Therefore one realization is one fresh Relation-Mapping execution and one article-level Attention outcome; it is not one article containing N separately counted Attention labels.

## Independent numerical recomputation

Phase 10D.4 artifact Attention counts were recomputed directly from `t1_samples` and `t2_samples`, without using the project JSD helper. The Jensen-Shannon divergence was then recomputed from the empirical categorical probabilities.

Results matched the stored artifact to floating-point precision:

- A: manual `0.04614631890499564`, stored `0.04614631890499565`.
- D: manual/stored `0.0054404950486043446`.
- X: manual/stored `0.11443532098173957`.
- N4: manual/stored `0.0013096289721030874`.

No discrepancy was found.

The t2 samples also carry varying latency/completion-token metadata across calls. A had 24/24 distinct latency values; X 12/12; N4 24/24. The client path performs a fresh HTTP POST for every `chat_json(...)` call and contains no response cache in the audited path.

## Metric independence

`cognitive_map_distance_v0_1.py` computes the three distributions independently:

- Attention distribution from `sample["attention"]` only;
- Topology-state distribution from `sample["topology"]` only;
- Load-bearing-state distribution from `necessary_core U sufficient_supports` only.

Thus Topology JSD is not reused to calculate Attention JSD.

## Existing contract coverage

`backend/tests/eval/test_cognitive_map_distance_v0_1.py` already contains an explicit contract: topology may move while Attention remains unchanged. It asserts `attention_js_bits == 0`, `topology_state_js_bits == 1`, and unchanged load-bearing state for a constructed example.

This is therefore intended metric semantics, not an accidental coupling bug.

## Interpretation boundary

Small Attention JSD does not by itself prove the decision theory is correct. Article Attention is a four-state projection of a much richer Cognitive Topology, so coarse-graining can naturally reduce entropy and divergence.

The stronger evidence for downstream robustness is the combination:

1. topology/load-bearing variation is independently observed;
2. the frozen decision strategy is replayed on each realization;
3. article Attention remains concentrated or null-calibrated within the same basin;
4. the result repeats at an independent checkpoint.

D is the clearest Phase 10D.4 example: topology drift is supported by the permutation-null gate, while load-bearing and Attention distributions remain basin-compatible.

A and X should not be described as "unstable topology rescued by Attention": their cross-checkpoint topology JSD is itself small and null-compatible. N4 has high raw topology JSD because the topology state space is broad, but permutation calibration finds it compatible with the same topology basin.

## Conclusion

No evidence of an Attention/JSD implementation bug was found in the audited path. The evidence supports a layered interpretation: realization-level cognition can vary more than the final article-level decision, but this should be called robust only when the distributional and counterfactual controls support it, not merely because the output space is smaller.
