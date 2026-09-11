# Phase 10D.6L — End-to-End Business Logic Integrity Audit

**Status:** ACTIVE / ALL NEW COGNITIVE OUTCOME SAMPLING PAUSED
**Date:** 2026-09-11

## Why this gate exists

10D.6K exposed two independent cases where legacy business logic or instrumentation changed the semantics of an otherwise controlled experiment. Before any further Attention or Phase 9A outcome sampling, audit the full cognition-to-side-effect path for hidden authority, duplicated rules, cache identity gaps, and production/research divergence.

## Authoritative invariants

1. `Decision Cause = Public Update Cause = Authorized Side-Effect Cause` unless a versioned projection explicitly declares and safely contains a lossy compatibility view.
2. Effect-existence / legality belongs to the selected Decision Strategy. Measurement and replay code must not silently re-filter effects with another policy.
3. A frozen strategy / prompt / cognitive contract must be part of execution identity. Cache hit, reschedule, replay, and live execution must not change semantics because of control-flow state.
4. LLM semantic judgment must not regain hidden cardinal decision authority through compatibility fields.
5. WATCH responsibility and OPEN_NEW jurisdiction should trace to causal effect-specific anchors, not unrelated global matches when exact provenance is available.

## Confirmed findings so far

### P0 — Pareto decision cause can diverge from public update / patch cause
`ParetoMultiDeltaDecisionStrategy.route()` chooses article Attention from the Pareto frontier, but `visible_prediction()`, `ModelBackedCognitiveProvider.propose_model_delta()`, and patch synthesis still use legacy `select_primary_effect()` / `primary_update()` ranked by `change_magnitude × target_importance`.

A synthetic counterexample reproduces: effect A is the unique Magnitude-Free Pareto cause of `ENGAGE + KERNEL_PATCH`, while legacy public update selects effect B because B has larger raw magnitude. This can make the cognitive side effect land on a different relation/target from the effect that authorized the side effect.

### P1 — explicit strategy may be lost on completed-run runtime reschedule
`run_pipeline()` passes an explicit `decision_strategy` into the RUNNING→COMPLETED reschedule path, but the immediate existing-COMPLETED fast path calls `_reschedule()` without it. `_reschedule()` then falls back to current settings.

### P0/P1 — Impact prompt/contract missing from AnalysisRun execution identity
`ModelBackedCognitiveProvider` supports `_impact_system_prompt` and `impact_contract_version`, but `analysis_execution_snapshot()` fingerprints model/runtime/retrieval without either the prompt hash or contract version. Two semantically different Impact contracts can therefore share an AnalysisRun identity unless forced reprocess is used.

### P1 — causal responsibility is not carried into WATCH / OPEN_NEW side effects
`PlanDraft` does not retain frontier/representative effect identity. Policy-created WATCH stores all Locate matches and uses the first match title as `target_ref`. `AnchoredOpenNewAdmission` admits OPEN_NEW when any global match is a jurisdiction anchor. These are legacy approximations; the new support-bound contract has exact effect-level jurisdiction/support provenance that is currently discarded before side effects.

## Audit scope before fixes

- production acquisition / extraction bridge / Locate / Impact provider and prompt identity;
- effect legality, grounding, authority enrichment, Anchored, Magnitude-Free, Pareto, Attention join;
- runtime overlays and reschedule paths;
- public update / delta / KernelPatch / WATCH authorization and target binding;
- AnalysisRun identity, hydration, replay, execution snapshots;
- Decision-Causal Core and other eval instrumentation for semantic duplication;
- fallback/provider provenance and versioning.

No new 10D.6K or Phase 9A cognitive outcomes are valid until P0 audit items are repaired and regression-tested.

## Regression checkpoint — 2026-09-11

After the P0/P1 repairs through commit `c65e140`, the full backend regression is `666 passed, 63 skipped, 1 failed, 1 warning`. The sole failure is the pre-existing `tests/acceptance/test_cases.py::test_case_k_preempt` (`PREEMPT` expected, `PRIORITY` actual); no new regression failure was introduced and Case K remains intentionally untouched.

The remaining production semantic blocker is upstream Impact prompt authority: the mature production prompt still contains (a) an OPEN_NEW `change_magnitude >= 0.55` materiality instruction and (b) a single-winner `change_magnitude × target_importance` public-update instruction. `IMPACT_SYSTEM_PARETO_COMPAT` removes exactly those two downstream-policy instructions and changes nothing else. It is experimental only; production default is unchanged pending a controlled shadow.

OPEN_NEW jurisdiction is no longer a hidden responsibility bug: current production explicitly labels its decision scope as `global-locate-jurisdiction-approximation`; exact effect-level `jurisdiction_anchor_ids` remain a research-contract gap rather than an implicit production truth.

## Repair status after first end-to-end pass

### REPAIRED / regression-locked

- `cfd6204`: Impact prompt/contract hash is part of AnalysisRun execution identity; explicit decision strategy survives completed-run reschedule.
- `cba6e6f`: strategy-selected `decision_cause` is carried through public update, ModelDelta, and KernelPatch authorization. Legacy single-primary selection is no longer allowed to choose a different side-effect target after Pareto Attention has decided.
- `fb2a37d` + `48c29ad`: policy WATCH and `AttentionPlan.kernel_target_ids` consume explicit decision scope. Targeted effects use exact target scope; current OPEN_NEW scope is explicitly labeled `global-locate-jurisdiction-approximation` rather than masquerading as exact effect provenance.
- `b712f78`: runtime reschedule preserves the provider selected by the identity-bearing `run_pipeline()` call instead of silently reacquiring a global provider.
- `09c066d`: Impact Replay separates historical `primary_update` as a legacy Impact-local projection from the persisted strategy-selected decision cause. Impact-only replay does not claim to re-execute the decision stage.
- `db65ed5`: completed AnalysisRun provenance records the actual fallback path (`model+rule-fallback`) while preserving identity as the planned execution contract.
- `dee5d84`: Pareto execution snapshots now declare decision-cause public projection and strategy-bound decision scope, so execution metadata matches current semantics.

Focused regressions for these repairs have passed; no new cognitive outcome samples were collected.

### AUDITED / non-blocking compatibility layers

- `features_from_impact()` still derives compatibility/debug numeric features from the legacy primary projection, but Magnitude-Free/Pareto disposition does not consume those projected cardinal fields. Empty Pareto frontier remains fail-closed DROP unless explicit `AwarenessSignals` are supplied.
- Legacy `primary_update()` / `select_primary_effect()` remain intentionally available for one-delta history, legacy replay diagnostics, and already-projected single-effect synthesis. They are no longer allowed to reselect a cause after a bound Pareto decision.
- Decision-strategy hydration checks stored strategy version and fails on version mismatch rather than silently interpreting an old run with a different registered version.

### REMAINING BLOCKERS

1. **Production Impact prompt still contains downstream-policy authority.** The current default `IMPACT_SYSTEM` still instructs the LLM to threshold OPEN_NEW by `change_magnitude` and choose one public update by `change_magnitude × target_importance`, which conflicts with multi-effect Pareto semantics before downstream policy can act. `833a7bb` introduces `IMPACT_SYSTEM_PARETO_COMPAT`, defined as the mature production prompt with only those two downstream-policy lines removed. It is experimental only; production default is unchanged until a controlled shadow validates it.
2. **Exact OPEN_NEW jurisdiction provenance is not yet present in production CognitiveEffect.** Current scope is now explicit and safely labeled as a global-Locate jurisdiction approximation. Exact effect-specific `jurisdiction_anchor_ids` remains a capability of the support-bound research contract, not yet a production authority.
3. Run the full backend regression after the audit repairs. Only after regressions and the prompt-contract decision may 10D.6K outcome sampling resume. Phase 9A remains paused.

## Current audit decision

The major P0 plumbing defects that could make measurement, public update, or side effects disagree with the selected Attention cause have been repaired. The audit is still ACTIVE because the production Impact prompt remains semantically inconsistent with the downstream Pareto contract. No 10D.6K or Phase 9A cognitive outcome should be interpreted until that prompt seam is resolved or explicitly excluded by the frozen experimental path.
