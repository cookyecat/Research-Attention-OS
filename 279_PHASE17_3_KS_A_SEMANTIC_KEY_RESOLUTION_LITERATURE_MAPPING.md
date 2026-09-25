# Phase17.3-KS-A Semantic Key Resolution Literature Mapping

Date: 2026-09-22

Status: Research Draft

## 1. Research Question

RAOS-specific problem:

```text
ResolveKey(EventIdentity, CurrentSlots, NewEvidence)
```

Question:

> Given a new semantic evidence item, should it reuse an existing semantic state dimension or create a new dimension?

The downstream system is already adopted:

```text
History        -> Event Sourcing
State          -> Materialized View
Update         -> Delta Apply
Replay         -> Changelog Replay
```

Only semantic key resolution remains RAOS-specific.

## 2. Candidate Mature Theories

### 2.1 Entity Resolution

Purpose:

Determine whether two records refer to the same entity.

Useful concepts:

- similarity matching
- blocking
- candidate generation
- confidence scoring

Limitation:

RAOS does not mainly solve entity identity.

It solves semantic state dimension identity.

### 2.2 Schema Matching

Purpose:

Determine whether fields from different schemas correspond.

Closest analogy:

```text
existing slot
        vs
new proposition
```

Potential reuse:

- semantic similarity
- structural constraints
- type compatibility

## 3. Ontology Learning

Purpose:

Discover concepts, properties, and relations from unstructured data.

Useful idea:

```text
text evidence
 -> latent concepts
 -> attributes
```

Limitation:

Ontology learning is usually open-world discovery.

RAOS requires online incremental state maintenance.

## 4. Online Clustering

Most direct algorithmic analogy:

```text
new observation
       |
       +-- existing cluster
       |
       +-- new cluster
```

Correspondence:

```text
new evidence
       |
       +-- reuse semantic key
       |
       +-- create semantic key
```

Limitation:

Pure clustering ignores primitive-family constraints.

Example:

"fast because KV cache"

contains similarity to:

- mechanism
- performance

but should not merge automatically.

## 5. Bayesian Nonparametric Models

Important candidate:

Dirichlet Process / Chinese Restaurant Process.

Core property:

The number of clusters is not fixed.

Correspondence:

Traditional state model:

```text
fixed dimensions
```

RAOS:

```text
unknown number of semantic slots
```

Potential role:

CREATE probability prior.

Not sufficient alone because semantic typing is required.

## 6. Cognitive Science Analogy

Human concept formation:

Experience is not stored as sentences.

It forms reusable concepts:

```text
object
{
 attributes
 relations
 functions
}
```

Relevant principle:

new experience updates existing conceptual structure unless a genuinely new category is required.

## 7. Preliminary Conclusion

No single mature algorithm directly solves RAOS ResolveKey.

Best composition:

```text
Schema Matching
        +
Ontology / Type Constraints
        +
Online Clustering
        +
Bayesian Nonparametric Prior
```

RAOS-specific addition:

```text
primitive_family constraint
+
semantic slot continuity
```

The next step is to design the minimal resolver rather than invent a complete ontology.
