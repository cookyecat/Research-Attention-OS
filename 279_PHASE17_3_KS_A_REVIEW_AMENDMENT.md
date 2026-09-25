# Phase17.3-KS-A Review Amendment — Semantic Key Resolution Theory Correction

Date: 2026-09-22

Status: REVIEW AMENDMENT

Parent:

```text
279_PHASE17_3_KS_A_SEMANTIC_KEY_RESOLUTION_LITERATURE_MAPPING.md
```

Purpose:

This amendment records the theoretical refinement after reviewing the first literature mapping.

The original mapping direction is retained, but the relative importance of each external theory is corrected.

---

# 1. Review conclusion

The original Phase17.3-KS-A conclusion remains valid:

```text
No existing algorithm directly solves RAOS ResolveKey.
```

However, the problem classification is refined.

RAOS ResolveKey is NOT primarily:

```text
clustering
ontology learning
entity resolution
```

The closer abstraction is:

```text
Dynamic Semantic Schema Evolution
```

with additional constraints from:

```text
Type Systems
Bayesian Model Selection
Temporal State Estimation
```

---

# 2. Refined research boundary

Frozen RAOS-specific problem:

$$
ResolveKey(EventIdentity, CurrentSlots, NewEvidence)
$$

Input:

```text
Current semantic slots
Primitive-family constraints
New semantic proposition
Temporal context
```

Output:

```text
REUSE(existing semantic key)

or

CREATE(new semantic key)
```

The resolver does not create the whole world model.

It only maintains semantic continuity of dynamic state dimensions.

---

# 3. External theory mapping revision

## 3.1 Dynamic Schema Evolution — PRIMARY

Most relevant mature analogy.

Database systems already study:

```text
old schema
+
new information

=>

schema correspondence / evolution
```

RAOS extends this setting:

```text
schema itself is discovered dynamically
```

Therefore:

```text
Schema Matching
+
Schema Discovery
+
Schema Evolution
```

form the closest external foundation.

---

# 4. Type System / Ontology Upper Layer — PRIMARY CONSTRAINT

Primitive-family protection is not clustering metadata.

It behaves like a semantic type system.

Example:

```text
PROCESS

cannot update

FORM slot
```

This is analogous to programming language type safety:

```text
integer
cannot silently become
string
```

The primitive family restricts possible key resolution paths.

---

# 5. Bayesian Nonparametric Models — SECONDARY DECISION PRIOR

Models such as:

```text
Dirichlet Process
Chinese Restaurant Process
```

provide a useful abstraction:

```text
reuse existing latent state

or

create new latent state
```

However, they do not solve semantic identity.

They provide:

```text
new-slot probability
```

not:

```text
slot meaning resolution
```

---

# 6. Online Clustering — CANDIDATE RETRIEVAL ONLY

Clustering is useful for:

```text
candidate slot retrieval
```

but insufficient as the resolver.

Reason:

semantic similarity does not equal state dimension identity.

Example:

```text
KV cache improves generation speed

benchmark shows faster inference
```

Surface similarity exists, but semantic families differ:

```text
PROCESS

vs

QUALITY
```

Therefore clustering cannot be the final authority.

---

# 7. Entity Resolution — SUPPORTING COMPONENT

Entity resolution remains useful for:

```text
entity grounding
identity matching
referent normalization
```

But it answers:

```text
Are these the same entity?
```

while RAOS asks:

```text
Which state dimension does this evidence update?
```

Therefore it is not the core algorithm.

---

# 8. Temporal Database / State Estimation — REQUIRED CONTEXT

A semantic key is not only identified spatially.

It must persist through time.

Example:

```text
same key:
architecture.mechanism

value at t1:
method A

value at t2:
method B
```

This is a temporal state evolution problem.

Relevant concepts:

```text
valid time
transaction time
evidence time
late arriving evidence
```

RAOS already adopts this from Event Sourcing and stream processing.

---

# 9. Final theoretical composition

Phase17.3-KS ResolveKey is defined as:

```text
Dynamic Semantic Schema Evolution

+

Primitive-family Type Constraint

+

Bayesian Reuse/Create Prior

+

Temporal Semantic Continuity
```

Formally:

$$
K_{t+1}=ResolveKey(K_t,T,E_{t+1})
$$

where:

```text
K_t
= current semantic key space

T
= primitive-family type constraints

E
= new evidence
```

---

# 10. Architecture consequence

The downstream architecture remains unchanged:

```text
ResolveKey

↓

SlotDelta

↓

Deterministic Apply

↓

EventState
```

Only the semantic key resolution boundary is under research.

---

# 11. Phase17.3-KS-B implication

The next design should NOT implement a generic clustering system.

It should implement:

```text
Semantic Key Resolver
```

with stages:

1. Candidate retrieval
2. Primitive-family filtering
3. Semantic compatibility scoring
4. Reuse/Create decision
5. Deterministic persistence

This preserves the Phase17 principle:

```text
LLM decides semantic interpretation.
Deterministic system owns state mutation.
```
