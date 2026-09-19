# Phase 14C — Counterfactual Representation Decision Relevance Preregistration V0.1

Status: **PREREGISTERED / EVAL-ONLY COUNTERFACTUAL**  
Date: 2026-09-19

## 1. Question

Can the current RAOS decision contract distinguish a probabilistic SAME_EVENT hypothesis from its negation, and is a null result caused by true decision invariance or simply by the hypothesis not being wired into cognition?

## 2. Experimental design

Use one in-memory world with two independently observed Sources and one controlled high-value OPEN_NEW cognitive effect.

Three representation states are compared:

`R_BASE`: two independent Sources, no SAME_EVENT belief.

`R_SAME`: same Source/provenance state plus an admitted SAME_EVENT RepresentationAuditRun/belief.

`R_SECONDARY_POSITIVE_CONTROL`: replace the second Source's independent-evidence role with a REPOSTS/secondary relation.

## 3. Semantic guardrail

`SAME_EVENT != REPOSTS != DERIVED_FROM != non-independent`.

The SAME_EVENT intervention must not alter independent_source_count, secondary_report_count, or duplicate state.

The positive control intentionally changes provenance independence because that relation is already decision-bearing under the current contract.

## 4. Cognitive probe

Use current production deterministic cognition primitives, not a patched route:

- one OPEN_NEW effect;
- change_magnitude = 0.75;
- target_importance = 0.80;
- raw epistemic_strength = 0.90;
- evidence_maturity = 0.80;
- no direct observations.

With >=2 independent Sources, the epistemic cap should permit the high epistemic strength and the current Attention policy should ENGAGE.

With only 1 independent Source plus a secondary report, the single-source epistemic cap should reduce epistemic strength and the same current Attention policy should WATCH.

## 5. Measurements

For each representation state:

- graph_digest;
- decision_representation_digest;
- independent_source_count;
- secondary_report_count;
- is_duplicate;
- grounded epistemic strength;
- final disposition.

For R_SAME also record that an epistemic SAME_EVENT belief exists.

## 6. Interpretation preregistration

If the positive control changes decision digest and Attention, but R_SAME changes neither decision inputs nor Attention, conclude:

`current direct SAME_EVENT decision influence = 0`

and

`potential counterfactual SAME_EVENT decision relevance = UNKNOWN`.

Do NOT conclude that SAME_EVENT is intrinsically irrelevant.

If R_SAME unexpectedly changes an existing decision input, investigate that path before interpreting Attention.

## 7. Boundaries

- in-memory DB only;
- no production AttentionPlan persistence;
- no new production adapter;
- no new Hypothesis entity;
- no mapping SAME_EVENT to provenance dependence;
- no claim of calibrated mutual information.