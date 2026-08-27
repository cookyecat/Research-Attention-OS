# Research Attention OS — PRODUCT.md

Version: RAOS v1.1
Status: Development Baseline

## 1. Product definition

Research Attention OS (RAOS) is a personal cognitive operating system for researchers. It sits between the external information world and the researcher:

```text
External Information World
        ↓
Research Attention OS
        ↓
Researcher
```

RAOS does not aim to help the user read more. It allocates finite human attention to information most likely to change research understanding, decisions, and actions.

Primary optimization target:

CROA = Useful Cognitive Change / Human Attention Cost

Useful Cognitive Change includes belief update, model revision, new research question, hypothesis formation, bottleneck identification, decision change, and experiment generation.

## 2. Product thesis

The bottleneck has shifted from finding information to deciding:
1. what deserves attention;
2. how deeply to process it;
3. whether it changes the researcher's model;
4. whether action should follow.

## 3. Non-goals

RAOS v1.1 is not:
- a generic RSS reader;
- a news portal;
- a Zotero/Notion replacement;
- a paper summarizer;
- a bookmark manager;
- an infinite recommendation feed;
- an autonomous agent that silently edits user beliefs;
- a full web crawler;
- a general-purpose knowledge graph.

## 4. Constitution: non-negotiable invariants

### Rule 1 — Document is not the unit of cognition
Documents are source containers. The system reasons over Event, Claim, Observation, Inference, EvidenceLink, Question, Belief, Hypothesis, Model, and Decision.

### Rule 2 — Information value is relative to Cognitive State
Scheduler decisions must consider:
```text
Information Candidate
+ Cognitive Kernel
+ Runtime Context
+ Attention Policy
```

### Rule 3 — AI cannot silently rewrite the researcher
The LLM may propose KernelPatch objects but may not directly commit Belief, Model, Hypothesis, or Decision changes. Human Accept or Modify is required.

### Rule 4 — Disagreement is not low relevance
High relevance + high disagreement should usually raise `disposition` toward ENGAGE with `update.operation = CHALLENGE`, not DROP.

### Rule 5 — Claim, Observation, and Inference remain distinct
"Company says X" must never become "X is true". AI inference may not be persisted as observation.

### Rule 6 — Kernel remains small and high-density
The Kernel stores active Researcher State, not all accumulated information.

## 5. System architecture

```text
0. SOURCE INGESTION
        ↓
1. INFORMATION PLANE
        ↓
2. EPISTEMIC PLANE
        ↓
3. COGNITIVE SCHEDULER
        ↓
4. COGNITIVE KERNEL
        ↓
5. EXECUTION / FEEDBACK
```

### Source Ingestion
Receives external material and normalizes it into Source.

### Information Plane
Represents what happened and what was said:
- Source
- Event
- Claim
- Observation

### Epistemic Plane
Represents what information means relative to assertions:
- Inference
- EvidenceLink
- provenance
- credibility
- contradiction

### Cognitive Scheduler
Produces an AttentionPlan.

### Cognitive Kernel
Stores:
```text
INTENT: Goal / Project / Bottleneck
EPISTEMIC: Question / Belief / Hypothesis / Model
EXECUTION: Decision / Experiment
```

### Execution / Feedback
Stores human actions, experiment outcomes, new observations, and scheduler feedback.

## 6. UX principles

- No infinite feed.
- Home shows scheduled cognitive work, not unread-count anxiety.
- "Discarded" is a positive outcome.
- WATCH transfers attention responsibility to the system.
- Kernel UI emphasizes state changes, not document folders.

Example home:
```text
1 item may affect your current decision.
3 items deserve attention.
11 topics are being watched.
186 items were discarded.
Estimated attention required: 24 minutes.
```

## 7. v1.1 MVP objective

Prove one vertical slice:

```text
Source
  ↓
Claim / Observation extraction
  ↓
Kernel Match
  ↓
AttentionPlan
  ↓
Model Delta
  ↓
KernelPatch
  ↓
Human Accept / Modify / Reject
```

## 8. MVP input types

Required:
- pasted text;
- URL;
- PDF;
- manual user observation.

Optional after the core slice passes:
- arXiv;
- RSS;
- GitHub;
- WeChat shared URL.

## 9. MVP required capabilities

1. Create Source.
2. Extract Event, Claims, and Observations.
3. Match information to Kernel nodes.
4. Produce AttentionPlan.
5. Produce "What could this change?" Model Delta.
6. Produce KernelPatch.
7. Human Accept / Modify / Reject.
8. Create WATCH objects.
9. Preserve provenance and version history.

## 10. Explicitly out of scope for first implementation

- large-scale crawling;
- autonomous WeChat history crawling;
- recommendation feed;
- reward-model training;
- social features;
- automatic Kernel mutation;
- giant ontology;
- multi-agent orchestration;
- complex million-document event clustering.

## 11. Reference implementation defaults

Backend:
- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic

Database:
- PostgreSQL 16+
- pgvector

Background jobs:
- Redis
- Celery or equivalent

Frontend:
- Next.js
- TypeScript
- React

Storage:
- local filesystem in development;
- S3-compatible abstraction in production.

Tests:
- pytest;
- Playwright.

Product semantics take priority over stack preferences.

## 12. Initial UI surfaces

### Inbox / Add Source
Paste text, URL, upload PDF, or add observation.

### Attention
Show extracted cognitive objects, Kernel match, and AttentionPlan.

### Kernel
Show active Goals, Projects, Bottlenecks, Questions, Beliefs, Hypotheses, Models, Decisions, Experiments.

### Watch
Show active watches and triggers.

## 13. Codex implementation rule

When a product requirement conflicts with implementation convenience, preserve the epistemic/product invariant.

Codex must not:
- convert claims into facts;
- store AI inference as user belief;
- merge all objects into generic notes;
- allow automatic Kernel commits;
- replace AttentionPlan with one relevance score.

## 14. Definition of success

Given a pasted article and a pre-existing Kernel, the application can:
1. persist the article as Source;
2. extract attributed Claims;
3. separate Observations from Inferences;
4. identify Kernel matches;
5. produce a justified AttentionPlan;
6. explain what could change in the Kernel;
7. generate a KernelPatch proposal;
8. require explicit confirmation before commit;
9. preserve provenance and history;
10. pass `07_MVP_ACCEPTANCE_TESTS.md`.
