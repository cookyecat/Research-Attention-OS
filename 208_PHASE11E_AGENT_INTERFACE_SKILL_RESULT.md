# Phase 11E — Agent Interface / Skill Result

Status: **CLOSED**
Date: 2026-09-15
Parent: `198_PHASE11_EXTERNAL_ATTENTION_INFRASTRUCTURE_PLAN.md`
Preregistration: `207_PHASE11E_AGENT_INTERFACE_SKILL_PREREGISTRATION.md`

## 1. Result

RAOS now exposes a stable external-agent surface without creating a second cognition or Attention authority.

```text
External Agent
→ /agent/v1 or `raos` CLI
→ existing ingestion / cognition / WATCH / Attention / Delivery
```

The Agent facade never instantiates `AttentionPlan` and never calls an independent importance/relevance LLM. `DROP / AWARE / WATCH / ENGAGE` remain canonical RAOS outputs only.

## 2. Stable v0.1 surface

Agent API:

```text
GET  /agent/v1/capabilities
GET  /agent/v1/today
GET  /agent/v1/attention
POST /agent/v1/analyze
POST /agent/v1/watch
GET  /agent/v1/watch/{id}
POST /agent/v1/watch/{id}/cancel
GET  /agent/v1/why/{source_id}
```

CLI mirrors the same contract through HTTP rather than importing cognition internals.

```text
raos capabilities
raos today
raos attention
raos analyze <url-or-source-id>
raos watch "<topic>"
raos watch-status <id>
raos unwatch <id>
raos why <source-id>
```

`skills/raos/SKILL.md` packages the same semantics for external coding/research agents. MCP/A2A remain future transports over this API rather than separate semantic paths.

## 3. Real CLI dogfood

`raos capabilities` reported `canonical_raos_only` attention authority. `raos today` read current AWARE/ENGAGE residue and delegated WATCH responsibilities without cognition. `raos why` explained an existing ENGAGE decision with `reanalysis_performed=false`.
A research WATCH for `Google EnvHarness` was created through the CLI, expanded to four bounded retrieval queries, inspected, then cancelled. Cancellation also disabled its Active Acquisition bundle while preserving history.

Explicit CLI analysis of the existing `latency paper` Source entered the canonical pipeline and produced a new `DROP / NORMAL` plan plus a `SUPPRESSED` Phase 11D DeliveryEnvelope. The older historical decision for the same Source had been `ENGAGE / PRIORITY`; this difference demonstrates that the Agent Interface does not preserve or invent labels and instead defers to current canonical cognition.

## 4. Boundary correction

Phase 11E exposed one useful Phase 11B edge case. Short but explicit named targets such as `Google EnvHarness` are now valid self-contained WATCH intents for named target types. Generic trigger labels such as `code release`, `paper release`, or `new evidence` still require origin context and cannot become broad searches by themselves.

## 5. Validation

Phase 11A–11E plus WATCH/Attention/provenance focused regression:

```text
108 passed
1 existing Starlette/httpx deprecation warning
```

## 6. Adjacent Delivery hardening

Phase 11E dogfood also hardened the Phase 11D email transport: multiple recipients are supported through comma/semicolon-separated local configuration, and both STARTTLS and implicit SSL SMTP modes are supported.

Network preflight from the dogfood Mac reached Gmail and 163 SMTP endpoints. No SMTP sender credential is currently configured, so no real external email was falsely reported as sent. User delivery addresses remain local configuration only and are not persisted in repository tests or documentation.

## 7. Phase 11 conclusion

Phase 11 is closed. RAOS can now observe broadly, actively acquire for delegated WATCH responsibilities, measure real public-attention evidence for event-level P, execute sparse delivery, and expose the same attention infrastructure to external agents through one canonical authority path.

Phase 12 — Personalization / Scale — is next.
