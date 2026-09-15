# Phase 12A — Personalization Boundary & Feedback Attribution Result

Date: 2026-09-16
Status: **CLOSED / BOUNDARY IMPLEMENTED**
Production Attention policy change: **none**

## Result

Phase 12A extends the existing append-only `AttentionFeedback` record with one minimal JSON attribution object. It does not create a second feedback system or a personalization model.

Each feedback record now exposes:

```text
causal_scope
scope_source
feedback_class
evidence_provenance
personalization_eligible
rationale
```

The causal scopes remain: `PERCEPTION_ERROR`, `COGNITION_ERROR`, `AWARENESS_ERROR`, `RUNTIME_CAPTURE_ERROR`, `CORE_POLICY_ERROR`, `USER_POLICY_RESIDUAL`, `DELIVERY_PREFERENCE`, and `ACTOR_CONTEXT_ERROR`. `UNRESOLVED` is a fail-closed staging value, not a causal claim.

## Learning firewall

A correction is eligible for future `Theta_u` calibration only when all are true:

```text
causal_scope == USER_POLICY_RESIDUAL
feedback_class == ATTENTION_POLICY_CORRECTION
evidence_provenance == HUMAN_EXPLICIT
```

Disposition-only corrections without explicit scope become `UNRESOLVED`. Cognitive adjudication defaults conservatively to `COGNITION_ERROR`. Assistant proxy, passive behavior, Agent context, and system inference are never personalization-eligible. `USER_POLICY_RESIDUAL` is rejected if cognitive fields are also corrected.

## Persistence / migration

Migration `0012_feedback_attribution` adds only `AttentionFeedback.attribution`. The real dogfood upgrade path from `0011_delivery_plane` to `0012_feedback_attribution` was verified on a copy and then applied to `backend/raos.db`. Existing real feedback rows before migration: `0`.

A separate pre-existing migration-bootstrap debt was observed: replaying all migrations from an empty database conflicts because `0001_initial` calls current `Base.metadata.create_all()` before later migrations create newer tables. This is recorded as infrastructure debt and was not allowed to expand Phase 12A. The real incremental upgrade path is valid.

## Regression

Focused Feedback tests passed `30/30`. Broader Core + no-Delta + WATCH + Delivery + Agent regression passed `138/138`. Historical `AnalysisRun` and `AttentionPlan` remain immutable under feedback.

## Conclusion

Phase 12A exit criteria are satisfied. Feedback can now be causally attributed before any learning. Passive behavior remains non-Gold; Runtime remains Core-owned; cognition correction remains distinct from allocation correction. Phase 12B may test whether any stable personalization residual is actually necessary.
