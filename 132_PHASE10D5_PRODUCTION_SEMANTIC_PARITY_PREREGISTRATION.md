# Phase 10D.5 — Production Semantic Parity Audit Preregistration

Status: FORMAL REPLAY PLAN LOCKED / EXPLORATORY DIAGNOSTIC EXCLUDED
Date: 2026-09-11

## Question

Do the Phase 10D.4 real-web basin-persistence conclusions survive when stored stochastic CognitiveEffects are deterministically reinterpreted with the **same target-importance authority used by the deployed production ModelProvider**?

This is not a new-web or new-LLM experiment. It is a semantic-parity replay over the exact stored 10D.4 realizations.

## Why this audit exists

Phase 10D native research cognition copied the LLM-returned `target_importance` directly into `CognitiveEffect`. Production `ModelProvider` instead resolves targeted importance as:

`explicit Kernel payload importance/priority > Kernel node-type prior > LLM estimate > neutral`.

## Evidence-status boundary

An exploratory diagnostic replay was already performed after discovering this seam; it is **not** counted as preregistered evidence. The diagnostic found zero mismatch when replaying the original Phase-10 semantics and indicated that production importance rebinding can alter individual Attention decisions.

This document freezes the formal audited replay protocol before creating the formal Phase 10D.5 artifact. No new LLM call or outcome-dependent sample selection is allowed.

## Frozen corpus

Use exactly the four Phase 10D.4 selected real-web cases: `A`, `D`, `X`, `N4`, with the exact persisted `t1_samples` and `t2_samples` from the canonical Phase 10D.4 artifact.

Sample counts remain exactly those already measured: A 24+24, D 24+24, X 12+12, N4 24+24. No sample is added, removed, retried, or substituted.

The source text, Sensor/Auditor result, Locate fixture, Relation-Mapping realization, operation, target, epistemic strength, OPEN_NEW identity, and raw `change_magnitude` are immutable.

## Replay arms

**Arm R — Historical research semantics.** Reconstruct every stored effect exactly as persisted, then recompute Decision-Causal Core and Attention. This arm is a fail-closed replay check.

**Arm P — Production semantic parity.** Keep every stored effect field fixed except targeted `target_importance`. For REINFORCE/CHALLENGE with an existing Kernel target, recompute importance with production `resolve_target_importance(node, node_type, llm_estimate)`. OPEN_NEW keeps its stored LLM estimate because it has no target node.

No raw `change_magnitude` authority is reintroduced. Anchored OPEN_NEW + Magnitude-Free + Pareto remains the decision stack.

## Fail-closed replay gate

Before reading Arm-P conclusions, Arm R must reproduce **all 168 stored 10D.4 samples** exactly on:

- article Attention;
- `necessary_core`;
- `sufficient_supports`.

Any mismatch invalidates the formal parity replay until explained.

## Metrics

For Arm P, rebuild per-checkpoint static maps `M_t(E,K)=(P(r in T), P(r in B_pi(T)), P(A))` and compare t1 vs t2 with the same Phase-10 chips:

- Attention-state JSD;
- load-bearing-state JSD;
- topology-state JSD;
- 5000 fixed-seed permutation-null calibration.

Topology is expected to remain identical sample-by-sample because operation/target identity is frozen; only Pareto/load-bearing and Attention may change under importance rebinding.

Also report within-sample projection deltas from Arm R to Arm P: changed Attention count and changed load-bearing-set count per case.

## Decision rule

The Phase 10D.4 basin-persistence claim is production-semantic-parity supported at the Attention layer iff all four selected cases remain null-compatible under Arm P using the existing strict gate `observed > null_p95 AND tail_probability <= .05` for drift.

Load-bearing parity is reported independently and may succeed or fail without redefining the Attention result.

This audit does not establish decision correctness, production accuracy, stationarity, or a dynamical attractor. It only tests whether the already-observed real-web basin-persistence result survives the deployed importance-authority semantics.
