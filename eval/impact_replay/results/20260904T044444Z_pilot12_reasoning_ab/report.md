# RAOS Pilot-12 — Cognitive Impact Reasoning A/B

- **HEAD:** `983c7f01071a5456979fcae8516dbda7a2be118f`
- **Model:** `deepseek-v4-flash`
- **Thinking protocol:** `deepseek`
- **Manifest:** `eval/live/manifest.pilot12.v2.yaml`
- **Cases:** 12; **repeats/condition:** 2
- **Fresh EXACT inputs:** 12/12
- **Embedding used:** 12/12
- **Production errors:** 0; **runs with any fallback:** 2

## Experiment definitions

1. **Thinking:** `OFF = thinking=disabled, effort omitted` vs `ON = thinking=enabled, effort omitted`. Expected effective diff: `{thinking}`.
2. **Reasoning effort:** `LOW = thinking=enabled, effort=low` vs `HIGH = thinking=enabled, effort=high`. Expected effective diff: `{reasoning_effort}`.

> This is Impact-only replay. It evaluates **Update(Operation, Target)**. Scheduler/Disposition is not rerun and is not scored here.

## Experimental validity

| Experiment | Valid causal pairs | Total pairs | Diagnostic valid | Diagnostic total |
|---|---:|---:|---:|---:|
| Thinking OFF→ON | 22 | 24 | 7 | 8 |
| Effort LOW→HIGH | 24 | 24 | 8 | 8 |

## Aggregate Update quality and Impact cost

| Condition | N | Operation acc | Target acc* | Exact Update acc | Mean latency ms | Mean prompt tok | Mean completion tok |
|---|---:|---:|---:|---:|---:|---:|---:|
| OFF | 24 | 50.0% | 25.0% | 33.3% | 2326.542 | 10257.333 | 277.167 |
| ON | 24 | 41.7% | 12.5% | 41.7% | 44333.958 | 9744.958 | 4787.0 |
| LOW | 24 | 20.8% | 0.0% | 20.8% | 15353.208 | 10257.333 | 1869.417 |
| HIGH | 24 | 33.3% | 25.0% | 33.3% | 44373.458 | 10336.333 | 4798.333 |

*Target accuracy denominator only includes Gold REINFORCE/CHALLENGE cases.*

## Thinking effect: OFF → ON

| Scope | Improved | Regressed | Both correct | Both wrong | Raw changed | Grounded changed | Primary changed |
|---|---:|---:|---:|---:|---:|---:|---:|
| All | 4 | 3 | 5 | 10 | 14 | 14 | 13 |
| Diagnostic 03/05/07/12 | 0 | 0 | 0 | 7 | 5 | 5 | 5 |

## Reasoning-effort effect: LOW → HIGH

| Scope | Improved | Regressed | Both correct | Both wrong | Raw changed | Grounded changed | Primary changed |
|---|---:|---:|---:|---:|---:|---:|---:|
| All | 3 | 0 | 5 | 16 | 12 | 12 | 9 |
| Diagnostic 03/05/07/12 | 0 | 0 | 0 | 8 | 5 | 5 | 5 |

## Diagnostic probes

| Case | Gold Update | OFF | ON | LOW | HIGH | OFF exact | ON exact | LOW exact | HIGH exact |
|---|---|---|---|---|---|---:|---:|---:|---:|
| pilot12-03 | REINFORCE:M1 | REINFORCE:BT1×2 | OPEN_NEW×2 | NONE×2 | OPEN_NEW×2 | 0/2 | 0/2 | 0/2 | 0/2 |
| pilot12-05 | REINFORCE:BT1 | NONE×2 | NONE×2 | NONE×2 | NONE×2 | 0/2 | 0/2 | 0/2 | 0/2 |
| pilot12-07 | REINFORCE:M1 | REINFORCE:Q1×2 | NONE, OPEN_NEW | NONE, OPEN_NEW | NONE, OPEN_NEW | 0/2 | 0/2 | 0/2 | 0/2 |
| pilot12-12 | OPEN_NEW | NONE, REINFORCE:BT1 | NONE, OPEN_NEW | NONE×2 | NONE, REINFORCE:BT1 | 0/2 | 1/2 | 0/2 | 0/2 |

## Full selected set

| Case | Gold Update | OFF | ON | LOW | HIGH | OFF exact | ON exact | LOW exact | HIGH exact |
|---|---|---|---|---|---|---:|---:|---:|---:|
| pilot12-01 | OPEN_NEW | NONE×2 | OPEN_NEW×2 | NONE, OPEN_NEW | OPEN_NEW×2 | 0/2 | 2/2 | 1/2 | 2/2 |
| pilot12-02 | OPEN_NEW | NONE×2 | NONE, OPEN_NEW | NONE×2 | NONE×2 | 0/2 | 1/2 | 0/2 | 0/2 |
| pilot12-03 | REINFORCE:M1 | REINFORCE:BT1×2 | OPEN_NEW×2 | NONE×2 | OPEN_NEW×2 | 0/2 | 0/2 | 0/2 | 0/2 |
| pilot12-04 | OPEN_NEW | NONE, REINFORCE:Q1 | OPEN_NEW, REINFORCE:M1 | NONE, REINFORCE:M1 | NONE×2 | 0/2 | 1/2 | 0/2 | 0/2 |
| pilot12-05 | REINFORCE:BT1 | NONE×2 | NONE×2 | NONE×2 | NONE×2 | 0/2 | 0/2 | 0/2 | 0/2 |
| pilot12-06 | OPEN_NEW | NONE×2 | NONE, REINFORCE:BT1 | NONE×2 | NONE×2 | 0/2 | 0/2 | 0/2 | 0/2 |
| pilot12-07 | REINFORCE:M1 | REINFORCE:Q1×2 | NONE, OPEN_NEW | NONE, OPEN_NEW | NONE, OPEN_NEW | 0/2 | 0/2 | 0/2 | 0/2 |
| pilot12-08 | REINFORCE:BT1 | REINFORCE:BT1×2 | NONE, REINFORCE:BT1 | NONE×2 | REINFORCE:BT1×2 | 2/2 | 1/2 | 0/2 | 2/2 |
| pilot12-09 | NONE | NONE×2 | NONE×2 | NONE×2 | NONE×2 | 2/2 | 2/2 | 2/2 | 2/2 |
| pilot12-10 | NONE | NONE×2 | OPEN_NEW×2 | OPEN_NEW×2 | OPEN_NEW×2 | 2/2 | 0/2 | 0/2 | 0/2 |
| pilot12-11 | NONE | NONE×2 | NONE×2 | NONE×2 | NONE×2 | 2/2 | 2/2 | 2/2 | 2/2 |
| pilot12-12 | OPEN_NEW | NONE, REINFORCE:BT1 | NONE, OPEN_NEW | NONE×2 | NONE, REINFORCE:BT1 | 0/2 | 1/2 | 0/2 | 0/2 |

## Invalid / non-causal pairs

- `thinking` `pilot12-06` repeat 2: reasons=['b_fallback', 'b_runtime_error', 'runtime_error_or_timeout'], variable_diff={'model': {'a': 'deepseek-v4-flash', 'b': None}, 'provider': {'a': 'model', 'b': 'rule-fallback'}, 'thinking': {'a': 'disabled', 'b': None}, 'timeout': {'a': 120.0, 'b': None}}
- `thinking` `pilot12-12` repeat 2: reasons=['b_fallback', 'b_runtime_error', 'runtime_error_or_timeout'], variable_diff={'model': {'a': 'deepseek-v4-flash', 'b': None}, 'provider': {'a': 'model', 'b': 'rule-fallback'}, 'thinking': {'a': 'disabled', 'b': None}, 'timeout': {'a': 120.0, 'b': None}}

## Provenance notes

- Every case was rerun through the current production pipeline in an isolated SQLite DB before replay, so the intended input fidelity is `EXACT` (`impact-input-v0.2`).
- A/B comparisons use the Harness `causal_comparison` gate and actual wire-effective runtime conditions.
- Model stochasticity is not treated as Harness failure; repeats are reported rather than silently collapsed.
- No pre-`raos-impact-replay-0.2.1` replay artifact is reused.

## Files

- `report.md` — send this first
- `report.json` — aggregate + pairwise machine-readable details
- `replays.jsonl` — full raw/grounded/primary/runtime records
- `experiment.db` — isolated replay database

