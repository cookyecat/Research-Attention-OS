# RAOS Representation–Cognition Marginalization V0.1 — Math Result

Status: **MATH READY / REAL REPRESENTATION-CONDITIONED EXPERIMENT BLOCKED BY INPUT CONTRACT / NO PRODUCTION CHANGE**  
Date: 2026-09-19

## 1. Implemented scope

Pure eval-only utility:

`eval/live/representation_cognition_marginalization_v0_1.py`

Contract: `representation-cognition-marginalization-v0.1`.

No DB access, LLM call, Event mutation, AttentionPlan mutation, or production API is involved.

## 2. Core algebra

For representation scenarios `R_i`, weights `w_i`, and conditional Attention distributions `q_i(a)`:

q(a) = sum_i w_i q_i(a).

For calibrated posterior weights, categorical entropy decomposes as:

H(A|E) = E_R[H(A|R)] + I(A;R|E).

Interpretation:

- `E_R[H(A|R)]` = cognitive stochasticity remaining when Representation is fixed.
- `I(A;R|E)` = additional Attention uncertainty attributable to Representation uncertainty.

## 3. Operational-proxy boundary

Current `representation-belief-view-v0.1` is not calibrated world-truth probability.

Therefore under `OPERATIONAL_PROXY` weights:

- `mutual_information_interpretation_valid = false`
- `decision_authority = NONE`
- the mixture is diagnostic only.

## 4. Validation

Five preregistered tests pass.

They verify:

1. deterministic but different conditional Attention states produce representation-induced uncertainty;
2. identical conditional distributions produce zero representation contribution;
3. positive unnormalized weights normalize correctly;
4. mixed cognitive + representation uncertainty has near-zero decomposition residual;
5. invalid negative/zero mass fails closed.

Synthetic diagnostic:

R0 weight 0.5 -> DROP with probability 1
R1 weight 0.5 -> ENGAGE with probability 1

marginal = {DROP: 0.5, ENGAGE: 0.5}
H(A) = 1 bit
E[H(A|R)] = 0
representation-induced information = 1 bit.

Under OPERATIONAL_PROXY semantics this is information-form diagnostic only.

## 5. Production feasibility review

The production pipeline already freezes `FrozenRepresentationSnapshot`, `graph_digest`, and `decision_representation_digest`, and refuses one AnalysisRun if decision-relevant representation identity changes mid-run.

However the research-aligned cognition provider does not currently receive an explicit World Representation object `R`.

Its effective inputs are projected pieces such as:

- audited extraction / semantic units;
- Kernel matches;
- independence / duplicate context;
- P evidence packets;
- Runtime / Kernel state.

`FrozenRepresentationSnapshot` currently serves identity, replay, provenance, digest invalidation, and hybrid-R0/R1 protection; it is not a substitutable cognition input value.

## 6. Consequence

A real experiment computing `P(A|R0)` and `P(A|R1)` for controlled representation hypotheses cannot yet be run without changing the cognition input contract.

Mixing unrelated historical epochs would not answer the question and is forbidden.

## 7. Next missing capability

The missing capability is a **representation-conditioned cognition input contract**, not a new persistence entity.

Desired shape:

existing immutable evidence + explicit in-memory Representation view R_i + frozen Kernel K -> existing Phase10 / research-aligned cognition kernel.

Any future adapter should reuse existing `FrozenRepresentationSnapshot` semantics where possible and must not persist counterfactual topology or write Attention/WATCH.

## 8. Phase10 remains unchanged

Prior Phase10 code remains the validated conditional kernel `P(T,A|R,K,Theta)`.

The new marginalization layer belongs outside it. This is a theory extension, not a correction of Phase10.

## 9. Stop condition

V0.1 stops here.

Do not build a representation adapter merely to make the demo run. Reopen only when cognition has an independently justified need to consume an explicit Representation view.

This avoids creating a second World Representation stack.

## 10. Validation status

The marginalization algebra remains eval-only. Five dedicated tests pass. Full backend regression after the surrounding four-plane/Integrity changes is 896 passed, 63 skipped, with only the known Case-K urgency residual. No production Attention or Representation behavior was changed by the composition utility.


## 11. Phase14C bounded current-contract update

A later bounded counterfactual probe did not add an explicit Representation input contract, but it did test current-contract sensitivity with a positive control.

Changing a currently decision-bearing provenance variable (independent corroboration -> secondary REPOSTS) changes the frozen decision representation and moves a controlled OPEN_NEW probe from ENGAGE to WATCH. Adding SAME_EVENT belief while holding provenance independence fixed changes neither the current decision digest nor the probe decision.

Therefore the earlier feasibility conclusion is refined:

```text
current direct SAME_EVENT influence = zero by current contract
potential SAME_EVENT counterfactual relevance = unknown
```

A true `P(A|R_same)` versus `P(A|R_different)` experiment still requires a semantically justified event-continuity / representation-conditioned cognition input. No production adapter is introduced by this probe.
