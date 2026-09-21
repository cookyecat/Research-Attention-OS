# Phase 16B — Multi-Event Source Decision Projection Result

Status: **FRAME-CONDITIONED COGNITION INPUT VALIDATED / PRODUCTION MULTI-PLAN SWITCH DEFERRED**  
Date: 2026-09-20

Reference: `262_PHASE16B_MULTI_EVENT_SOURCE_DECISION_PROJECTION_PREREGISTRATION.md`.

## 1. Why Phase16B exists

Phase16 made current Attention decision identity Event-centric, but one primary Source analysis still resolved one source-local decision Event.

Dogfood already disproves the assumption that one Source implies one Event:

```text
EventEvidenceFrames total      499
Sources with frames            353
Sources with >1 frame           67
maximum frames in one Source     8
```

Sample multi-frame Sources contain distinct event keys and event summaries.

## 2. Evidence completeness gap found and fixed

The production Sensor/Auditor bridge already computed per-Event admitted semantic units but discarded them from returned diagnostics.

Those units contain:

```text
unit_id
statement
epistemic_status
confidence
supports[]
```

including Source support pointers/excerpts.

Phase16B now preserves them in bridge diagnostics and EventEvidenceFrame payload.

Contracts:

```text
phase8c2-production-sensor-bridge-v0.3
event-evidence-frame-v0.3
```

Historical v0.2 frames are not silently upgraded. Summary-only historical frames are invalid inputs for frame-conditioned cognition.

## 3. Frame-conditioned cognition adapter

New eval/engineering input contract:

```text
frame-conditioned-cognition-input-v0.1
```

Flow:

```text
EventEvidenceFrame
→ audited_semantic_units
→ ExtractionResult
→ existing ResearchAlignedCognitiveProvider
```

The adapter never re-extracts Source prose and never manufactures semantic support.

It fails closed when:

- audited_semantic_units are absent;
- unit ids/statements are absent;
- evidence supports are absent;
- support pointers/excerpts are absent.

An equivalence regression compares the new adapter against the historical Phase6B audited-units adapter. Their `canonical_semantic_units()` outputs are identical for the same evidence bundle.

## 4. Controlled multi-Event cognition probe

One synthetic Source contains two distinct Event frames under the same frozen Kernel.

Frame A:

```text
Profiler evidence shows kernel launch overhead dominates runtime
for a small 64x64 bf16 matrix multiplication.
```

This directly challenges an important frozen belief that computation dominates runtime.

Frame B:

```text
Agent Memory Challenge 2026 Cycle 2 opens on September 20.
```

It is unrelated to that Kernel belief.

Using the existing ResearchAligned provider, frozen Relation/Binding/Grounding contract, and existing route:

```text
Frame A
  semantic units = 1
  matches        = 1
  effects        = 1 CHALLENGE
  disposition    = ENGAGE

Frame B
  semantic units = 1
  matches        = 0
  effects        = 0
  disposition    = DROP

Whole Source A+B
  semantic units = 2
  matches        = 1
  effects        = 1 CHALLENGE
  disposition    = ENGAGE
```

Artifact:

`eval/live/results/phase16b_multi_event_frame_cognition_v0_1/phase16b_multi_event_frame_cognition_v0.1_20260919T205714Z.json`

## 5. Interpretation

The whole-Source decision is not wrong about Frame A.

But using that one decision as the identity of the whole Source masks the fact that Frame B independently deserves DROP.

Therefore:

```text
whole-Source cognition
!= complete Event-level decision decomposition
```

and:

```text
Event-centric candidate id alone
does not fix multi-Event Source aggregation
```

Frame-conditioned cognition is an independently justified representation-conditioned input contract. It is no longer an adapter invented merely to demonstrate probabilistic marginalization.

## 6. Production feasibility review

The persistence model already allows multiple AttentionPlans per AnalysisRun:

`AttentionPlan.analysis_run_id` is non-unique and `attention_plans_for_run()` returns a list.

However the production/public contract remains structurally single-plan in many places:

- AnalysisRun `result_payload['attention_plan']`;
- hydrate/latest plan semantics;
- feedback attribution;
- WATCH recheck;
- rescheduling;
- Agent CLI response handling;
- numerous acceptance/compatibility contracts.

Therefore directly emitting 0..N Event plans from one Source analysis now would create an unsafe half-migration:

```text
storage = multi-plan
public semantics = single-plan
```

Phase16B deliberately stops before that change.

## 7. Next required mainline contract

Before production multi-Event Attention, RAOS needs a versioned cardinality contract:

```text
AnalysisRun(Source)
→ 0..N EventDecisionProjections
→ 0..N AttentionPlan(EVENT)
```

without introducing a new EventDecision table unless irreducible.

The public API must distinguish:

- Source-level analysis provenance;
- per-Event plan collection;
- representative/default plan only where a compatibility caller requires one;
- per-Event feedback/WATCH/Delivery attribution.

## 8. Verification

Focused bridge / frame / research-aligned cognition tests:

```text
23 passed
```

Full backend:

```text
916 passed
63 skipped
1 known historical Case-K failure
```

The only failure remains PREEMPT expected vs PRIORITY actual.

## 9. Research consequence

Phase15D remains deferred one more step.

The correct ordering is now:

```text
Phase16B input validated
→ multi-Event public/decision cardinality contract
→ production per-Event plans
→ then Phase15D EventState-delta / resurfacing
```

This prevents a third re-test of Event lifecycle behavior.

## 10. Live rollout note: frame schema version is not cognition-readiness proof

After code update but before the final restart, one live frame was persisted with:

```text
frame_contract_version = event-evidence-frame-v0.3
bridge_execution.bridge_version = phase8c2-production-sensor-bridge-v0.2
audited_semantic_units = absent
```

Root cause was a development-time mixed module load: the long-running process had instantiated bridge v0.2 before the file update, while `event_evidence_frames` was lazy-imported after the on-disk contract had changed to v0.3.

The historical artifact is preserved append-only and is **not** considered frame-cognition-ready. `event_frame_to_extraction()` correctly fails closed because the audited units are absent.

After canonical restart, runtime execution snapshot reports:

```text
bridge_version = phase8c2-production-sensor-bridge-v0.3
```

Therefore the legal readiness predicate is semantic, not version-string-only:

```text
frame-conditioned cognition ready
iff
audited_semantic_units + explicit supports are present
```

not merely `frame_contract_version == v0.3`.

This also reinforces a development invariant: hot-editing modules under a live canonical process can create hybrid module-version artifacts even when each individual module is versioned. Canonical evaluation/rollout must restart or otherwise quiesce the process before interpreting new contract artifacts.