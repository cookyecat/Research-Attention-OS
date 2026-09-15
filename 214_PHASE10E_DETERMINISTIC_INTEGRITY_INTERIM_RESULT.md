# Phase 10E — Deterministic Integrity Interim Result

Date: 2026-09-16
Status: **GATE I PASS / GATE II HUMAN GOLD DEFERRED**
Production policy change: **none**
Operational decision: **continue current Core dogfood; do not redesign Pareto/Core from synthetic corner cases**

## 1. Scope clarification: Oracle-Delta was an eval harness, not the production pipeline

The historical Oracle-Delta path was introduced in commit `78c5c1b` on 2026-09-05 with the explicit scope: `Add Oracle-Delta Attention Policy eval path without changing production route.`

Its purpose was to freeze Delta/Human Gold, skip Extract/Locate/Impact, and isolate the then-current Attention Policy. `eval/live/oracle_policy.py` calls `scheduler.route()` without an explicit decision strategy. After the pluggable strategy seam was introduced in commit `664a906` on 2026-09-10, bare `route()` calls continued to preserve the legacy `one-delta-v1` compatibility contract. The old Oracle harness was not upgraded to select the later active Pareto/Magnitude-Free strategy.

Therefore:

```text
old Oracle-Delta frozen replay
→ bare route()
→ legacy one-delta-v1
```

This is an **evaluation-harness era mismatch**. It is not evidence that acquisition, frontend dogfood, continuous source arrival, WATCH, Delivery, Agent Interface, or the normal production analysis pipeline silently used legacy one-delta.

The current production pipeline resolves `decision_strategy = decision_strategy or get_decision_strategy()`, snapshots its id/version, and explicitly passes it into `route(...)`.

## 2. What historical evidence is affected

Affected / historical-only:

```text
Oracle-Delta / Oracle-Awareness policy-isolation results that relied on eval/live/oracle_policy.py
including the exploratory historical 30-case Human-Gold replay
```

These remain useful as historical hypotheses about Attention behavior, but they are not measurements of the current Phase-10 decision strategy.

Not invalidated by this issue:

```text
real acquisition → cognition → Attention pipeline dogfood
Phase 8C+ decision-strategy experiments that explicitly supplied a strategy
frontend/product integration against persisted production plans
Phase 11 acquisition / delivery / agent-interface dogfood through canonical pipeline
current persisted AnalysisRuns carrying explicit decision-strategy snapshots
```

## 3. Canonical Gate-I measurement

Versioned instrument: `eval/live/run_phase10e_core_validity_gate_v0_1.py`

Canonical artifact:

`eval/live/results/phase10e_core_validity_v0_1/phase10e_core_validity_v0.1_20260915T182340Z.json`

Observed current-strategy persisted runs:

```text
eligible current-strategy runs                78
exact disposition replay                     78 / 78
exact strategy identity replay               78 / 78
exact decision-cause replay                  78 / 78
audit errors                                  0
```

Thus the current persisted production decision path is deterministically replayable from its frozen engineering state under the stored strategy snapshot.

## 4. Pareto operating-regime check

Among current-strategy runs, three contained non-empty research-aligned effect sets. On those actually observed states:

```text
Pareto → channel policy → article join
vs
all admitted effects → same channel policy → article join
```

produced:

```text
disposition differences      0
decision-cause differences   0
```

The previously found `25 / 946` two-effect differences remain **synthetic algebraic counterexamples**, not an observed production failure rate. They are recorded for future flywheel monitoring and do not currently justify a Core change.

## 5. Interim decision

Phase 10E Gate I — Deterministic Integrity: **PASS**.

Current Core status:

```text
USE AS-IS for continued dogfood
Pareto = KEEP + MEASURE
no scheduler tuning
no new Core variable
no personalization fitting from historical Oracle-Delta Gold
```

Gate II — Operating-Regime Adequacy requires fresh Human Gold and is intentionally **DEFERRED** until the user chooses to run it. Phase 12 calibration remains paused; ordinary RAOS dogfood may continue.
