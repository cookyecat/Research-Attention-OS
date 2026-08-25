# Research Attention OS

Personal cognitive OS: allocate finite attention to information that can change research understanding.

Vertical slice (v1.1):

```text
Source → Claim/Observation → Kernel Match → AttentionPlan → Model Delta → KernelPatch → Human Commit
```

## Run (development)

Backend (SQLite by default):

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

Open `http://localhost:3000`. Seed the MVP Kernel from Home (`POST /kernel/seed`) or the Kernel page.

If port 8000 is already taken, run the API on another port and point the Next.js rewrite in `frontend/next.config.ts` at it.

Optional PostgreSQL:

```bash
docker compose up -d
export RAOS_DATABASE_URL=postgresql+psycopg://raos:raos@localhost:5432/raos
```

## Tests

```bash
cd backend
pytest -q
```

Cases A–O in `07_MVP_ACCEPTANCE_TESTS.md` are the acceptance suite under `backend/tests/acceptance/`.

## Explicitly not in this slice

Large-scale crawling, recommendation feed, automatic Kernel mutation, WeChat history scraping, learned attention policy.
