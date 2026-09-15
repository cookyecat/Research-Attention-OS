# Phase 12D — Multi-Actor Attention Arbitration Preregistration

Date: 2026-09-16
Status: **PREREGISTERED / IMPLEMENTATION NEXT**
Parent: `209_PHASE12_PERSONALIZATION_SCALE_PLAN.md`
Depends on: 12A CLOSED; 12B CLOSED; 12C SKIPPED.

## 1. Question

Can many external Agents delegate persistent monitoring responsibility to one RAOS without multiplying cognitive authority, WATCH obligations, or human interruptions?

Canonical form:

```text
Many Agents
→ many delegations
→ one canonical RAOS responsibility
→ one canonical Attention scheduler
→ one human
```

An Agent may state what it wants observed. It may not assign DROP/AWARE/WATCH/ENGAGE, importance, urgency, D/S/P, or cognitive authority.
## 2. Minimal state

The v0.1 addition is one provenance relation:

```text
WatchDelegation
  watch_id
  declared_actor_id
  status
  request_context
  created_reason
  created_at / cancelled_at
```

`declared_actor_id` is provenance supplied by the caller. It is not authentication and carries no Attention authority.

A canonical `Watch` remains the future-attention responsibility. Multiple delegations may point to the same Watch.

No actor-specific scheduler weight, importance score, urgency score, or cognitive state is introduced.
## 3. Shared-responsibility invariant

For an agent-originated Watch `W`:

```math
Active(W) \iff CoreOwned(W) \lor \exists d \in Delegations(W): Active(d)
```

Two Agents delegating the same normalized target must not create two independent WATCH responsibilities merely because there are two callers.

Target sharing is deliberately conservative in v0.1: only exact normalized `(target_type, target_ref)` identity is merged. No LLM semantic deduplication is introduced.

Cancelling one delegation removes only that actor's responsibility. The canonical Watch remains active while another active delegation exists. Active Acquisition is disabled only when the canonical responsibility is no longer active and no core-owned Watch authority remains.
## 4. Attention / Delivery invariants

Multi-actor provenance is orthogonal to cognition and Attention:

```text
actor count != importance
actor count != urgency
actor count != D/S/P
actor count != Attention severity
```

The same Source/candidate continues through the existing canonical pipeline. Multiple Agent delegations must not create multiple human interruptions for the same canonical `AttentionPlan`; Phase 11D's one-`DeliveryEnvelope`-per-plan contract remains authoritative.

One-shot `analyze` requests are not persistent attention responsibilities and are not given actor-specific decision authority in v0.1.
## 5. Non-goals

12D v0.1 will not add:

- per-Agent importance or Attention models;
- actor-specific D/S/P;
- actor-specific scheduler thresholds;
- quota/fairness weights before real contention is observed;
- semantic merging of vaguely similar WATCH topics;
- authentication/authorization claims around `declared_actor_id`.

If future flywheel evidence shows sustained contention, quotas or permissions may be studied as a later control layer. They are not prerequired for correct shared responsibility.
## 6. Measurement / close criteria

Controlled multi-actor dogfood must prove:

1. two declared Agents can delegate the same normalized topic;
2. both delegations resolve to one canonical Watch;
3. only one Active Acquisition bundle exists for that Watch;
4. cancelling one actor leaves the Watch active while the other delegation remains;
5. cancelling the last actor cancels an agent-only Watch and disables its bundle;
6. a core-owned Watch is never cancelled merely because Agent delegations disappear;
7. no Agent request can directly set Attention disposition/urgency/importance;
8. existing cognition, WATCH, Delivery, and Agent-interface regressions remain green.

A successful v0.1 closes the shared-responsibility problem. Quota/fairness arbitration is deferred unless real flywheel contention becomes material.