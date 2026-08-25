# Research Attention OS

Personal cognitive OS: allocate finite attention to information that can change research understanding.

```text
Source → Claim / Observation / Inference
      → Kernel Match → AttentionPlan → Model Delta
      → KernelPatch → Human Accept / Modify / Reject
```

Vertical Slice 2 adds a **Model-backed Cognitive Engine** behind the same constitution: AI never silently writes Belief / Model / Hypothesis / Decision.

## Run (development)

Backend defaults to SQLite + the rule-based provider (stable, no API key):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Seed the MVP Kernel from Home or the Kernel page.

If port 8000 is taken, point `frontend/next.config.ts` at the API port.

## PostgreSQL + pgvector (target database)

```bash
docker compose up -d
cd backend
export RAOS_DATABASE_URL=postgresql+psycopg://raos:raos@localhost:5432/raos
export RAOS_AUTO_CREATE_TABLES=false
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

SQLite remains a light local mode (`create_all` when `RAOS_AUTO_CREATE_TABLES=true`).

## Cognitive providers

```bash
export RAOS_COGNITIVE_PROVIDER=rule    # default; A–O regression baseline
export RAOS_COGNITIVE_PROVIDER=model   # OpenAI-compatible + rule fallback
export RAOS_LLM_BASE_URL=https://api.openai.com/v1
export RAOS_LLM_API_KEY=...
export RAOS_LLM_MODEL=gpt-4o-mini
export RAOS_EMBEDDING_BASE_URL=
export RAOS_EMBEDDING_API_KEY=
export RAOS_EMBEDDING_MODEL=text-embedding-3-small
```

`POST /analysis/extract` is idempotent. Use `POST /analysis/reprocess` to force a new `AnalysisRun`. `GET /analysis/by-source/{id}` reads the latest run without rerunning the pipeline.

`POST /kernel/bootstrap/propose` emits KernelPatch proposals only (Human Commit required).

## Tests

```bash
cd backend
pytest -q
```

PostgreSQL:

```bash
export RAOS_TEST_DATABASE_URL=postgresql+psycopg://raos:raos@localhost:5432/raos
pytest -q
```

Eval Set v0.1 lives in `eval/v0.1/` (50+ structured cases). A–O paraphrases are in `backend/tests/acceptance/paraphrases.py`.

## Explicitly not in this slice

Large-scale crawling, recommendation feed, automatic Kernel mutation, WeChat history scraping, learned attention policy, multi-agent orchestration, notification system, mobile.
