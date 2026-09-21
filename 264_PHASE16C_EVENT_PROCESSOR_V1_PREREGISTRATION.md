# Phase 16C — Event Processor V1 Preregistration

Status: **PREREGISTERED / DIRECT CANONICAL INTEGRATION**  
Date: 2026-09-20

## 1. V1 ontology

`Source` is one raw information item observed by Sensor.

`Event` is RAOS's structured description of one coherent real-world episode/story that deserves one shared Attention lifecycle.

V1 prior:

```text
1 Source -> 1 primary EventCandidate
N Sources -> 0/1 shared Event
```

Multi-news digest Sources are explicitly deferred to V2 and do not alter the V1 downstream architecture.

## 2. Event granularity

Event is deliberately coarse. Claims, benchmark numbers, quotes, observations, and intermediate state changes do not define Event count.

Operational editorial test:

> Would a competent editor normally keep this information in the same evolving news story/case/research story, or open a separate story/case?

Examples treated as one Event in V1:

- launch preparation -> launch -> successful booster recovery for one SpaceX launch episode;
- a paper publication plus its method, benchmark results, conclusions, and later discussion;
- multiple independent reports of the same product/model release.

## 3. Event V1 structure

Identity-bearing core:

- actors;
- main action/change;
- object/target;
- time context;
- optional location.

Materialized current representation additionally stores:

- title;
- summary/description;
- event_type;
- current_state/progress;
- attributes;
- source evidence.

Claims/Observations remain supporting evidence and never define Event multiplicity.

## 4. Event history

World Event identity is stable once created. RAOS knowledge may be enriched/revised.

Implementation:

- stable `Event.id`;
- current materialized Event row;
- append-only `EventRevision` for CREATE/UPDATE knowledge history.

## 5. Sensor and Auditor

Sensor and Semantic Auditor contracts remain unchanged.

Event Processor consumes the audited extraction result; it must not re-audit Source truth.

## 6. Event Processor

Canonical flow:

```text
Audited Source
-> extract one coarse EventCandidate
-> retrieve plausible existing Events
-> resolve SAME_EVENT / DIFFERENT_EVENT / UNCERTAIN
-> SAME: attach Source + append EventRevision + update current projection
-> DIFFERENT: create Event + attach Source
-> UNCERTAIN: conservatively create a separate Event hypothesis
-> Event-level Attention decision
```

## 7. Resolution semantics

`SAME_EVENT` is story/episode-level continuity, not atomic transition identity.

Resolver guidance:

- same actor/topic/product alone is insufficient;
- supporting claims/details do not create new Events;
- natural progress inside one story may remain SAME_EVENT;
- independent real-world story deserving separate reporting is DIFFERENT_EVENT;
- insufficient evidence -> UNCERTAIN.

UNCERTAIN must never force a merge.

## 8. Candidate retrieval

V1 uses high-recall deterministic retrieval over current decision-committed Events using title/summary/actors/action/object/time proximity.

Retrieval score is never SAME_EVENT probability.

## 9. Resolver strategy

Canonical strategy:

`llm-coarse-event-resolver-v1`.

A rollback/replay strategy may exist, but only one strategy writes canonical state at a time.

## 10. Attention integration

New canonical Attention continues to persist:

`AttentionPlan(candidate_type=EVENT, candidate_id=event.id)`.

Event Processor becomes the only normal canonical path that selects/creates the Event candidate for new analysis.

Legacy source-local Event creation remains rollback/migration compatibility only.

## 11. Analysis identity

Event Processor execution contract/model/strategy is included in AnalysisRun execution snapshot so a resolver change invalidates stale decision reuse.

Reprocessing a Source with one existing decision-committed Event reuses that Event rather than creating a new occurrence.

## 12. Success criteria

1. Event schema supports V1 identity/progress fields.
2. Sensor/Auditor tests remain unchanged in semantics.
3. Two Sources describing the same coarse story resolve to one Event and one current Event candidate.
4. Distinct stories create distinct Events.
5. UNCERTAIN never merges.
6. SAME update produces EventRevision and does not create a duplicate Event.
7. AttentionPlan points at the resolved Event.
8. Forensic/Replay cannot mutate Event topology.
9. Full regression introduces no failure beyond known Case-K.
10. Bounded canonical dogfood demonstrates real cross-Source aggregation.

## 13. Non-goals

- multi-event digest Source handling;
- claim-centric Attention path;
- probabilistic event marginalization;
- EventLineage redesign;
- changing Sensor/Auditor ontology;
- atomic event mention benchmark compatibility.

## 14. Fixed controlled real-model resolver cases

Before any real-model run, V1 fixes exactly three cases:

```text
Case A — SAME_EVENT
Source A: Acme launches the Nimbus API public beta at AtlasConf.
Source B: Reuters independently reports the same Nimbus API public-beta launch at AtlasConf.

Case B — DIFFERENT_EVENT
Existing Event: Nimbus API public-beta launch.
New Source: Acme opens a separate Nimbus university grant program.

Case C — UNCERTAIN
Existing Event: Nimbus API public-beta launch.
New Source: 'Nimbus update is underway; more details soon.'
with no concrete occurrence identity.
```

Expected labels:

- A: SAME_EVENT;
- B: DIFFERENT_EVENT;
- C: UNCERTAIN is preferred; DIFFERENT_EVENT is acceptable only if the model grounds a genuinely separate occurrence. SAME_EVENT is not acceptable from generic product/topic overlap alone.

No case wording, retrieval threshold, or prompt will be tuned after observing these outputs in the first bounded run.

The run uses an in-memory database and the configured canonical LLM transport. It is a controlled mechanism validation, not natural dogfood.