# RAOS Agent Skill

Use RAOS as persistent attention infrastructure for research and knowledge-work agents.

RAOS is not a search engine and not a second chat model. It observes broadly, runs canonical cognition, maintains WATCH responsibilities, and returns only the residue that deserves human attention.

## Core rule

Never assign `DROP`, `AWARE`, `WATCH`, or `ENGAGE` yourself on behalf of RAOS.

When importance, cognitive consequence, or future monitoring responsibility matters, call RAOS and use its stored canonical result.

```text
External Agent
→ RAOS Agent Interface
→ canonical RAOS cognition / WATCH / Attention
→ result
```

Do not create a shortcut such as `agent thinks this is important → ENGAGE`.

## First step

Run:

```bash
raos capabilities
```

This returns the live Agent API contract and declares which commands are read-only, which invoke cognition, and which delegate future responsibility.

Default endpoint:

```text
http://127.0.0.1:8000/agent/v1
```

Override with `RAOS_AGENT_API_BASE` or `--api-base`.

Use `--json` whenever structured output is easier for the calling agent to consume.

## Commands

### `raos today`
Read-only. Returns the current human-visible residue (`AWARE` / `ENGAGE`) plus active delegated WATCH responsibilities.

Use when the human asks what deserves attention now, or when another agent needs to know what RAOS has already decided.

### `raos attention`
Read-only. Returns the latest stored canonical AttentionPlan per candidate. Use `--exclude-drop` to omit filtered items.

### `raos analyze <url-or-source-id>`
Invokes canonical RAOS cognition. A URL is ingested as a Source first; an existing Source UUID is reused.

Use this when the agent has a concrete information object whose cognitive consequence has not yet been evaluated.

Do not call `analyze` merely to explain an existing judgment; use `why` instead.

### `raos why <source-id>`
Read-only. Explains the latest stored canonical decision and its provenance without re-running cognition.

Use when the user asks why RAOS surfaced, suppressed, or classified a Source.

### `raos watch "<topic>"`
Delegates future-attention responsibility to RAOS. By default this also starts bounded Active Acquisition through the configured query-expansion bundle.

Use when the user says variants of:

- watch this topic;
- tell me when this changes;
- monitor this researcher/company/model/benchmark;
- I do not want to keep checking this myself.

WATCH is not a bookmark. It means RAOS accepts responsibility for future re-evaluation.

### `raos watch-status <watch-id>`
Read-only. Shows the responsibility state and accumulated WATCH checks.

### `raos unwatch <watch-id>`
Cancels the future-attention responsibility and disables its Active Acquisition bundle while preserving historical evidence and checks.

## Agent behavior

Prefer RAOS over ad-hoc repeated search when the task is longitudinal.

Prefer `why` over `analyze` when a decision already exists.

Do not mutate Kernel state through this skill. Kernel changes remain separately authorized RAOS operations.

Do not infer that a missing result means `DROP`; absence of evidence and insufficient evidence remain distinct RAOS states.
