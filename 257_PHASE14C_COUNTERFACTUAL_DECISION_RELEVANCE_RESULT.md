# Phase 14C — Counterfactual Representation Decision Relevance Result V0.1

Status: **CURRENT-CONTRACT BLINDNESS CONFIRMED / POSITIVE CONTROL SENSITIVE / POTENTIAL SAME_EVENT RELEVANCE UNKNOWN**  
Date: 2026-09-19

Reference preregistration: `256_PHASE14C_COUNTERFACTUAL_DECISION_RELEVANCE_PREREGISTRATION.md`.

## 1. Experimental states

`R_BASE`: two independent Sources, no SAME_EVENT belief.

`R_SAME`: same two independent Sources plus an admitted SAME_EVENT audit/belief. Provenance independence is held fixed.

`R_SECONDARY_POSITIVE_CONTROL`: the second Source is a REPOSTS/secondary report, exercising an already decision-bearing representation dimension.

## 2. Positive control

The deterministic cognitive probe uses the current production epistemic cap and Attention policy for the same high-value OPEN_NEW effect.

R_BASE:

- independent sources = 2;
- grounded epistemic strength = 0.90;
- Attention = ENGAGE.

R_SECONDARY_POSITIVE_CONTROL:

- independent sources = 1;
- secondary reports = 1;
- grounded epistemic strength = 0.35;
- decision_representation_digest changes;
- Attention = WATCH.

The harness is therefore capable of detecting a representation-driven decision change.

## 3. SAME_EVENT intervention

R_SAME has a real epistemic SAME_EVENT belief in the controlled belief view while preserving:

- independent sources = 2;
- secondary reports = 0;
- is_duplicate = false.

Compared with R_BASE:

- graph_digest unchanged;
- decision_representation_digest unchanged;
- grounded epistemic strength remains 0.90;
- Attention remains ENGAGE.

## 4. Correct interpretation

The null SAME_EVENT effect is **not** evidence that SAME_EVENT is intrinsically irrelevant.

It proves a narrower architectural fact:

`current direct SAME_EVENT decision influence = ZERO_BY_CURRENT_CONTRACT`.

The current decision projection does not consume probabilistic SAME_EVENT or Event identity.

Therefore:

`potential counterfactual SAME_EVENT decision relevance = UNKNOWN`.

To answer the potential-relevance question, cognition would need a semantically justified event-continuity representation input. That contract does not yet exist.

## 5. Why the positive control matters

Without the REPOSTS/independence positive control, an unchanged Attention decision could be explained by an insensitive experimental harness.

Because the positive control changes both decision digest and Attention, current-contract blindness is localized specifically to SAME_EVENT projection rather than to the counterfactual method itself.

## 6. Semantic guardrail

`SAME_EVENT != REPOSTS != DERIVED_FROM != non-independent`.

The experiment never maps SAME_EVENT to provenance dependence.

## 7. Research consequence

The earlier statement `direct decision relevance = 0` must be read as an implementation fact, not an intrinsic or causal conclusion.

The revised state is:

`current direct influence = 0`

`potential decision relevance = UNKNOWN`.

Do not promote SAME_EVENT into production cognition merely to make it measurable. A future event-continuity input contract must have an independent semantic/product justification.

## 8. Artifact

`eval/live/results/phase14c_counterfactual_decision_relevance_v0_1/phase14c_counterfactual_decision_relevance_v0.1_20260919T101125Z.json`

## 9. Regression validation

The dedicated counterfactual test passes. Full backend regression: `901 passed / 63 skipped / 1 known Case-K failure`. No production cognition, Attention, topology, or persistence contract was changed by this experiment.
