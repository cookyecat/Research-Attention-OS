# Phase17 Key-Space Basis Completeness — Preregistration V0.1

Date: 2026-09-22  
Status: PREREGISTERED AFTER V0.5 LONGITUDINAL FAILURE — NOT CANONICAL  
Scope: Phase17.3 ResolveKey v0.6

## 1. Trigger

ResolveKey v0.5 passed its controlled semantic gate:

```text
17 / 17 controlled cases
59 / 59 combined deterministic Phase17 tests
```

but failed the first frozen Jev longitudinal run.

Observed trajectory:

```text
obs1:
CREATE 2 slots
- Demonstrated capabilities
- Intended application domains

obs2:
UPSERT only
slots remain 2
```

Observation 2 contained a material, independently variable World proposition:

```text
20–200x faster
40–400x cheaper
free output tokens
10 calls / second
```

but ResolveKey did not create a Performance / Quality coordinate.

Its own rationale stated that the performance figures were material World propositions but did not justify a stable coordinate from one Source. This violates the frozen plane-separation rule:

```text
low evidence maturity
!=
non-World proposition
```

Observation 3 then triggered deterministic rejection because the model attempted to re-emit an unchanged Intended-Application slot without new support.

Therefore v0.5 does NOT pass Phase17.3 longitudinal evaluation.

## 2. New requirement: basis completeness

The semantic key-space is treated as a dynamically discovered basis for current WorldState. Orthogonality alone is insufficient.

A useful basis must satisfy:

```text
Plane Purity
+ Generality
+ Counterfactual Orthogonality
+ Basis Completeness
```

Basis Completeness means:

> Every distinct material World proposition in the new observation must either be representable by an existing key or cause creation of a new independently variable key.

Formally, let M(e) be the distinct material World propositions in new evidence e. For every p in M(e):

```text
exists k in K_t:
    p materially changes value(k)

OR

exists new k:
    p defines a new independently variable World coordinate
```

Otherwise the key-space is incomplete for that update.

## 3. Low dimensionality is not the optimization target

A smaller key-space is not automatically better.

Bad compression:

```text
10 material dimensions
→ 2 broad keys
→ semantic loss
```

Good materialization:

```text
many evidence units
→ few non-overlapping semantic coordinates
→ all material World information preserved
```

Therefore `minimize key count` is rejected. The desired objective is closer to:

```text
minimal redundancy
subject to
material World coverage
```

No scalar optimization function is frozen at this stage.

## 4. Evidence Projection Ledger

ResolveKey v0.6 will make evidence routing explicit in the LLM draft.

Every NEW support key Nxxx must receive exactly one semantic disposition:

```text
WORLD_MUTATION
IDENTITY
EVIDENCE
PERIPHERAL_OR_REDUNDANT
```

For WORLD_MUTATION, the disposition must reference one or more proposed mutations.

A semantic unit is assigned to exactly one plane, but one World proposition may legitimately update multiple orthogonal coordinates.

Conceptually:

```text
N001 → WORLD_MUTATION → [mutation 0]                 → Capability
N002 → IDENTITY
N003 → WORLD_MUTATION → [mutation 0, mutation 1]     → Capability + Performance
N004 → EVIDENCE
N005 → PERIPHERAL_OR_REDUNDANT
```

This ledger is eval-only reasoning/audit metadata. It is NOT persisted into canonical EventState.

The persisted authoritative transition remains:

```text
SlotDelta
→ deterministic Apply
```

## 5. Deterministic ledger invariants

The v0.6 draft validator must require:

1. every allowed NEW support key appears exactly once in the ledger;
2. no unknown NEW key appears;
3. WORLD_MUTATION points to one or more valid mutation indices;
4. every referenced mutation includes the same NEW support key;
5. non-World dispositions do not point to mutations;
6. every proposed mutation is referenced by at least one WORLD_MUTATION ledger entry and still contains at least one NEW support key;
7. existing slot state_question remains immutable.

This does not make semantic classification deterministic. It makes semantic omission auditable and structurally fail-closed.

## 6. Material proposition rule

Semantic units may duplicate or restate the same proposition. Therefore basis completeness is NOT:

```text
one semantic unit → one slot
```

Multiple units may project to the same mutation. Identity/evidence/duplicate units may project to no World mutation.

The requirement is:

```text
every input semantic unit is accounted for
AND
every distinct material World dimension is represented
```

## 7. Required v0.6 controlled probes

Preserve all v0.5 successful probes and add:

### 7.1 Multi-proposition completeness

Existing:

```text
Capability
Affordance
```

New observation contains:

```text
new demonstrated behavior
new performance metrics
new application proposal
```

Expected:

```text
UPSERT Capability
UPSERT Affordance
CREATE Performance
```

No material World proposition may disappear merely because the observation is multi-topic.

### 7.2 Source-count independence

A concrete single-source performance proposition must still map to Performance. Evidence maturity may change EvidenceState, not whether the semantic coordinate exists.

### 7.3 Evidence-only corroboration

If independent reproduction changes support but not the World proposition:

```text
World mutation = NONE
EvidenceState changes structurally
```

### 7.4 Unchanged-coordinate omission

If new evidence changes Performance only:

```text
Performance mutation
Mechanism absent from SlotDelta
Affordance absent from SlotDelta
Capability absent from SlotDelta
```

### 7.5 Ledger completeness

All new N-keys must be dispositioned exactly once and validated before Apply.

## 8. Longitudinal gate

After controlled pass:

```text
fresh v0.6 n8
→ deterministic replay
→ n14
→ n20
```

Record:

- slot count trajectory;
- key creation steps;
- CREATE/UPSERT/NONE;
- evidence-disposition counts;
- World coverage failures;
- Identity/Evidence leakage;
- pairwise key orthogonality;
- value growth;
- support-ref growth.

Compare with v0.4 and failed v0.5.

## 9. Frozen interpretation

The Phase17 key-space hypothesis is now:

> **Current WorldState is a dynamically discovered semantic basis: persistent keys should be plane-pure, general, approximately orthogonal, and complete for material World propositions.**

Or compactly:

```text
Good Key-Space
=
Orthogonal
∩ General
∩ Plane-Pure
∩ Materially Complete
```

The next experiment tests this claim.
