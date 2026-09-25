# RAOS SESSION CHECKPOINT

Updated: 2026-09-25
Status: USER SPACE MATERIALIZED PROJECTION DIRECTION VALIDATED / PERSISTENT READ MODEL NEXT

## Current problem

Event-centric cognition is correct, but commercial User Space must not reconstruct
or download whole current/history tables on every page open.

Target:

~~~text
canonical Source/Event/Attention/Watch state
→ deterministic idempotent projector
→ durable User Space read model
→ bounded Today / Inbox / Attention / Watch / Context queries
~~~

## Confirmed root causes

### DB pool exhaustion

Backend logs proved SQLAlchemy QueuePool exhaustion:
size 5 + overflow 10, timeout 30 s.

Cause: delivery WebSocket previously held one Session for socket lifetime.

Runtime-active repair:
- socket lifetime long;
- DB Session short per polling unit;
- Session closes before sleep.

This is correct dogfood ownership. Product scale still needs broker/pubsub rather
than 0.5 s DB polling per connected client.

### Source surface contamination

Measured:

~~~text
active Source rows                     6067
REFERENCE_STUB                         3903
non-stub active                        2164
current non-stub                       2137
METADATA_ONLY                          1146
User Space visible                      992
~~~

REFERENCE_STUB = explicit CITES target placeholder, valid provenance but not an
ordinary readable/news Source.

The previous rough phrase "about 2145 real Sources" was imprecise. The canonical
Inbox population is the User Space filter (~992 at measurement time) after
excluding reference stubs, metadata-only acquisition/discovery rows, deleted
rows and non-current immutable snapshots.

## World Context / References

Literal CITES authority is correct: explicit link only; no automatic original,
derived, independent or same-event claim.

Presentation was too literal.

Frontend now separates:
- resolved known RAOS Sources -> Referenced sources
- unresolved REFERENCE_STUBs -> folded Other explicit links

All literal provenance is retained.

Frontend typecheck/build passed and frontend service was restarted; this Reader
presentation change is live.

## Existing latency repairs

Current HEAD includes:
- Source compact response + stale-while-revalidate cache;
- current Attention stale-while-revalidate materialization;
- compact Attention cache;
- frontend cachedApi;
- Inbox Source/Attention decoupling;
- Event Attention -> Source evidence projection;
- current Source version resolver.

These make current dogfood navigation fast, but are not the final architecture.

## New research docs

- 291_USER_SPACE_MATERIALIZED_PROJECTION_RESEARCH_PLAN.md
- 292_USER_SPACE_MATERIALIZED_PROJECTION_RESEARCH_RESULT.md

RAOS_CANONICAL_ARCHITECTURE.md and 11_ROADMAP_AND_PROGRESS.md updated.

## Read-only User Space prototype

Backend-live:

~~~text
GET /user-space/today
GET /user-space/inbox?limit=30&cursor=...
GET /user-space/attention?limit=30&cursor=...
~~~

Properties:
- read-only, no cognition/topology/Attention authority;
- Event remains Attention identity;
- Source returned as reading/evidence card;
- bounded payload;
- keyset-style cursor.

Focused User Space + Event + Delivery regression:
38 passed, 0 failed.

Frontend is intentionally NOT migrated to these routes yet.

## Dogfood benchmark

~~~text
legacy Sources compact:
  992 rows / ~1.74 MB / warm ~9.6 ms cache-served

User Space Inbox:
  30 rows / ~25.7 KB
  cold after backend restart ~4.51 s
  warm ~186–233 ms
  remaining problem = current Source snapshot reconstructed at read time

legacy Attention compact:
  ~1424 rows / ~1.32 MB / warm ~93 ms

User Space Attention:
  30 rows / ~30.3 KB / warm ~33–36 ms

User Space Today:
  7 cards / ~6.7 KB / warm ~24 ms
  first cold request after restart ~1.17 s
~~~

Inbox decomposition:

~~~text
current Source page SQL     ~54 ms warm
Event membership mapping    ~0.7 ms
cached Attention lookup     ~0.1 ms
Python join                 ~0.02 ms
~~~

SQLite EXPLAIN shows Source scan + current immutable snapshot window function +
temporary ordering. Therefore persistent SourceSurfaceProjection is the next
critical schema, not more request-time cache.

## 200k synthetic read-model benchmark

Indexed SQLite in-memory isolation benchmark:
- surface_seq BIGINT-like monotonic key
- page size 50
- 100 repeats

At 200k rows:

~~~text
first page median        ~0.038 ms
AWARE filter median      ~0.040 ms
cursor page median       ~0.038 ms
payload                  ~15.6 KB
~~~

Not a production SLA. It validates that indexed bounded read-model queries need
not scale linearly with total corpus size.

## Multi-user / hybrid conclusion

Current runtime remains SINGLE_USER_DOGFOOD and is NOT ready for direct
50–200-user external deployment.

Frozen ownership:

Shared/potentially shared:
- public Sources
- public Event/world state
- public provenance/evidence/cache when permitted

User-private:
- Kernel
- user-conditioned AnalysisRun
- AttentionPlan/Feedback
- Watch/Delegation
- Delivery
- credentials/private observations
- User Space projections

Target cloud:
- PostgreSQL
- authenticated user/tenant ownership
- shared public World + private Brain/Attention state
- durable projection workers
- broker/pubsub realtime
- object/media store

Target device:
- encrypted local SQLite read/cache
- local Reader/media
- optional local-only private connectors/cognition
- semantic sync cursor/outbox

Do not duplicate public world state per user.
Do not use shared SQLite as a 50–200-user network database.
Do not generic two-way replicate SQL tables.

## Final validation

Backend focused regression: 38 passed.
Frontend typecheck: PASS.
Next production build: PASS.
Frontend restarted.
Live /, /inbox, /attention: HTTP 200.
git diff --check: PASS.

## Next action

Design and implement durable:
1. SourceSurfaceProjection
2. UserAttentionProjection
3. UserSourceAttentionProjection
4. projector checkpoint/outbox
5. rebuild command/test

Only after rebuild/performance gates pass should Today/Inbox/Attention frontend
cut over from current cached legacy endpoints to /user-space.
