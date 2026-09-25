# Phase17.3-KS Semantic Key Resolution Research Plan

Date: 2026-09-22
Status: ACTIVE RESEARCH PLAN

## 1. Research Boundary

Phase17.3 established that mature systems already solve:

- Event Sourcing
- immutable History
- materialized Current State
- keyed state update
- changelog replay
- compaction

RAOS does not reimplement these components.

The remaining RAOS-specific problem is:

```
ResolveKey(EventIdentity, CurrentSlots, NewEvidence)
```

Given new semantic evidence, determine:

1. reuse an existing semantic state dimension;
2. create a genuinely new state dimension.

## 2. Adopted External Foundations

Directly reuse:

```
Event Sourcing
CQRS / Materialized View
Flink Keyed State
Kafka Streams KTable
Incremental View Maintenance
Bayesian filtering
CRDT conflict handling
```

RAOS-specific layer:

```
Evidence
  -> semantic proposition
  -> semantic key resolution
  -> existing state infrastructure
```

## 3. Phase17.3-KS-A Literature Mapping

Investigate existing solutions:

- Entity Resolution
- Schema Matching
- Ontology Learning
- Online Clustering
- Bayesian Nonparametric Models
- Category Formation
- Concept Learning

Goal:

Find reusable algorithms for semantic key assignment.

## 4. Phase17.3-KS-B Resolver Design

Target contract:

```
ResolveKey(
    EventIdentity,
    CurrentSlots,
    NewEvidence
)

return:
    REUSE(existing_key)
    or
    CREATE(new_key)
```

Constraints:

- primitive_family immutable;
- no LLM authority after key resolution;
- deterministic Apply remains unchanged.

## 5. Phase17.3-KS-C Benchmark

Required cases:

1. Same meaning, different wording.
2. Similar wording, different semantic dimension.
3. New dimension emergence.
4. Correction of existing state.
5. Multi-source conflict.
6. Primitive-family boundary cases.

Metrics:

- KeyReuseAccuracy
- FalseCreateRate
- FalseMergeRate
- DimensionStability
- ReplayDeterminism

## 6. Phase17.3-KS-D Integration

Successful resolver output feeds existing pipeline:

```
Semantic Proposition
        |
        v
ResolveKey
        |
        v
SlotDelta
        |
        v
Deterministic Apply
        |
        v
EventState
```

No replacement of Event Sourcing / Keyed State architecture.

## Research Principle

Use mature systems wherever possible.

Only research the missing semantic boundary:

> Which existing state dimension should this new evidence update?
