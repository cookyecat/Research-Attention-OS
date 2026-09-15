# Research Attention OS

Research Attention OS (RAOS) is a personal cognitive operating system for allocating scarce human attention to information that can change, challenge, extend, or materially affect a researcher's current world model.

Core product doctrine:

```text
Observe broadly.
Understand automatically.
Interrupt sparsely.

External World → Acquisition → Automatic Cognition → Attention → User
```

RAOS should see more than the user, understand more than the user must read, and surface only the small residue that deserves human attention. Genuine post-baseline new arrivals normally enter canonical cognition automatically; opening a Source does not trigger cognition.

Current HEAD architecture is defined by `RAOS_CANONICAL_ARCHITECTURE.md`. Historical numbered phase documents explain how the system reached that architecture; they are not current configuration guides.

Frontend/User-Space design is governed by `RAOS_FRONTEND_DESIGN_PRINCIPLES.md`: RAOS Reader is an attentional recomposition of a Source, not a mirror of the publisher webpage.

```text
External World
  → Acquisition Plane
  → RAOS Source
  → Semantic Sensor / Auditor
  → Audited World Representation
       ├─ cognitive effects → Relation Mapping / Binding / Grounding / Authority
       │                    → Magnitude-Free / Pareto
       └─ no cognitive effect → D / S / P situational-awareness gate
  → DROP / AWARE / WATCH / ENGAGE
  → authorized public update / WATCH / KernelPatch
```

## Current developer dogfood

RAOS currently runs as developer dogfood: validated research cognition is the online cognition contract rather than a separate production-only semantic path.

Active dogfood identity:

```text
cognition:        research-aligned-cognition-v1
decision strategy: pareto-multidelta-cardinal-free-effect-anchored-open-new-v0.2
no-Delta branch:  dsp-v1
```

Repository compatibility defaults remain conservative (`rule`, `legacy`, `one-delta`) so historical tests/replays do not silently change semantics. Dogfood must set the research-aligned contract explicitly.

## Run locally

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file ../.env
```

Frontend dogfood runtime:

```bash
cd frontend
npm install
npm run dogfood:restart
```

`dogfood:restart` is the safe local launch path: it stops any existing frontend on port 3000, removes `.next`, runs typecheck + a clean production build, then starts `next start`. Open `http://localhost:3000`. Use `npm run dev` only while actively editing the frontend.

Acquisition worker (separate process, same execution environment as backend):

```bash
cd backend
source .venv/bin/activate
python -m app.acquisition_worker --env-file ../.env --interval 60 --limit-per-source 5
```

Never run `next build` while either `next dev` or `next start` is still serving the same `.next` directory. That can produce HTML/CSS/JS chunk-hash mismatch and a raw unstyled page. For normal dogfood recovery/restart, use `npm run dogfood:restart`.

## Dogfood configuration

Typical local `.env` contract:

```bash
RAOS_COGNITIVE_PROVIDER=model
RAOS_COGNITIVE_CONTRACT=research-aligned-v1
RAOS_NO_DELTA_AWARENESS_CONTRACT=dsp-v1
RAOS_DECISION_STRATEGY_ID=pareto-multidelta-cardinal-free-effect-anchored-open-new
RAOS_LLM_BASE_URL=...
RAOS_LLM_API_KEY=...
RAOS_LLM_MODEL=...
```

Never commit secrets from `.env`.

## Current user surfaces

RAOS now separates **User Space** from **Operating System View**. Normal use must show information, meaning, and actions; scheduler/cognition/provenance internals belong in explicit Inspector surfaces.

- **Today** — action-first overview of what needs focused attention now, what RAOS is watching, and how much information has already been filtered away.
- **Inbox** — the observed-world Source Library plus manual URL/text/PDF/observation entry. The library uses an editorial-rhythm layout rather than a uniform storage grid and shows each Source's latest RAOS cognition state when available; unanalyzed Sources remain directly readable.
- **Attention** — source-centric filtered world with search and disposition filters. Opening a Source defaults to **Reader**: source title, author/origin/time, preserved/cached hero and semantic article media (images, native video, and trusted video embeds) when available, preserved article text, audited evidence anchors mapped back to original sentences, a scroll-aware RAOS reading companion, optional embedded Half-bold reading, and plain-language personal relevance. Scholarly arXiv Sources use a dedicated Paper Reader that preserves title/authors/affiliations, Abstract, real section navigation, Figures, MathML equations, tables, References, and PDF/arXiv/HTML actions instead of mirroring the arXiv abstract-page template. Direct media is cached locally when reasonably small and otherwise falls back to its original URL; embeds preserve provider playback without copying publisher page machinery. The separate **RAOS Inspector** exposes D/S/P, cognitive effects, Kernel mapping, evidence extraction, AnalysisRun provenance, and feedback controls.
- **Context** (`/kernel`) — user-facing durable projects, questions, beliefs, models, and constraints. Raw Kernel type/status/version metadata is subordinate under `RAOS Inspector`. Human authorization remains required for proposed context changes.
- **Watch** — delegated future-attention responsibilities grouped by monitored target. User Space describes what RAOS is waiting for; raw Watch records and developer trigger simulation are subordinate under `RAOS Inspector`.
- **Preferences** — real RAOS appearance controls stored in the browser. Theme supports Dark / Light / System and text size supports Compact / Default / Large across the full product.
- **RAOS System** (`/system`) — explicit operating-system view for runtime identity, raw ledgers, pipeline/model provenance, and subsystem inventory. It is intentionally outside normal reading flow.

The active frontend boundary is: **User Space = content + meaning + action; RAOS System = scheduling + cognition + provenance + execution internals**. User-facing timestamps interpret backend naive datetimes as UTC and render them explicitly in `Asia/Shanghai` (UTC+8). This presentation contract changes no cognition semantics or backend authority boundaries.

`POST /analysis/extract` is idempotent. `POST /analysis/reprocess` forces a new `AnalysisRun`. `GET /analysis/by-source/{id}` reads the latest run without rerunning cognition.

## Acquisition Plane v0.2 — Phase 11A expansion

Acquisition answers only: **what became observable?** It does not judge cognitive relevance.

The current ontology remains the v0.1 four-object model:

```text
SourceDefinition → Observation → Information Object → Snapshot → RAOS Source
```

Acquisition is transport-adapter based. RSS/Atom remains the baseline unattended transport; `WEIBO_PUBLIC` and `X_PUBLIC` are anonymous public-social adapters. Phase 11A adds pragmatic discovery adapters for `HACKERNEWS_SEARCH`, `BILIBILI_SEARCH`, `BILIBILI_CREATOR`, and `SOGOU_SEARCH`. HN/Sogou are web-discovery transports that prefer the existing URL ingestion boundary; Bilibili is currently metadata-only and explicitly defers cognition until fuller video semantics are acquired. New Sources establish a present-time baseline before cognitive analysis so old backlog does not masquerade as newly arrived information. One Source failure must not terminate independent Sources, and one failed item must not abort sibling items in the same Source.

When an article page cannot be fetched but its discovery/feed record contains usable publisher/platform text, Acquisition may preserve an explicit provenance-labelled fallback rather than bypassing access controls. The dogfood registry now also contains enabled Hacker News and Bilibili search Sources. Bilibili Creator and Sogou search are registered disabled residuals until their current anonymous public paths are reliable; Hugging Face remains disabled under the conservative SSRF policy. Raw platform engagement/rank signals may be preserved as Acquisition evidence, but they have no D/S/P or Attention authority in Phase 11A.

Identity deduplication belongs to Acquisition; semantic event clustering remains downstream. Public social adapters consume only anonymously observable material. Logged-in Following/friends timelines are a separate future authenticated layer and must carry explicit authorization/provenance rather than hidden browser cookies. Acquisition volume is allowed to grow independently of cognition spending: baseline backlog can be persisted without analysis, but genuine post-baseline arrivals normally enter automatic canonical cognition. A persisted Source is always readable before analysis, and merely opening it never triggers cognition; `Analyze with RAOS` exists for recovery or explicit user action.

Phase 11B adds WATCH-driven `ACTIVE_QUERY_BUNDLE` sources. A self-contained WATCH observation intent can be expanded into bounded aliases/cross-language retrieval queries and polled across the live HN/Bilibili discovery adapters. A cheap semantic Retrieval Scope Guard rejects search-engine drift before items enter the ordinary Acquisition path. Query Expansion and Scope Guard answer only **where to look / whether a hit is still inside the declared observation scope**; they have no D/S/P, Delta, or Attention authority.

Phase 11C adds a compact public-attention signal ledger for HN/Bilibili/Weibo/X-compatible engagement telemetry. Unchanged signal states extend their observation interval; changed metrics or content-age buckets create a new historical segment. Magnitude-free platform/context normalization uses each item's latest state and returns `UNKNOWN` under insufficient support. These observations project through Event links into the existing P Evidence Packet and frozen `collective-attention-estimator-v1`; raw popularity never becomes P or Attention authority.

## D / S / P no-Delta awareness

When no legal cognitive effect exists, RAOS does **not** automatically DROP. It evaluates audited event semantics using:

```text
D = standing attention jurisdiction
S = material consequence
P = collective-attention salience

AWARE iff S AND (D OR P)
```

`UNKNOWN` is not False. P must not be invented from article prose. Observed, estimated, and simulated P evidence must remain provenance-distinct.

## Database

Current migration head: `0009_acquisition_plane_v01`.

SQLite is the active lightweight local dogfood database; PostgreSQL 16+ with pgvector remains the target scalable database.

PostgreSQL example:

```bash
docker compose up -d
cd backend
export RAOS_DATABASE_URL=postgresql+psycopg://raos:raos@localhost:5432/raos
export RAOS_AUTO_CREATE_TABLES=false
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file ../.env
```

## Tests

From repo root for the complete backend suite:

```bash
PYTHONPATH=. backend/.venv/bin/pytest -q backend/tests
```

Frontend:

```bash
cd frontend
npm run typecheck
```

Historical acceptance fixtures remain in `07_MVP_ACCEPTANCE_TESTS.md` and `eval/`; current architecture and status are governed by `RAOS_CANONICAL_ARCHITECTURE.md` and `11_ROADMAP_AND_PROGRESS.md`.

## Still intentionally deferred

- broad authenticated / anti-bot crawling and paywall bypass;
- adaptive Attention→Acquisition feedback loops;
- autonomous hidden Kernel mutation;
- learned personal attention policy before sufficient dogfood feedback;
- large-scale event clustering without measured need;
- mobile / notification productization.
