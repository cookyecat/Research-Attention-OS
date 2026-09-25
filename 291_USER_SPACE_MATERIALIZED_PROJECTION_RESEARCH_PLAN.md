# 291 — User Space Materialized Projection Research Plan

Date: 2026-09-25  
Status: **PREREGISTERED / IMPLEMENTATION RESEARCH ACTIVE**

## 1. Trigger

Phase17 made canonical cognition Event-centric while the frontend data plane continued to behave largely like a small single-user database browser.

Dogfood crossed a performance and product boundary:

- thousands of durable Source rows;
- thousands of reference/discovery artifacts;
- about 1k human-visible current Sources;
- about 1.3k current Event Attention decisions;
- Source↔Event evidence projection;
- immutable historical AttentionPlans / AnalysisRuns / membership assertions.

The old page-open pattern became:

~~~text
open page
→ fetch broad current Source set
→ fetch broad current Attention set
→ join/filter/sort in browser
→ render
~~~

This is acceptable at small N but is not the intended commercial read path.

## 2. Frozen product doctrine

RAOS_FRONTEND_DESIGN_PRINCIPLES remains authoritative.

User Space is not an inspection surface for internal ledgers.

~~~text
Inbox     = what RAOS observed / preserved for the human
Attention = what RAOS currently judges deserves attention state
Today     = what should enter consciousness now
Watch     = delegated future-attention responsibility
Context   = what RAOS currently knows for the human
~~~

Event remains cognition identity.

Source remains reading / provenance / evidence path.

The UI may show Sources while the decision is Event-centric. This is an intentional product projection, not a reversion to Source-centric cognition.

## 3. Core research question

How should RAOS expose User Space so normal reads are independent of total history size?

Target:

~~~text
write / state transition
→ incrementally update read model

page open
→ read only precomputed rows required by the screen
~~~

Normal read complexity should approach O(page_size), rather than O(total Sources + total Attention history + memberships).

## 4. Mature architecture mapping

RAOS already uses the write-side concepts required by Event Sourcing:

- immutable evidence/history;
- current EventState;
- append-only AttentionPlan history;
- explicit current projections.

The missing piece is a durable CQRS-style read model for User Space.

The materialized view is disposable:

~~~text
canonical history/state
→ projector
→ User Space read model
~~~

If lost, it can be rebuilt from canonical state/history.

Applications do not directly mutate the read model.
## 5. Projection families

### 5.1 Shared Source Surface Projection

One row per current human-readable Source snapshot.

Contains only display/query fields:

~~~text
source_id
current_version_id
title
publisher
source_type
canonical_url
published_at
ingested_at
excerpt
hero thumbnail identity
reading metadata
event_id / current authorized membership if unique
sort cursor
~~~

Excludes full body, raw parser metadata, reference stubs, metadata-only acquisition artifacts, and analysis payloads.

This projection is potentially shareable for public Sources.

### 5.2 User Attention Projection

Private per-user read model.

One current row per semantic Attention identity:

~~~text
user_id
event_id
attention_plan_id
disposition
created_at
representative_source_id
explanation summary
watch responsibility summary
attention sort/rank key
~~~

Historical AttentionPlans remain immutable elsewhere.

### 5.3 User Source Attention Projection

Read-optimized bridge from Event cognition to Source presentation.

~~~text
user_id
source_id
event_id
attention_plan_id
disposition
projection_status
sort_key
~~~

Only authorized, unambiguous current Event membership may project Event Attention to a Source.

This is a presentation/read model and has no cognition authority.

### 5.4 Today Projection

Today should not fetch the whole Attention population.

It needs only:

~~~text
lead ENGAGE/AWARE item
small brief set
WATCH responsibility summary
Behind-the-quiet counters
new-since-last-visit counters
~~~

This can be maintained from User Attention Projection and queried with bounded LIMITs.

### 5.5 Inbox Projection

Inbox is a living intake landscape, not storage-grid replication.

Default query:

~~~text
current human-readable Sources
ORDER BY arrival cursor DESC
LIMIT 30–50
~~~

Use keyset/cursor pagination.

Do not use OFFSET as the long-term pagination primitive for 200k+ rows.

Search is a separate indexed operation and may span the complete allowed corpus.

### 5.6 Attention Projection

Normal Attention list:

~~~text
WHERE user_id = ?
AND disposition = optional filter
ORDER BY attention_sort_key
LIMIT 30–50
~~~

The list contract excludes large score_debug/result payloads.

Open detail fetches full explanation on demand.

### 5.7 Watch Projection

Private durable responsibilities only.

Normal Watch page should query current active responsibility rows, not replay WatchDelegation history.

### 5.8 Context Projection

Context is a current read model over user-private Kernel/current knowledge surfaces. It must not reconstruct full Kernel history on page open.
## 6. Reference Presentation Projection

Literal link provenance and human-facing World Context are different views.

Canonical truth remains:

~~~text
Source A --CITES--> target URL
~~~

CITES proves only an explicit link.

The current Reader incorrectly presents all literal links at equal visual weight.

Future presentation classes:

~~~text
SUBSTANTIVE
  resolved articles/papers/reports
  linked technical docs or primary material with article-body context

RELATED_OR_RECIRCULATION
  publisher related stories / internal recirculation

UTILITY
  privacy / terms / ethics / author index / navigation

COMMERCE
  retailer/product links / advertiser destinations

OTHER_LITERAL
  preserved but not promoted
~~~

All links may remain in provenance history.

Normal World Context expands SUBSTANTIVE.
Other classes are folded behind "Other explicit links".

Classification must not change epistemic relationship authority.

## 7. Update model

Do not refresh an entire User Space projection every five seconds.

Prefer event/change-driven incremental updates.

Examples:

~~~text
new current Source snapshot
→ upsert SourceSurface row

Event membership change
→ update affected Source↔Event projection rows

new authoritative AttentionPlan
→ upsert one UserAttention row
→ update affected UserSourceAttention rows
→ update Today counters/top candidates

Watch mutation
→ upsert affected WatchProjection row
~~~

Projection operations must be deterministic and idempotent.

## 8. Projector reliability

Introduce a durable projector checkpoint/outbox concept before distributed deployment.

Each canonical mutation has a monotonic/projectable identity.

~~~text
canonical commit
→ projection work item / change record
→ idempotent projector
→ checkpoint advances
~~~

Crash between write and projection may cause temporary staleness, not semantic loss.

Read models are rebuildable.

## 9. Consistency contract

User Space may be eventually consistent over a short bounded interval.

Target interactive contract:

~~~text
canonical decision commits
→ User Space reflects change within < 1 s typical
~~~

Critical delivery/ENGAGE execution remains governed by canonical Delivery, not by whether a page projection has refreshed.
## 10. 200k-Source target

A 200k corpus must not materially increase normal page response time.

Target query properties:

- indexed keyset pagination;
- bounded row count;
- bounded payload;
- no full history replay;
- no N+1;
- no full text/body in list endpoints;
- no browser-side full-corpus sort/filter.

Indicative targets:

~~~text
Today server query       < 50 ms warm DB target
Inbox first page         < 100 ms DB target
Attention first page     < 100 ms DB target
API payload              preferably < 200 KB per normal page
interaction paint        < 500 ms local/LAN target
~~~

Targets are engineering goals, not current measured claims.

## 11. Multi-user ownership

Reuse frozen Phase12E boundary.

### Shared / potentially shareable

~~~text
public Source content
public Event/world representation
public provenance/evidence where access permits
public media/cache artifacts
~~~

### User-private

~~~text
Kernel / cognitive state
user-conditioned AnalysisRun
AttentionPlan / feedback
Watch responsibility
Delivery
User Space projections
private Source scope / connector observations
credentials
~~~

Do not duplicate public world state per user.

Do not globally add user_id to every world table.

## 12. 50–200-user deployment target

Current SQLite single-user dogfood is **not** multi-user product-ready.

Recommended cloud serving boundary:

~~~text
Cloud:
  PostgreSQL canonical/shared + private relational state
  object/media store
  async workers / projection workers
  realtime broker/pubsub
  API/auth layer

Per-user/device:
  local encrypted SQLite read/cache store
  local Reader/media cache
  optionally local-only private connectors/cognition
  sync cursor + append-only outbox
~~~

PostgreSQL private tables should use explicit tenant/user ownership and defense in depth such as Row-Level Security where appropriate.

SQLite remains appropriate for one-device local state/cache. It should not be used as a shared network database for hundreds of concurrent users.
## 13. Hybrid cloud/local synchronization

Do not attempt generic two-way table replication.

Sync semantic changes/events:

~~~text
device_id
user_id
sequence / cursor
entity type + stable identity
operation
version
payload digest
authority/provenance
~~~

Cloud public world state can flow down to device caches.

Private local state flows up only when product/privacy policy authorizes it.

Conflicts should be resolved per domain:

- append-only evidence: union/idempotent;
- current projection: derived, never manually merged;
- user commands/feedback: append-only with stable id;
- Kernel mutations: canonical authorization/version semantics;
- preferences: version/LWW acceptable only if explicitly defined.

CRDT machinery is not a prerequisite for v1 hybrid serving.

## 14. WebSocket / realtime rule

A long-lived socket must never own a long-lived DB Session.

Correct pattern:

~~~text
socket lifetime: long
DB transaction/session: short
broker subscription: long
~~~

At multi-user scale, canonical writes publish lightweight change notifications to a broker/pubsub layer. WebSocket workers deliver already-authorized notifications without polling the relational database every 500 ms per client.

The current short-lived polling Session is safe as an immediate dogfood repair, but broker-driven delivery is the product-scale target.

## 15. LLM/cognition execution

LLM work must remain outside interactive page request paths.

~~~text
new observation
→ queued canonical cognition
→ persist Event/Attention transition
→ update projections
→ user reads precomputed result
~~~

Opening Today/Inbox/Attention must never launch global cognition.
## 16. Acceptance gates

### Gate A — semantics
- Event remains Attention identity.
- Source remains reading/evidence surface.
- projection has zero mutation authority.

### Gate B — product
- User Space follows RAOS_FRONTEND_DESIGN_PRINCIPLES.
- internal graph/reference artifacts do not leak into ordinary Inbox.
- "system busier → human quieter" remains true.

### Gate C — performance
- page reads are bounded by page size;
- no endpoint returns tens of MB for normal navigation;
- 200k synthetic Source scale does not cause O(N) request work.

### Gate D — multi-user
- shared/private ownership explicit;
- no private cognitive state crosses users;
- authenticated tenant identity exists before external multi-user launch.

### Gate E — rebuild
- read model can be deleted and reconstructed from canonical state/history.

## 17. Immediate research implementation

1. Freeze lightweight UserSpace card contracts.
2. Add read-only prototype /user-space endpoints:
   - /user-space/today
   - /user-space/inbox
   - /user-space/attention
3. Use existing current projection caches as prototype source, but return only bounded result sets.
4. Benchmark payload/time versus legacy endpoints.
5. Add synthetic 200k projection benchmark.
6. Then decide persistent schema/projector migration.

Do not prematurely add distributed infrastructure before the query/read-model contract is validated.
