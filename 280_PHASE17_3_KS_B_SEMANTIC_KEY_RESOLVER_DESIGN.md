# Phase17.3-KS-B Semantic Key Resolver Design v0.1

日期：2026-09-22

## 1. Purpose

Phase17.3-KS studies the missing layer between semantic evidence and existing state infrastructure.

The mature components remain unchanged:

- Event Sourcing for immutable history
- CQRS / Materialized View for current state
- Keyed state systems for incremental updates
- Deterministic Apply for state mutation

RAOS-specific research boundary:

```
New Semantic Evidence
        |
        v
Semantic Key Resolution
        |
        v
Existing State Key / New State Key
```

The core function is:

```
ResolveKey(EventIdentity, CurrentSlots, NewEvidence)
```

## 2. Scope Boundary

Resolver does NOT perform:

- raw evidence extraction
- primitive family classification
- state mutation
- replay
- storage

These responsibilities belong to:

```
Evidence
  |
  v
Semantic FlatMap
  |
  v
Primitive Proposition
  |
  v
ResolveKey
  |
  v
SlotDelta
  |
  v
Deterministic Apply
```

The resolver only decides semantic state address.


## 3. Resolver Input and Output Contract

Input:

### Event Identity

Defines the entity and event scope.

### Current Semantic Slots

Current materialized schema:

```
key
family
summary
history
aliases
```

### New Proposition

Output from Phase17 FlatMap:

```
primitive_family
subject
predicate
object
referent_scope
```

Output:

```
REUSE(existing_key)

or

CREATE(new_key)
```

with confidence and audit information.


## 4. Resolver Pipeline

The v0.1 design contains five stages.

## Stage 1 Candidate Retrieval

Reduce search space using:

- Event identity
- Entity scope
- Primitive family
- Existing schema constraints

## Stage 2 Semantic Compatibility

Compare proposition with candidate slots.

Possible methods:

- embedding similarity
- LLM judgement
- cross encoder

Similarity is evidence, not final decision.


## Stage 3 Temporal Continuity

Check whether the new evidence continues the evolution of an existing slot.

Example:

```
performance.latency

300ms
  |
200ms
```

is refinement, not a new dimension.

## Stage 4 Reuse/Create Decision

Decision should combine:

- semantic compatibility
- type compatibility
- temporal continuity
- new dimension prior

Bayesian ideas are used as decision support, not as the complete resolver.


## 5. Frozen Invariants

### Primitive Family Immutability

```
PROCESS cannot become QUALITY
QUALITY cannot become RELATION
```

### Key Stability

Equivalent evidence should converge to the same semantic key.

### Controlled Key Expansion

CREATE is allowed only when no existing semantic dimension explains the evidence.

### Deterministic Resolution

Same:

```
History + CurrentSlots + NewEvidence
```

must produce the same key assignment.

## 6. Next Step

Phase17.3-KS-C will implement controlled benchmarks:

- paraphrase reuse
- type boundary separation
- new dimension creation
- correction handling
- multi-source conflict
