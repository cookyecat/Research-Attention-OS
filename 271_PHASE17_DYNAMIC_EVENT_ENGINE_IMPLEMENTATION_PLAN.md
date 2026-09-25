# Phase 17 — RAOS Dynamic Event Engine Implementation Plan V1.0

Status: **IMPLEMENTATION SOURCE OF TRUTH / ACTIVE**  
Date: 2026-09-21

Primary theory reference:

- `269_PHASE17_EVENT_SOURCED_RECURSIVE_STATE_FILTER_THEORY.md`

Supporting benchmark/research references:

- `267_PHASE17_EVENT_STATE_MODEL_REVIEW_AND_JEV_BENCHMARK.md`
- `268_PHASE17_JEV_LONGITUDINAL_BENCHMARK_IDENTITY_RESULT.md`
- `270_PHASE17_RECURSIVE_EVENT_STATE_FILTER_PRIMITIVE_RESULT.md`

Historical preregistration/reference only:

- `266_PHASE17_EVENT_STATE_COGNITION_PREREGISTRATION.md`

---

# 0. Document authority and change discipline

This document is the **implementation source of truth for Phase17 Dynamic Event Engine**.

Authority order:

```text
1. RAOS_CANONICAL_ARCHITECTURE.md
   -> long-lived architecture invariants

2. 269_PHASE17_EVENT_SOURCED_RECURSIVE_STATE_FILTER_THEORY.md
   -> frozen Phase17 theory / mathematical model

3. 271_PHASE17_DYNAMIC_EVENT_ENGINE_IMPLEMENTATION_PLAN.md
   -> implementation sequence, contracts, gates, rollout

4. 11_ROADMAP_AND_PROGRESS.md
   -> current progress summary

5. 266/267/268/270 and eval artifacts
   -> preregistration, historical experiments, results
```

Implementation discipline:

> **If implementation reality forces a design change, update this document in the same work session/patch.**

Required synchronization:

```text
implementation detail changes
-> update this plan

theory changes
-> update 269 + this plan

canonical invariant changes
-> update RAOS_CANONICAL_ARCHITECTURE + 269 + this plan

phase/gate status changes
-> update this plan + 11_ROADMAP_AND_PROGRESS

experiment result changes understanding
-> write immutable result doc
-> then update this plan if the forward design changes
```

Do not allow code to become the only source of a changed architecture decision.

No commit/push is implied by this plan.

---

# 1. Review verdict

## 1.1 Direction approved

The Phase17 top-level design is internally consistent and should proceed.

RAOS directly adopts mature external architecture/theory rather than inventing substitutes:

```text
Event Sourcing
-> immutable history + materialized current state

Apache Flink keyed-state semantics
-> state is maintained per Event.id

Recursive/Bayesian state estimation
-> new state = previous sufficient state + new observation

Evidence accumulation
-> repeated evidence changes a stateful signal, not article-by-article classification

Hysteresis / Schmitt-trigger principle
-> Attention has memory/inertia and does not chatter around boundaries
```

Canonical dynamics:

\[
\boxed{
H_{t+1}=H_t\oplus e_{t+1}
}
\]

\[
\boxed{
S_{t+1}=U(S_t,e_{t+1})
}
\]

\[
\boxed{
D_{t+1}=F(S_{t+1},K_t,C_t)
}
\]

\[
\boxed{
A_{t+1}=\mathcal H(A_t,D_{t+1},C_t)
}
\]

Conservation principle:

```text
History is append-only.
Current State is revisable.
```

## 1.2 What is no longer a research question

Phase17 will NOT research whether RAOS should use:

- Event Sourcing;
- recursive materialized state;
- Event-keyed stateful processing;
- stateful evidence accumulation;
- hysteretic Attention.

These are adopted architectural principles.

The research questions are now only:

1. what one RAOS Event observation contains;
2. how `Φ` estimates a semantic state update;
3. how deterministic `R` commits the update;
4. how information innovation is measured;
5. how evidence momentum is parameterized;
6. how EventState enters the existing cognition contract;
7. how hysteresis should operate over the existing cardinal-free Attention output.

---

# 2. Five review corrections before production wiring

The current Phase17 primitives are useful but are not yet the final production contract.

The following corrections are mandatory before EventState becomes decision-bearing.

## 2.1 Identity must not be duplicated into dynamic State

Current experimental `WorldStateV01` copies:

```text
actors
action
object
occurred_at
time_context
location
event_type
```

These belong to **Event Identity**.

Final dynamic State must not duplicate them.

Target separation:

```text
Event Identity
-> who / main episode-action / object / coarse time / optional location/type

Current EventState
-> what the Event currently means / where it currently stands
```

## 2.2 History head must not live inside EventState

Current experimental EventState includes:

```text
history_head_revision_id
```

This is conceptually redundant/circular because EventState is stored inside `EventRevision`.

The revision chain is History metadata.

Target:

```text
EventRevision
├─ parent_revision_id
├─ observation identity
├─ transition metadata
└─ event_state snapshot
```

The EventState payload itself does not point back to the history head.

## 2.3 Filter/controller state must not masquerade as WorldState

Experimental fields:

```text
arrival_momentum
momentum_model
last_evidence_key
rho / thresholds
```

are algorithm/filter/controller state.

They are NOT world facts.

Final payload separation:

```text
event_state
├─ world_state
└─ evidence_state

filter_state
└─ algorithm-specific recursive sufficient statistics

policy metadata
└─ algorithm/parameter versions
```

Until an algorithm is selected, filter state remains eval-only.

## 2.4 Knowledge-time ordering must not use crawler arrival order

RAOS must distinguish:

```text
world_time
= when the represented world occurrence/state is about

evidence_time
= when this Source/evidence became public/effective as knowledge

ingest_time
= when RAOS received/processed it
```

Recursive epistemic state evolves by `evidence_time`, not crawler `ingest_time`.

## 2.5 Exactly-once requires durable Observation identity

Experimental immediate replay protection based only on:

```text
last_evidence_key
```

is insufficient.

The same observation may be replayed:

- after other observations;
- after restart;
- during history rebuild;
- through migration/reprocessing.

Production requires a durable observation key with a uniqueness invariant.

---

# 3. Final conceptual data model

The minimal model is:

\[
\boxed{
Event_t = (Identity,\;CurrentState_t,\;History_{\le t})
}
\]

Decision and Attention remain outside Event.

## 3.1 Event Identity

Existing `Event` identity fields remain the canonical coarse identity descriptor:

```text
event.id
actors
action / coarse episode
object
occurred_at / time_context
location?
event_type?
```

Notes:

- missing fields are legal;
- title/summary are renderings, not identity keys;
- `Event.confidence` is legacy compatibility and MUST NOT mean `P(SAME_EVENT)`;
- probabilistic identity remains relational:

\[
P(H_{same}(A,B)=1\mid Evidence)
\]

and belongs to Event Resolver / Representation.

## 3.2 Current EventState — target `event-state-v0.2`

Phase17 target State:

```text
EventStateV02 {
    contract
    event_id

    world_state {
        synopsis
        status
        effective_at
        active_semantic_unit_refs[]
    }

    evidence_state {
        member_source_count
        independent_source_count
        secondary_report_count
        relational_digest
        active_support_digest
    }

    state_digest
}
```

### Why `active_semantic_unit_refs`

This is the key mechanism that keeps Current State small without recreating Claim ontology.

History may contain:

```text
old claim A
later correction B
supporting report C
contradiction D
...
```

Current WorldState references only the semantic units that currently define the projection.

Therefore:

### Enrichment

```text
active refs:
A
-> A + B
```

### Correction

```text
History:
A remains immutable
B arrives later

Current active refs:
A
-> B
```

### Genuine unresolved contradiction

```text
Current active refs:
A + D

synopsis/status:
contested / unresolved
```

### Corroboration

```text
WorldState active refs unchanged

EvidenceState:
independent support increases
```

No permanent Event schema fields named:

```text
correction
supersession
contradiction
enrichment
```

are required.

Those may be internal transition semantics of `Φ`.

## 3.3 History

Canonical History remains existing append-only substrate:

```text
Source
InformationSnapshot
EventEvidenceFrame
EventMembershipAssertion
SourceEdge
RepresentationAuditRun
EventRevision
historical AttentionPlan(EVENT)
```

No new general History table is required.

## 3.4 FilterState

Algorithm-internal sufficient statistics are separate from EventState.

Candidate internal payload:

```text
FilterState {
    contract
    momentum?
    momentum_updated_at?
    algorithm_state_digest?
}
```

This payload is not user/world ontology.

A production FilterState contract is introduced only after the corresponding algorithm passes benchmark gates.

---

# 4. EventObservation V0.1

Do not create a new database table initially.

Define a versioned logical contract derived from existing Source/Frame/Acquisition records:

```text
EventObservationV01 {
    contract
    event_id
    observation_key

    source_id
    source_snapshot_id?
    frame_ids[]
    semantic_input_digests[]

    evidence_time
    ingest_time
    world_time?

    provenance_digest
    audited_semantic_unit_refs[]
}
```

## 4.1 Observation identity

Production `observation_key` must be stable across reprocessing.

Recommended V0.1:

```text
SHA256(
    event_id
    + source_id
    + source content/snapshot identity
    + sorted semantic_input_digests
)
```

The key must change when actual admitted evidence changes.

The key must NOT change merely because:

- runtime PID changes;
- AnalysisRun UUID changes;
- frame row UUID changes while semantic evidence is identical;
- ingestion/replay order changes.

## 4.2 Durable uniqueness

Before production recursive updates:

add a nullable `observation_key` column to `EventRevision` with uniqueness:

```text
UNIQUE(event_id, observation_key)
```

Legacy revisions may keep NULL.

This is the production exactly-once barrier.

`revision_digest` remains revision-content integrity, not observation identity.

---

# 5. Time semantics and late evidence

This is a direct adaptation of mature stream-processing practice.

## 5.1 Three times

### world_time

Time represented by the world fact/event.

### evidence_time

Time the evidence/claim became public/effective as knowledge.

Usually:

```text
Source.published_at
```

fallback:

```text
AcquisitionObservation.observed_at
```

### ingest_time

When RAOS processed it:

```text
Source.ingested_at / InformationSnapshot.captured_at
```

## 5.2 Recursive ordering

Event knowledge evolution uses:

```text
ORDER BY
evidence_time,
observation_key
```

not ingest time.

## 5.3 Late-arriving evidence

For Phase17 scale, choose correctness over distributed complexity.

If:

```text
new observation evidence_time >= current state head evidence_time
```

apply incrementally.

If:

```text
late observation evidence_time < current state head evidence_time
```

then:

```text
append immutable observation evidence
-> rebuild/replay this Event from the nearest valid prior snapshot
   (full per-Event replay is acceptable for V0.1)
-> produce deterministic new head projection
```

Do NOT simply apply late evidence as though it occurred "now".

Future distributed scaling may map this to Flink event-time/watermark semantics without changing the RAOS contract.

---

# 6. Recursive filter architecture

The production form remains:

\[
\Delta_t=\Phi(S_t,e_{t+1})
\]

\[
S_{t+1}=R(S_t,\Delta_t)
\]

## 6.1 `Φ / Decide` — Semantic Relation + Minimal State Delta

`Φ` may use an LLM, but it no longer rewrites the whole next EventState.

Input:

```text
Event Identity
Previous canonical current state
Previous active audited semantic units
New EventObservation
New audited semantic units
minimal provenance/evidence context
```

`Φ` must NOT read arbitrary full-history prose by default.

The Phase17 contract is the mature Event-Sourcing aggregate split:

```text
Current State + Input
-> Decide
-> Domain Event / State Delta
-> Apply
-> New State
```

RAOS adopts this rather than inventing a second state-transition architecture.

The RAOS-specific research question is deliberately narrow:

> Given new audited semantic evidence relative to the current Event state, what semantic state change, if any, has occurred?

`Φ` returns either no material WorldState delta:

```text
None
```

or one minimal semantic delta:

```text
StateDeltaV01 {
    contract

    kind:
        ADD
        | SUPERSEDE
        | CONTEST

    activate_refs[]
    retire_refs[]

    supersession_pairs[] {
        previous_ref
        new_ref
        reason
    }

    phase_change?
    rationale?
}
```

Interpretation:

```text
redundant / corroborating only
-> None

new compatible current information
-> ADD

explicit correction / replacement
-> SUPERSEDE

unresolved incompatible current assertions
-> CONTEST
```

`retire_refs` under ADD means projection compaction, not that immutable historical evidence became false.

A later different occurrence, demo, example, object, timestamp, or use case is NOT by itself supersession.

Phase17 intentionally does not introduce a larger semantic ontology such as REFINE/STRENGTHEN/WEAKEN/MERGE unless a benchmarked counterexample later proves one is required.

### Support constraint and aliases

Every delta ref must belong to:

```text
previous active refs
UNION
new observation audited refs
```

The LLM may not invent unsupported current-state facts.

Long semantic-unit identifiers are mechanical identifiers, not a reasoning task. A Decide implementation may expose temporary aliases:

```text
P001, P002, ... = previous active support
N001, N002, ... = new observation support
```

The program maps these aliases back to canonical semantic-unit refs before persistence. Aliases never become canonical EventState or History identifiers.

## 6.2 `R / Apply` — Deterministic State Transition Authority

`R` owns canonical state formation.

Responsibilities:

```text
1. validate observation_key / Event identity invariants
2. validate every delta ref
3. validate delta-kind semantics
4. apply activate_refs / retire_refs deterministically
5. apply explicit supersession semantics
6. apply coarse lifecycle phase transition
7. recompute EvidenceState deterministically from:
   Event membership + SourceGraph provenance
8. materialize EventState
9. compute state_digest
10. append EventRevision
11. update non-authoritative read-model rendering
```

`R` is deterministic for the same:

```text
previous canonical state
+ admitted StateDelta
+ evidence prefix
+ reducer/policy version
```

No second LLM repair step sits between Decide and Apply. Invalid deltas fail closed.

## 6.3 Relation-only raw-ref baseline and the minimal RAOS extension

A controlled Event-Sourcing baseline was evaluated with StateDelta operating directly on raw `active_semantic_unit_refs`.

On the frozen Jev prefix (8 observations / 79 Event-Gold semantic units), the relation classifier was semantically clean but produced:

```text
ADD x 8
retire_refs = [] throughout
active refs = 79 / history refs = 79
```

This falsifies the hypothesis that raw evidence refs alone are a sufficient Aggregate State representation.

The reason is structural rather than a prompt bug:

> many historical evidence statements can remain true simultaneously, while the Aggregate State must still summarize them into a smaller set of derived current facts.

This is exactly the distinction Event Sourcing makes between immutable domain events and derived Aggregate State.

The minimal RAOS-specific extension to evaluate next is therefore:

```text
CurrentFactV01 {
    fact_id
    text
    support_refs[]
}
```

with StateDelta operating on current facts rather than directly treating every evidence ref as one state variable.

The intended invariant is:

```text
History:
all admitted observations / audited semantic units / admitted deltas

Current semantic state:
small set of derived current facts

Grounding:
each current fact -> audited support refs
```

No fixed fact-count cap, salience weighting, large Claim ontology, or threshold model is introduced at this stage.

This CurrentFact layer is an experimental Phase17.3 candidate until it passes the frozen Jev longitudinal gate.

## 6.4 `synopsis` is a read-model rendering, not transition authority

`WorldStateV02.synopsis` remains temporarily for schema compatibility and human/cognition-facing rendering.

Its role is explicitly downgraded:

```text
Canonical transition authority:
active semantic state/support
+ lifecycle/status
+ effective time
+ EvidenceState

Read-model rendering:
synopsis
```

Decide must not rewrite the next state by treating synopsis as the canonical object.

For Phase17.3, no database migration is required solely to remove the existing synopsis field.

## 6.4 Do not let Event.attributes become the hidden state engine

After production recursive filtering is enabled:

```text
Event.attributes["source_descriptions"]
```

and similar legacy aggregation fields lose decision authority.

They may remain compatibility/history metadata temporarily.

Current EventState becomes the canonical decision-bearing Representation projection.

---

# 7. EventRevision V2 — persist Observation and admitted StateDelta

Phase17 production revision payload should evolve toward:

```text
EventRevision {
    event_id
    parent_revision_id
    observation_key

    revision_payload {
        contract: event-revision-v2

        observation {
            evidence_time
            ingest_time
            source_id
            semantic_input_digests
            provenance_digest
        }

        transition {
            decide_contract
            reducer_contract

            state_delta? {
                contract: event-state-delta-v0.1
                kind
                activate_refs[]
                retire_refs[]
                supersession_pairs[]
                phase_change?
                rationale?
            }
        }

        event_state {
            contract: event-state-v0.2
            world_state
            evidence_state
            state_digest
        }

        filter_state? {
            contract
            ...
        }
    }
}
```

If Decide returns no material WorldState delta, the Observation still remains in immutable evidence/history and EvidenceState may still advance.

A material WorldState event is not fabricated merely to record that an Observation arrived.

Revision-chain authority remains structural:

```text
unique unreferenced revision = head
multiple heads = fail closed
```

No timestamp-based head guessing.

---

# 8. Replay contract

Replay is a first-class Event-Sourcing correctness mechanism.

The canonical replay path MUST NOT re-call the stochastic LLM Decide function.

Online admission:

```text
Observation
+
Current State
-> Decide / Φ
-> admitted persisted StateDelta
-> Apply / R
-> EventState
```

Deterministic rebuild:

```text
persisted admitted StateDelta stream
+ deterministic evidence-prefix reconstruction
-> Apply / R only
-> rebuilt EventState
```

Define:

```text
rebuild_event_state(event_id, as_of_evidence_time=None)
```

Algorithm:

```text
load admitted Event revisions / deltas
dedupe observation identity
order by evidence_time + observation_key
start from empty/nearest valid snapshot
apply persisted admitted deltas through frozen reducer/policy versions
recompute deterministic EvidenceState
return rebuilt state + state_digest
```

Production invariant:

```text
online canonical state_digest
==
replayed canonical state_digest
```

for the same admitted delta stream, evidence prefix, and policy versions.

If not equal:

```text
fail validation
do not silently overwrite canonical state
```

Re-calling Decide over the same observations is a model reproducibility experiment, not Event-Sourcing replay correctness.

---

# 9. Evidence accumulation

Accumulation is adopted; exact innovation remains research.

Generic filter primitive:

\[
M_{t+1}
=
\rho^{\Delta t}M_t
+
I_{t+1}
\]

## 9.1 Important separation

```text
raw Source count
!=
information innovation
```

Candidate innovation estimators are evaluated later.

No weights are canonical until benchmarked.

## 9.2 Momentum is observational state, not truth probability

Momentum may describe:

```text
arrival intensity
cross-source activity
persistent external attention
```

It must not be interpreted as:

```text
truth confidence
P(SAME_EVENT)
technical correctness
```

## 9.3 Current Jev raw-count trace

The frozen:

```text
3 -> 8 -> 15 -> 8 -> 10 items/day
```

is only an observed-arrival baseline.

It may be used to validate leaky dynamics but not to fit Attention directly.

---

# 10. Decision integration

Production Decision should consume **Current EventState**, not Latest Source and not Full History Bag.

Target view:

```text
EventDecisionView {
    identity
    world_state.synopsis
    world_state.status
    evidence_state
    hydrated current active semantic units
    support refs
}
```

## 10.1 Reuse existing cognition

Do NOT create a second cognition engine.

Build an adapter:

```text
EventState
-> current active semantic units
-> existing frozen ExtractionResult / ResearchAligned provider
```

The existing Phase10/ResearchAligned cognition remains `F`.

## 10.2 Full-history adapter status

Current `event_cognition_input.py` full-history aggregation remains:

```text
research / negative baseline
```

It is NOT the target production Decision input.

---

# 11. Attention hysteresis

Hysteresis is adopted as architecture.

However Phase10 is cardinal-free; do not invent a total scalar score merely to obtain a Schmitt trigger.

## 11.1 Production-first candidate: ordinal hysteresis

Use the existing ordinal Attention states:

```text
DROP < AWARE < WATCH < ENGAGE
```

Candidate semantics:

```text
upward transition
-> may occur when current base EventDecision moves to a higher state

same state
-> hold

single downward fluctuation
-> hold current Attention

sustained lower state / elapsed dwell / reduced momentum
-> allow downgrade
```

Exact persistence/dwell rules are benchmark parameters.

## 11.2 Numeric Schmitt trigger remains eval primitive

Current normalized-signal hysteresis code is useful for simulation.

Do not wire it into production until a defensible continuous signal exists.

---

# 12. Jev benchmark contract

Jev is the first longitudinal benchmark, not the only future one.

Four layers remain distinct.

## 12.1 Observed World Trace

Frozen RAOS sample:

```text
44 deduplicated ExternalInformationItems
2026-09-16 .. 2026-09-20
daily arrivals:
3 -> 8 -> 15 -> 8 -> 10
```

This is not global-population attention truth.

## 12.2 Event Gold

```text
t0/t1/t2/t3
-> SAME coarse Event
```

Current real-model Event Resolver passes.

## 12.3 Human Gold

Profile scoped:

```text
profile=user-primary-v0.1
subjective=true

AWARE
-> WATCH
-> WATCH
-> ENGAGE
```

This is not a universal normative trajectory.

Before using it for strict algorithm comparison, freeze a benchmark Kernel/profile reference:

```text
kernel_snapshot_ref / kernel_digest
```

All algorithms must use the same frozen profile.

Do not retune the profile after observing algorithm outputs.

## 12.4 Algorithm output

Every candidate algorithm replays the same frozen trace.

No fixture rewriting after results.

---

# 13. Evaluation metrics

Phase17 does not use a single benchmark score initially.

Report orthogonal metrics.

## Representation / filter correctness

```text
Event identity correctness
state replay determinism
state digest equality
observation idempotence
late-arrival correctness
order robustness
state compactness
support-grounding validity
revision-chain integrity
```

## Evidence correctness

```text
repost/non-independent evidence inflation
independent corroboration handling
redundant evidence behavior
momentum boundedness/decay
```

## Attention dynamics

```text
profile-scoped Human Gold agreement
transition timing
number of Attention transitions
chatter count
false escalation from redundant/repost volume
failure to resurface on material state change
```

## Interpretability

```text
can current state explain why it changed?
can support refs recover the evidence?
can replay reconstruct the same state?
```

---

# 14. Baselines and candidate algorithms

The architecture is no longer under ablation.

## Negative/reference baselines

### A — Latest Source

```text
Decision = F(latest Source)
```

Known weakness: loses cumulative state.

### B — Full History Bag

```text
Decision = F(all historical evidence)
```

Known weakness: obsolete/corrected evidence remains concurrently active.

These remain benchmark baselines only.

## Mainline architecture

```text
Event Sourcing
+
Recursive Event State Filter
+
Hysteretic Attention
```

Ablate implementation details inside this architecture.

### Candidate Φ0

LLM proposes next small WorldState from:

```text
previous WorldState
+ one new EventObservation
```

with support-constrained active refs.

### Candidate R0

Deterministic reducer described in Section 6.2.

### Candidate innovation estimators

To be preregistered separately before testing Human Gold.

### Candidate Attention controllers

```text
H0 = no hysteresis reference
H1 = ordinal persistence/dwell hysteresis
H2 = continuous Schmitt trigger only if a calibrated continuous signal exists
```

---

# 15. Implementation stages

## Phase17.0 — Contract cleanup

Status: **COMPLETE — 2026-09-21**

Tasks:

1. introduce `event-state-v0.2`;
2. remove Identity duplication from WorldState;
3. remove history-head pointer from EventState;
4. separate FilterState from EventState;
5. define `EventObservationV01`;
6. define three-time semantics;
7. freeze observation-key algorithm;
8. preregister schema change for durable exactly-once.

Gate:

```text
contract tests pass
no production Decision/Attention behavior changes
```

## Phase17.1 — Durable observation + replay substrate

Status: **COMPLETE — 2026-09-21 / CANONICAL SCHEMA 0018 LIVE**

Tasks:

1. add `EventRevision.observation_key` nullable column;
2. unique `(event_id, observation_key)`;
3. migration + fresh schema zero drift;
4. build observation materializer from existing Source/Frame data;
5. build deterministic per-Event replay;
6. add late-arrival replay behavior;
7. verify deterministic durable-observation ordering/replay substrate.

Gate:

```text
exactly once at observation identity layer
deterministic evidence-time observation replay
late evidence detectable/reorderable
no mixed writer rollout
```

`online state_digest == replay state_digest` is intentionally deferred to Phase17.2, because semantic state replay is not meaningful until a frozen `Phi/R` reducer exists. Phase17.1 must not invent a fake semantic reducer merely to satisfy a gate.

## Phase17.2 — Φ/R semantic state update

Status: **CONTROLLED GATE PASSED — 2026-09-21 / EVAL-ONLY**

Tasks:

1. implement support-constrained `Phi V0.1`;
2. implement deterministic `R V0.1`;
3. controlled fixtures:
   - no material change
   - enrichment
   - correction/replacement
   - unresolved contradiction
   - corroboration
4. verify history conservation;
5. verify active semantic refs;
6. verify no unsupported current-state facts.

Gate:

```text
all controlled state-transition fixtures pass
replay state_digest equals online state_digest
state remains compact
```

## Phase17.3 — Longitudinal Event-state replay

Status: **ACTIVE — LONGITUDINAL REPLAY RUNNING / CURRENT-STATE REPRESENTATION RESEARCH ACTIVE**

Historical-data readiness finding:

```text
Jev frozen World Trace: 44 items
with Snapshot/Source:   44/44
with Event membership:  43/44
with any Event frame:   27/44
with current audited semantic units: 2/44
```

The 44-item World Trace therefore must NOT be replayed by pretending old title/frame summaries are current audited semantic evidence.

Phase17.3 uses two eval-only evidence preparation steps:

```text
frozen Source versions
-> current Sensor + Auditor semantic hydration
-> benchmark Event-Gold semantic projection
-> longitudinal EventState replay
```

Semantic hydration result after bounded same-prompt repair:

```text
44/44 Sources hydrated successfully
352 audited semantic units
0 failed
0 no-source
```

The benchmark Event-Gold projector exists because the Jev fixture has already frozen one coarse Event identity while the historical/current bridge does not always emit event-level admitted units for every Source. The projector:

- consumes only already-audited semantic units;
- classifies every supplied unit_id exactly once as IN_EVENT or OUT_OF_EVENT;
- may select only supplied unit_ids;
- may not create, rewrite, or infer a new semantic fact;
- uses the frozen Jev Event Gold and therefore is **eval-only benchmark projection**;
- has no production Event Resolver, topology, membership, or state authority.

A Source with zero projected Event units is legal. It contributes no new WorldState semantic content; during replay it may only produce deterministic `NO_MATERIAL_CHANGE` at the WorldState layer while still being available to EvidenceState/provenance accounting.

### 2026-09-22 representation finding

The raw active-ref representation is rejected as the canonical Phase17.3 Current State because the Jev n8 baseline degenerated into a full History Bag:

```text
History refs = 79
Current refs = 79
```

The derived `CurrentFact` candidate materially improved semantic compactness and enabled explicit merge, correction, contest, materiality filtering, and deterministic persisted-delta replay. At n20 it produced 24 live CurrentFacts over 191 historical semantic refs. It is therefore an effective intermediate representation, but Phase17.3 is **not yet PASS** because the free fact set remains finer-grained than the desired materialized Event state.

Commercial keyed-materialization patterns (Kafka compacted logs / KTable, Flink upsert tables, Materialize UPSERT) suggest the next candidate:

```text
Fine Evidence / immutable History
        ↓
ResolveKey(EventIdentity, CurrentSlots, NewEvidence)
        ↓
Keyed Semantic Materialized State
        ↓
stable slot_id → current value + audited support
```

Eval-only semantic-key experiments found:

```text
n8  CurrentFacts: 10 → 6 semantic slots + 1 peripheral drop
n20 CurrentFacts: 24 → approximately 9 slots when rediscovered freely

Temporal reuse test:
frozen n8 slots = 6
reused at n20 = 6 / 6
new slots created = 1
final keyed slots = 7
```

Therefore the active Phase17.3 candidate is now **Keyed Semantic Materialized State**, documented in `273_PHASE17_KEYED_SEMANTIC_MATERIALIZED_STATE_RESEARCH.md`.

Key principle:

```text
Do not coarsen audited Evidence.
Coarsen Current State by persistent semantic key.
```

No global ontology, fixed slot list, or hard slot-count cap is authorized. The RAOS-specific research surface is reduced to stable semantic key resolution; once a key is known, current-state maintenance should reuse ordinary upsert/materialized-view semantics.

Tasks:

0. hydrate the frozen Jev trace eval-only with current Sensor + Auditor; freeze repaired artifact without overwriting the original failed artifact;
1. project each Source's audited semantic units onto the frozen benchmark Event using the unit-id-only Event-Gold projector;
2. replay Jev observed trace in evidence-time order;
3. inspect State trajectory without Human Gold tuning;
4. compare Latest Source / Full History Bag / Recursive State;
5. add additional longitudinal benchmark samples as they become available;
6. freeze first benchmark set before parameter tuning.

Gate:

```text
recursive state qualitatively coherent
no monotonic history-bag failure
no replay/order failure
```

### Phase17.3-KS — Key-Space research subphases

Naming reconciliation (2026-09-23):

The semantic-key research opened while Phase17.3 keyed materialization was still active. To avoid collision with the canonical roadmap phases below, this work is formally scoped as an internal Phase17.3 Key-Space line:

```text
Phase17.3-KS-A  theory / literature mapping
Phase17.3-KS-B  semantic resolver contract
Phase17.3-KS-C  controlled benchmark / baseline / Jev integration
Phase17.3-KS-D  semantic coordinate candidate retrieval and refinement
Phase17.3-KS-E  candidate adjudication / address-locked REUSE-CREATE (ACTIVE — research gate passed; production default not switched)
Phase17.3-KS-F  learned semantic-address gate / LLM distillation (ACTIVE — data/baseline stage)
```

This naming does **not** redefine the canonical roadmap:

```text
Phase17.4 = Information innovation + momentum
Phase17.5 = EventState -> frozen cognition
```

Key-Space experiments remain subordinate to the Phase17.3 gate until keyed semantic Current State is accepted. Earlier temporary experiment labels using Phase17.4/17.5 were relabeled before being admitted as tracked project state.

KS-E checkpoint (2026-09-24):

- KS-D candidate retrieval is retained as recall-oriented search, not semantic authority.
- Candidate-only constrained joint KeyBy was experimentally rejected as the final architecture.
- Pairwise Direct-Answer v0.9 reached 16/16 strict cases and 32/32 repeated judgments on the current Jev boundary set.
- A five-round single-judgment stress test produced 79/80 correct decisions; therefore pairwise_repeats=1 is not admitted for key-space mutation.
- A matched five-round two-judgment consensus stress test produced 80/80 correct consensus decisions and 16/16 fully stable cases.
- Address-Locked synthesis v0.6 achieved 4/4 reviewed semantic-gold agreement on Jev ordinals 5–8, with 11 CREATE-group cross-checks and all 4 observations passing semantic group validation.
- Latest broad targeted regression after Address-Locked integration: 130 passed, 0 failed.
- Production semantic-key resolution is **not** switched to the new path yet. The next gate is breadth: more Events/domains, larger same-family key-spaces, raw-observation end-to-end replay, and durable coordinate persistence/migration design.

KS-F checkpoint (2026-09-24):

- Cost problem is now treated as an architectural constraint: the current 4-observation Address-Locked Jev window expands to 36 semantic pair checks, 72 pairwise LLM calls at repeats=2, plus 4 synthesis calls.
- A versioned Direct-Answer learning-data contract and HUMAN_REVIEWED Jev dataset v0.1 were created: 16 examples, balanced 8 DIRECT / 8 NOT_DIRECT, one Event, status DEVELOPMENT_ONLY.
- LLM-consensus teacher pool v0.2 contains 31 unique pairs. Fourteen overlap human gold and agree 14/14; 17 are teacher-only, including 3 DIRECT positives from CREATE-group cross-validation.
- Generic Qwen3-Embedding-0.6B cosine is rejected as a final Direct-Answer gate. Retrieval-protocol cosine reached AUROC 0.8438 but only 0.75 leave-one-out accuracy on the 16 human-reviewed cases.
- Leave-one-out selective thresholding still produced one false DIRECT and one false NOT_DIRECT at 56.25% coverage.
- A threshold fitted only on 17 non-overlapping teacher pairs transferred poorly to human gold: 56.25% accuracy, 6 false DIRECT, 1 false NOT_DIRECT.
- Therefore further scalar-cosine tuning is stopped. The next learned-model candidate is a small pair cross-encoder or Direct-Answer-specific learned metric model with explicit abstention.
- A human review pack v0.1 now contains 17 teacher-only/boundary pairs, including 6 high-priority cases, to support multi-event HUMAN_REVIEWED dataset growth.
- Cost model shows that 90% safe local-student coverage would reduce expected LLM calls on the current window from 76 to about 11.2 without cache; 95% coverage to about 7.6. With 25% cache hits and 95% student coverage, expected calls are about 6.7.
- Neural training is intentionally deferred until multi-event gold exists. Random pair split on the single Jev Event is not accepted as a generalization claim.

Primary result documents:

- `docs/phase17_3_ks_d/283_PHASE17_3_KS_D_SEMANTIC_COORDINATE_RETRIEVAL_IMPLEMENTATION_RESULT.md`
- `docs/phase17_3_ks_e/284_PHASE17_3_KS_E_CANDIDATE_ADJUDICATION_PREREGISTRATION.md`
- `docs/phase17_3_ks_e/286_PHASE17_3_KS_E_PAIRWISE_GUARDED_ADJUDICATION_RESULT.md`
- `docs/phase17_3_ks_e/287_PHASE17_3_KS_E_ADDRESS_LOCKED_SYNTHESIS_RESULT.md`
- `docs/phase17_3_ks_f/288_PHASE17_3_KS_F_LEARNED_SEMANTIC_ADDRESS_GATE_PREREGISTRATION.md`
- `docs/phase17_3_ks_f/289_PHASE17_3_KS_F_DATA_AND_EMBEDDING_BASELINE_RESULT.md`
- `docs/phase17_3_ks_f/290_PHASE17_3_KS_F_PROGRESS_CHECKPOINT_20260924.md`

## Phase17.4 — Information innovation + momentum

Tasks:

1. preregister innovation estimator candidates;
2. compare independence-aware vs raw-count baselines;
3. evaluate decay/retention sensitivity;
4. keep truth confidence separate from momentum;
5. freeze selected estimator/version if evidence supports one.

Gate:

```text
redundant/repost volume does not create uncontrolled escalation
momentum decays
material new evidence produces larger innovation than duplicate evidence
```

## Phase17.5 — EventState -> frozen cognition

Tasks:

1. implement `EventStateDecisionView`;
2. hydrate only active semantic-unit refs;
3. preserve Support Binding / Grounding;
4. reuse current ResearchAligned cognition;
5. compare EventState Decision against negative baselines.

Gate:

```text
no second cognition stack
correction case no longer exposes obsolete + corrected claims as concurrent current facts
support-grounding remains intact
```

## Phase17.6 — Hysteretic Attention ablation

Tasks:

1. freeze benchmark Kernel/profile digest;
2. run H0 no-hysteresis;
3. run H1 ordinal hysteresis;
4. optionally H2 continuous controller only with defensible signal;
5. measure chatter and transition timing;
6. compare with profile-scoped Human Gold.

Gate:

```text
reduced chatter
no suppression of real escalation
no tuning fixture after seeing output
```

## Phase17.7 — Production preregistration and canonical rollout

Only after prior gates.

Tasks:

1. write production preregistration;
2. freeze:
   - EventState contract
   - Observation contract
   - Phi version
   - Reducer version
   - innovation/filter version
   - Attention hysteresis version
3. include all versions in AnalysisRun execution identity;
4. quiesce canonical writers;
5. migrate schema if needed;
6. run replay/migration;
7. start one canonical runtime;
8. verify READY/ATTESTED/schema head;
9. validate natural dogfood Event revisions;
10. validate current Attention remains Event-centric.

Rollout order:

```text
stop writers
-> backup
-> migration/replay
-> validation
-> start new runtime
```

No dual canonical strategy may write simultaneously.

## Phase17.8 — Natural longitudinal dogfood

Validate on real incoming Event streams.

Write a result document before closing Phase17.

---

# 16. Rollback strategy

Every production algorithm is versioned.

If selected recursive Decision/Attention behavior is invalid:

```text
1. stop canonical writers
2. disable new decision strategy
3. preserve append-only EventRevision/Observation history
4. restore prior Event Decision strategy
5. rebuild materialized state from history if necessary
6. restart one canonical runtime
```

Never delete history to rollback policy.

---

# 17. Current code status vs target

## Already implemented and retained

```text
Event Processor V1
Event-centric current Attention identity
EventRevision append-only chain
unique chain-head validation
event-state-v0.1 experimental snapshot
leaky-integrator primitive
hysteresis primitive
Jev World Trace fixture
Jev Event identity gate
profile-scoped Human Gold
full-history Event cognition negative experiment
```

## Experimental / not final production contract

```text
WorldStateV01 identity-field duplication
history_head_revision_id in EventState
arrival_momentum inside EventState
last_evidence_key immediate-only idempotence
normalized scalar hysteresis
full-history event_cognition_input
```

## Not implemented yet

```text
EventObservationV01
durable observation_key
event-state-v0.2
evidence-time replay
late-arrival rebuild
Phi V0.1
R V0.1 production reducer
active semantic-unit current-state refs
EventStateDecisionView
ordinal hysteresis production candidate
```

---

# 18. Known unrelated residuals

Current backend baseline:

```text
947 passed
63 skipped
1 known failure
```

Known residual:

```text
Case-K
expected PREEMPT
actual PRIORITY
```

Do not attribute this historical residual to Phase17 unless new evidence shows a causal link.

---

# 19. Definition of Phase17 completion

Phase17 is complete only when all are true:

```text
[ ] EventState V0.2 minimal orthogonal contract frozen
[ ] durable EventObservation exactly-once identity
[ ] deterministic evidence-time replay
[ ] late-evidence behavior validated
[ ] Phi/R controlled state transitions pass
[ ] current active semantic-unit refs grounded
[ ] innovation/momentum policy selected or explicitly deferred
[ ] EventState -> existing cognition wired
[ ] hysteretic Attention selected and validated
[ ] Jev + additional frozen longitudinal benchmarks run
[ ] profile-scoped Human Gold handled correctly
[ ] full backend regression clean except known residuals
[ ] canonical rollout READY/ATTESTED
[ ] natural dogfood validation complete
[ ] final result document written
[ ] roadmap/canonical docs synchronized
```

---

# 20. Change log

## V1.0 — 2026-09-21

Initial implementation plan after architecture review.

Key review decisions:

1. architecture adopts Event Sourcing + keyed state + recursive state estimation + hysteresis directly;
2. Identity removed from target dynamic State;
3. History-head pointer removed from target State;
4. FilterState separated from EventState;
5. three-time semantics introduced;
6. durable Observation identity required;
7. active semantic-unit refs chosen as the minimal bridge between immutable history and current world projection;
8. EventState Decision must reuse existing cognition;
9. ordinal hysteresis preferred for first production candidate because Phase10 is cardinal-free;
10. Jev Human Gold remains profile-scoped, not universal.
