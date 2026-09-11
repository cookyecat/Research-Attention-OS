# Phase 10D.6L.2 — Model-Capacity Bracketing Strong Reference

**Status:** FROZEN BEFORE SUPPORT-BINDING DIAGNOSTIC OUTCOME
**Date:** 2026-09-12
**Adjudicator:** GPT-5.6 Sol, manual strong-model review in the active research session

## Purpose

Separate RAOS architecture failure from evaluator-model failure. DeepSeek-Flash is treated as a weak-model robustness lower bound; this manual strong-model adjudication is a qualitative architecture-capability upper-bound reference.

This is **not Human Gold** and not a production promotion criterion by itself. The primary 10D.6L.1 weak-model relation topology was already known, so this is not blind to observed relation families. However, it is frozen before any 10D.6L.1 support-binding diagnostic outcome and is based directly on the frozen audited units, frozen Locate, and Kernel propositions.

## Adjudication rule

Judge only whether the frozen evidence supports a semantic relation at the proposition's actual scope. Absence of discussion is not evidence. A relation should prefer an existing fitting Kernel node over `OPEN_NEW`; `OPEN_NEW` requires genuine located jurisdiction with no fitting existing epistemic target.

## Case A — Microsoft Astra / Foundry announcement

**Strong-reference relation set:** empty.

The source describes frontier-model availability, enterprise workflows, computer use, safeguards, and token efficiency. None of the supplied evidence directly addresses fastest embodied-control latency, control-loop architecture, or the current collective-intelligence questions.

`REINFORCE/CHALLENGE(B1/Q1/BT1/M1)` would be scope extrapolation. `OPEN_NEW` is also not justified inside the frozen Motor/Collective Kernel merely because the source is broadly about advanced AI.

## Case D — secondary report on Astra / safety incidents

**Strong-reference relation set:** empty within the frozen Kernel.

The report contains potentially important AI-safety material: opaque recurrence, alignment-monitoring difficulty, alleged agent breakout, recursive self-improvement, and cybersecurity capability. But the frozen Kernel has no AI-safety/recursive-self-improvement jurisdiction node.

In particular, the absence of high-frequency motor-control discussion does **not** support `REINFORCE(Q1)`. "The article does not discuss X" is not evidence about X.

## Case X — AgentHands / XR co-speech gesture architecture

**Strong-reference core relation:** `REINFORCE(M1)`.

Primary support is `neu-0005`: the backend LLM generates semantic GestureEvents while a local parser and animation engine use word-level timing to synchronize execution. `neu-0004` and `neu-0006` provide additional architectural context.

This is a legitimate narrower-scope example of partially separable cognitive planning and temporal execution, so it supports M1. It does not directly establish fastest embodied-control latency, energy, or task-success limits, so `B1/Q1/BT1` should not be promoted from this evidence. `OPEN_NEW` is not required because M1 already provides a fitting epistemic landing point.

## Case N4 — robotics control-interface benchmark

**Strong-reference core relations:** `REINFORCE(B1)`, `REINFORCE(M1)`, and a partial-scope `REINFORCE(BT1)`.

`neu-002` directly reports the real-time mismatch: roughly 83 Hz control requirement versus ~0.2–0.4 Hz non-reasoning inference. `...evt-001:action_change:2` reports direct joint-control failure and improved completion through pretrained/high-level control. `neu-001` and `neu-008` further separate low-level direct control from higher-level/programmatic/policy interfaces.

These facts directly support B1 at the scope of current evaluated language models and support M1's separation between cognitive intelligence and temporal motor execution. They also validate the latency/task-success dimensions of BT1, while leaving the energy dimension unresolved. Q1 is informed by the evidence, but B1/M1/BT1 are more precise semantic landing points than treating the Question itself as the main relation.

## Interpretation for lower/upper-bound evaluation

The weak-model D `REINFORCE(Q1)` is therefore provisionally classified as an evaluator error, not evidence that the deletion-only Relation Mapping architecture is wrong. The architecture should be judged by whether deterministic support binding / grounding can contain such errors without suppressing valid N4/X relations.

The desired research envelope is:

```text
Strong evaluator succeeds + weak evaluator succeeds
    -> robust architecture, strongest evidence.
Strong evaluator succeeds + weak evaluator fails
    -> architecture ceiling is sound; weakness is robustness/model-capacity boundary.
Strong evaluator fails + weak evaluator fails
    -> architecture/representation problem becomes plausible.
Deterministic invariant fails regardless of evaluator
    -> architecture bug.
```

Do not tune prompts or ontology to rescue isolated weak-model samples unless the failure repeats systematically or survives strong-model adjudication. Production deployment may choose the strongest available LLM for accuracy; research should continue to include weaker models to expose architecture/model dependence.
