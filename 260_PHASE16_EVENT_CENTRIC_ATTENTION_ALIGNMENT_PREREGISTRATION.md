# Phase 16 — Event-Centric Attention Alignment V0.1 Preregistration

Status: **PREREGISTERED / PRODUCTION MAINLINE ALIGNMENT / NO CROSS-SOURCE E2 OPENING**  
Date: 2026-09-20

## 1. Problem

World Representation is Event-centric, while production AttentionPlan is still Source-centric.

This leaves the main architecture misaligned:

```text
Source -> Event Representation
       -> Source AttentionPlan
```

instead of:

```text
Source evidence -> Event hypothesis -> current Event Attention decision
```

## 2. V0.1 objective

Make the **decision object** Event-centric without authorizing cross-publication SAME_EVENT topology writes.

Reuse the existing `AttentionPlan` table:

```text
candidate_type = EVENT
candidate_id   = event_id
```

No new EventDecision entity is introduced.

## 3. Critical authority split

### Source-local Event membership

A Source may create its own local Event hypothesis during its own canonical analysis.

This does not assert that any second Source describes the same World Event.

It is therefore allowed to define the Source's Event-level Attention candidate.

### Cross-Source shared Event membership

Attaching Source B to an Event already representing Source A is a topology commitment.

It remains governed by EventMembershipAssertion / E2 policy.

Phase16 must not infer or authorize this merely from title similarity, content similarity, actor overlap, or probabilistic SAME_EVENT belief.

## 4. Legacy topology constraint

Legacy `attach_or_create_event()` currently reuses Event rows by title/content and can create multi-Source working topology without EventMembershipAssertion.

V0.1 must stop creating new cross-Source shared membership through this legacy path.

For new canonical analysis:

- if the Source already has one decision-authorized Event membership, reuse it;
- otherwise create a new source-local Event hypothesis;
- never reuse another Source's Event by title/content alone.

Historical legacy EventSource rows remain append-only history and are not destructively rewritten.

## 5. Membership authority representation

Reuse the existing `EventMembershipAssertion` entity.

Source-local membership uses a dedicated deterministic policy:

`source-local-event-membership-v0.1`.

It must state explicitly that:

- action = ASSERT;
- membership = REPORTS_EVENT;
- authority_status = AUTHORIZED_SOURCE_LOCAL;
- cross_source_commitment = false.

This authority means only:

`this Source's own analysis is represented by this local Event hypothesis`.

It does not certify objective world truth and does not authorize merging another Source.

## 6. Event Attention candidate resolution

Production Attention may use an Event candidate only when exactly one active decision-authorized Event membership resolves for the primary Source.

Ambiguous or conflicting authorized memberships fail closed.

Historical multi-member legacy topology without authority is not sufficient by itself.

## 7. AnalysisRun identity boundary

V0.1 does not force Event membership into the pre-extraction `decision_representation_digest`, because the source-local Event is created during extraction.

Instead:

- the persisted AttentionPlan records EVENT candidate identity;
- reuse of a completed AnalysisRun must verify that the currently resolved Event candidate still matches the stored AttentionPlan candidate;
- mismatch forces re-analysis rather than reusing a stale Event decision.

A later `decision-representation-v0.2` may absorb authorized Event membership once cross-Source topology authority is operational.

## 8. Reschedule

Runtime-only rescheduling must preserve the original Attention candidate type/id. It must not silently revert an EVENT plan to SOURCE.

## 9. Human-visible current Attention

Agent/Today/Delivery already carry generic candidate_type/candidate_id and may expose EVENT plans.

V0.1 must add Event summary metadata for EVENT candidates where useful, while preserving Source analysis provenance.

## 10. Continuous Attention

Shared Event routing must eventually consume decision-authorized membership, not raw legacy EventSource rows.

Phase16 should update the router only where this can be done without opening cross-Source E2 authority.

## 11. Success criteria

1. New canonical source analysis creates exactly one source-local Event membership assertion.
2. The resulting AttentionPlan has candidate_type=EVENT and candidate_id equal to that Event.
3. Re-analysis/reschedule preserves Event candidate identity.
4. Title-identical independent Sources do not automatically share an Event.
5. Legacy ambiguous multi-Source EventSource topology is not silently treated as decision authority.
6. Forensic/Replay still creates no Event/Attention topology.
7. Full backend regression has no new failure beyond known Case-K.

## 12. Non-goals

- no automatic cross-publication SAME_EVENT commit;
- no EventLineage decision authorization;
- no Event-level probability calibration;
- no destructive migration of historical Event/EventSource rows;
- no new EventDecision table.