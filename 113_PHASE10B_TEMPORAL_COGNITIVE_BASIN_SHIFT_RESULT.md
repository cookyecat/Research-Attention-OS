# Phase 10B — Temporal Cognitive Basin Shift Result

Status: CROSS-EPOCH SHIFT DETECTED / STOCHASTIC-PROCESS MODEL NOT YET JUSTIFIED

## Frozen comparison

Two frozen epochs are replayed under the same downstream research stack: Anchored OPEN_NEW Admission + Magnitude-Free Calibration + Pareto + Decision-Causal Core + branch-level OPEN_NEW identity. No LLM calls occur in the cross-epoch replay or null calibration.

- Phase 10B artifact: `eval/live/results/phase10b_temporal_cognitive_basin_shift_v0_1/phase10b_temporal_cognitive_basin_shift_v0.1_20260910T081018Z.json`
- SHA256: `098dde0df2922a2244c26b99777a7744384394603831031f647d066605dc72d0`
- Phase 10B.1 null artifact: `eval/live/results/phase10b1_cross_epoch_null_calibration_v0_1/phase10b1_cross_epoch_null_calibration_v0.1_20260910T083329Z.json`
- SHA256: `439d6556ddea38eca28ca18e7a6ef5a059091ce99f4826a50ba05f4f4820fc46`

## Null-calibrated result

| Case | Attention JSD | Attention drift | Load-bearing JSD | Core drift | Topology JSD | Topology drift |
|---|---:|---|---:|---|---:|---|
| RS05 | 0.000 | no | 0.288 | **yes** | 0.108 | no |
| RS15 | 0.655 | **yes** | 1.000 | **yes** | 1.000 | **yes** |
| RS11 | 1.000 | **yes** | 1.000 | **yes** | 1.000 | **yes** |
| RS12 | 0.000 | no | 0.717 | **yes** | 1.000 | **yes** |

A v0.1 drift gate requires observed JSD > permutation-null p95 and Monte Carlo upper-tail probability <= 0.05 with 5000 fixed-seed permutations.

## Interpretation

RS15 and RS11 show system-level longitudinal basin-shift signals that propagate through the Decision-Causal Core into the final Attention distribution. RS12 is the strongest robustness control: cognitive topology and load-bearing structure shift, yet Attention remains WATCH with zero Attention JSD. RS05 keeps the same Attention and approximately the same topology while some redundant load-bearing participation changes.

Therefore:

`Topology drift != Decision drift`

and
`Load-bearing drift != necessarily Attention drift`.

The most decision-relevant stability object is not exact topology equality but the distribution of decision-bearing structure together with the resulting Attention distribution.

## Model-identity instrumentation caveat

Historical artifacts recorded only provider response model names. Current live instrumentation verifies that requesting `deepseek-v4-flash` can return response model `deepseek-flash`. `chat_json()` now records both `requested_model` and `response_model`. Historical requested-model identity is therefore inferred rather than directly observed; this result is a **RAOS system-level longitudinal comparison**, not proof of intrinsic same-model weight drift.

## Decision

Do **not** fit a Markov/HMM/stochastic-process model yet. Two epochs are insufficient to distinguish a persistent basin transition from an isolated epoch shift. The next gate is an independently sampled current checkpoint `t2`. If `t0` differs from both `t1` and `t2`, while `t1` and `t2` are mutually compatible under the same configuration identity, the basin-shift interpretation becomes substantially stronger.

Production default remains `one-delta-v1`.
