# Phase 10E — Core Decision-State Sufficiency Gate Preregistration

Date: 2026-09-15
Status: **PREREGISTERED / NOT YET MEASURED**
Production impact: **none; validation-only gate**

## 1. Physical meaning

Phase 10E is **not a new RAOS runtime module, state variable, or policy layer**. It is a validation gate on the existing Phase 1–10 core.

The current core assumes that once cognition has been reduced to a decision-relevant state `Z_t`, Attention is determined by the core policy:

```math
A_t = \pi_{core}(Z_t)
```

For positive cognitive change, `Z_t` contains only decision-authorized effects plus the already-canonical decision-relevant Kernel facts and Runtime consumed by the active strategy. For no-Delta cases, `Z_t` contains the frozen D/S/P awareness state plus Runtime.

The physical question is therefore **state sufficiency**:

```math
Z(x_1)=Z(x_2) \Rightarrow A^*(x_1)=A^*(x_2)
```

If two cases are identical under the current canonical decision state but reproducibly require different Human-Gold Attention, then the current state representation is insufficient. No new variable is assumed in advance.

## 2. Why this gate is necessary

The historical `Oracle-Delta` harness still routes frozen Delta through legacy `one-delta-v1` when no strategy is supplied. Active dogfood instead uses `research-aligned-cognition-v1` with `pareto-multidelta-cardinal-free-effect-anchored-open-new-v0.2`.

Therefore the exploratory replay of the old 30-case questionnaire measured a historical policy, not the current active core. It must not be used to justify current Core or Phase-12 changes.

## 3. Occam constraints

Phase 10E may add **measurement code only**. It may not add:

```text
new production state variables
new database tables
new scheduler parameters
new personalization parameters
new LLM stages
new Attention dispositions
```

Reuse the existing decision-strategy seam, execution snapshots, persisted effect/match provenance, D/S/P traces and Runtime records.

A historical candidate such as `GenerativePotential` is only a probe axis. It is not a Core variable unless fresh matched evidence proves that existing state is insufficient and replication supports a universal factor.

## 4. Gate A — strategy-explicit replay parity

Build or amend the evaluation harness so it never relies on the bare legacy default of `scheduler.route()`.

Historical replay must use the exact stored decision-strategy snapshot. Current-core counterfactual replay must explicitly use the current active strategy. Missing or mismatched strategy identity fails closed.

For completed current-architecture AnalysisRuns, freeze the exact inputs already consumed by the decision strategy and replay only the decision path. No Sensor, Auditor, Locate, Relation Mapping, Support Binding, Grounding, Jurisdiction evaluator, or other upstream model call is allowed.

Primary gate:

```text
exact disposition parity = 100%
exact strategy identity parity = 100%
upstream model calls = 0
```

Any failure is an instrumentation/replay defect, not Human-Gold evidence.

## 5. Gate B — minimal state-sufficiency probe

Only after Gate A passes, run a small randomized matched-pair Human-Gold probe.

Each pair holds the current canonical decision state `Z_t` fixed while varying one semantic property that the current Core does not represent. Include null-control pairs where only irrelevant wording changes.

Use the smallest probe that can expose a violation; do not recreate the historical 30-question questionnaire by default. Historical findings such as future optionality or generative potential may suggest probe construction, but they are not labels and do not receive privileged status.

The key endpoint is not classifier accuracy. It is whether the invariance claim holds:

```text
same current Core state
→ same Human-Gold Attention
```

A reproducible violation creates a **candidate Core-insufficiency hypothesis**, not an automatic new chip.

## 6. Attribution firewall

Any mismatch must first be classified as one of:

```text
INSTRUMENT_ERROR
UPSTREAM_STATE_ERROR
RUNTIME_CAPTURE_ERROR
CURRENT_RULE_ERROR
CANDIDATE_STATE_INSUFFICIENCY
USER_SPECIFIC_RESIDUAL
UNRESOLVED
```

`USER_SPECIFIC_RESIDUAL` is not allowed unless current Core inputs are correct and the same residual is stable across repeated matched cases. A candidate universal factor requires additional replication before entering the Core.

## 7. Minimality audit of existing chips

Phase 10E does not assume every historical chip must remain forever. As a diagnostic only, replay may test whether removing a chip changes observable decision/provenance behavior on a broad frozen corpus.

If a chip is observationally redundant, record it as a simplification candidate. Do not remove it during this gate without a separate preregistered equivalence test.

The burden of proof is symmetric:

```text
new variable/module must prove necessity
existing module must continue to prove non-redundant function
```

## 8. Exit rule

Phase 10E closes after Gate A and Gate B are complete and all mismatches are attributed.

- If current state is sufficient, Phase 12 may resume with identity/no-op personalization as the default.
- If a candidate universal Core omission remains, Core research continues before Phase 12 fitting.
- If only stable user-specific residuals remain after Core reconciliation, Phase 12 may test the smallest bounded calibration.

No production policy change is part of Phase 10E itself.
