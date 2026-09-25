# 292 — User Space Materialized Projection Research Result

Date: 2026-09-25  
Status: **ARCHITECTURE DIRECTION VALIDATED / READ-ONLY V0.1 PROTOTYPE IMPLEMENTED / PERSISTENT READ MODEL NOT YET ADMITTED**

Preregistration: 291_USER_SPACE_MATERIALIZED_PROJECTION_RESEARCH_PLAN.md

## 1. Trigger and result

Dogfood exposed a mismatch:

~~~text
cognition architecture = Event-centric
frontend data plane    = still largely whole-table Source-era reads
~~~

The visible symptoms were:

- 0 Sources / Internal Server Error during pool exhaustion;
- 10 second class page waits;
- broad endpoints transferring MB to tens of MB;
- 5k+ apparent Source rows including reference/discovery artifacts;
- Event Attention needing to be reprojected to Source presentation.

The strongest result of this stage is:

> User Space should be a disposable, incrementally maintained read model over
> canonical Source/Event/Attention/Watch state. Normal pages should read bounded
> page-sized projections rather than reconstructing state from historical
> tables on every navigation.

## 2. Clarified object boundaries

### REFERENCE_STUB

A REFERENCE_STUB is a durable placeholder for a target that a Source explicitly
links but that RAOS has not acquired as a first-class readable Source.

Example:

~~~text
The Verge article
  --CITES--> Amazon product link
  --CITES--> Privacy Policy
  --CITES--> another Verge article
~~~

If the target has not been acquired, RAOS can preserve its URL/title as a
REFERENCE_STUB so the literal provenance edge is not lost.

It is:

- valid provenance/evidence graph state;
- not proof of same Event or derivation;
- not automatically a readable/news Source;
- not allowed in default User Space Source surfaces.

### Source count reconciliation

Current dogfood counts during this stage:

~~~text
active Source rows                     6067
REFERENCE_STUB                         3903
non-stub active                        2164
non-stub current snapshot              2137
METADATA_ONLY                          1146
final User Space visible                992
~~~

The earlier rough statement that about 2145 rows were "real Sources" was too
coarse. 2164 means non-stub active rows; it still includes metadata-only and
historical/internal rows. The correct Inbox population is defined by
is_user_visible_source_clause(), which yielded about 992 at measurement time.

## 3. World Context / References audit

The Reader's epistemic statement was correct:

~~~text
CITES proves only a literal explicit link.
It does not prove:
- original source
- derivation
- independence
- same-event identity
~~~

However, presentation was too literal.

One article could display Privacy Policy, Terms, Amazon, Best Buy, author pages,
navigation, and substantive linked articles at identical visual weight.

The parser already captures literal links correctly. The product error was
flattening provenance into User Space context.

Frontend v0.1 correction implemented:

~~~text
Referenced sources
  resolved RAOS Sources shown normally

Other explicit links
  unresolved REFERENCE_STUB links folded by default
~~~

All literal CITES edges remain preserved.

Longer-term ReferencePresentationProjection should classify substantive,
recirculation, utility, commerce, and other literal links without changing
epistemic authority.
## 4. Pool-exhaustion root cause and immediate fix

The hardest latency failure was not Clash Verge.

Backend logs contained direct evidence:

~~~text
sqlalchemy.exc.TimeoutError
QueuePool limit size 5
overflow 10
timeout 30 s
~~~

A long-lived delivery WebSocket received a FastAPI dependency Session and held
it for the socket lifetime.

This converted browser tabs/reconnects into long-lived DB resource ownership.

Observed failure chain:

~~~text
WebSocket clients
→ long-lived SQLAlchemy sessions/connections
→ pool exhaustion
→ normal API waits/timeouts
→ backend failures/restarts
→ Next upstream socket reset
→ ECONNRESET / socket hang up
→ User Space shows 0 or Internal Server Error
~~~

Immediate repair:

~~~text
WebSocket lifetime = long
DB Session          = short per polling unit of work
~~~

The current running backend was verified to have started after this code change.

This is safe for dogfood and low-scale operation.

It is not the final 50–200-user realtime architecture because polling every
0.5 s per connected user would itself create unnecessary DB transaction load.

Product-scale target:

~~~text
canonical write
→ broker/pubsub notification
→ WebSocket delivery

socket holds broker subscription
socket does not hold DB Session
~~~

## 5. Clash Verge assessment

Clash Verge / mihomo was running on the Mac, but:

- RAOS frontend/backend LaunchAgents did not contain HTTP_PROXY /
  HTTPS_PROXY / ALL_PROXY environment variables;
- local serving path is 127.0.0.1:3000 → 127.0.0.1:8000;
- the backend produced direct SQLAlchemy pool exhaustion evidence sufficient to
  explain ECONNRESET and socket hang ups.

Therefore Clash Verge was not required to explain the failure and was not the
primary root cause.

TUN/network interception can remain a secondary environmental variable, but the
captured RAOS defect was local DB/session ownership.

## 6. Why Event-centric exposed the old read architecture

Source-based dogfood tolerated a whole-table UI because N was small.

Phase17 introduced:

~~~text
Source
→ Event
→ authorized membership
→ Event Attention
→ Source evidence presentation
~~~

and accumulated:

- about 1k human-visible Sources;
- more than 1k current Event Attention rows;
- Source↔Event projection;
- immutable historical AttentionPlan / AnalysisRun / membership state.

The frontend still frequently followed:

~~~text
page open
→ broad Source fetch
→ broad Attention fetch
→ browser-side join/filter/sort
~~~

This crosses a performance threshold as N grows.

The problem is not "Event is inherently slow".

The problem is:

> Event-centric write/cognition architecture was paired with a small-N read
> architecture.

## 7. Existing stop-gap improvements

Several stop-gap improvements were implemented during diagnosis:

- compact Source response strips large body/raw metadata;
- compact Source server snapshot cache with stale-while-revalidate;
- current Attention stale-while-revalidate cache;
- compact Attention cache;
- frontend in-memory cachedApi for repeated navigation;
- Source and Attention loading decoupled in Inbox;
- Event Attention mapped to Source evidence for presentation;
- historical representative Source IDs resolved to current snapshots;
- REFERENCE_STUB and METADATA_ONLY excluded from User Space.

These explain why localhost navigation recovered to near-instant behavior after
the failure.

They are useful, but they are caches around the existing read model, not the
final scalable architecture.
## 8. Read-only User Space v0.1 prototype

Implemented:

~~~text
GET /user-space/today
GET /user-space/inbox?limit=30&cursor=...
GET /user-space/attention?limit=30&cursor=...
~~~

Properties:

- read-only;
- no cognition authority;
- no Event/Attention mutation;
- bounded response size;
- Event remains Attention identity;
- Source is returned as the user-facing reading card;
- Inbox uses keyset-style cursor;
- full score_debug/result payload is omitted.

Focused tests:

~~~text
9 passed
~~~

including:

- REFERENCE_STUB excluded;
- paginated Inbox;
- Event identity preserved on Attention card;
- Source card returned for reading;
- bounded Today contract.

## 9. Dogfood benchmark

Live localhost comparison, same canonical data:

~~~text
legacy Sources compact
  992 rows
  1,743,073 bytes
  warm median ~9.6 ms
  cache-served broad response

User Space Inbox
  30 rows
  25,628 bytes
  warm median ~259 ms
  cold ~4.96 s

legacy Attention compact
  1424 rows
  1,318,023 bytes
  warm median ~93 ms

User Space Attention
  30 rows
  29,984 bytes
  warm median ~34 ms

User Space Today
  7 cards
  6,671 bytes
  warm median ~22 ms
~~~

Interpretation:

Today and bounded Attention validate the response contract strongly.

Inbox v0.1 is not production-ready despite the small payload because it still
computes "current human-readable Source snapshot" at request time.

## 10. Inbox bottleneck localization

Warm breakdown for the first 30 Source rows:

~~~text
current Source page SQL     ~54 ms
Event membership mapping    ~0.7 ms
cached Attention lookup     ~0.1 ms
Python join                 ~0.02 ms
~~~

SQLite EXPLAIN shows current Source selection still performs:

- Source scan;
- correlated snapshot lookup;
- window function row_number partitioned by external_item_id;
- temporary B-tree for ordering.

Therefore the next durable projection must materialize the current human-visible
Source surface at write/project time.

The key bottleneck is not Event membership itself.
## 11. Cursor finding

Prototype keyset pagination exposed a cross-database edge case.

SQLite stores server-default datetimes with second precision and UUIDs in a
backend-specific representation. A naive datetime+UUID cursor could duplicate or
skip same-second rows.

Prototype was corrected using normalized UTC epoch + UUID.

Long-term projection should avoid depending on storage-format tie breakers and
own a monotonic:

~~~text
surface_seq BIGINT
~~~

This gives stable, database-independent keyset pagination.

## 12. Synthetic 200k read-model benchmark

Synthetic SQLite in-memory projection:

~~~text
page size = 50
repeats   = 100
indexed by (user_id, surface_seq DESC)
and (user_id, disposition, surface_seq DESC)
~~~

Results:

~~~text
10k rows:
  first page median      ~0.036 ms
  disposition page       ~0.037 ms
  cursor page            ~0.035 ms

200k rows:
  first page median      ~0.038 ms
  disposition page       ~0.040 ms
  cursor page            ~0.038 ms
  payload                ~15.6 KB
~~~

This is an algorithm-isolation benchmark, not a production PostgreSQL or
end-to-end SLA claim.

The important observation is structural:

> Indexed bounded read-model queries did not grow linearly with corpus size from
> 10k to 200k rows.

This supports the O(page_size)-style User Space design.

Artifacts:

- eval/live/results/user_space_projection_dogfood_v0_1/
- eval/live/results/user_space_projection_scale_v0_1/
## 13. 50–200-user assessment

Current RAOS implementation is **not safe to expose directly to 50–200 external
users**.

This is not because Event-centric semantics cannot scale.

Current blockers are implementation/product boundaries:

1. deployment scope is explicitly SINGLE_USER_DOGFOOD;
2. no authenticated user/tenant identity exists;
3. multi_user_isolation=false;
4. cloud/private state ownership is not tenantized;
5. canonical dogfood database is SQLite;
6. realtime delivery still uses DB polling rather than broker/pubsub;
7. durable User Space projections are not yet persisted per user.

Phase12E already froze the correct ownership model.

### Shared external world

Potentially shared:

- public Sources;
- public Event/world state;
- source-derived provenance/evidence when access allows;
- public media/cache.

### User-private Brain / Attention

Must be isolated:

- Kernel;
- user-conditioned AnalysisRun;
- AttentionPlan / Feedback;
- WATCH responsibility;
- Delivery;
- credentials/private observations;
- User Space read models.

A public article should not be stored 200 times merely because 200 users exist.

Its world/event representation can be shared, while each user owns a separate
Attention projection.

## 14. Recommended product-scale deployment

~~~text
                    CLOUD
        ┌──────────────────────────────┐
        │ PostgreSQL                   │
        │  shared World state          │
        │  private user state          │
        │  durable projection state    │
        │                              │
        │ projection workers           │
        │ cognition workers            │
        │ broker / pubsub              │
        │ object/media storage         │
        │ auth/API                     │
        └──────────────┬───────────────┘
                       │ semantic sync
              ┌────────┴────────┐
              │                 │
          device A          device B
          local SQLite      local SQLite
          read/cache        read/cache
          local media       local media
          optional          optional
          private work      private work
~~~

PostgreSQL is appropriate for shared multi-user relational serving and supports
row-level security policies for per-user/private tables.

SQLite remains appropriate for one-device local state/cache. WAL improves local
reader/writer concurrency, but SQLite WAL still has one writer at a time and
requires all WAL users on the same host; it is not the cloud multi-user shared
database.

## 15. Short-lived Session assessment

Changing WebSocket DB access from socket-lifetime Session to short unit-of-work
Session is the correct ownership pattern.

For one user it removes catastrophic pool leaks.

For 50–200 users it remains only an interim implementation if each client polls
the DB every 500 ms.

At product scale:

~~~text
bad:
200 sockets × 2 DB polls/s
→ ~400 empty DB polling transactions/s

better:
one canonical state change
→ publish notification once
→ broker fans out to subscribed sockets
~~~

Therefore short DB sessions are necessary but not sufficient for scale.

## 16. Hybrid local/cloud conclusion

Do not replicate arbitrary SQL tables bidirectionally.

Synchronize semantic operations/events and rebuild local projections.

Suggested split:

- public world flows cloud → device cache;
- local private observations remain local unless user policy permits upload;
- user commands/feedback are append-only stable-id operations;
- projections are derived and rebuildable;
- Kernel changes continue through explicit canonical authorization/versioning.

A full CRDT framework is not required for first hybrid deployment.

## 17. Stage conclusion

The research direction is accepted:

~~~text
Canonical History / World / Attention
        ↓
incremental projector
        ↓
User Space materialized read model
        ↓
bounded Today / Inbox / Attention / Watch / Context queries
~~~

Do not treat browser caching as the architecture.

Do not treat process-memory cache as the architecture.

Do not reconstruct current User Space from immutable history on page open.

Next engineering gate:

1. define persistent SourceSurfaceProjection + UserAttentionProjection schema;
2. add deterministic idempotent projector;
3. rebuild projection from canonical state;
4. move Inbox/Today/Attention frontend to bounded User Space APIs;
5. benchmark against current dogfood;
6. then reopen Phase12E tenantization for real multi-user deployment.


## 18. Final validation note

Focused backend regression after the User Space prototype and delivery-session fix:

~~~text
38 passed
1 existing Starlette/httpx deprecation warning
0 failures
~~~

Frontend:

~~~text
TypeScript typecheck PASS
Next production build PASS
~~~

The frontend service was restarted after the Reader reference-presentation
change. Live page smoke:

~~~text
/          200
/inbox     200
/attention 200
~~~

The read-only prototype is live in the backend but remains intentionally
disconnected from normal frontend navigation.

After a backend restart, first prototype requests still exposed the remaining
cold-materialization cost:

~~~text
/user-space/today           ~1.17 s cold
/user-space/inbox?limit=30  ~4.51 s cold
/user-space/attention?limit=30 ~49 ms
~~~

Subsequent warm measurements:

~~~text
Today         ~24 ms / 6.7 KB
Inbox 30      ~186–233 ms / 25.7 KB
Attention 30  ~33–36 ms / 30.3 KB
~~~

This confirms the stage conclusion rather than weakening it:

> bounded APIs solve transfer size and browser work, but cold-start and Inbox
> read-time current-snapshot reconstruction remain. Production cutover should
> wait for durable SourceSurfaceProjection / UserAttentionProjection rather
> than relying on process-local warm caches.

git diff --check passed.
