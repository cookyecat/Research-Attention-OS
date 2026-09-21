# Phase 17 — Dynamic Event Engine Phase17.0–17.2 Result V0.1

Status: **PHASE17.0 COMPLETE / PHASE17.1 COMPLETE / PHASE17.2 CONTROLLED GATE PASSED**  
Date: 2026-09-21

Primary plan:

- `271_PHASE17_DYNAMIC_EVENT_ENGINE_IMPLEMENTATION_PLAN.md`

## 1. Contract cleanup

Implemented:

```text
event-state-v0.2
event-filter-state-v0.1
event-observation-v0.1
```

Target separation is now explicit:

```text
Event Identity
!= Dynamic EventState

EventState
= WorldState + EvidenceState

FilterState
!= EventState

History head
!= EventState
```

WorldState V0.2 contains only:

```text
synopsis
status
effective_at
active_semantic_unit_refs
```

EvidenceState V0.2 contains only structural support:

```text
member_source_count
independent_source_count
secondary_report_count
relational_digest
active_support_digest
```

## 2. Durable EventObservation / exactly-once

Observation V0.1 distinguishes:

```text
world_time
evidence_time
ingest_time
```

Stable observation identity uses:

```text
event_id
source_id
source content/snapshot identity
sorted semantic_input_digests
```

It excludes AnalysisRun UUID, frame-row UUID, process identity and replay order.

Alembic `0018_event_revision_observation_key` adds:

```text
EventRevision.observation_key nullable
UNIQUE(event_id, observation_key)
```

Canonical rollout:

```text
stop writers
backup DB
0017 -> 0018
schema drift = 0
restart one canonical service set
READY / ATTESTED
```

Backup:

```text
backups/phase17/raos_before_0018_20260921T055956.db
```

No natural post-0018 EventRevision had arrived at the first validation cutoff, so natural V2 revision observation remains pending.

## 3. Evidence-time replay

Implemented `event-observation-replay-v0.1`.

Replay ordering is:

```text
evidence_time
observation_key
```

not ingest time or append order.

A persisted-revision control appended later evidence before earlier evidence. Replay correctly restored earlier -> later.

Identical observation keys are exactly-once during replay.

The plan was corrected so semantic state-digest equality is a Phase17.2 gate, not a Phase17.1 gate. That comparison is meaningless before a semantic reducer exists.

## 4. Phi / R V0.1

Implemented:

```text
event-state-transition-estimator-v0.1
event-state-reducer-v0.1
```

Phi proposes a small supported WorldState.

R retains canonical authority and validates:

```text
Event identity
allowed semantic refs
transition invariants
authorized source prefix
EvidenceState recomputation
state digest
```

Transition metadata:

```text
INITIALIZE
NO_MATERIAL_CHANGE
ENRICH
REPLACE_CURRENT
CONTEST
```

These are algorithm transition labels, not Event ontology fields.

## 5. Transition semantics

```text
INITIALIZE
-> only new admitted refs may become active

NO_MATERIAL_CHANGE
-> WorldState must remain exactly unchanged
-> EvidenceState may still strengthen through corroboration

ENRICH
-> previous active refs remain
-> at least one new ref becomes active

REPLACE_CURRENT
-> current active refs materially change
-> at least one new ref becomes active
-> old evidence stays immutable History

CONTEST
-> at least one prior ref and one new ref remain active
```

A schema-valid model proposal with an invented semantic ref is rejected by R.

## 6. Future-leakage bug found and fixed

Initial R recomputed EvidenceState from all current Event members.

That would leak future sources into historical replay.

Repair:

```text
R requires an explicit replay/online supporting-source prefix.
EvidenceState is computed only from that prefix.
```

Controlled result with A/B/C already present in DB:

```text
replay t0 -> 1 source
replay t1 -> 2 sources
replay t2 -> 3 sources
```

Two identical replays produced identical state digests.

## 7. Real-model Phi probe

Configured real model was used only for Phi proposals. R remained deterministic authority.

A provider-compatibility issue was found first: DeepSeek JSON mode requires an explicit JSON instruction. A second contract issue showed the outer proposal fields needed to be enumerated. These were output-contract fixes; cases and expected transition labels were not changed.

Final result:

```text
INITIALIZE          5/5 expected-kind family: PASS
NO_MATERIAL_CHANGE  PASS
ENRICH              PASS
REPLACE_CURRENT     PASS
CONTEST             PASS

kind matches      = 5/5
reducer accepted  = 5/5
```

Artifact:

```text
eval/live/results/phase17_state_transition_phi_real_model_v0_1/
phase17_state_transition_phi_real_model_v0.1_20260920T220931Z.json
```

## 8. Jev trace readiness

Frozen Jev World Trace:

```text
44 deduplicated items
```

Read-only census:

```text
Snapshot/Source coverage              44/44
Event membership                      43/44
any EventEvidenceFrame                27/44
current audited semantic units         2/44
audited units total                    14
```

Historical AnalysisRun check confirms this is real old-contract missingness:

```text
45 completed bridge runs
43 with zero admitted_semantic_units
2 with admitted_semantic_units
1 Source with no run
```

Therefore legacy titles/frame summaries must NOT be treated as audited EventState evidence.

Phase17.3 begins with eval-only semantic hydration using the current Sensor + Auditor over the frozen trace. It must not rewrite canonical historical Event topology or Attention.

## 9. Current phase status

```text
Phase17.0  COMPLETE
Phase17.1  COMPLETE / schema 0018 live
Phase17.2  CONTROLLED GATE PASSED / eval-only
Phase17.3  ACTIVE / semantic hydration required
```
