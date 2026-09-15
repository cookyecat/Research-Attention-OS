# Phase 10E — Proxy Human Gold Preregistration

Date: 2026-09-16
Status: **PROXY GOLD FROZEN / NOT YET MEASURED**
Parent: `212_PHASE10E_CURRENT_CORE_ATTENTION_RECONCILIATION_PREREGISTRATION.md`

## Scope

The user explicitly delegated an initial Human-Gold pass to the assistant so research can continue without blocking on manual annotation. This is recorded as `assistant_proxy_for_user`, not as direct user-authored Gold.

The proxy set is deliberately small and covers common/high-value operating regimes only. It excludes rare synthetic corner cases, which remain flywheel watch items.

Frozen labels are in:

`eval/live/manifest.phase10e_proxy_human_gold.v0_1.json`

## Guardrails

- Labels are frozen before running the Gate-II instrument.
- No proxy mismatch alone may introduce a new Core variable.
- A mismatch must first be attributed to estimator, representation, Runtime, or policy error.
- Historical 30-case Oracle-Delta labels are not copied into this set.
- Proxy Gold may provisionally close 10E if main-regime adequacy is clean; any future Core-changing claim still requires direct user review or repeated flywheel evidence.

## Covered regimes

```text
ordinary REINFORCE
important QUESTION reinforcement
important BOTTLENECK reinforcement
strong / weak CHALLENGE
strong / weak valid OPEN_NEW
Runtime deferral
no-Delta AWARE / DROP via D-S-P awareness semantics
```

The intended question is practical operating-regime adequacy, not mathematical completeness of the latent state.
