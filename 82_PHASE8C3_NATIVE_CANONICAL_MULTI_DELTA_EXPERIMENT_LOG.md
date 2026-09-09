# Phase 8C.3 — Native Canonical Multi-Delta Experiment Log

Status: **ACTIVE — STEP 1 TEMPERATURE A/B PREREGISTERED**
Date: 2026-09-09

## Purpose

Test the next RAOS architecture without treating the Phase 8C.2 legacy `ExtractionResult` bridge as the final production language.

Working sequence:

```text
1. Temperature 0.1 vs 0
2. Native Canonical Semantic Interface
3. Multi-Locate / Multi-Delta
4. Per-channel Attention
5. Article-level Attention aggregation and RS05/RS15/RS11/RS12 rerun
```

Phase 7A remains the semantic working baseline:

$$
\boxed{Decision\text{-}Sufficient\ Semantic\ Precision=Evidence\ Fidelity+Scope\ Fidelity+Relational\ Fidelity}
$$

Do not replace this formulation without controlled contrary evidence.
## Step 1 — Temperature stability A/B

Question: how much of the observed instability can be reduced by removing intentional sampling variance?

Freeze the perception layer completely:

```text
Sensor + Auditor + Audited Semantic Representation = fixed
```

Repeat only the cognitive decision modules:

```text
Locate / match_kernel
→ Cognitive Impact / Delta
→ Attention Policy
```

Cases:
- RS15 fixed semantic world from the prior boundary attribution.
- RS05 frozen Phase 7A canonical four-unit world as a stable control.

Conditions: `temperature=0.1` versus `temperature=0.0`, 6 repeats each, interleaved. Production defaults remain unchanged. The new client parameter preserves `0.1` as the default and exists only to make the A/B controllable.

### Step 1 measurement clarification

An exploratory pre-measurement call showed that `temperature=0` can deterministically repeat a structurally invalid `ModelDeltaResponse` even after repair. This is not silently repaired or excluded. The canonical A/B therefore records both valid-decision variance and schema/technical failure rate. The exploratory calls are not measurement evidence.

## Step 1 — Result

Measurement SHA: `9373c93cb9360e329ff2f502ac5e989c789f6446`
Artifact: `eval/live/results/phase8c3_temperature_stability_ab_v0_1/phase8c3_temperature_stability_ab_v0.1_20260909T130755Z.json`
Artifact SHA256: `056909a0c0454d9e8e4c07b50fc7b4eaeceb9602a37c1b0c9009990e8b75c15d`

```text
RS15 T=0.1: 3/6 valid; B2/WATCH x2, Q2/ENGAGE x1; 3 schema failures
RS15 T=0.0: 2/6 valid; B2/WATCH x1, Q2/ENGAGE x1; 4 technical/schema failures
RS05 T=0.1: 2/6 valid; CHALLENGE/ENGAGE x2; 4 schema failures
RS05 T=0.0: 3/6 valid; CHALLENGE/ENGAGE x3; 3 schema failures
```

Decision: `temperature=0` is **not** a validated stabilization fix on the current DeepSeek API / structured-output protocol. It neither removed the RS15 Q2/B2 boundary nor improved technical reliability. Low temperature remains a plausible engineering principle for a different provider or self-hosted deployment, but provider/model A/B is deferred so it does not interrupt the five-step architecture experiment.

## Step 2 — Native Canonical Semantic Interface preregistration

Question: can the cognitive modules consume Phase 7 audited semantic units directly, without constructing legacy `ExtractionResult` or invoking the 8C.2 bridge?

Measurement path:

```text
Frozen Phase7A audited semantic units
→ native_locate(units, Kernel)
→ native_assess(units, matches, Kernel)
→ CognitiveImpactResponse.effects[]
```

This probe intentionally bypasses `ExtractionResult`, bridge projection, production evidence fields, and single-primary `ModelDelta`. Cases: RS05/RS15/RS11/RS12, using the exact Phase7A canonical Auditor artifact; 3 repeats each at current provider temperature 0.1. Step 2 is an interface viability/stability probe only. Step 3 will analyze the multiple effects as cognitive deltas rather than selecting an argmax.

### Step 2 pre-measurement correction

The first live attempt failed before producing usable native-interface evidence because the new measurement prompt referenced `CognitiveImpactResponse` by name but did not include its explicit JSON shape. `chat_json_schema` validates locally; it does not automatically transmit the Pydantic schema to the model. This is a harness-contract defect, not a semantic result. The invalid attempt is excluded. The native impact prompt now carries the exact output shape before the measurement SHA is re-frozen.

### Step 2 control-set correction

The first complete native run showed RS05/RS15 successfully but RS11/RS12 failed before model execution because the selected Phase7A audit artifact contains only RS05/RS15. The canonical v0.2.6 regression audit artifact contains RS11/RS12. This is a fixture-loading error, not a semantic result. The loader now selects the appropriate frozen Phase7A artifact per case; the mixed run is excluded and Step 2 is re-frozen before rerun.

## Step 2 — Result

Measurement SHA: `d961ccb0c71ebcae79e78e04e1f7a2bff2241a29`
Artifact: `eval/live/results/phase8c3_native_interface_probe_v0_1/phase8c3_native_interface_probe_v0.1_20260909T135412Z.json`
Artifact SHA256: `3f68c034b55fd8a132c282027f87fe3665a388ed94e8be2e653bfba6aaf55d9e`

All four cases completed 3/3 without bridge or `ExtractionResult`. RS15 produced the same six REINFORCE target channels in all three repeats, including both Q2 and B2 simultaneously; the old Q2↔B2 argmax oscillation disappears at the effect-set level. RS05 preserved its core CHALLENGE 3/3 while optional OPEN_NEW branches varied. RS11 exposed weak over-generation (many effects with very small magnitude/importance), so native multi-effect output requires effect-level materiality/attention handling rather than treating every emitted effect as equally decision-bearing. RS12 remained a weak multi-effect boundary case.

Decision: native canonical semantic consumption is viable enough to continue. Step 3 will preserve multiple effects and analyze stable/core versus optional/weak channels; it will not restore single-primary selection.

## Step 3 — Multi-Locate / Multi-Delta preregistration

Step 3 does not make new LLM calls. It deterministically re-reads the frozen Step-2 native artifact and treats each distinct `(operation, target)` CognitiveEffect as a separate candidate Δ channel. No `select_primary_effect()` or argmax is applied.

For each case it records: per-repeat effect set; repeat frequency of every operation-target channel; `core` channels present in every valid repeat; optional channels; and diagnostic utility `change_magnitude × target_importance`. Utility is descriptive only in Step 3. No Attention threshold is introduced until Step 4.

## Step 4 — Per-channel Attention

Input is frozen Step 2 native `CognitiveEffect[]`; no new LLM calls.
Each candidate effect is classified independently using the existing cognitive thresholds:
`MATERIAL_CHANGE_MIN=0.35`, `MEANINGFUL_CHANGE=0.55`, `LOW_EPISTEMIC=0.45`.

Multi-Delta-specific clarification: sub-material candidate effects do not receive article-level AWARE merely because an LLM mentioned them; channel-level sub-material effects are DROP. AWARE remains an article-level no-Delta / D-S-P situational-awareness outcome. Production policy remains unchanged.
