# Phase 8C.3 — Native Canonical Multi-Delta Result

Status: **EXPERIMENTALLY COMPLETE / PRODUCTION NOT PROMOTED**
Date: 2026-09-09

## Question

Test whether RAOS becomes more faithful and stable when the Phase 7 canonical audited semantic representation is consumed natively, without the legacy `ExtractionResult` bridge and without forcing one article into one primary cognitive transition.

Frozen semantic baseline remains:

$$
\boxed{Decision\text{-}Sufficient\ Semantic\ Precision=Evidence\ Fidelity+Scope\ Fidelity+Relational\ Fidelity}
$$

No result in this phase justifies replacing that formulation.
## Step 1 — Temperature stability

Frozen perception; repeated only Locate / Cognitive Impact / Delta / Attention Policy.

- RS15 `T=0.1`: 3/6 valid, B2×2 / Q2×1; 3 schema failures.
- RS15 `T=0`: 2/6 valid, B2×1 / Q2×1; 4 technical/schema failures.
- RS05 valid outputs remained CHALLENGE/ENGAGE at both temperatures.

Result: on the current DeepSeek structured-output path, `T=0` neither removed RS15 target oscillation nor improved schema reliability.

Artifact SHA256: `056909a0c0454d9e8e4c07b50fc7b4eaeceb9602a37c1b0c9009990e8b75c15d`.

## Step 2 — Native canonical interface

Path:
`Audited Semantic Units -> Native Locate -> CognitiveImpactResponse.effects[]`.
No bridge, no `ExtractionResult`, no single-primary ModelDelta.
RS05 preserved the core `CHALLENGE(CF-B-PERF)` effect 3/3; optional OPEN_NEW branches varied.

RS15 produced the same operation-target effect set 3/3 and simultaneously retained Q2, B2, M1, B1, Q1, and BT1. The previous Q2-vs-B2 forced choice disappeared at the effect-set level.

RS11 and RS12 also produced multiple weak candidate effects; this showed that native multi-effect output needs a materiality gate and cannot treat every generated relation as decision-worthy.

Exact measurement SHA: `d961ccb0c71ebcae79e78e04e1f7a2bff2241a29`.
Artifact SHA256: `3f68c034b55fd8a132c282027f87fe3665a388ed94e8be2e653bfba6aaf55d9e`.

## Step 3 — Multi-Delta analysis

No new LLM calls. Step 2 effects were decomposed deterministically by operation/target and utility.

RS15 Q2 and B2 were both present 3/3:
- Q2 utility mean `0.33` (min `0.18`, max `0.54`).
- B2 utility mean `0.283` (min `0.17`, max `0.425`).

This establishes stable target-set membership under the native multi-effect probe while leaving magnitude variance visible.
Exact measurement SHA: `6ee83dfb4f366d93d0cce131817b0a98e15e9d46`.
Artifact SHA256: `2076501c50862bc15abd8e809f5f6cf81a92c9d131603ed37469f517e88b0bd0`.

## Step 4 — Per-channel Attention

No new LLM calls. Existing cognitive thresholds were applied independently to each candidate effect:
`MATERIAL_CHANGE_MIN=0.35`, `MEANINGFUL_CHANGE=0.55`, `LOW_EPISTEMIC=0.45`.
Sub-material candidate effects are channel DROP; article-level AWARE remains reserved for no-Delta D/S/P / situational-awareness logic.

- RS05: core CHALLENGE -> ENGAGE 3/3.
- RS11: all 19 weak candidate channels -> DROP.
- RS12: all 18 weak candidate channels -> DROP.
- RS15: 16/18 channels -> DROP; only repeat 3 yielded Q2=ENGAGE and B2=WATCH.

Exact measurement SHA: `d77d429b55a2735b1e3991e578adf57d2169d171`.
Artifact SHA256: `b094c4b153bae559a98a1c7c0e63dba537dbc93727cdb3d3eb89feb6ff611e89`.
## Step 5 — Article Attention aggregation

Article Attention was reduced only by the fixed order:

`ENGAGE > WATCH > AWARE > DROP`

with no post-result threshold tuning.

Results:
- RS05: ENGAGE 3/3, stable.
- RS15: DROP 2/3, ENGAGE 1/3, unstable.
- RS11: DROP 3/3, stable.
- RS12: DROP 3/3, stable.

Exact measurement SHA: `219e30006367a01d5fddcb5f27efdb50b719ee72`.
Artifact SHA256: `ed8a62959c76ec5746169171829c8d98c1beba402cda9e1770738bdd1d054bfd`.

## Experimental closure

The five-step experiment is complete. Native canonical Multi-Delta removes the forced Q2/B2 single-target competition for RS15, but does **not** by itself make RS15 article Attention stable under the current magnitude estimates and frozen materiality thresholds.

Production defaults remain unchanged. The Phase 8C.2 bridge remains a compatibility experiment path; this Phase 8C.3 probe independently validates the native canonical direction without promoting it into production.

## Regression

Post-experiment broader regression:
`72 passed, 1 deselected, 1 warning in 1.18s`.
The deselected Case K remains the pre-existing non-8C.3 residual. No production behavior was changed by this measurement phase.
