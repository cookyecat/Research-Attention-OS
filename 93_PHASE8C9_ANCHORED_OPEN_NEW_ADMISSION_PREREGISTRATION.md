# Phase 8C.9 — Anchored OPEN_NEW Admission Preregistration

Status: PREREGISTERED / NOT YET MEASURED
Date: 2026-09-10

## Trigger

Phase 8C.8 found one product-level failure under a completely frozen upstream state: real-web D had modal Locate = empty, yet Cognitive Impact emitted five OPEN_NEW effects in 1/6 repeats and raised Magnitude-Free Attention from DROP to ENGAGE.

## Hypothesis

`OPEN_NEW` means “create a new user-relative cognitive branch”, not “the source contains an interesting new fact”. Therefore a new branch may have `target=null`, but it must not be free-floating relative to the Cognitive Kernel.

Working invariant:

```text
OPEN_NEW -> exists Kernel jurisdiction anchor
```

## Candidate admission chip

`anchored-open-new-v0.1` is a deterministic, magnitude-free Effect Admission strategy. It leaves REINFORCE/CHALLENGE unchanged. OPEN_NEW is admitted only when Locate contains at least one jurisdiction anchor:

- a GOAL or PROJECT node; or
- a STRUCTURAL / DECISION / BOTTLENECK / EVIDENCE relevance; or
- a structurally flagged match.

A bare TOPIC match to an epistemic node is not sufficient by itself. No new LLM call, score, threshold tuning, or continuous magnitude is introduced.

Baseline admission remains `legal-public-v1` and is behavior-preserving.

## Experiment

1. Extend the existing Pareto strategy seam with a versioned Effect Admission slot while keeping pass-through admission as the default.
2. Replay the exact Phase 8C.8 frozen Impact outputs under:
   - Pareto + Magnitude-Free + legal-public-v1
   - Pareto + Magnitude-Free + anchored-open-new-v0.1
3. Require all non-OPEN_NEW relations to be invariant.
4. D should no longer allow an OPEN_NEW-only burst to create ENGAGE when frozen Locate has no jurisdiction anchor.
5. RS05 is the natural positive-jurisdiction control: its modal Locate contains EVIDENCE/STRUCTURAL project anchors, so its OPEN_NEW candidates must remain admissible. Its critical CHALLENGE must remain untouched.
6. After deterministic replay, stress D with **12** additional fresh Cognitive Impact repeats using the same frozen audited world and exact empty modal Locate. The candidate strategy must remain insensitive to any repeated free-floating OPEN_NEW burst.

## Boundaries

This v0.1 tests only the structural anchor invariant. It does not yet verify branch novelty, source grounding, or semantic non-redundancy with a second LLM auditor. If anchored false positives remain, those become a later admission problem rather than a reason to reintroduce pseudo-cardinal magnitude.

Production default remains `one-delta-v1`.
