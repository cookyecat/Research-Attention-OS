# Research Attention OS

Research Attention OS (RAOS) is a personal cognitive operating system for allocating scarce human attention to information that can change, challenge, extend, or materially affect a researcher's current world model.

Current HEAD architecture is defined by `RAOS_CANONICAL_ARCHITECTURE.md`. Historical numbered phase documents explain how the system reached that architecture; they are not current configuration guides.

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

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

Acquisition worker (separate process, same execution environment as backend):

```bash
cd backend
source .venv/bin/activate
python -m app.acquisition_worker --env-file ../.env --interval 60 --limit-per-source 5
```

Do not run `next build` concurrently with a long-running `next dev` using the same `.next` directory. If client-side controls stop hydrating, stop dev, remove `frontend/.next`, and restart `npm run dev`.

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

- **Today** — action-first overview of what needs focused attention now, what RAOS is watching, and how much information has already been filtered away.
- **Inbox** — URL, text, PDF, or manual observation entry with recent-source recovery.
- **Attention** — source-centric filtered world with search and disposition filters. Detail views lead with the decision, why RAOS surfaced it, cognitive impact, and Kernel relevance; raw evidence and pipeline internals stay available under Technical trace.
- **Kernel** — searchable human-authorized cognitive workspace with durable state and a visually separate authorization area for proposed changes.
- **Watch** — delegated future-attention responsibilities grouped by monitored target rather than raw watch-record rows; developer trigger simulation is hidden under technical controls.

The frontend follows an action-first presentation rule: **human action first -> cognitive explanation -> evidence -> technical trace**. This presentation contract changes no cognition semantics or backend authority boundaries.

`POST /analysis/extract` is idempotent. `POST /analysis/reprocess` forces a new `AnalysisRun`. `GET /analysis/by-source/{id}` reads the latest run without rerunning cognition.

## Acquisition Plane v0.1

Acquisition answers only: **what became observable?** It does not judge cognitive relevance.

The current v0.1 model is:

```text
SourceDefinition → Observation → Information Object → Snapshot → RAOS Source
```

RSS/Atom is the first unattended transport. New Sources establish a present-time baseline before cognitive analysis so old feed backlog does not masquerade as newly arrived information. One Source failure must not terminate polling of independent Sources.

Identity deduplication belongs to Acquisition; semantic event clustering remains downstream.

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
