# Phase17 Key-Space Orthogonality and Plane Separation — Preregistration V0.1

Date: 2026-09-22  
Status: PREREGISTERED RESEARCH CANDIDATE — NOT CANONICAL  
Scope: Phase17.3 keyed semantic materialized Current State

## 1. Why this experiment exists

Phase17 has converged on a strong engineering pattern:

```text
Immutable Evidence / History
        ↓
ResolveKey
        ↓
persisted SlotDelta
        ↓
deterministic keyed Apply
        ↓
Current Semantic State
```

The v0.4 Jev longitudinal run produced:

```text
20 observations
191 historical semantic refs
→ 6 persistent slots

CREATE = 6
UPSERT = 48
NONE   = 1
```

After observation 4, no additional slot was created through observation 20.

This is a strong stability result, but slot-count stability is not sufficient.

A bad key can be perfectly stable.

The new research question is therefore:

> **What makes a semantic state key a good coordinate of Event Current State?**

The working answer is not "small" and not "topic-like".

It is:

> **orthogonal, general, plane-pure, persistent semantic coordinates.**

---

## 2. Key-space is a coordinate system, not a taxonomy

A CurrentSlot key is not merely a category label for evidence.

It defines one coordinate of the current Event state space:

```text
W_t = { k_i → v_i }_{i=1..m_t}
```

Evidence is projected onto these coordinates.

Repeated evidence should update the coordinate value:

```text
evidence about K_i
→ UPSERT(K_i)
```

rather than create a new topical fact.

The desired key-space therefore behaves more like a state vector basis than a document taxonomy.

---

## 3. Frozen RAOS plane separation

Existing Phase17 theory already freezes:

```text
Event
├── Identity          # stable referent / topology layer
├── Current EventState
│   ├── WorldState
│   └── EvidenceState
├── History           # immutable audit/replay
└── FilterState       # algorithm/controller state
```

Therefore candidate semantic keys must respect four distinct planes.

### 3.1 Identity plane

Identity answers:

```text
What world referent / episode is this?
```

Examples:

- actor identity;
- coarse action/episode;
- object;
- identity time context;
- location;
- Event type.

Identity is NOT an ordinary mutable WorldState coordinate.

A key such as:

```text
"What is Jev and what is its release status?"
```

is mixed because it combines:

```text
Identity:
what is Jev / who is it from?

World:
what lifecycle / availability state is it currently in?
```

The identity portion must not live in keyed WorldState.

### 3.2 World plane

WorldState answers mutable questions about the Event itself:

```text
What condition is currently true of the identified Event?
```

Examples may include:

- lifecycle / phase;
- structure / composition;
- mechanism / dynamics;
- capability / behavior;
- quality / quantity / performance;
- relation / context / affordance.

These are inspirations, not a fixed ontology.

### 3.3 Evidence / epistemic plane

EvidenceState answers:

```text
Why does RAOS currently support this WorldState?
How mature / independent / conflicting is the support?
```

Examples:

- provenance;
- source independence;
- corroboration;
- first-party vs secondary support;
- uncertainty / conflict structure;
- evidence maturity.

A world proposition and its epistemic status are different objects.

```text
World proposition:
"The system executes a decision in 300 ms."

Epistemic qualifier:
"This is a single source-reported benchmark with no independent reproduction."
```

The second must not become a competing semantic World key.

### 3.4 History and Filter planes

Historical omission, previous wording, arrival momentum, hysteresis, and replay bookkeeping are not Current World coordinates.

---

## 4. Open-World update rule

Phase17 ResolveKey v0.4 adopts the mature open-world principle:

```text
absence from one Source
!= false
!= globally unknown
!= superseded
```

Therefore:

```text
Current State:
Jev is an AI model.

New Source:
This report does not specify whether Jev is a model/human/system.

Correct:
NO CHANGE

Incorrect:
CREATE "Jev identity is unknown"
```

By contrast:

```text
New Source explicitly asserts:
"Jev is not an AI model; it is a human-operated system."

Correct:
CONTEST existing identity proposition
```

Controlled v0.4 gate already validated both directions.

---

## 5. Orthogonality criterion

For candidate keys K_i and K_j, define a counterfactual independence test.

Ask:

```text
Can K_i change while K_j remains fixed?
Can K_j change while K_i remains fixed?
```

If both are coherent, the dimensions are approximately orthogonal:

```text
K_i ⟂ K_j
```

This is semantic independence, not statistical independence.

Two keys may often co-update in one dataset while remaining ontologically orthogonal.

Example:

```text
Mechanism ↔ Performance
```

In the Jev trace they frequently co-update because sources describe both together.

But it is coherent for:

```text
mechanism changes, performance fixed
performance changes, mechanism fixed
```

Therefore empirical co-update does not justify merging them.

---

## 6. Generality criterion

A good key should be reusable beyond one Event and preferably beyond one domain.

Test:

> Replace the concrete subject with "this entity / event / system". Does the question still express one coherent state coordinate?

Bad:

```text
"What games has Jev played?"
```

Better:

```text
"What capabilities or behaviors has this system been demonstrated performing?"
```

Bad:

```text
"What Jev browser agent examples exist?"
```

Better:

```text
"What application contexts or affordances currently characterize this system?"
```

Generality does NOT mean every Event must instantiate every key.

The key-space remains dynamically discovered.

---

## 7. Primitive / single-axis criterion

One key should answer one basic kind of question.

Avoid conjunctions of counterfactually independent dimensions.

Examples of suspicious mixed questions:

```text
identity + release
output format + reliability
mechanism + performance
capability + validation
```

A question is a candidate primitive coordinate when:

1. its answer can change independently of neighboring coordinates;
2. it has one stable semantic interpretation;
3. repeated evidence naturally UPSERTs it;
4. it generalizes beyond the current source wording.

Upper-ontology inspirations include:

```text
Being / Identity          → outside mutable WorldState
Becoming / Lifecycle      → current phase / availability
Structure                 → composition / organization
Dynamics / Mechanism      → how it works / changes
Capacity / Behavior       → what it can / does do
Quality / Quantity        → how well / how much / at what cost
Relation / Affordance     → where / with what / for what it is used or suited
```

This list is explanatory, not a globally fixed schema.

---

## 8. Current Jev v0.4 six-slot audit

Frozen source artifact:

```text
eval/live/results/phase17_jev_longitudinal_state_replay_v0_6/
phase17_jev_longitudinal_state_replay_v0.6_n20_20260921T212553Z.json
```

Current six keys:

```text
1. Demonstrated capability: game playing
2. Model identity and release status
3. Output format and hallucination claim
4. Claimed suitability for real-time use cases
5. Claimed performance and cost characteristics
6. Mechanism and architecture
```

The first orthogonality audit finds:

### 8.1 Strong / mostly valid coordinates

```text
capability / behavior
performance / quality
mechanism / dynamics
application / affordance
```

These are counterfactually separable.

### 8.2 Boundary violations

```text
identity + release
```

must separate Identity from mutable lifecycle.

### 8.3 Mixed-axis candidates

```text
output format + hallucination claim
mechanism + architecture
```

may contain separable dimensions:

```text
interface/output form vs reliability quality
structure vs operating mechanism
```

Whether to split them is an empirical question; do not split merely to satisfy a philosophical list.

---

## 9. Empirical co-update result

Across the frozen Jev n20 v0.4 trace:

```text
mechanism touched: 9 observations
performance touched: 13 observations
mechanism ∩ performance: 9 observations
P(performance | mechanism) = 1.00
```

This is high empirical dependence.

However this trace-specific correlation does not defeat counterfactual orthogonality.

Therefore Phase17 must distinguish:

```text
dataset co-update
from
semantic coordinate dependence
```

Do not infer ontology from co-occurrence alone.

---

## 10. Key-space evolution must be separate from ordinary state update

Normal Event evidence update must preserve key identity:

```text
CREATE / UPSERT / CONTEST
```

The state_question of an existing slot remains immutable during ordinary Apply.

However, a persistently keyed system also needs a separate low-frequency mechanism for improving the coordinate system itself.

Conceptually:

```text
ordinary evidence path:
Observation → ResolveKey → SlotDelta → Apply

rare schema path:
KeySpace Audit → KeySpaceMigration
              → MERGE / SPLIT / RETIRE / REKEY
```

This is analogous to database schema evolution.

It must NOT be mixed into ordinary evidence processing, otherwise key identity drifts on every observation.

No KeySpaceMigration will be implemented in this preregistered experiment.

First establish whether a better key-creation policy prevents bad keys from being created.

---

## 11. ResolveKey v0.5 preregistered semantics

The next ResolveKey candidate will add three gates before CREATE.

### Gate A — Plane purity

Before creating a World slot:

```text
Is this about Event identity?
→ do not CREATE World slot

Is this only provenance / validation / source completeness?
→ do not CREATE World slot

Otherwise:
→ continue
```

Evidence remains in History / EvidenceState.

### Gate B — Generality

For a new state question:

```text
replace the concrete subject with "this entity/event/system"
```

If the question collapses into a source-specific topic label, abstract it upward.

### Gate C — Counterfactual independence

Compare the new question with each existing state_question.

If it directly changes an existing answer:

```text
UPSERT existing key
```

If it represents a genuinely independently variable World dimension:

```text
CREATE new key
```

Do not optimize for fewer keys.

---

## 12. Preregistered controlled tests

ResolveKey v0.5 must preserve all v0.4 controlled gates and add:

1. **Identity/lifecycle separation**
   - Event Identity already says what the entity is.
   - New release evidence may CREATE/UPSERT lifecycle status.
   - It must not create or mutate an identity World slot.

2. **Evidence-only update**
   - A new independent reproduction may update EvidenceState.
   - It must not automatically CREATE a World key named validation/confidence.

3. **World proposition vs epistemic qualifier**
   - A reported numeric performance proposition may update Performance.
   - "single source / no independent reproduction" remains epistemic support, not a separate World key.

4. **Generality**
   - Mario / DOOM / Tetris evidence must resolve to a generic capability/behavior question, not a game-specific key.

5. **Mechanism vs performance**
   - New mechanism evidence with no performance change may CREATE/UPSERT Mechanism without touching Performance.
   - New benchmark evidence with no mechanism change may UPSERT Performance without touching Mechanism.

6. **Capability vs affordance**
   - A demonstrated action updates Capability/Behavior.
   - Mere proposed suitability may update Affordance/Application without pretending the capability was demonstrated.

7. **Open-world omission**
   - missing Source fields remain NONE for already-known properties.

8. **Explicit conflict**
   - materially incompatible assertion CONTESTs the existing affected World coordinate.

---

## 13. Longitudinal gate

Run the frozen Jev trace under v0.5.

Record:

```text
slot count trajectory
CREATE / UPSERT / CONTEST / NONE
key creation step
key survival
pairwise co-update
active grounding refs
value length
boundary violations
qualitative information preservation
```

Compare against:

```text
CurrentFact
v0.3 keyed slots
v0.4 open-world keyed slots
```

The goal is NOT fewer than six slots.

Pass condition:

> **The resulting key-space is more plane-pure and counterfactually orthogonal without losing material World information or reintroducing key churn.**

---

## 14. Non-goals

Do NOT:

- freeze a universal seven-category ontology;
- force every Event to instantiate the same dimensions;
- minimize slot count as an objective;
- infer semantic dependence from co-update statistics alone;
- move Event Identity into WorldState;
- create a validation/confidence World key merely because evidence is uncertain;
- introduce KeySpaceMigration before the creation policy is tested;
- modify production canonical Event Processor.

---

## 15. Working thesis

The current thesis is now stronger than "Current State is keyed".

```text
History
= fine-grained immutable evidence

Identity
= stable referent boundary

WorldState
= dynamically discovered, persistently keyed,
  approximately orthogonal semantic coordinates

EvidenceState
= structural / epistemic support for those coordinates

FilterState
= algorithmic memory
```

In one line:

> **RAOS should not merely discover keys; it should discover a low-dimensional semantic basis for the current world state.**
