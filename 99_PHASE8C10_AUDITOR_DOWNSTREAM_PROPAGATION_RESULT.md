# Phase 8C.10 — Auditor Gate 2B Downstream Propagation Result

Status: GATE 2B COMPLETE / BOUNDARY-UNIT ABLATION REQUIRED
Date: 2026-09-10

## Measurement

Final measurement SHA: `7f4d2d5c1b2bebe228d2c210b55b080da77a81f3` (the preceding harness commit failed before model calls because it read the Phase 8C.8 artifact with the wrong top-level key; no measurement artifact was produced from that revision).

Artifact: `eval/live/results/phase8c10_auditor_downstream_propagation_v0_1/phase8c10_auditor_downstream_propagation_v0.1_20260910T034552Z.json`

SHA256: `6c015289a31ecce1de6d7a9d0649d513616af1af9e27ae0bb9d4ccf687f45734`.

Each distinct Gate 2A admitted world that differed from the historical Phase 7A audited reference was evaluated with Locate ×3, frozen modal Locate, Cognitive Impact ×4, then Anchored OPEN_NEW Admission + Magnitude-Free + Pareto.

## Results

### RS05 — Auditor variance absorbed

Historical 4-unit audited world: critical `CHALLENGE(CF-B-PERF)` recall 6/6, `ENGAGE 6/6`.

Current 6-unit modal world (+U06,+U08): critical recall 4/4, `ENGAGE 4/4`.

Current 7-unit minority world (+U03,+U06,+U08): critical recall 4/4, `ENGAGE 4/4`.

The additional admitted units change peripheral topology volume but do not alter the critical relation or Article Attention.

### RS15 — stable Auditor basin shift propagates

Historical 7-unit audited world: `REINFORCE(B2)` and `REINFORCE(Q2)` recall 6/6; `WATCH 6/6`.

Current 8-unit world (+NEU4), produced by fresh Auditor 4/4: both critical REINFORCE relations remain 4/4, but new CHALLENGE topology appears and Article Attention becomes `ENGAGE 4/4`.

Thus the old critical relation is preserved while the admitted-world expansion adds new decision-bearing relations. This is an Attention change, not a loss of the RS15 core topology.

### RS11 — one-unit Auditor boundary jitter propagates strongly

Historical/modal 8-unit world: `AWARE 6/6` in Phase 8C.8.

One fresh Auditor repeat additionally admitted N1. On that 9-unit world, Article Attention is `ENGAGE 4/4` despite topology variation. High admitted-set Jaccard (~0.94 within fresh repeats) therefore does not imply decision irrelevance.

### RS12 — stable Auditor basin shift reopens Attention variation

Historical 11-unit world: `WATCH 6/6`.

Current 12-unit world (+N11), produced by fresh Auditor 4/4: `ENGAGE 3/4`, `WATCH 1/4`. The admitted-world shift increases attention and exposes additional Cognitive Mapping variance.

## Evidence-boundary inspection

The changed units are not semantically equivalent cases:

- RS15 NEU4: historical `MISSING_SUPPORT`; current `SUFFICIENT 4/4`. Its frozen packet contains three consecutive supports for the predictive-introspection mechanism and the 87% vs 61% comparison, so current admission may correct an earlier false negative.
- RS12 N11: historical `OVERSTRONG_SCOPE`; current `SUFFICIENT 4/4`. The frozen support explicitly states cumulative delivery near 10k and an expected September crossing, making the historical/current boundary genuinely debatable rather than obviously erroneous.
- RS11 N1: historical `MISSING_SUPPORT`; fresh `INSUFFICIENT 3/4`, `SUFFICIENT 1/4`. The statement aggregates several benchmark comparisons while the frozen packet is much narrower, making the lone fresh admission a stronger false-positive candidate.

## Conclusion

\[
\boxed{V_{Auditor}\text{ can be decision-causal even when admitted-set Jaccard is high.}}
\]

But stability and correctness are distinct. A current admission differing from history may be a correction, a false positive, or a legitimate boundary judgment. Do not optimize for historical identity.

Next gate: paired same-SHA boundary-unit ablation for NEU4 / N1 / N11, with RS05 as a negative propagation control. Only after causal necessity is established should Auditor admission semantics be redesigned.
