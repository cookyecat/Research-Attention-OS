# Phase 14B-Controlled — Representation Belief Evolution Result V0.1

Status: **CONTROLLED EVOLUTION COMPLETE / DIRECTIONAL RESPONSE VALIDATED / PROXY SATURATION GAP IDENTIFIED**  
Date: 2026-09-19

Reference preregistration: `254_PHASE14B_CONTROLLED_REPRESENTATION_EVOLUTION_PREREGISTRATION.md`.

## 1. Fixed experiment

Four immutable evidence stages, exactly N=4 Auditor realizations per stage, no adaptive expansion or case tuning.

Conceptual hypothesis:

`Do Publisher Alpha and Publisher Beta describe the same Acme Nimbus API public-beta launch event?`

## 2. Results

### E0_WEAK

`0 SAME_EVENT / 0 DIFFERENT_EVENT / 4 UNCERTAIN`

Response spectrum: `{SAME:0, DIFFERENT:0, UNCERTAIN:1}`.

Operational masses: belief=0, disbelief=0, uncertainty=1, projected proxy=0.5.

### E1_NAMED

`4 SAME_EVENT / 0 DIFFERENT_EVENT / 0 UNCERTAIN`

Operational masses: belief=0.666667, uncertainty=0.333333, projected proxy=0.833333.

JSD from E0 = 1.0 bit.

### E2_CORROBORATED

`4 SAME_EVENT / 0 DIFFERENT_EVENT / 0 UNCERTAIN`

Operational masses remain exactly the same as E1.

JSD from E1 = 0.0.

### E3_CONFLICT

`0 SAME_EVENT / 4 DIFFERENT_EVENT / 0 UNCERTAIN`

Operational masses: disbelief=0.666667, uncertainty=0.333333, projected SAME proxy=0.166667.

JSD from E2 = 1.0 bit.

## 3. What the experiment validates

The current Representation Auditor is directionally evidence-sensitive in this bounded controlled case:

- weak evidence preserves UNCERTAIN;
- naming the same concrete actor/product/action moves the response to SAME_EVENT;
- stronger matching detail preserves SAME_EVENT;
- explicit conflict in event date/status reverses the response to DIFFERENT_EVENT.

This is a mechanism test, not a calibration claim.

## 4. Important engineering gap: response-spectrum saturation

E1 and E2 contain materially different evidence strength, but the response spectrum is identical because both stages are 4/4 SAME_EVENT.

Therefore `representation-belief-view-v0.1` cannot distinguish:

`enough evidence to produce a stable SAME_EVENT label`

from

`substantially stronger corroborating evidence that still produces the same stable label`.

The current operational proxy is driven by repeated Auditor categorical realizations plus prior ignorance. It is not an evidence-strength posterior.

This empirically confirms the existing theoretical distinction:

`Q_Theta(Y | B_t) != P(H | E_<=t)`.

Once the categorical response saturates, additional evidence can change `E` without changing `Q` or the operational proxy.

## 5. Consequence

Do not use proxy movement as the sole definition of epistemic evolution.

A representation trajectory must retain at least:

- immutable evidence epoch identity/digest;
- the evidence bundle itself/provenance;
- Auditor response spectrum;
- any future calibrated evidence-sensitive estimator separately.

No scalar evidence-strength heuristic is introduced in V0.1.

## 6. Natural vs controlled evolution

This controlled result demonstrates that evidence-update behavior is a core Representation-path test and is not a corner case.

It does not replace Phase14B natural longitudinal dogfood. Natural trajectory analysis remains blocked until real cross-time evidence epochs can be linked without ad hoc hypothesis identity machinery.

## 7. Artifact

`eval/live/results/phase14b_controlled_representation_evolution_v0_1/phase14b_controlled_representation_evolution_v0.1_20260919T100915Z.json`

## 8. Regression validation

Focused Representation/counterfactual regression: 18 passed. Full backend regression after adding the eval-only experiments: `901 passed / 63 skipped / 1 known Case-K failure`. The only failure remains PREEMPT expected vs PRIORITY actual.
