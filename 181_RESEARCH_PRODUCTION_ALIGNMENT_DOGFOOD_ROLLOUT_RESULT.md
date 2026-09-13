# Research == Production Developer Dogfood Rollout Result

Date: 2026-09-13
Status: **CLOSED / ACTIVE MAC DOGFOOD ALIGNED**

## 1. Decision

RAOS has no external production users yet. The active Mac runtime is developer dogfood and therefore should not maintain a second cognitive semantics that differs from the research path.

The rollout rule is now:

```text
validated research contract
        =
developer dogfood online contract
```

Legacy code remains available only for historical replay / rollback compatibility. New dogfood AnalysisRuns use the research-aligned contract explicitly.

## 2. Online cognitive contract

Active dogfood cognition is versioned as:

- cognition contract: `research-aligned-cognition-v1`
- decision strategy: `pareto-multidelta-cardinal-free-effect-anchored-open-new-v0.2`
- effect calibration: `magnitude-free-v0.1`
- effect admission: `effect-anchored-open-new-v0.2`

The online path is:

```text
Semantic Sensor
→ Semantic Evidence Auditor
→ Locate
→ Relation Mapping
→ FREEZE topology
→ Support Binding
→ Grounding / OPEN_NEW Jurisdiction
→ deterministic ordinal Authority
→ semantic cardinal-free effect existence
→ Magnitude-Free
→ Pareto
→ Attention
→ exact Decision Cause
→ Public Update / WATCH / KernelPatch
```

## 3. Research contracts shared online

The developer runtime executes the frozen research contracts directly rather than maintaining semantically similar copies:

- Phase 8C.2 Sensor + Auditor bridge
- Phase 9A v0.2 Relation Mapping
- Phase 10D.6L.3 Support Binding
- Phase 10D.6L.4 Grounding
- Phase 10D.6L.4J OPEN_NEW Jurisdiction

The four cognition prompt strings are stored in `backend/app/cognitive/research_aligned_contract.py`; parity tests assert byte identity against the closed research instruments.

Relation Mapping remains relation-only. Its schema has no `change_magnitude`, `epistemic_strength`, `target_importance`, support IDs, jurisdiction IDs, Attention, or ranking authority.

Sensor/Auditor semantic-unit identity and exact support provenance now survive `ExtractionResult`, frozen impact snapshots, cache/replay reconstruction, and `CognitiveEffect`.

`CognitiveEffect` now carries effect-level causal provenance:

```text
support_unit_ids
jurisdiction_anchor_ids
grounding_class
provenance_role
authority_reason
```

This lets downstream responsibility remain attached to the same semantic cause.

## 4. Exact Decision Cause invariant

The research-aligned path no longer performs a second legacy winner selection during artifact synthesis.

For a strategy-bound decision, pipeline first projects the full assessment to the selected `Decision Cause`, then downstream synthesis consumes only that projected semantic effect.

The intended invariant is now executable:

```text
Decision Cause
= Public Update Cause
= WATCH responsibility scope
= authorized ModelDelta / KernelPatch Cause
```

Targeted effects bind exact target scope. OPEN_NEW effects use exact `jurisdiction_anchor_ids` when available; global-Locate jurisdiction remains only a legacy compatibility fallback.

A focused ENGAGE test confirms that a cardinal-free `CHALLENGE` selected as Decision Cause generates a KernelPatch against the same target node, without consulting raw magnitude.

## 5. Active Mac dogfood configuration

The local `.env` was switched to:

```text
RAOS_COGNITIVE_PROVIDER=model
RAOS_COGNITIVE_CONTRACT=research-aligned-v1
RAOS_DECISION_STRATEGY_ID=pareto-multidelta-cardinal-free-effect-anchored-open-new
```

Repository compatibility defaults remain legacy so historical replay and rollback remain possible. The active developer runtime explicitly opts into the aligned contract.

## 6. Live end-to-end smoke

A real HTTP analysis was executed against the running Mac backend using a technical robotics measurement source comparable to the N4 evidence family.

Successful AnalysisRun:

```text
run_id = d20b65dd-48eb-454f-80b7-4d5c50f1ff14
attempt = 2
status = COMPLETED
provider = model / deepseek-flash
fallback_used = false
```

Observed execution identity:

```text
extraction_path.mode = bridge
bridge = phase8c2-production-sensor-bridge-v0.2
sensor = semantic-evidence-extractor-v0.2.6
auditor = semantic-evidence-auditor-v0.1.1
cognition = research-aligned-cognition-v1
decision strategy = pareto-multidelta-cardinal-free-effect-anchored-open-new-v0.2
```

The Sensor/Auditor admitted five semantic units. Relation Mapping produced three targeted `REINFORCE` relations. Support Binding attached exact source-namespaced semantic-unit IDs, and Grounding classified the relations as `DIRECT`, `DIRECT`, and `PARTIAL`.

The selected Decision Cause was:

```text
REINFORCE(BOTTLENECK)
support_unit_ids = [...:neu-0002]
grounding = PARTIAL
provenance = PRIMARY_SOURCE
importance = HIGH
epistemic = WEAK
```

This produced `WATCH`, not ENGAGE. The public update was the same `REINFORCE` on the same bottleneck, and the created Watch targeted that same bottleneck with the same `analysis_run_id` and `attention_plan_id`.

No KernelPatch was authorized for this WATCH outcome, as expected.

After the backend was restarted with the final code, a normal `/analysis/run` call on the same source returned the same completed run in `0.066s`, proving the running server loaded the same research-aligned execution identity rather than creating a legacy-path run.

## 7. Dogfood deployment residuals found and repaired

The first live smoke reached WATCH persistence but failed because the local SQLite database was still at Alembic revision `0003_slice21_hardening`, while the code expected the current schema through `0008_watch_recheck_history`.

The local database was upgraded through the existing Alembic chain:

```text
0003_slice21_hardening
→ 0008_watch_recheck_history (head)
```

No hand-written schema mutation was used.

The failed first smoke also exposed a transaction-recovery bug: a database flush error poisoned the SQLAlchemy session, and the old exception handler attempted to mark the AnalysisRun `FAILED` before rolling back. The FAILED update was therefore rolled back too, leaving a permanent live `RUNNING` identity.

The orphaned smoke run was explicitly recovered to `FAILED`, and production code now uses `fail_run_after_rollback()`:

```text
pipeline/database exception
→ rollback poisoned transaction
→ reopen persisted AnalysisRun in a clean transaction
→ mark FAILED + completed_at + error
→ commit
```

If the failed run itself never persisted, the recovery function safely returns without manufacturing state. A regression test forces an `IntegrityError` after a persisted RUNNING row and verifies that the identity is released as `FAILED`.

## 8. Verification

Focused research/production alignment regression:

```text
37 passed, 1 warning
```

Failure-recovery and adjacent focused regression:

```text
18 passed, 1 warning
```

Final full backend regression:

```text
701 passed
63 skipped
1 failed
1 warning
```
The sole failure remains the historical acceptance Case K:

```text
expected urgency = PREEMPT
actual urgency   = PRIORITY
```

No new regression failure was introduced by the rollout.

## 9. Closure

Status: **CLOSED / ACTIVE MAC DOGFOOD ALIGNED**.

The practical operating rule is now:

```text
new developer dogfood AnalysisRun
→ research-aligned-cognition-v1
→ audited Sensor/Auditor representation
→ effect-specific semantic provenance
→ cardinal-free Magnitude-Free/Pareto decision
→ exact Decision Cause downstream
```

Legacy cognition remains available only as an explicit historical replay / rollback compatibility path; it is no longer the active Mac dogfood semantics.

No separate research-to-production promotion audit is required while RAOS has no external production users. Real dogfood use is now the next source of residuals and research questions. Any future semantic change should be validated in research and then become the shared online contract, rather than creating a second production-only interpretation.
