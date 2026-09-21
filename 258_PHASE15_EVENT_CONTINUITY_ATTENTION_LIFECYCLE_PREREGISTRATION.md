# Phase 15 — Event Continuity to Attention Lifecycle V0.1 Preregistration

Status: **PREREGISTERED / EVAL-ONLY / NO PRODUCTION EVENT ATTENTION YET**  
Date: 2026-09-20

## 1. Core question

Where should Event identity and Event-to-Event continuity enter RAOS downstream decision flow?

V0.1 tests the hypothesis that their primary role is **world-update routing and Attention lifecycle identity**, not direct scalar Attention scoring.

## 2. No new Episode entity

Event Continuity is a routing relation over existing objects, not a new persisted domain entity.

Existing substrate is sufficient:

- Event;
- EventSource / future EventMembershipAssertion;
- EventRevision;
- EventLineage;
- WATCH / AnalysisRun;
- CandidateType.EVENT (already defined, not yet production-used).

## 3. Ontology

### Same occurrence / state transition

`SAME_EVENT` means two frames describe the same underlying occurrence/state transition.

Lifecycle routing:

`attach evidence to the same Event hypothesis`.

This is orthogonal to provenance. Independent Sources may report the same Event.

### Distinct follow-up state transition

A later cancellation, reversal, response, follow-up, or extension is normally a **different Event**, not a revision of the original world occurrence.

If concretely related:

`distinct Event + EventLineage / continuity routing`.

`EventRevision` is reserved for revising RAOS's description/hypothesis about one Event, not for hiding a second real-world transition inside the first Event.

### Distinct unrelated/new Event

`new Event lifecycle`.

Same actor/product/topic alone is insufficient to establish continuity.

### Uncertain

Preserve competing hypotheses/branches. Do not collapse materialized topology merely to obtain one Attention path.

## 4. Decision separation

Event Continuity answers:

`Which Event / existing lifecycle context should this evidence update?`

It does not itself answer:

`DROP / AWARE / WATCH / ENGAGE`.

Downstream Attention depends on the decision-bearing change after the evidence is routed.

Conceptually:

```text
new evidence
→ Event Continuity routing
→ updated Event / successor Event context
→ decision-bearing EventState delta
→ Attention lifecycle action
```

## 5. Eval-only lifecycle actions

V0.1 may use the following **derived labels only inside eval**:

- `UPDATE_EXISTING_EVENT`: same occurrence; attach evidence;
- `RECOMPUTE_EXISTING_LIFECYCLE`: same Event or related successor introduces decision-bearing new evidence;
- `SPAWN_NEW_EVENT_DECISION_PATH`: distinct/new Event with no existing lifecycle relation;
- `PRESERVE_COMPETING_BRANCHES`: uncertain continuity.

These are not new DB entities or production enums.

## 6. Phase15B experiment

Use an in-memory DB and existing `process_source_arrival()` / WATCH machinery to compare routing under controlled topology.

Measure:

- whether new Source matches existing WATCH;
- recheck vs ordinary-analysis path;
- cumulative evidence identity;
- existing WATCH count/status;
- whether a second lifecycle path is required;
- current Source-level AttentionPlan count as a diagnostic only.

## 7. Phase15C fixed cases

Exactly three cases:

1. same Event + independent corroboration;
2. distinct but concretely related successor/contradiction Event;
   - 2a uses EventLineage only;
   - 2b keeps the same semantic case and adds the current SourceEdge.CONTRADICTS routing proxy, solely to localize which substrate the existing router actually consumes;
3. distinct Event with same actor/product but no continuity relation.

No benchmark expansion after seeing results.

## 8. Interpretation guardrails

- SAME_EVENT != REPOSTS != DERIVED_FROM != non-independence;
- related follow-up != SAME_EVENT;
- EventRevision != real-world successor transition;
- existing Source-level AttentionPlan multiplicity must not be presented as an Event-level product design;
- if current WATCH routing already expresses useful continuity semantics, reuse it rather than creating EventDecision persistence;
- production Event-level Attention is not authorized by this experiment.