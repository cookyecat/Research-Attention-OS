# Phase 12E — Multi-User Scale Boundary Preregistration

Date: 2026-09-16
Status: **PREREGISTERED / BOUNDARY REVIEW ACTIVE**
Parent: `209_PHASE12_PERSONALIZATION_SCALE_PLAN.md`
Depends on: 12A CLOSED; 12B CLOSED; 12C SKIPPED; 12D CLOSED.

## 1. Question

What must be isolated before RAOS can safely support more than one human, and what should remain shared, without prematurely tenantizing the entire schema?

Current fact:

```text
RAOS dogfood has one human user.
There is no authenticated user/tenant identity in backend or frontend.
```

Therefore Phase 12E must not pretend that product-scale multi-user isolation already exists.
## 2. Ownership model

The future product boundary is not `every table + user_id`. It is a state-ownership split:

```text
WORLD / SHAREABLE
  public Source content, public Events, public attention evidence,
  transport/cache artifacts when access provenance permits sharing

BRAIN / USER-PRIVATE
  Kernel, D profile, Runtime, AnalysisRun, AttentionPlan/Feedback,
  WATCH responsibility, WatchDelegation, Delivery, Kernel authorization

AUTHENTICATED OBSERVATION / USER-PRIVATE AUTHORITY
  connector credentials, private/following feeds, private Source scope
```

A public Source may be shared while the cognition produced against a user's Kernel is private.
## 3. Conservative ambiguous-state rule

Some current tables mix source-derived and run-derived state (`Claim`, `Observation`, `Inference`, etc.). v0.1 will not redesign them for hypothetical sharing.

Future isolation rule:

```text
if an object depends on user-private Kernel/Runtime/AnalysisRun state,
then treat it as private unless a separate source-only canonical artifact is explicitly defined.
```

This fails closed against cross-user cognitive leakage without forcing duplication of the external world.

## 4. Current deployment guard

RAOS will explicitly advertise the current truth:

```text
deployment_scope = SINGLE_USER_DOGFOOD
multi_user_isolation = false
```

This is a capability declaration, not a feature flag. Changing configuration must not magically claim multi-user safety.
## 5. Non-goals

12E will not add before a real second-user/product requirement:

- `user_id` to every table;
- user/account/authentication models;
- row-level security policy;
- per-user copies of public Source/Event state;
- non-identity `Theta_u` profiles when 12B found no evidence for them;
- distributed storage/sharding/queue machinery.

Those are product-scale mechanisms, not prerequisites for validating the semantic boundary.

## 6. Close criterion

12E closes for the current dogfood phase when:

1. ownership/isolation boundaries are frozen;
2. runtime/API explicitly declares single-user dogfood and lack of multi-user isolation;
3. tests prevent accidental claims of multi-user readiness;
4. no current Core/Attention semantics are changed.

Actual tenantization reopens only when a second-user or external deployment requirement exists.