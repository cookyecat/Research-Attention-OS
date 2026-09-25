# Phase17 Primitive-Family Guard — Preregistration Amendment

Date: 2026-09-22  
Status: PREREGISTERED AMENDMENT — NOT CANONICAL  
Parent: 274_PHASE17_KEYSPACE_ORTHOGONALITY_AND_PLANE_SEPARATION_PREREGISTRATION.md

## 1. Trigger

ResolveKey v1.1 successfully made semantic-unit decomposition explicit:

```text
SemanticUnit
→ atomic proposition basis
→ proposition-level plane routing
→ ResolveKey
```

The Jev n8 trace shows that proposition decomposition itself works.

Example from observation 3:

```text
N007
├ "returns typed judgments rather than strings"
└ "structurally incapable of hallucination"
```

The model emitted these as two distinct propositions.

However, both propositions were routed to the same existing `Output Form` slot.

Observation 4 showed the same failure more strongly:

```text
"single Transformer decoder + KV-cache reuse ..."
```

was correctly extracted as an atomic World proposition, but was still routed into `Output Form` rather than a new/existing mechanism coordinate.

Therefore the remaining failure is:

> **proposition → semantic key routing, not proposition decomposition.**

---

## 2. Research diagnosis

A free-text `state_question` is a good semantic key description but is too weak as the only machine-checkable type.

Example:

```text
Output Form:
"In what form does the system express its outputs?"

Mechanism proposition:
"The system uses a Transformer decoder with KV-cache reuse."
```

A human sees immediately that the proposition does not answer the Form question.

A language model may nevertheless route it there because the concepts are causally/topically related.

Prompt-level Direct Answer rules reduce this error but do not eliminate it.

The next candidate adds a very thin upper-level type system.

---

## 3. External design inspiration

Foundational ontologies such as BFO use a deliberately small domain-neutral upper layer rather than encoding domain taxonomies directly. Relevant distinctions include:

```text
continuant vs process
quality
role
function / disposition
relation
```

W3C PROV separately models provenance information used for reliability/trust assessment, reinforcing the existing RAOS decision that epistemic support is not an ordinary World coordinate.

RAOS will not import either ontology wholesale.

Only the architectural lesson is reused:

> **dynamic domain semantics can be constrained by a small upper-level type system.**

---

## 4. Candidate primitive families

Each mutable World slot will carry exactly one `primitive_family`.

Candidate V0.1:

```text
STATE
STRUCTURE
PROCESS
FORM
DISPOSITION
QUALITY
RELATION
OTHER
```

Interpretation:

### STATE

Current condition / lifecycle / availability.

### STRUCTURE

Composition, parts, organization, topology.

### PROCESS

Mechanism, dynamics, transformation, procedure.

### FORM

Manifestation, representation, interface, output/action form.

### DISPOSITION

Capability, function, tendency, realizable behavior.

### QUALITY

Performance, quantity, reliability, correctness, cost, rate, magnitude.

### RELATION

Role, context, affordance, suitability, relation to other entities/systems.

### OTHER

Material World proposition that cannot yet be coherently typed.

`OTHER` is an escape hatch, not a preferred bucket.

---

## 5. What this is NOT

This is NOT a fixed Event ontology.

RAOS does NOT define:

```text
every Event must have:
- Performance
- Mechanism
- Capability
- Reliability
...
```

Instead:

```text
primitive_family = upper-level type

state_question = dynamically discovered semantic coordinate
slot_id = stable primary key
value = current materialized answer
```

For example, two QUALITY slots can legitimately coexist:

```text
QUALITY:
"What operational performance ...?"

QUALITY:
"What output correctness / failure behavior ...?"
```

Their free semantic keys remain distinct.

Therefore the family guard catches gross cross-family routing but does not replace ResolveKey.

---

## 6. Plane separation remains frozen

```text
Identity
!= World primitive family

Evidence / provenance
!= World primitive family
```

Identity and Evidence do not receive a World `primitive_family`.

Only WORLD_MUTATION propositions are typed.

---

## 7. Deterministic invariant

For every WORLD proposition P routed to mutation M:

```text
P.primitive_family
==
M.slot.primitive_family
```

For an EXISTING mutation:

```text
M.slot.primitive_family
==
previous_slot.primitive_family
```

Therefore:

```text
PROCESS proposition
→ cannot update FORM slot

QUALITY proposition
→ cannot update FORM slot

RELATION proposition
→ cannot update DISPOSITION slot
```

The reducer owns this invariant.

---

## 8. Why this is preferable to another LLM pass

Alternative:

```text
ResolveKey
→ second semantic critic LLM
→ repair
```

is rejected for now because it:

- adds latency;
- adds cost;
- creates another stochastic authority;
- duplicates reasoning.

Primitive-family typing gives the reducer a deterministic semantic type check while keeping one LLM Decide call.

This is the simpler architecture.

---

## 9. Controlled gate additions

The existing v1.1 gate must continue to pass.

Add family-specific tests:

1. Mechanism proposition is PROCESS.
2. Output-form proposition is FORM.
3. Hallucination/correctness proposition is QUALITY.
4. Operational performance proposition is QUALITY.
5. Demonstrated capability is DISPOSITION.
6. Proposed role/application/affordance is RELATION.
7. Lifecycle/release is STATE.
8. PROCESS proposition cannot route to FORM mutation.
9. QUALITY proposition cannot route to FORM mutation.
10. RELATION proposition cannot route to DISPOSITION mutation.
11. Existing slot family is immutable under UPSERT/CONTEST.
12. One semantic unit may yield multiple propositions with different families.

---

## 10. Longitudinal pass criterion

Re-run the same frozen Jev trace from scratch under the new contract.

Do not optimize for slot count.

The candidate passes this amendment only if:

1. proposition-basis completeness remains intact;
2. gross cross-family routing is zero;
3. no Identity/Evidence World slot appears;
4. no generic Benefit/Feature wrapper slot appears;
5. slot families remain immutable;
6. persisted SlotDelta replay remains deterministic;
7. qualitative World information is not materially lost.

---

## 11. Working model

```text
SemanticUnit
→ PropositionBasis
    proposition + plane + primitive_family
→ ResolveKey
    existing slot or CREATE
→ deterministic family check
→ SlotDelta
→ deterministic Apply
```

In short:

> **The semantic key stays dynamic; the key's ontological type becomes checkable.**
