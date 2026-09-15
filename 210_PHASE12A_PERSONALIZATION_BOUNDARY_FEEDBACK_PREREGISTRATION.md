# Phase 12A — Personalization Boundary & Feedback Attribution Preregistration

Status: **CLOSED / RESULT: `217_PHASE12A_FEEDBACK_ATTRIBUTION_RESULT.md`**
Date: 2026-09-15
Parent: `209_PHASE12_PERSONALIZATION_SCALE_PLAN.md`

## 1. Question

Can RAOS establish a causally clean feedback/personalization boundary such that Phase 12 remains an optional calibration layer and cannot absorb errors that belong to Phase 1–10 cognition, D/S/P, Runtime, or the shared Attention Policy?

## 2. Frozen architectural baseline

Phase 12 does not own the canonical core:

```text
Sensor/Auditor
→ Delta or no-Delta D/S/P
→ Runtime-conditioned canonical Attention Policy
→ AttentionPlan
```

Runtime `R_t` is a Phase 1–10 core input. It is separate from `Delta`, but it is not a Phase-12 parameter.

Null hypothesis for personalization:

```math
\boxed{A_t^{user}=A_t^{core}}
```

No `Theta_u` is required unless Phase 12B demonstrates a stable residual after causal attribution.

## 3. Frozen hypotheses

H1. Existing personalization through `K_t` and the D profile may already explain most user specificity.

H2. A user disagreement with an `AttentionPlan` is not automatically a personalization label; its causal layer must be attributed first.

H3. Runtime capture/policy error must not be learned as durable user preference.

H4. Existing append-only `AttentionFeedback` immutability is correct and should be preserved.

H5. Cognitive adjudication and Attention-policy correction are distinct evidence classes even when stored around the same plan.

H6. Passive interaction events are confounded and cannot become direct disposition Gold without separate validation.

H7. External Agent/task context may inform delegation provenance but cannot create a second Attention authority.

## 4. Required attribution vocabulary

Every explicit Phase-12 feedback item must be attributable to one or more named scopes before learning:

```text
PERCEPTION_ERROR
COGNITION_ERROR
AWARENESS_ERROR
RUNTIME_CAPTURE_ERROR
CORE_POLICY_ERROR
USER_POLICY_RESIDUAL
DELIVERY_PREFERENCE
ACTOR_CONTEXT_ERROR
```

Only `USER_POLICY_RESIDUAL` is eligible to update `Theta_u`.

`DELIVERY_PREFERENCE` updates delivery configuration only. `RUNTIME_CAPTURE_ERROR` corrects transient context only. A repeated `CORE_POLICY_ERROR` triggers a separate core-policy research question rather than personalization.

## 5. Existing feedback asset

`AttentionFeedback` already preserves:

```text
system_prediction
user_correction
corrected_fields
immutable original AttentionPlan
```

This is retained.

However current rows may mix:

```text
Cognitive adjudication:
  update / target / delta_content

Attention allocation correction:
  disposition
```

12A must expose this distinction explicitly in the feedback contract or in a provenance-preserving projection. Historical rows are never rewritten.

## 6. WATCH / Delivery / Agent outcomes

The following are observations, not automatic Gold:

```text
Delivery ACKNOWLEDGED
Delivery DISMISSED
WATCH CANCELLED
WATCH PROMOTED
Agent requested analysis
Agent requested WATCH
```

They become calibration evidence only when paired with explicit human adjudication or a separately validated causal rule.

## 7. Non-goals

12A will not:

- tune scheduler thresholds;
- alter Delta semantics;
- alter D/S/P definitions or estimators;
- change the no-Delta gate;
- learn Runtime response coefficients;
- fit the historical 30-case questionnaire;
- train a user embedding/model;
- infer preference from clicks, dwell, acknowledgement, or dismissal.

## 8. Measurement / implementation plan

1. Audit current `AttentionFeedback`, WATCH, Delivery and Agent provenance stores.
2. Define the minimal attribution fields/projection needed to distinguish causal scopes.
3. Preserve append-only history and frozen system prediction.
4. Prove that feedback recording cannot mutate `AnalysisRun`, `AttentionPlan`, `DeliveryEnvelope`, WATCH history, Delta, D/S/P or Runtime snapshots.
5. Audit existing historical feedback and classify what is actually usable for future calibration.
6. Produce a Phase 12B fresh residual-necessity instrument only after the boundary is unambiguous.

## 9. Exit criteria

12A closes only when:

1. core-owned vs Phase-12-owned state is frozen in docs;
2. Runtime is explicitly excluded from durable personalization ownership;
3. feedback causal scope is explicit and provenance-preserving;
4. cognition correction is distinguishable from policy correction;
5. passive behavior remains non-Gold by default;
6. current Phase 11 Agent/Delivery and Phase 1–10 cognition/attention regressions still pass;
7. no production policy has been tuned from old Human Gold;
8. Phase 12B can test whether a personal residual exists without assuming one.

## 10. Stop rule

If apparent personalization gains disappear after correcting Sensor, cognition, D/S/P, Runtime, shared-policy, or data-quality errors, stop. The scientifically correct outcome is an identity calibration layer.
