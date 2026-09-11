# Phase 10D.6C — Canonical Input Reconciliation Result

**Status:** CLOSED / CANONICAL INPUT IS DECISION-BEARING BUT NOT SUFFICIENT ALONE  
**Valid measurement SHA:** `cd809fd`  
**Artifact:** `eval/live/results/phase10d6c_canonical_input_reconciliation_v0_1/phase10d6c_canonical_input_reconciliation_v0.1_20260911T034802Z.json`  
**SHA256:** `dccddbd86adfa6ed8b3b7eb8724d179ab167975ed3c71a1e1740573e43ae40ab`

The earlier `08963a4` execution is retained separately as a schema-plumbing technical failure with zero valid C1 outcomes; it is not used for semantic conclusions.

## Controlled variable

B0 used the production `ExtractionResult` Impact payload. C1 supplied the same Auditor-admitted canonical units directly (`unit_id`, statement, epistemic status, confidence, supports). Both arms kept the current production system prompt, Kernel, modal Locate, DeepSeek Flash path, importance resolver, `ground_effects`, features, runtime and Pareto + Magnitude-Free + Anchored decision strategy frozen.

## Results

| Case | B0 Attention N=6 | C1 Attention N=6 | Raw -> grounded observation |
|---|---|---|---|
| A | DROP 6 | WATCH 2, DROP 4 | C1 recovers OPEN_NEW in 2/6; both survive grounding |
| D | DROP 6 | AWARE 3, WATCH 1, DROP 2 | C1 recovers 5 raw effects across six runs; most survive grounding |
| X | WATCH 4, AWARE 1, DROP 1 | WATCH 5, AWARE 1 | C1 removes the one DROP realization |
| N4 | WATCH 6 | WATCH 6 | both stable; C1 adds Q1 reinforcement in 2/6 |

The representation change is therefore decision-bearing. A/D effects absent in B0 appear in C1 before grounding, and generally remain after grounding. The dominant measured cause is upstream of `ground_effects`: flattening canonical units into the legacy Impact payload removes information used by Relation Mapping.

## Boundary

Canonical input alone does **not** reproduce the richer Phase-10 native maps. A/D recovery is dominated by OPEN_NEW rather than the multiple targeted REINFORCE/CHALLENGE relations observed under the native Phase-10 Relation-Mapping contract. Therefore `ExtractionResult` flattening is a real causal seam but not the only one.

10D.6B showed prompt-only P1 is also insufficient and can over-suppress X. Together the two experiments motivate an interaction test rather than further one-variable tuning.

## Decision

- Keep production default unchanged.
- Preserve current production grounding/scope/runtime safeguards.
- Treat direct canonical audited units as the preferred vNext cognitive input direction, but do not promote yet.
- Next: **10D.6D — Canonical Input × Reconciled Prompt Interaction**, testing the combined candidate while holding importance authority frozen.
- Target-importance calibration remains deferred until the input/prompt cognitive contract is resolved.
- Phase 9A remains paused.
