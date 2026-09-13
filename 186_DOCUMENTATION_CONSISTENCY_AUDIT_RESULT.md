# RAOS Documentation Consistency Audit Result

Date: 2026-09-13
Status: CLOSED
Scope: repository documentation consistency against current developer-dogfood HEAD

## 1. Why this audit was needed

RAOS evolved quickly from early MVP rules through Sensor/Auditor research, D/S/P calibration, Multi-Delta/Pareto cognition, research-aligned dogfood, Acquisition, and source-centric UI.

Several older documents were still internally correct as historical records but could be misread as current deployment truth. Examples included `production default remains legacy`, `Phase 9A remains paused`, RSS as a future connector, and `Delta=NONE` being treated as automatic DROP.

The goal of this audit was not to rewrite history. It was to make current authority explicit while preserving experimental provenance.

## 2. Documentation authority hierarchy

### Level 1 — current HEAD truth

- `RAOS_CANONICAL_ARCHITECTURE.md` — authoritative online architecture and authority split.
- `35_RAOS_MATHEMATICAL_LANGUAGE_REGISTRY.md` — authoritative mathematical/semantic quick reference.
- `11_ROADMAP_AND_PROGRESS.md` — current project progression and latest closures.
- `README.md` — current operator/developer entry point.

If these disagree with code, the mismatch is an explicit defect to resolve.

### Level 2 — living subsystem specifications

These remain maintained conceptual/specification documents, but must defer to the canonical HEAD architecture for exact online wiring:

- `01_PRODUCT.md`
- `02_DOMAIN_MODEL.md`
- `03_DATABASE_SCHEMA.md`
- `04_SCHEDULER_SPEC.md`
- `05_INGESTION_SPEC.md`
- `06_SOURCE_GRAPH_SPEC.md`
- `49_RAOS_CORE_MODULE_POSITIONING.md`
- `50_SEMANTIC_EVIDENCE_AUDITOR_ROLE_AND_BOUNDARIES.md`
- `61_SEMANTIC_SENSOR_RESEARCH_PRODUCTION_MODEL_STRATEGY.md`
- `68_RAOS_DUAL_WORLD_MODEL_AND_PERCEPTION_DISCIPLINE.md`

`07_MVP_ACCEPTANCE_TESTS.md` remains a foundational regression/product-behavior suite, not an exhaustive current-HEAD cognition specification.

### Level 3 — historical research provenance

Preregistrations, experiment results, failed-run amendments, checkpoints, and phase-opening documents preserve the state that was true at measurement time.

They must not be silently rewritten to match later deployment. When an old `ACTIVE`, `current frontier`, or `production default` label is likely to mislead a future reader, add a short historical/superseded status note while leaving the original experimental content intact.

## 3. Main corrections made

The audit aligned current living documentation with these HEAD facts:

1. Acquisition is a first-class plane before normalized RAOS `Source`; discovery/polling is not part of cognition.
2. Current unattended Acquisition v0.1 uses Source Registry + independent worker + RSS/Atom transport with present-time baseline semantics and per-Source failure isolation.
3. Active developer dogfood runs the validated research-aligned cognition contract; repository legacy/rule defaults exist for compatibility, not as the active semantic path.
4. The cognitive branch is Relation Mapping → Support Binding → Grounding / OPEN_NEW Jurisdiction → Authority → cardinal-free effect existence → Magnitude-Free / Pareto.
5. `Decision Cause = Public Update Cause = Authorized Side-Effect Cause` remains the causal invariant.
6. `Delta=NONE` does not imply DROP. The orthogonal audited-event D/S/P branch owns no-Delta DROP/AWARE using `AWARE iff S AND (D OR P)`.
7. `UNKNOWN` is not False; observed, estimated, and simulated P evidence must remain provenance-distinct.
8. The active Sensor/Auditor path is v0.2.6 / v0.1.1 and is shared by cognitive and no-Delta branches.
9. Current migration head is `0009_acquisition_plane_v01`; AnalysisRun, WatchCheck, Acquisition objects, and current Attention provenance are reflected in living schema docs.
10. The Attention UI is source-centric rather than a raw AttentionPlan ledger; historical dev data may still coexist with live dogfood data until explicitly separated.

## 4. Historical-status clarification

Selected older documents that still advertised themselves as the active/current phase received a non-destructive historical note, including Phase 6/7/8 integration and Sensor/Auditor development checkpoints.

The original result text, preregistered claims, old defaults, and measurement-time conclusions were intentionally preserved.

## 5. Deliberate non-changes

This audit did **not** reopen any RAOS theory or experimental result.

In particular:

- no new canonical mathematical state variable was introduced;
- D, S, P, Delta, and Attention semantics were not redefined;
- historical `production default remains legacy` statements were not rewritten inside old result bodies;
- old failed artifacts and preregistration constraints were not normalized to later behavior;
- no code, model prompt, decision strategy, or runtime configuration was changed by this documentation audit.

During review, an attempted `W_t` addition to the mathematical registry was explicitly rejected because documenting Acquisition must not silently change the mathematical theory.

## 6. Validation

Repository-wide Markdown-reference scan found:

```text
missing referenced .md files = 0
```

Living-document stale-signal scans were rerun after edits for old one-delta/legacy deployment claims, future-only RSS/crawler claims, duplicate canonical-architecture authority, and automatic no-Delta DROP semantics.

`03_DATABASE_SCHEMA.md` now explicitly labels itself a living conceptual schema and defers physical truth to current SQLAlchemy models and Alembic migrations.