# Phase 12A — Personalization Boundary & Feedback Semantics Preregistration

Status: **PREREGISTERED / ACTIVE**
Date: 2026-09-15
Parent: `209_PHASE12_PERSONALIZATION_SCALE_PLAN.md`

## 1. Question

Can RAOS define a personalization surface that improves human attention allocation without allowing user calibration, passive UI behavior, or external Agents to redefine canonical cognition, D/S/P semantics, or Attention authority?

## 2. Frozen hypotheses

H1. Personalization belongs primarily in explicit user state/parameters and Attention-policy calibration, not in semantic-variable redefinition.

H2. Passive interaction events are too confounded to serve as direct disposition Gold.

H3. Explicit corrections can be represented as provenance-preserving feedback without mutating the historical `AttentionPlan` that triggered them.

H4. Runtime state is transient context and must remain separable from durable user parameters.

H5. Agent/task context may affect runtime/delegation context but may not create a second Attention authority.
## 3. Non-goals

12A will not tune scheduler thresholds, train a personalized model, change D/S/P meanings, change the no-Delta gate, or infer preferences from clicks.

The historical 30-case questionnaire is development evidence only and cannot be the confirmatory 12A/12B Gold set.

## 4. Required state separation

The implementation/design review must keep these stores logically distinct:

```text
K_t      cognitive state / committed world model
J_u      standing jurisdiction / D profile
Θ_u      durable Attention-economics calibration
R_t      transient runtime state
Λ_u      delivery/channel preferences
C_a      actor/agent/task context
F        explicit feedback / correction evidence
```

No one field may silently stand in for another.

## 5. Feedback classes to support

Minimum explicit feedback vocabulary:

```text
DISPOSITION_CORRECTION   expected DROP/AWARE/WATCH/ENGAGE
TIMING_CORRECTION        right item, wrong time / interruption timing
WATCH_OUTCOME            useful watch / missed trigger / unnecessary watch
DELIVERY_CORRECTION      should interrupt / should not interrupt
RATIONALE                optional user explanation
```
## 6. Historical immutability

Feedback must attach to an existing decision/delivery/watch record without rewriting the original evidence, decision cause, disposition, or delivery history.

A later calibrated policy may make a different decision on replay/new evidence, but the old decision remains auditable truth.

## 7. Evidence-strength ordering

For later 12C learning, evidence should be ranked rather than flattened:

```text
explicit correction
> explicit outcome judgment
> causally attributable task outcome
> passive acknowledgement/dismissal/open/dwell
```

Passive signals remain weak/confounded unless separately validated.

## 8. Measurement plan

12A will audit current schemas and interaction logs against the state taxonomy above, then implement only the minimal missing feedback boundary needed to preserve explicit corrections.

Primary checks:

- no semantic-field reuse for personalization;
- no mutation of historical AttentionPlan/DeliveryEnvelope;
- feedback provenance is explicit;
- actor identity/context is recorded without Attention authority;
- passive UI events remain behavior logs, not automatic Gold;
- regression proves current Phase 11 authority boundaries remain intact.
## 9. Exit criteria

12A closes only when:

1. the personalization boundary is frozen in docs;
2. an explicit feedback record can be attached to Attention / WATCH / Delivery outcomes without rewriting history;
3. feedback provenance distinguishes human explicit correction from passive behavior and Agent-supplied context;
4. current Phase 11 Agent/Delivery authority tests still pass;
5. no production scheduler threshold has been tuned using the historical 30-case set;
6. a fresh Phase 12B calibration instrument can be designed against the current architecture without semantic ambiguity.

## 10. Stop rule

If explicit feedback cannot be represented cleanly without mixing user calibration into D/S/P or cognition semantics, stop and redesign the state boundary before collecting new Gold.
