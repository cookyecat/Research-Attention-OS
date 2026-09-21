# Phase 16 — Event-Centric Attention Alignment Result

Status: **DECISION IDENTITY ALIGNMENT COMPLETE / CROSS-SOURCE AGGREGATION + MULTI-EVENT DECOMPOSITION INCOMPLETE**  
Date: 2026-09-20

Reference: `260_PHASE16_EVENT_CENTRIC_ATTENTION_ALIGNMENT_PREREGISTRATION.md`.

## 1. Result

Production current Attention is now Event-centric:

```text
Source evidence
→ source-local or decision-authorized Event hypothesis
→ Event-scoped decision
→ AttentionPlan(candidate_type=EVENT, candidate_id=event_id)
→ current Attention projection
→ representative Source reading path
```

No `EventDecision` table was added. The existing generic `AttentionPlan` entity is reused.

## 2. Source analysis vs Event decision identity

The system now separates:

```text
AnalysisRun.source_id
= evidence / computation provenance

AttentionPlan(EVENT)
= current decision identity
```

A Source remains the object that was observed and analyzed. The Event is the object whose current state is allocated human Attention.

`plan_public()` and initial pipeline serialization expose `candidate_type` and `candidate_id`.

Runtime-only rescheduling preserves the Event candidate and cannot silently regress the plan to Source identity.

## 3. Source-local Event membership authority

New contract:

```text
source-local-event-membership-v0.1
```

Source-local assertions use:

```text
action = ASSERT
membership = REPORTS_EVENT
authority_status = AUTHORIZED_SOURCE_LOCAL
cross_source_commitment = false
```

Meaning:

> this Source's own canonical analysis is represented by this local Event hypothesis.

It does **not** mean:

> another Source has been proven to describe the same World Event.

This distinction allows Event-centric Attention without opening cross-publication E2 topology commitment.

## 4. Cross-Source E2 remains closed

Phase16 does not authorize deterministic SAME_EVENT collapse across independent publications.

The following are insufficient to create shared Event decision identity:

```text
same title
same actor/product
content similarity
raw EventSource
probabilistic SAME_EVENT belief
```

Cross-Source shared membership remains a topology commitment and requires a future authorized `EventMembershipAssertion` policy.

Therefore Phase16 accepts conservative over-segmentation rather than false merge.

## 5. Legacy event materialization correction

Production pipeline no longer uses legacy title/content-based `attach_or_create_event()` to choose the Event Attention candidate.

For new canonical analysis:

```text
one Source
→ one decision-safe source-local Event hypothesis
```

unless exactly one decision-authorized Event membership already resolves the Source.

Identical titles in independent Sources no longer cause Event sharing.

## 6. Current Attention projection

Historical Source-level AttentionPlans remain immutable audit history.

Current projection rule:

```text
if a decision-authorized Event plan represents a Source:
    Event plan = current
    historical Source plan = audit history only
```

The migration does not delete historical plans.

## 7. Representative reading path

The Attention UI and Agent API now separate decision identity from reading evidence:

```text
EVENT candidate
+ Event title / summary
+ representative_source_id
```

The Event card is the current Attention object. Clicking it opens the representative Source reader.

Agent contract upgraded to:

```text
agent-interface-v0.4
attention_candidate_contract = event-centric-v0.1
representative_reading_path = analysis-run-primary-source
```

## 8. Delivery / WATCH side-effect boundary

Identity migration is intentionally non-cognitive and non-delivery:

```text
SOURCE AttentionPlan
→ clone decision identity as EVENT AttentionPlan
```

with:

```text
cognition_recomputed = false
delivery_reenqueued = false
```

No WATCH is created or changed.

Observed final V0.2 migration delta:

```text
Event                 661 → 686   (+25)
EventMembershipAssert 650 → 675   (+25)
AttentionPlan        1344 → 1369  (+25)
DeliveryEnvelope      610 → 610   (unchanged)
WATCH                  45 → 45    (unchanged)
```

All 675 membership assertions are:

```text
authority_status = AUTHORIZED_SOURCE_LOCAL
cross_source_commitment = false
```

A second V0.2 migration run created zero Event plans.

## 9. Dogfood current projection

Under the canonical research-dogfood runtime profile after V0.2 migration:

```text
current Attention decisions = 625

EVENT  = 625
SOURCE = 0
```

Thus the current product **decision-identity surface** is fully Event-centric for the migrated dogfood corpus. This does not imply that cross-Source Event aggregation or one-Source-to-many-Event decomposition is complete.

## 10. Legacy multi-member topology

The bounded migration found:

```text
675 latest Source decision candidates
650 safe single-member Event structures
25 legacy ambiguous / multi-member structures
```

V0.1 migrated the safe 650 and deliberately skipped 25.

V0.2 did **not** trust those old shared Events. It preserved the legacy topology for audit and created a separate source-local Event hypothesis for each affected Source.

This converts ambiguity into conservative epistemic over-segmentation rather than unauthorized merge.

## 11. Continuous Attention authority refinement

The router previously treated raw shared EventSource membership as enough to match an existing WATCH.

That is now prohibited.

Current rule:

```text
decision-authorized Event membership
OR selected decision-authorized SourceEdge relation
→ may route to existing lifecycle
```

Raw EventSource alone does not.

The Phase15 controlled SAME_EVENT test therefore uses an explicit authorized cross-source membership fixture.

EventLineage remains outside current routing authority.

## 12. AnalysisRun identity boundary

Phase16 deliberately does not put source-local Event identity into pre-extraction `decision-representation-v0.1`.

Reason:

```text
AnalysisRun identity freezes before extraction
source-local Event may materialize during extraction
```

Making that Event part of the same pre-extraction digest would create a guaranteed first-run identity drift.

Instead:

```text
AnalysisRun
= evidence computation identity

AttentionPlan(EVENT)
= decision candidate identity
```

Completed-run reuse has an Event-candidate guard. A stale Source-centric plan is not silently reused as the current decision.

A future `decision-representation-v0.2` may absorb authorized Event membership when cross-Source topology authority becomes operational.

## 13. Verification

Focused Phase16 / Phase15 / continuous-attention suites passed.

Final full backend regression after the authority tightening:

```text
912 passed
63 skipped
1 known historical failure
```

The only failure remains:

```text
backend/tests/acceptance/test_cases.py::test_case_k_preempt
expected PREEMPT
actual PRIORITY
```

Frontend TypeScript validation passed. Python compile and `git diff --check` passed.

## 14. What is complete vs not complete

Complete:

```text
Event-level current decision identity
Event-level current AttentionPlan
Source-local membership authority
historical Source-plan suppression in current projection
representative Source reading path
migration to Event-centric dogfood state
raw EventSource removed from Attention routing authority
```

Not complete:

```text
automatic 5 Sources -> 1 shared World Event
cross-publication deterministic SAME_EVENT commitment
EventLineage-driven lifecycle routing
probabilistic continuation-vs-new-event marginalization
decision-bearing EventState-delta resurfacing experiment (Phase15D)
```

The compression target remains:

```text
many Sources
→ one World Event
→ one current Event Decision
→ one Attention object
→ one representative reading path
```

but the first collapse is still gated by cross-Source topology authority.

## 15. Rollout-order race found in live smoke

After the first completed migration, live serving briefly showed two new Source-centric current plans.

Root cause was not the new pipeline. The first migration ran while old backend/acquisition writers were still alive; two tail analyses were persisted under the old Source-centric contract before restart.

Observed live smoke before correction:

```text
/kernel/attention
625 items
623 EVENT
2 SOURCE
```

The rollout sequence was corrected to:

```text
stop backend / acquisition / delivery / frontend
→ run event-attention identity migration
→ start new code
→ doctor
→ live read-only smoke
```

The tail migration created exactly two Event plans. Final live APIs then returned:

```text
/kernel/attention  625 EVENT / 0 SOURCE
/agent/v1/attention 625 EVENT / 0 SOURCE
representative_source_id present for every Event item
agent-interface-v0.4
```

Final persistence census after this rollout:

```text
Event                    688
EventMembershipAssertion 677
AttentionPlan           1373
DeliveryEnvelope         612
WATCH                     45
```

The Delivery increase from 610 to 612 came from the two old-writer tail analyses themselves, not from identity migration. The migration still does not enqueue Delivery.

This yields a general rollout invariant:

> canonical identity migrations must quiesce old writers before migration.

## 16. Design audit: one Source may contain multiple Events

Phase16 closes the Source-vs-Event **decision identity** gap, but a second structural gap remains.

`EventEvidenceFrame` explicitly permits:

```text
1 Source
→ 0..N event propositions
```

A dogfood census found:

```text
EventEvidenceFrames total      499
Sources with frames            353
Sources with >1 frame           67
maximum frames in one Source     8
```

Sample multi-frame Sources contain genuinely distinct event keys and summaries, e.g. one Source reporting both a new evaluation-cycle opening and a historical leaderboard release.

Current source-local Event Attention still resolves:

```text
one primary Source analysis
→ one source-local decision Event
```

and all 677 source-local membership assertions have exactly one active local Event per Source.

Therefore:

```text
Event-centric Attention identity = implemented
full Source → 0..N decision-Event decomposition = not implemented
```

This is not a corner case and must be preserved as an explicit next mainline gap. Phase15D should not be interpreted as the final Event-lifecycle experiment until the decision projection can select the relevant Event/frame rather than treating an entire multi-event Source as one Event candidate.