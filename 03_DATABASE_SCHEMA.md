# Research Attention OS — DATABASE_SCHEMA.md

Version: RAOS v1.1
Reference database: PostgreSQL 16+ with pgvector

## 1. Design principles

1. Do not collapse all objects into generic notes.
2. Preserve provenance.
3. Preserve Claim / Observation / Inference boundaries.
4. Evidence is represented as links.
5. Kernel commits are versioned.
6. Vector similarity is retrieval assistance, not truth.
7. JSONB is allowed, but semantics must remain validated/queryable.
8. Prefer soft deletion for provenance-bearing objects.

## 2. Extensions

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

## 3. Source tables

### sources
```text
id UUID PK
source_type VARCHAR NOT NULL
title TEXT
canonical_url TEXT
content_text TEXT
published_at TIMESTAMPTZ
ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
publisher TEXT
language VARCHAR
fingerprint TEXT NOT NULL
content_hash TEXT
ingestion_method TEXT NOT NULL
raw_metadata JSONB NOT NULL DEFAULT '{}'
embedding VECTOR(...)
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
deleted_at TIMESTAMPTZ
```

Indexes: fingerprint, canonical_url, published_at; ANN vector index only when scale justifies it.

### source_authors
```text
source_id UUID FK sources
author_name TEXT
author_type TEXT
```

### source_edges
Defined in `06_SOURCE_GRAPH_SPEC.md`.

## 4. Event tables

### events
```text
id UUID PK
title TEXT NOT NULL
event_type TEXT
occurred_at TIMESTAMPTZ
location TEXT
summary TEXT
confidence REAL NOT NULL
status VARCHAR NOT NULL
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

### event_sources
```text
event_id UUID FK
source_id UUID FK
relationship VARCHAR NOT NULL
confidence REAL
PRIMARY KEY(event_id, source_id)
```

### event_clusters
Optional in first MVP:
```text
id UUID PK
event_id UUID FK
canonical_source_id UUID FK
cluster_confidence REAL
created_at TIMESTAMPTZ
```

## 5. Information Plane tables

### claims
```text
id UUID PK
source_id UUID NOT NULL FK
event_id UUID NULL FK
text TEXT NOT NULL
normalized_text TEXT
claim_type VARCHAR NOT NULL
attributed_to TEXT
attribution_type VARCHAR
scope TEXT
confidence_extraction REAL
credibility_estimate REAL
temporal_policy_id UUID NULL
embedding VECTOR(...)
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

### observations
```text
id UUID PK
source_id UUID NULL FK
event_id UUID NULL FK
observer_type VARCHAR NOT NULL
text TEXT NOT NULL
observation_type VARCHAR NOT NULL
measured_values JSONB
scope TEXT
confidence REAL NOT NULL
temporal_policy_id UUID NULL
embedding VECTOR(...)
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

### inferences
```text
id UUID PK
text TEXT NOT NULL
author_type VARCHAR NOT NULL
confidence REAL NOT NULL
scope TEXT
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

### inference_sources
```text
inference_id UUID FK
source_object_type VARCHAR NOT NULL
source_object_id UUID NOT NULL
PRIMARY KEY(inference_id, source_object_type, source_object_id)
```

## 6. Epistemic Plane tables

### evidence_links
```text
id UUID PK
source_object_type VARCHAR NOT NULL
source_object_id UUID NOT NULL
target_object_type VARCHAR NOT NULL
target_object_id UUID NOT NULL
stance VARCHAR NOT NULL
strength VARCHAR NOT NULL
confidence REAL NOT NULL
scope TEXT
proposed_by VARCHAR NOT NULL
accepted_by_user BOOLEAN
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

Indexes:
- target object;
- source object;
- stance.

### temporal_policies
```text
id UUID PK
freshness_window_seconds BIGINT
relevance_decay VARCHAR NOT NULL
validity_review_seconds BIGINT
review_triggers JSONB NOT NULL DEFAULT '[]'
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

## 7. Kernel storage

Use one node table with type-specific validated payload.

### kernel_nodes
```text
id UUID PK
node_type VARCHAR NOT NULL
title TEXT
current_version INTEGER NOT NULL DEFAULT 1
status VARCHAR NOT NULL
payload JSONB NOT NULL
embedding VECTOR(...)
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
deleted_at TIMESTAMPTZ
```

Allowed node types:
```text
GOAL PROJECT BOTTLENECK QUESTION BELIEF HYPOTHESIS MODEL DECISION EXPERIMENT
```

API validates payload using type-specific Pydantic models.

### kernel_edges
```text
id UUID PK
source_node_id UUID FK kernel_nodes
target_node_id UUID FK kernel_nodes
relationship VARCHAR NOT NULL
metadata JSONB NOT NULL DEFAULT '{}'
created_at TIMESTAMPTZ
deleted_at TIMESTAMPTZ
```

## 8. Kernel versioning

### kernel_versions
```text
id UUID PK
kernel_node_id UUID NOT NULL FK
version INTEGER NOT NULL
snapshot JSONB NOT NULL
patch_id UUID NULL
committed_by VARCHAR NOT NULL
committed_at TIMESTAMPTZ NOT NULL DEFAULT now()
UNIQUE(kernel_node_id, version)
```

### kernel_patches
```text
id UUID PK
target_object_type VARCHAR NOT NULL
target_object_id UUID
change_type VARCHAR NOT NULL
current_state JSONB
proposed_state JSONB NOT NULL
evidence_link_ids JSONB NOT NULL DEFAULT '[]'
reasoning TEXT NOT NULL
suggested_confidence_change JSONB
status VARCHAR NOT NULL
proposed_by VARCHAR NOT NULL
reviewed_by_user_at TIMESTAMPTZ
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

Commit must be transactional:
1. lock target;
2. verify patch accepted/modified;
3. insert version snapshot;
4. update node;
5. associate patch;
6. commit.

## 9. Scheduler tables

### runtime_contexts
```text
id UUID PK
current_task TEXT
session_topic TEXT
available_attention_minutes INTEGER
interruptibility VARCHAR
cognitive_capacity VARCHAR
deadline_at TIMESTAMPTZ
captured_at TIMESTAMPTZ NOT NULL
```

### attention_plans
```text
id UUID PK
candidate_type VARCHAR NOT NULL
candidate_id UUID NOT NULL
disposition VARCHAR NOT NULL  -- stored in column attention_state
urgency VARCHAR NOT NULL
cognitive_budget_minutes INTEGER
kernel_target_ids JSONB NOT NULL DEFAULT '[]'
expected_output VARCHAR NOT NULL
reason TEXT NOT NULL
watch_after_processing BOOLEAN NOT NULL DEFAULT false
scheduler_version TEXT NOT NULL
score_debug JSONB NOT NULL DEFAULT '{}'
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

## 10. Watch tables

### watches
```text
id UUID PK
target_type VARCHAR NOT NULL
target_ref TEXT NOT NULL
status VARCHAR NOT NULL
created_reason TEXT NOT NULL
kernel_target_ids JSONB NOT NULL DEFAULT '[]'
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

### watch_triggers
```text
id UUID PK
watch_id UUID NOT NULL FK watches
trigger_type VARCHAR NOT NULL
trigger_config JSONB NOT NULL DEFAULT '{}'
last_checked_at TIMESTAMPTZ
last_triggered_at TIMESTAMPTZ
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

## 11. User feedback

### attention_feedback
```text
id UUID PK
attention_plan_id UUID NOT NULL FK attention_plans
system_attention_state VARCHAR
user_attention_state VARCHAR
system_modes JSONB
user_modes JSONB
opened BOOLEAN
engaged_seconds INTEGER
created_kernel_patch BOOLEAN
created_decision BOOLEAN
created_experiment BOOLEAN
feedback_text TEXT
created_at TIMESTAMPTZ
```

## 12. Ingestion tables

### ingestion_jobs
```text
id UUID PK
connector_type VARCHAR NOT NULL
input_ref TEXT
status VARCHAR NOT NULL
attempt_count INTEGER NOT NULL DEFAULT 0
error_message TEXT
started_at TIMESTAMPTZ
finished_at TIMESTAMPTZ
created_at TIMESTAMPTZ
```

### parser_runs
```text
id UUID PK
source_id UUID NOT NULL FK
parser_name TEXT NOT NULL
parser_version TEXT NOT NULL
output_metadata JSONB
created_at TIMESTAMPTZ
```

## 13. Suggested repository mapping

```text
app/
  models/
    source.py
    event.py
    claim.py
    observation.py
    inference.py
    evidence.py
    kernel.py
    scheduler.py
    watch.py
    temporal.py
```

## 14. Migration order

1. sources
2. events / event_sources
3. claims / observations / inferences
4. evidence_links / temporal_policies
5. kernel_nodes / kernel_edges
6. kernel_patches / kernel_versions
7. runtime_contexts / attention_plans
8. watches / watch_triggers
9. feedback
10. ingestion_jobs / parser_runs
11. source_edges

## 15. Database invariants to test

1. Kernel mutation requires accepted/modified KernelPatch.
2. EvidenceLink targets resolve.
3. Fingerprint prevents obvious duplicate explosion.
4. Kernel versions are append-only.
5. Claim cannot silently become Observation.
6. Inference has at least one source object.
7. Provenance objects use soft deletion.
8. WATCH transitions persist.
