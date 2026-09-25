# Phase 17 Keyed Semantic Materialized State Research

Date: 2026-09-22  
Status: RESEARCH CANDIDATE — NOT YET CANONICAL  
Scope: Phase 17.3 recursive Event current-state representation

## 1. Problem

The Phase17 Event-Sourcing baseline is working:

```
Observation
→ Decide
→ persisted Delta
→ deterministic Apply
→ Current State
```

Persisted Delta replay deterministically reconstructs the same state.

However, the representation of Current State is still a RAOS-specific research problem.

The raw-reference candidate failed because Current State degenerated into History Bag:

```
Jev n8 raw-ref baseline
History refs = 79
Current refs = 79
ratio = 100%
```

CurrentFact improved this substantially and fixed several semantic failures, but the live fact set still grew:

```
n8  = 11 CurrentFacts
n14 = 19 CurrentFacts
n20 = 24 CurrentFacts
```

This does not prove CurrentFact is wrong. The Jev episode genuinely accumulates new dimensions. But it suggests that a free set of CurrentFacts is still finer-grained than the desired decision-facing materialized state.

## 2. Commercial baseline

The relevant commercial pattern is not another Event-Sourcing variant. It is keyed materialization / upsert.

### Kafka log compaction

Kafka log compaction retains the latest known value for each message key. History may contain many updates, but current recoverable state is bounded primarily by the key-space, not by update count.

### Kafka Streams / Confluent KTable

A table is a current snapshot of the latest value for each key. A changelog can reconstruct the table.

### Apache Flink updating/upsert tables

An upsert table requires an explicit key. Incoming INSERT / UPDATE_AFTER / DELETE operations update the keyed current table.

### Materialize UPSERT

Materialize interprets a stream as keyed inserts, updates, and deletes. Normal upsert semantics require at most one live value per key.

### Microsoft Materialized View

Event history is retained independently while a query-oriented current projection is incrementally materialized.

The common commercial answer is:

```
History can be fine-grained and unbounded.

Current State
= latest materialized value per stable key.
```

## 3. Main insight for RAOS

Do NOT coarsen the Evidence / History representation.

Fine-grained semantic units are useful and should remain fine because they support:

- provenance
- correction
- contradiction
- audit
- deterministic replay grounding

Coarsen the materialized Current State instead.

```
Fine Evidence / Immutable History
        ↓
Resolve semantic state key
        ↓
Coarse Keyed Materialized State
```

This separates two concerns that CurrentFact partially conflated:

1. evidence granularity;
2. state-variable granularity.

## 4. Candidate representation

Replace an unordered/free set of CurrentFacts with a keyed current-state map.

Conceptually:

```
Event
├── Identity
├── History
└── Current Semantic State
    ├── Slot A → current value + support
    ├── Slot B → current value + support
    └── Slot C → current value + support
```

Candidate cell:

```
CurrentSlot
{
    slot_id          # stable immutable identity / primary key
    slot_label       # human-readable, may evolve
    state_question   # what current-state question this slot answers
    value            # current materialized value
    support_refs[]   # audited grounding
}
```

Important:

- `slot_id` is the stable key.
- `slot_label` is not the identity.
- A label/question may become clearer over time without changing `slot_id`.
- One observation may update multiple slots.
- One semantic unit may support multiple slots when it genuinely changes multiple state dimensions.
- There is no global fixed ontology.
- Slots are derived within the boundary of Event Identity.
- No hard limit is imposed on slot count.

## 5. RAOS-specific research question

Commercial systems solve materialization once the key is known.

The remaining RAOS-specific problem becomes:

```
ResolveKey(EventIdentity, CurrentSlots, NewEvidence)
    → EXISTING(slot_id)
      | CREATE(new slot)
```

Then ordinary materialization semantics apply:

```
slot_id + new evidence
→ UPSERT current value
```

This is a substantially smaller research surface than unconstrained CurrentFact merging.

## 6. Jev semantic-key discovery experiment

### 6.1 n20 free discovery

Input:

```
24 live CurrentFacts
```

A one-shot semantic-key discovery projected them into approximately 9 semantic state questions.

Examples:

- identity / positioning
- mechanism / architecture
- release / availability
- performance claims
- validation evidence
- application domains
- preprocessing / routing pattern
- community / ecosystem
- limitations / uncertainty

All 24 input facts were covered.

Two facts affected two slots, which is acceptable: commercial keyed systems do not require one input event to update only one key.

### 6.2 n8 independent discovery

Input:

```
10 live CurrentFacts
```

Output:

```
6 semantic slots
1 peripheral DROP
```

The six early state questions were approximately:

- identity + release
- performance claims
- mechanism
- output characteristics
- demonstrations
- validation status

## 7. Temporal key-stability experiment: n8 → n20

The critical experiment did NOT rediscover the key-space from scratch.

It froze the six n8 slot keys and asked whether the n20 CurrentFacts could update those existing slots, creating a new slot only if genuinely necessary.

Result:

```
n8 existing slots: 6

n20:
reused old slots = 6 / 6
created new slots = 1
final slots       = 7
input CurrentFacts = 24
```

This is the strongest result of this research round.

It suggests:

```
24 free CurrentFacts
≈
7 keyed state cells
```

More importantly, all six early keys survived to n20.

Therefore the semantic dimensions are not arbitrarily drifting. The free-text facts are primarily over-fragmenting updates to a much smaller persistent state space.

## 8. Why independent n20 discovery found 9 slots while frozen-key reuse found 7

When rediscovering from scratch, the model tends to refine/split dimensions as more evidence becomes available, e.g.:

```
early:
demonstrations

later rediscovery:
validation evidence
application domains
```

But when stable early keys are treated as primary identities, the later evidence can remain coherently materialized into the broader existing key.

This is analogous to schema/key stability in commercial systems.

Therefore:

> Recomputing semantic keys from scratch on every observation is the wrong architecture.

Use persistent slot identity.

## 9. Candidate state transition semantics

The next candidate should look closer to an upsert table than to a bag of facts.

```
New Observation
    ↓
ResolveKey
    ↓
SlotDelta[]
    ├── UPSERT existing slot
    ├── CREATE new slot
    └── optionally CONTEST / RETIRE when explicitly required
    ↓
deterministic Apply
    ↓
Keyed Current State
```

The initial implementation should remain minimal.

Do NOT introduce:

- a global ontology;
- a fixed list of Jev-specific categories;
- a maximum slot count;
- arbitrary score thresholds;
- periodic full re-clustering.

## 10. Relation to CurrentFact

CurrentFact was not a failed detour.

It established several necessary results:

- History is not Current State.
- Current meaning must be derived.
- materiality filtering works.
- multiple narrow examples can be merged.
- deterministic Apply can reject semantic-loss transitions.
- new evidence can leave WorldState unchanged.
- persisted semantic deltas replay deterministically.

The next representation is best understood as:

```
CurrentFact
+ stable semantic primary key
= CurrentSlot
```

The key is the missing abstraction.

## 11. Updated Phase17.3 hypothesis

Old hypothesis:

> A compact free set of derived CurrentFacts is sufficient as Event Current State.

New candidate hypothesis:

> Event Current State is better represented as a small, dynamically discovered but persistently keyed semantic materialized view.

Formally:

```
S_t = { k_i → v_i }_{i=1..m_t}
```

where:

- `k_i` is a persistent semantic state key;
- `v_i` is the current materialized value and audited grounding;
- History remains immutable and separate;
- `m_t` grows only when a genuinely new state dimension appears.

The desired property is not a predetermined small `m_t`.

The desired property is:

```
repeated evidence about an existing dimension
→ UPSERT(k)
not
→ CREATE(new fact)
```

## 12. Next experimental gate

Implement an eval-only keyed-slot prototype.

Required tests:

1. Existing-key reuse:
   repeated / broader evidence updates the same slot.

2. New-dimension creation:
   genuinely new state question creates one slot.

3. Multi-slot update:
   one observation may update more than one existing slot.

4. Peripheral evidence:
   History changes, keyed Current State does not.

5. Correction:
   corrected evidence updates the same stable slot identity.

6. Contest:
   unresolved conflict remains attached to the affected slot rather than creating an unrelated top-level fact.

7. Replay:
   persisted SlotDelta + deterministic Apply reproduces identical slot-state digest.

8. Jev longitudinal:
   replay the frozen Jev trajectory and measure:
   - current slot count over time;
   - CREATE vs UPSERT ratio;
   - key survival / churn;
   - grounding coverage;
   - qualitative information preservation.

Phase17.3 should not be declared PASS until this keyed-state candidate is compared against CurrentFact on the same frozen longitudinal benchmark.

## 13. Current conclusion

The mature commercial systems strongly suggest that the right abstraction is not:

```
How do we keep merging an ever-growing bag of CurrentFacts?
```

but:

```
What is the stable semantic key of this state change?
```

Once the key is resolved, the rest is standard keyed materialization.

This moves the RAOS-specific novelty to the smallest plausible place:

```
ResolveKey(EventIdentity, CurrentSlots, NewEvidence)
```

and reuses established Event Sourcing + upsert/materialized-view machinery for everything else.
