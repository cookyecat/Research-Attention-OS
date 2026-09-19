# RAOS 50–200 User Local-First Deployment Review V0.1

Status: **ARCHITECTURE REVIEW / PRIVATE BETA PLAN**  
Date: 2026-09-19

## 1. Conclusion

The current RAOS conceptual architecture can serve an initial 50–200 user Private Beta without a microservice rewrite.

Recommended product architecture:

```text
Local-first RAOS
+
optional cloud sync / remote access
+
default 30-day cloud content retention
+
one Canonical Authority Home per workspace
```

The current single-user SQLite runtime should remain a device-local engine. It must not be placed behind shared authentication and treated as multi-user. The main blockers are identity/tenancy, durable jobs, sync semantics, cloud persistence, retention, and Phase 13 authority split-brain prevention—not database scale.

## 2. Current runtime facts

The current deployment contract is intentionally:

```text
scope = SINGLE_USER_DOGFOOD
authenticated_user_identity = false
multi_user_isolation = false
state_ownership_boundary = DEFINED_NOT_TENANTIZED
```

At review time the local dogfood database is approximately:

```text
SQLite DB            110 MB
Sources             1005
ParserRuns           962
SourceEdges          205
Events               524
EventSources         535
AnalysisRuns        1497
AttentionPlans       554
InformationSnapshots 956
```

SQLite WAL, busy timeout, short acquisition transactions and post-commit cognition are appropriate for a single device. The current analysis-job lease is process memory and is not durable across restart, so it is not beta-ready.

## 3. Local-first is structurally compatible with RAOS

RAOS already favors append-oriented state:

```text
immutable Source evidence
append-only ParserRuns / Snapshots
historical AnalysisRuns / AttentionPlans
frozen Representation Snapshots
future EventRevision / EventLineage
```

This makes synchronization substantially easier than ordinary mutable CRUD.

The hard problem is not merging Source rows. It is deciding which runtime is allowed to create authoritative cognition, representation and attention transitions.

## 4. Canonical Authority Home

Each workspace must have exactly one active Canonical Authority Home:

```text
LOCAL_DEVICE
or
CLOUD
```

When LOCAL_DEVICE is canonical, cloud may sync, store an encrypted replica, serve remote reads and accept pending commands, but it must not silently produce competing authoritative cognition/representation/attention.

When CLOUD is canonical, local devices may observe, cache, read and submit work, but the cloud runtime is the authority-bearing execution environment.

Invariant:

```text
one workspace
→ one authority home
→ one authority epoch
→ no split-brain authority
```

Moving authority home is itself a Phase 13 transition.

## 5. Private Beta topology

### Local device

```text
Desktop/local RAOS
├─ SQLite
├─ media/object cache
├─ local search/vector index
├─ optional local model endpoints
├─ sync client
└─ canonical runtime when authority_home=LOCAL_DEVICE
```

For true local-first behavior, use a desktop wrapper or local daemon. A pure browser surface is not a good owner for the existing SQLite + long-running acquisition/cognition worker model.

### Cloud

Keep the first online deployment simple:

```text
Auth / HTTPPS
    ↑
FastAPI modular monolith
    ↑
PostgreSQL
├─ tenant-scoped metadata
├─ append-only sync log
├─ durable jobs
└─ optional vector index
    ↑
Object storage
├─, encrypted Source payloads
├─ PDFs
└─ media/presentation objects
    ↓
bounded worker pool
├─ acquisition
├─ cognition
├─ representation audit
└─ delivery
```

No Kafka, service mesh, distributed vector database or broad microservice split is justified at 50–200 users.

## 6. Tenantization

Every cloud object that is user-owned must carry at least:

```text
user_id
workspace_id
```

This includes Sources, Snapshots, ParserRuns, SourceEdges, Events, Event revisions/assertions, RepresentationAuditRuns, AnalysisRuns, AttentionPlans, Watches, Delivery, Kernel state and sync operations.

Shared external-world artifacts may eventually be physically deduplicated, but access and cognitive state remain workspace-scoped.

Do not expose the current database as a multi-user service before tenant isolation is complete.

## 7. Cloud persistence

Recommended split:

```text
local device → SQLite
cloud service → PostgreSQL
i```

PostgreSQL is preferred for the shared service because of concurrent writers, transactional tenant isolation, durable queues, backups, indexing and future vector support.

Do not use one shared SQLite file for 50–200 users.

## 8. Sync protocol

Do not implement naive bidirectional table replication.

Use an append-oriented operation log:

```text
SyncOperation
├─ op_id
├─ workspace_id
├─ device_id
├─ entity_type / entity_id
├─ operation_type
├─ payload or payload_digest
├─ authority_epoch
├─ execution_identity
├─ created_at
└─ server_sequence
```

Immutable evidence usually converges by set union of globally unique IDs.

Authority-bearing representation state never uses last-writer-wins. It is accepted only from the active authority epoch.

Event merge/split/correction uses EventRevision/EventLineage rather than overwrite conflict resolution.

## 9. 30-day cloud retention

Recommended product modes: 

### Local only

No cloud content. No remote browser history unless the local device is reachable.

### 30-day Sync Cache — Default

```text
local DB = durable primary
cloud content payload = rolling 30 days
remote access = retained window
minimal sync checkpoints/tombstones = retained only as long as needed
```

### Full cloud — Opt in

Durable online copy for users who want it.

Content retention and minimal synchronization metadata should be distinguished explicitly. A 30-day content promise should not be confused with the minimum non-content metadata needed to prevent re-upload or replay errors.

## 10. Security

Minimum beta requirements:

```text
TLS
per-workspace authorization
encryption at rest
object-store encryption
device registration/revocation
connector secret isolation
local OS keychain for device secrets
auditable deletion
```

For stronger privacy, cloud Source/file payloads can be client-side encrypted. This is most compatible with LOCAL_DEVICE authority; cloud cognition over encrypted content requires explicit decryption/trusted execution and should not happen implicitly.

## 11. Durable jobs

The current in-memory analysis job registry must be replaced before beta.

Use a durable Job table with transactional leasing:

```text
Job
├─ id
├─ workspace_id
├─ job_type
├─ entity_id
├─ identity_key
├─ status
├─ lease_owner
├─, lease_expires_at
├─ attempts
├─ execution_context
┚─ timestamps
```

At 50–200 users PostgreSQL itself can provide the queue. Redis is optional; Kafka is unnecessary.

Use the same logical Job contract locally in SQLite.

## 12. Embedding architecture

Qwen3-Embedding-0.6B remains a retrieval sensor.

Recommended flow:

```text
cheap lexical/entity/time/reference/graph filters
        ↑
Qwen3-Embedding-0.6B high-recall retrieval
        ↓
optional reranker / semantic adjudication
        ↓
Representation Auditor
        ↑
deterministic Authority Gate
```

Model size should be upgraded only if RAOS-specific Recall@K / hard-negative calibration demonstrates a meaningful gain.

Local ORIN NX can own local embeddings. Cloud mode can use a shared embedding worker with tenant-scoped vectors.

At this cohort size, PostgreSQL vector support or a simple vector service is enough; a distributed vector database is not needed.

## 13. Scale

A useful first stress target is:

```text
200 users × 1,000 Sources/user = 200,000 Sources
```

This is modest for PostgreSQL.

One 1024-dimensional float32 vector is roughly 4 KB, so one vector per 200,000 Sources is about 0.8 GB of raw vector values before index overhead. Chunk-level vectors increase this, but the likely cost bottlenecks remain LLM cognition, acquisition, polling and media—not relational row capacity.

## 14. P0 blockers before 50–200 user beta

1. Authenticated user/workspace identity.
2. Tenant-scoped persistence and authorization.
3. Durable job queue.
4. Canonical Authority Home + authority epoch.
5. Append-oriented sync protocol.
6. 30-day retention/deletion enforcement.
7. Per-workspace connector/secret isolation.
8. Backup, restore, local export/import.
9. Per-user quotas/rate limits and bounded worker concurrency.
10. Phase 13 extended with workspace identity + authority epoch.

## 15. What can wait

The following are not required for 50–200 users:

```text
microservice rewrite
Kafka
service mesh
multi-region active-active
distributed vector database
general CRDT framework
large Kubernetes deployment
```

## 16. First-beta product boundary

Start with:

```text
one user
▒ one private workspace
→ one authority home
→ multiple read/sync devices
```

Do not start with collaborative workspaces. Shared RAOS workspaces raise semantic ownership questions—whose Kernel, Attention, Watch responsibility and authority policy—that are not ordinary document-sharing problems.

## 17. Remote browser behavior

If LOCAL_DEVICE is canonical, browser/cloud may read synced state, append observations/feedback and request work.

Authority-bearing requests become:

```text
PENDING_CANONICAL_COMMAND
```

until the canonical local device executes them.

The cloud must not create a second canonical decision merely because the local device is offline.

A user may explicitly transfer authority home to CLOUD if they want 24/7 acquisition/cognition.

## 18. Final assessment

Conceptual architecture for 50–200 users: **suitable**.

Current runtime directly exposed as multi-user: **not suitable**.

Required deployment evolution: **moderate and bounded**.

Recommended server form: **modular monolith + PostgreSQL + object storage + bounded durable workers**.

Recommended product form: **local-first with optional cloud authority and default 30-day encrypted sync cache**.

The research/Representation track and deployment track should remain separate and meet only at identity, ownership, Phase 13 authority and replayable history.
