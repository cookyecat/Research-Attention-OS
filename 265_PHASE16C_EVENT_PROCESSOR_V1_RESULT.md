# Phase 16C — Event Processor V1 Result

Status: **COMPLETE / CANONICAL PRODUCTION ENABLED**  
Date: 2026-09-21

Reference: `264_PHASE16C_EVENT_PROCESSOR_V1_PREREGISTRATION.md`.

## 1. Executive result

Phase16C replaces the transitional source-local Event bootstrap with a real coarse-grained Event Processor in the canonical pipeline.

The production path is now:

```text
Source
-> Sensor / Semantic Auditor
-> audited semantic evidence
-> Event Processor V1
-> EventCandidate
-> candidate Event retrieval
-> SAME_EVENT / DIFFERENT_EVENT / UNCERTAIN
-> existing Event update or new Event creation
-> AttentionPlan(EVENT)
```

The primary architectural target is now operational:

```text
N Sources
-> 1 coherent World Event representation
-> 1 current Event Decision
-> 1 Attention identity
-> representative Source reading path
```

This is not claim clustering. Event V1 uses a coarse editorial episode/story granularity.

## 2. Event V1 contract implemented

The Event row now supports:

```text
id
title
event_type
actors
action
object
occurred_at
time_context
location
summary
current_state
attributes
confidence
status
```

Fields may be incomplete on first observation and may be enriched by later Sources.

Claims, Observations, benchmark values, quotations and atomic semantic units remain evidence inside the Event. They do not define Event multiplicity.

The materialized Event row is the current RAOS representation. Event knowledge history is append-only through EventRevision.

## 3. V1 granularity frozen

The operational test is:

> Would a competent editor normally continue one evolving story/case/research story, or open a genuinely separate story/case?

Therefore, for V1:

```text
one normal Source
-> one primary EventCandidate
```

Examples that may remain one Event:

- launch preparation -> launch -> immediate recovery/result for one launch episode;
- one paper publication plus method, benchmark results and later discussion of that same paper;
- multiple independent reports of the same model/product release.

A multi-news digest Source is deferred to V2. Phase16B's 0..N frame-conditioned work remains valid research input, but it is no longer an immediate blocker for Event V1.

## 4. Event resolution semantics

Canonical resolver:

```text
llm-coarse-event-resolver-v1
```

Resolution effects:

```text
SAME_EVENT
-> attach new Source to existing Event
-> cross-Source topology commitment
-> append EventRevision
-> update current Event projection

DIFFERENT_EVENT
-> create a new Event
-> source-local initial membership

UNCERTAIN
-> create a separate Event hypothesis
-> never merge
```

SAME_EVENT is a lifecycle-routing decision. It is not inserted as a direct cognition/Attention score.

The older probabilistic RepresentationAuditRun SAME_EVENT response spectrum remains epistemic evidence and is not silently promoted into topology authority.

## 5. Sensor / Auditor boundary preserved

Sensor and Semantic Auditor semantics were not redesigned.

Source extraction now owns semantic evidence only. It no longer creates Event topology as a side effect.

Event creation/join/update is owned by Event Processor V1.

This removes the prior dual-writer ambiguity where extraction could "helpfully" create Event/EventSource topology before the actual Event decision.

## 6. Controlled resolver validation

The preregistered real-model cases were run without post-result prompt or case tuning.

Results:

```text
Case A
Acme launches Nimbus API public beta
+ Reuters independently reports the same launch
-> SAME_EVENT
-> one Event
PASS

Case B
existing Nimbus API launch
+ separate Nimbus university grant program
-> DIFFERENT_EVENT
PASS

Case C
"Nimbus update is underway; more details soon"
without occurrence identity
-> UNCERTAIN
-> no merge
PASS
```

All three fixed case constraints passed.

Artifact:

```text
eval/live/results/phase16c_event_processor_real_model_v0_1/
phase16c_event_processor_real_model_v0.1_20260920T145229Z.json
```

Interpretation is bounded: this validates the mechanism and prompt contract on the fixed cases; it is not a calibrated benchmark of Event identity accuracy.

## 7. Production natural dogfood validation

After canonical rollout and service cleanup, natural acquisition produced three new authoritative completed runs in the first audited window.

```text
completed Event Processor runs: 3
failed runs:                  0
```

Observed resolutions:

```text
1 x DIFFERENT_EVENT
2 x SAME_EVENT
```

For both natural SAME_EVENT cases:

```text
authorized membership Sources = 2
EventSource Sources            = 2
historical Event plans         = 2
canonical current Event plan   = 1
active Event WATCH duplicates  = 0
```

For the natural DIFFERENT_EVENT case:

```text
authorized membership Sources = 1
EventSource Sources            = 1
historical Event plans         = 1
canonical current Event plan   = 1
```

All audited production relations passed.

The canonical serving projection was also checked with the real runtime profile:

```text
current Attention items = 774
non-EVENT current items = 0
```

Live `/kernel/attention`:

```text
API items               = 774
non-EVENT                = 0
Event structure present  = true for all items
```

Thus historical multiple AttentionPlans remain immutable audit history while current projection collapses them by Event identity.

## 8. WATCH lifecycle

Policy-generated WATCH responsibility is now Event-keyed.

For repeated WATCH decisions on the same Event:

```text
same Event
-> reuse one active Event WATCH
-> advance responsibility to latest AttentionPlan
```

Kernel target ids remain explanatory cognition targets; they no longer define WATCH lifecycle identity.

## 9. Analysis identity

Event Processor execution contract is included in AnalysisRun execution identity.

Changing Event Processor resolver/model/contract therefore invalidates stale analysis reuse rather than silently replaying an old Event decision under a new Event policy.

## 10. Schema-authority root-cause repair

Phase16C rollout exposed a deeper migration defect.

### Root cause

Historical `0001_initial.py` dynamically imported current ORM metadata and called:

```python
Base.metadata.create_all(...)
```

Therefore "migration 0001" was not historical. Its meaning changed whenever today's ORM changed.

Application startup also defaulted to `create_all()`, which could silently repair missing schema and mask migration drift.

### Repair

The original 2026-08-26 commit `c57af066` was used to reconstruct the actual initial ORM metadata.

The original schema contained 22 tables.

`0001_initial.py` is now a frozen explicit Alembic DDL snapshot. It no longer imports current models/Base or uses create_all/drop_all.

New migration:

```text
0017_schema_authority_hardening
```

repairs historical structural drift including missing SQLite FKs, nullable contracts, index identity and uniqueness representation.

Validation:

```text
fresh empty DB -> 0001 -> ... -> 0017
structural drift vs current ORM = 0

real dogfood DB clone -> 0017
structural drift vs current ORM = 0
```

Real dogfood migration:

```text
0015
-> 0016_event_processor_v1
-> 0017_schema_authority_hardening
```

Row-count integrity:

```text
business rows before = 39117
business rows after  = 39117
changed table counts = {}
```

Canonical schema authority is now:

```text
Alembic migrations = authority
ORM metadata        = declared application contract
create_all          = ephemeral/test opt-in only
```

Canonical startup refuses `Base.metadata.create_all()` and fails closed if the database Alembic revision is not repository head.

A fresh-schema regression test now requires:

```text
empty DB
-> alembic upgrade head
-> compare head schema with ORM metadata
-> SCHEMA_DRIFT_COUNT == 0
```

Migration files are also statically checked against importing runtime `app.models` / `Base` for dynamic schema mutation.

## 11. SQLite database identity hardening

The configured relative SQLite URL previously depended on process cwd.

That could make:

```text
repo root / raos.db
```

and:

```text
backend / raos.db
```

look like the same configured database while actually being different files.

Relative SQLite database URLs are now normalized to an absolute path anchored at the backend directory.

Backend, Alembic, scripts and launchd therefore resolve one database identity independent of cwd.

## 12. Runtime single-owner hardening

Rollout found an old manual RAOS process set still alive while launchd service mode was starting.

The old backend held port 8000, causing the new launchd backend to repeatedly fail bind while health checks accidentally reached the old process.

The service script now cleans only orphan processes whose cwd belongs to this RAOS repo before start/after stop.

The cleanup removed the old manual backend/acquisition/delivery/frontend processes and launchd now uniquely owns:

```text
backend
acquisition
delivery
frontend
ports 8000 / 3000
```

This prevents manual/service mixed-writer operation from silently reappearing.

## 13. Reconciler retry churn repair

Three historical deferred Sources had no `content_text`.

The reconciler retried them every minute, generating repeated FAILED AnalysisRuns that could never succeed.

The admission rule is now:

```text
deferred snapshot
+ no analyzable Source content
-> cognition_reconcile_eligible = false
-> reconciliation_outcome = skipped_unanalyzable_no_content
-> no pipeline call
```

The three historical snapshots were naturally closed under this rule.

After clean restart:

```text
new FAILED AnalysisRuns from this condition = 0
```

## 14. Production canary lesson

A direct canary ran the real production Source/model/schema path and successfully returned:

```text
event_processor-v1
SAME_EVENT
Attention candidate_type = EVENT
Attention candidate_id   = Event id
```

AttentionPlan count returned to the pre-canary count.

However, one RUNNING AnalysisRun live-identity row survived the outer rollback.

Root cause: AnalysisRun acquisition intentionally uses a nested SAVEPOINT/live identity, and SQLite transaction semantics do not make an arbitrary outer rollback a safe isolation guarantee for this operational row.

That row was explicitly closed as FAILED with a `PRODUCTION_CANARY_ABORTED` provenance note.

Therefore the final production acceptance evidence is the subsequent natural dogfood completed runs, not a claim that direct canonical `run_pipeline()` can be made side-effect-free merely by wrapping it in an outer rollback.

No Event/Attention/WATCH canary topology residue was retained.

## 15. Regression

Final backend regression after Event Processor, schema-authority hardening, SQLite identity normalization, orphan cleanup and reconciler admission:

```text
930 passed
63 skipped
1 failed
```

The only failure remains the pre-existing Case-K residual:

```text
expected urgency = PREEMPT
actual urgency   = PRIORITY
```

No new failure was introduced.

## 16. What Phase16C proves

Phase16C supports the following claims:

1. RAOS can use a coarse editorial Event as the production Attention identity.
2. Multiple independent Sources can be committed to one shared Event under the explicit Event Processor V1 resolver contract.
3. SAME_EVENT has a natural product role as world-update routing rather than a direct cognition score.
4. Current Attention can remain one Event decision while preserving immutable per-analysis historical plans.
5. Sensor/Auditor evidence processing and Event identity commitment can remain separate responsibilities.
6. The canonical database can now be reconstructed from migration history without relying on current ORM side effects.

## 17. What Phase16C does not prove

Phase16C does not establish:

- calibrated `P(SAME_EVENT | E)`;
- general Event Resolver benchmark accuracy;
- multi-event digest Source support;
- a learned stochastic Event process;
- EventState-delta resurfacing rules;
- that every Event V1 identity field is observable in the first Source;
- that EventLineage should enter current decision routing;
- that Representation Auditor response frequencies are topology truth probabilities.

Those remain separate research questions.

## 18. Final status

```text
World Representation: Event-centric
Event creation/join:  Event Processor V1
Attention identity:   Event-centric
Current projection:   one latest decision per Event
Cross-Source merge:   enabled only through explicit coarse Event resolver
UNCERTAIN:             fail-safe no merge
Schema authority:      Alembic
Canonical services:    single launchd-owned runtime
```

Phase16C is closed.
