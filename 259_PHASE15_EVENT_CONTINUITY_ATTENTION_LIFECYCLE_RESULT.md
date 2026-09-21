# Phase 15 — Event Continuity to Attention Lifecycle Result V0.1

Status: **ROUTING HYPOTHESIS VALIDATED / EVENTLINEAGE DECISION BRIDGE MISSING / TOPOLOGY BYPASS FIXED**  
Date: 2026-09-20

Reference: `258_PHASE15_EVENT_CONTINUITY_ATTENTION_LIFECYCLE_PREREGISTRATION.md`.

## 1. Core architectural result

The experiment supports the hypothesis that Event identity / continuity belongs primarily in a **world-update and Attention-lifecycle routing layer**, not as a direct scalar input to the cognition provider.

Canonical conceptual flow:

```text
new evidence
→ Event Continuity routing
→ same Event / successor Event / new Event context
→ decision-bearing state change
→ cognition / Attention recomputation if warranted
```

Event Continuity is not itself a DROP/AWARE/WATCH/ENGAGE decision.

## 2. Ontology correction retained

`SAME_EVENT` is strict identity of one underlying occurrence/state transition.

A later cancellation, reversal, extension, response, or follow-up is normally a **different Event** with an EventLineage relation, not a revision of the original world occurrence.

`EventRevision` revises RAOS's description/hypothesis about one Event.

`EventLineage` relates distinct Event hypotheses/transitions over time.

No Episode entity was added.

## 3. Case 1 — same Event + independent corroboration

Controlled representation:

- Source A is attached to Event E;
- independent Source B is also attached to Event E;
- no provenance dependency is asserted.

Observed current router:

`EXISTING_LIFECYCLE_RECHECK`.

Properties:

- existing WATCH is reused;
- WATCH count remains 1 -> 1;
- B is classified as INDEPENDENT;
- ordinary analysis path is not used;
- no unexpected Event membership is created during recheck.

This validates the basic lifecycle interpretation:

`same Event evidence -> update/recheck existing lifecycle context`.

## 4. Case 2 — distinct successor/contradiction Event

Source B reports a later real-world transition and is attached to a distinct successor Event.

An EventLineage row links predecessor Event A to successor Event B.

### 2a EventLineage only

Observed current router:

`ORDINARY_NEW_ANALYSIS_PATH`.

The current `continuous_attention` router does not consume EventLineage.

### 2b Same semantic case + SourceEdge.CONTRADICTS proxy

Observed current router:

`EXISTING_LIFECYCLE_RECHECK`.

Properties:

- existing WATCH is reused;
- WATCH count remains 1 -> 1;
- the successor remains a distinct Event after the topology-bypass repair.

This localizes the current implementation boundary:

```text
current continuous-attention routing
consumes shared EventSource membership + selected SourceEdge relations
but not EventLineage
```

Long-term, EventLineage is the semantically cleaner substrate for distinct successor transitions, but it must not be wired into decisions until its authority/decision-representation contract is explicit.

## 5. Case 3 — distinct Event, same actor/product, no continuity relation

Source B mentions the same actor/product but represents a distinct program/event and has no shared Event, EventLineage continuity, or decision-authorized SourceEdge continuity fact.

Observed current router:

`ORDINARY_NEW_ANALYSIS_PATH`.

This is the desired conservative behavior. Actor/product overlap alone does not manufacture lifecycle continuity.

## 6. Current Attention object boundary

`CandidateType.EVENT` already exists, but production `run_pipeline()` currently creates Source-level AttentionPlans.

In every arm, one additional analysis produced one additional Source-level AttentionPlan row.

This must not be interpreted as the desired Event-level product model.

The stable lifecycle identity in the current continuous-attention implementation is the existing WATCH obligation, not an Event-level AttentionPlan.

Therefore V0.1 does not introduce EventDecision or Event-level Attention persistence.

## 7. Hidden topology bypass found and fixed

Before the fix, rechecking a successor Source through a SourceEdge.CONTRADICTS path caused the successor Source to gain an additional membership in the predecessor Event.

Root cause:

`extract_source()` treated every `extra_source` as if it implicitly belonged to the primary merged Event and called `attach_or_create_event(extra, primary_merged_event_title, ...)`.

This violated the architecture:

`extra evidence input != Event membership authority`.

Fix:

`extract_source()` now materializes legacy Event topology only for the primary Source.

Extra Sources remain AnalysisRun evidence inputs. Their Event membership must come from:

- their own primary analysis; or
- an explicit future Representation / topology transition.

A regression verifies that a successor Source entering an existing WATCH recheck remains only in its successor Event and is never silently attached to the predecessor Event.

## 8. What this experiment does not prove

The generic controlled texts produced DROP/KEEP_ACTIVE on recheck under the rule cognition provider.

That does not show that a material successor Event can never resurface Attention.

The experiment validated **lifecycle routing**, not the value function for a decision-bearing EventState delta.

A separate probe would be required to test:

`existing lifecycle + materially decision-bearing successor state -> PROMOTED/resurfaced Attention`.

Do not force such an outcome by patching the router merely to satisfy the expected narrative.

## 9. Next architectural gap

The clean next gap is not a SAME_EVENT probability prompt input.

It is:

`authorized EventContinuity / EventLineage -> lifecycle router`.

Before production use, RAOS needs a versioned rule for which EventLineage / membership facts are decision-authorized. Current shadow/candidate lineage must not directly drive WATCH or Attention.

## 10. Artifact

`eval/live/results/phase15_event_continuity_lifecycle_v0_1/phase15_event_continuity_lifecycle_v0.1_20260919T192329Z.json`

## 11. Regression and rollout validation

Focused continuous-attention + Phase15 regression: `6 passed`.

Full backend regression after removing implicit extra-source Event materialization: `903 passed / 63 skipped / 1 known Case-K failure`.

The only failure remains the historical PREEMPT expected vs PRIORITY actual residual. No new regression is attributable to Phase15.


## 12. Post-Phase16 authority refinement

Phase15 observed the router against the then-current materialized `EventSource` working graph.

Phase16 tightened the production decision boundary:

```text
raw EventSource
!=
Attention lifecycle routing authority
```

Current continuous-attention Event routing now consumes decision-authorized Event membership (`EventMembershipAssertion`) rather than trusting raw legacy EventSource rows.

Therefore the Phase15 SAME_EVENT controlled fixture now uses an explicit authorized cross-source membership assertion. The semantic conclusion is unchanged:

```text
authorized same Event identity
→ update / recheck existing lifecycle
```

but the authority boundary is stricter:

```text
working topology alone
→ no lifecycle authority
```

EventLineage remains non-decision-bearing until a separate authority/decision contract is introduced.