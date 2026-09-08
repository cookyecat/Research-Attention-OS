# Phase 8 — Narrow Continuous Attention Loop

Status: **ACTIVE**
Opened: 2026-09-08

## 1. Goal

Phase 8 moves RAOS from static single-shot analysis into a narrow continuous operating loop.

The first objective is not broad crawling. It is to prove that an attention obligation can persist through time:

```text
information -> WATCH -> later evidence -> re-evaluate -> keep waiting or surface
```

A WATCH label is insufficient. WATCH means the system assumes future attention responsibility.
## 2. Phase 8A — WATCH Responsibility Loop

Required semantics:

```text
ACTIVE WATCH
+ new evidence
-> cumulative re-evaluation
-> DROP/WATCH  => KEEP_ACTIVE
-> AWARE/ENGAGE => PROMOTED
```

Every recheck must be auditable through a WatchCheck record. Existing WATCH rechecks must not create duplicate Watch obligations.

Cumulative evidence is mandatory: if evidence B was already incorporated, the next recheck with C must analyze A+B+C rather than A+C.
## 3. Exit criterion

Phase 8A is sufficient when a controlled lifecycle demonstrates all of the following on one exact SHA:

```text
WATCH created
first recheck keeps obligation ACTIVE
second recheck preserves prior evidence and PROMOTES
WatchCheck history records both decisions
no duplicate Watch is created
```

After 8A, Phase 8 should add narrow ingestion/dogfooding rather than expanding synthetic lifecycle cases indefinitely.
