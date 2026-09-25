# Phase17 Proposition FlatMap → KeyBy Preregistration V0.1

Date: 2026-09-22  
Status: PREREGISTERED RESEARCH CANDIDATE — NOT CANONICAL  
Scope: Phase17.3 semantic keyed materialized Current WorldState

## 1. Trigger

ResolveKey v1.0 passed the controlled orthogonality gate, but the frozen Jev n8 longitudinal run still exposed one residual failure: a single audited semantic unit containing both "typed judgments rather than strings" and "structurally incapable of hallucination" was materialized into one Output-Form slot instead of two orthogonal coordinates, Form and Reliability.

The root cause is architectural. One LLM call currently performs too many jobs at once:

1. decompose semantic-unit conjunctions;
2. classify Identity / World / Evidence plane;
3. discover primitive World propositions;
4. resolve propositions to existing/new keys;
5. construct current slot values.

## 2. Commercial baseline

Mature stream processors separate these responsibilities.

Kafka Streams flatMap supports:

~~~text
one input record
→ zero, one, or many output records
~~~

Flink ETL commonly composes:

~~~text
flatMap(...)
→ keyBy(...)
→ keyed state
~~~

RAOS should reuse the same topology instead of requiring ResolveKey to perform implicit flatMap internally.

## 3. Candidate RAOS topology

~~~text
Audited Semantic Evidence
        ↓
Proposition FlatMap
        ↓
0..N normalized plane-pure World propositions
        ↓
ResolveKey / KeyBy
        ↓
SlotDelta[]
        ↓
deterministic Apply
        ↓
Keyed Semantic Materialized WorldState
~~~

Identity and Evidence-plane inputs remain separately accounted for and do not become World propositions.

The authoritative persisted transition remains SlotDelta → deterministic Apply.

## 4. Proposition FlatMap contract

Candidate normalized proposition:

~~~text
WorldProposition {
    proposition_id
    statement
    support_keys[]
}
~~~

Required properties:

- plane-pure WORLD content only;
- one primitive semantic family per proposition;
- domain-independent wording when possible;
- exact support binding to audited N-keys;
- no provenance/confidence language as semantic content;
- same-primitive facets may remain together;
- cross-primitive conjunctions must split.

Example:

~~~text
INPUT UNIT:
typed judgments, not strings, and structurally incapable of hallucination

FLATMAP:
P1: outputs are expressed as typed structured judgments rather than free-form strings
P2: system is claimed to resist / be structurally incapable of hallucination
~~~

Another example:

~~~text
INPUT UNIT:
benefits are lower latency and 100% valid structured output

FLATMAP:
P1: operational latency is lower
P2: structured-output validity is reported as 100%
~~~

## 5. Basis accounting

Every new semantic support key Nxxx must be accounted for at the plane level as WORLD, IDENTITY, EVIDENCE, or PERIPHERAL_OR_REDUNDANT.

For WORLD:
- it must support at least one normalized World proposition;
- one N-key may support multiple propositions.

For non-World:
- it must support no World proposition.

Multiple N-keys may jointly support one proposition.

Therefore:

~~~text
one semantic unit != one proposition
one proposition != one semantic unit
one proposition != one slot
~~~

## 6. ResolveKey / KeyBy contract

ResolveKey receives only:

- Event Identity;
- previous persistent CurrentSlots;
- normalized World propositions.

It no longer decides Identity/Evidence plane and no longer decomposes conjunctions.

For each proposition it decides:

~~~text
NO_WORLD_VALUE_CHANGE
EXISTING(slot_id)
CREATE(new slot)
~~~

Frozen semantics remain:

~~~text
Plane-pure
General but not semantically broad
Direct-answer only
Primitive-family normalized
Counterfactually orthogonal
Materially complete
Open-world
~~~

A single slot mutation may consume multiple propositions from the same primitive family.

## 7. Why this is simpler

Old operator:

~~~text
DecideEverything(e, S)
~~~

Candidate:

~~~text
FlatMap(e)
→ KeyBy(p, S)
→ Apply
~~~

Each stage has one job.

No global ontology, fixed slot list, or hard slot-count cap is introduced.

## 8. Deterministic invariants

FlatMap ledger must require:

1. every new N-key is accounted for exactly once at plane level;
2. every WORLD N-key supports at least one proposition;
3. non-WORLD N-keys support zero World propositions;
4. every proposition has at least one WORLD support key;
5. proposition support is a subset of allowed new N-keys;
6. proposition IDs are deterministic after semantic output is admitted.

KeyBy must require:

1. existing state_question remains immutable;
2. every mutation consumes at least one normalized World proposition;
3. every proposition is dispositioned exactly once into no-value-change or mutation routing;
4. CREATE may not reuse existing slot_id;
5. UPSERT/CONTEST must use existing slot_id.

Apply reuses the existing deterministic SlotDeltaV01 → SemanticSlotStateV01 → EventStateV02 reducer.

## 9. Controlled gate

The two-stage candidate must preserve all v1.0 semantics and explicitly pass:

1. one unit → Form + Reliability;
2. "benefits" wrapper → Performance + Correctness, no Benefits key;
3. Mechanism vs Output bidirectional independence;
4. Mechanism vs Performance bidirectional independence;
5. Capability vs Affordance;
6. Capability + Performance + Affordance completeness;
7. Evidence-only corroboration → no World proposition/value change;
8. Identity-only conflict → no World proposition;
9. source omission → no World proposition/value change;
10. same-primitive performance metrics → one Performance coordinate.

## 10. Longitudinal gate

Fresh contract only:

~~~text
n8
→ deterministic replay
→ n20
→ if clean, full 44
→ full deterministic replay
~~~

Record proposition-layer expansion, plane counts, cross-primitive split count, CREATE/UPSERT/NONE, slot count, key survival, grounding refs, synopsis size, qualitative preservation, and replay digests.

## 11. Pass criterion

Pass only if there is:

- no History-Bag regression;
- no cross-plane leakage;
- no generic wrapper keys such as Benefits/Features;
- no persistent cross-primitive slot pollution;
- materially complete World coverage;
- auditable proposition/key routing;
- deterministic SlotDelta replay;
- key growth driven by new World dimensions rather than source count.

## 12. Working thesis

~~~text
History
  = immutable fine-grained evidence

FlatMap
  = semantic proposition normalization

KeyBy
  = projection onto persistent orthogonal World coordinates

Materialized State
  = latest current value per semantic key
~~~

RAOS should treat new semantic evidence like a stream record: normalize it into plane-pure propositions, key those propositions by semantic state dimension, then materialize the latest value per key.
