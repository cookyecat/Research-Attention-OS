# Phase 11E — Agent Interface / Skill Preregistration

Status: **PREREGISTERED / IMPLEMENTATION ACTIVE**
Date: 2026-09-15
Parent plan: `198_PHASE11_EXTERNAL_ATTENTION_INFRASTRUCTURE_PLAN.md`
Depends on: Phase 11D closed result `206_PHASE11D_DELIVERY_PLANE_RESULT.md`

## 1. Question

Can RAOS expose its attention infrastructure to external agents through a stable API/CLI/Skill without creating a second cognition or Attention authority?

Canonical boundary:

```text
External Agent
→ RAOS Agent Interface
→ existing RAOS ingestion / cognition / WATCH / Attention / Delivery
```

Forbidden shortcut:

```text
Agent LLM says important
→ direct AWARE / WATCH / ENGAGE
```

The Agent Interface is orchestration and presentation only. Canonical RAOS remains the sole semantic authority.

## 2. v0.1 capability surface

Stable `/agent/v1` capabilities:

```text
GET  /today                 current human-visible residue + delegated WATCH summary
GET  /attention             current latest Attention state per candidate
POST /analyze               explicit URL/source analysis through canonical pipeline
POST /watch                 create canonical WATCH + optional Active Acquisition
GET  /watch/{id}            inspect delegated responsibility / checks / triggers
POST /watch/{id}/cancel     cancel WATCH and disable its Active Acquisition bundle
GET  /why/{source_id}       explain stored latest canonical decision without reanalysis
```

CLI mirrors the same API:

```text
raos today
raos attention
raos analyze <url-or-source-id>
raos watch "<topic>"
raos watch-status <id>
raos unwatch <id>
raos why <source-id>
```

The CLI calls the Agent API over HTTP; it does not import internal cognition services. This keeps local and remote agents on the same contract.

## 3. Semantic invariants

1. `today` and `attention` are reads over stored canonical plans; they must not trigger cognition.
2. `analyze` is explicit cognition. URL input first enters ordinary Source ingestion, then the existing production pipeline.
3. `watch` creates an ordinary canonical `Watch`; optional Query Expansion changes observation scope only.
4. `why` explains the stored latest decision; it must not silently re-run analysis.
5. `unwatch` cancels responsibility and stops the corresponding Active Acquisition bundle; it does not delete historical evidence.
6. Agent API code must never instantiate `AttentionPlan` directly and must never call an independent importance/relevance LLM.
7. Delivery remains downstream of canonical Attention, including when analysis was initiated by an Agent.
8. Reading or retrieving a Source through an Agent never implicitly triggers cognition.

## 4. Skill contract

`skills/raos/SKILL.md` will describe when an external coding/research Agent should delegate to RAOS. The Skill may teach command usage, but it must explicitly prohibit substituting the Agent's own judgment for a RAOS disposition.

MCP/A2A are transport candidates over the same Agent API and are not separate semantic implementations in v0.1.

## 5. Close criteria

11E closes when: the API supports Today/Attention/Analyze/WATCH/Why/Cancel; the CLI mirrors those capabilities over HTTP; the Skill is packaged; tests prove no direct Agent-side Attention authority; an actual CLI dogfood can read Today, explain an existing Source, create and inspect a research WATCH with Active Acquisition, then cancel it cleanly; explicit Agent analysis still creates an ordinary canonical AttentionPlan and Phase 11D DeliveryEnvelope; and living architecture/docs are updated.
