# Phase 12B — Residual Necessity Test Preregistration

Date: 2026-09-16
Status: **MEASURED / CLOSED — see `219_PHASE12B_RESIDUAL_NECESSITY_RESULT.md`**
Parent: `209_PHASE12_PERSONALIZATION_SCALE_PLAN.md`
Depends on: Phase 12A CLOSED; Phase 10E forward-progress closure.

## Question

After canonical cognition, D/S/P, Runtime and shared Attention policy are treated as correct enough for the current operating regime, is there enough causally clean evidence to justify a non-identity user calibration `Theta_u`?

The null hypothesis remains:

```math
A_t^{user}=A_t^{core}
```

Phase 12B is a necessity test, not model fitting.
## Evidence allowed

Primary evidence is explicit `AttentionFeedback` after Phase 12A attribution. Only rows satisfying all of the following count as calibration-eligible residual evidence:

```text
causal_scope == USER_POLICY_RESIDUAL
feedback_class == ATTENTION_POLICY_CORRECTION
evidence_provenance == HUMAN_EXPLICIT
personalization_eligible == true
```

The Phase-10E proxy Human Gold is secondary evidence about current operating-regime adequacy. Because it is `ASSISTANT_PROXY`, it can support the identity default but cannot by itself authorize personalization.

Historical Oracle-Delta Gold remains excluded from current calibration evidence.
## Decision rule

12C is justified only if the current evidence contains a repeatable, causally clean user-policy residual that cannot be better explained by Core, estimator, Runtime, delivery, or actor-context error.

If there are zero eligible residual rows, or only isolated/unresolved corrections, the correct result is:

```text
Theta_u = identity
12C = NOT JUSTIFIED
```

This is not proof that no future personal residual can exist. It means the current evidence does not justify extra model capacity.

## Measurement

The instrument will be deterministic and read-only. It will report current feedback counts by causal scope / provenance / eligibility and the frozen Phase-10E proxy-Gold mismatch count. No LLM call, scheduler tuning, or feedback synthesis is permitted.

## Exit

A null result closes 12B with identity calibration retained and skips 12C. Research then proceeds to 12D Multi-Actor Attention Arbitration, which is orthogonal to whether `Theta_u` exists.