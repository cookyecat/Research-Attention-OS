# Phase 10B.2 — Current Basin Persistence Result

Status: PERSISTENT BASIN PATTERN OBSERVED / NO STOCHASTIC PROCESS FIT

## Artifacts

- fresh `t2`: `eval/live/results/phase10b2_current_basin_persistence_v0_1/phase10b2_current_basin_persistence_v0.1_20260910T083922Z.json`
- t2 SHA256: `67c36fb40e2185784bf75d744e54c86213f10a6c74d07f9897a68f54845b5f28`
- triangular comparison: `eval/live/results/phase10b2_persistence_comparison_v0_1/phase10b2_persistence_comparison_v0.1_20260910T084056Z.json`
- comparison SHA256: `8ecc8cb58f252a9175818bc3c5702870035361d35c4ed1f43eabdbf05946ab40`

All t2 samples record `requested_model=deepseek-v4-flash` and `response_model=deepseek-flash`. Audited semantic worlds, Kernel fixtures, historical modal Locate fixtures, downstream admission/calibration/Pareto/core logic, prompt and temperature are frozen as preregistered.

## Fresh t2 Attention map

| Case | t2 Attention |
|---|---|
| RS05 | ENGAGE 12/12 |
| RS15 | ENGAGE 11/12, WATCH 1/12 |
| RS11 | WATCH 12/12 |
| RS12 | WATCH 12/12 |

## Three-checkpoint persistence gate

A metric has a `persistent_new_basin_pattern` only when `t0↔t1` drift is supported, `t0↔t2` drift is supported, and `t1↔t2` drift is not supported under the same 5000-permutation null gate.

| Case | Attention | Load-bearing | Topology |
|---|---|---|---|
| RS05 | stable | not persistent | stable |
| RS15 | **persistent shift** | **persistent shift** | **persistent shift** |
| RS11 | **persistent shift** | **persistent shift** | **persistent shift** |
| RS12 | stable | **persistent shift** | **persistent shift** |

RS15 is the clearest bimodal cognitive-map case: t1 was ENGAGE 20/24 vs WATCH 4/24 and t2 is ENGAGE 11/12 vs WATCH 1/12; their Attention JSD is only 0.0116 and is null-compatible, while both remain strongly separated from historical t0 WATCH-only.

RS11 likewise remains in the new WATCH basin at t2, separated from historical AWARE-only. RS12 demonstrates a persistent internal structural basin change that is absorbed by the Attention layer. RS05 does not support a persistent load-bearing shift despite the earlier t0↔t1 signal.

## Interpretation boundary

This is evidence for persistent **RAOS system-level cognitive basin structure** across three checkpoints, not proof of a dynamical attractor, Markov process, or intrinsic model-weight drift. Historical requested-model identity remains incompletely instrumented.

The next Occam layer is a deterministic temporal regime/change-point classifier over null-calibrated checkpoint distances. Do not fit a stochastic-process model yet. Production default remains `one-delta-v1`.
