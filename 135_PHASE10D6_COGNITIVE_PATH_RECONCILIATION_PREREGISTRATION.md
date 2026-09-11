# Phase 10D.6 — Cognitive Path Reconciliation Preregistration

**Status:** PREREGISTERED / NO OUTCOME SAMPLES YET  
**Date:** 2026-09-11

## Problem

Phase 10D.5 confirmed that the deployed cognitive path and the Phase-10 research path are not semantically identical. A targeted code-history audit then found that deployed `ModelProvider` is not a disposable legacy block: it contains later production safeguards (`Location != Update`, scope legality, evidence grounding/caps, trusted runtime authority, typed/fail-closed targets), but its Impact prompt still contains pre-Pareto/pre-Magnitude-Free decision algebra.

The clearest stale instructions are: (1) asking the LLM to reason toward a single public update using `change_magnitude * target_importance`, and (2) using a raw `change_magnitude >= 0.55` instruction to distinguish OPEN_NEW branches. Both predate the validated Pareto Multi-Delta + Magnitude-Free + Anchored OPEN_NEW stack.

## Frozen authority contract

The reconciliation target is not `native_assess()` copied verbatim and not old `ModelProvider` preserved verbatim. It is a production-grade canonical cognition contract:

| Variable / rule | Authority | 10D.6 treatment |
|---|---|---|
| semantic units / evidence | Sensor + Auditor | frozen authoritative world |
| Locate membership | Locate | Location only; never an update |
| operation | Relation Mapping LLM | semantic judgment only |
| target | Relation Mapping LLM + deterministic legality | targeted effects must land on legal frozen Locate targets |
| scope legality | deterministic grounding | preserve production fail-closed rules |
| raw `change_magnitude` | none for decision | compatibility/debug only |
| `target_importance` | Kernel/user state; current resolver held fixed in 10D.6B | separate 10D.6C calibration |
| epistemic support | evidence/grounding; current band held fixed | not redesigned in this phase |
| runtime overlap | trusted Brain/runtime state | LLM has no authority |
| OPEN_NEW admission | Kernel jurisdiction + Anchored admission | target may be null; jurisdiction may not |
| article decision | Pareto frontier + Magnitude-Free channel policy + join | downstream authority |

## Sequential gates

**10D.6A — Authority Contract.** Freeze the table above before any outcome sampling.

**10D.6B — Prompt Reconciliation.** Change only the Impact prompt. The vNext prompt must preserve all distinct legal effects, must not ask the LLM to choose/rank a single public update, and must state that `change_magnitude` is diagnostic-only and cannot gate, rank, suppress, or promote an effect. Existing production grounding, importance resolver, epistemic handling, strategy and runtime remain frozen.

**10D.6C — Importance Authority Calibration.** Only after 10D.6B closes, isolate `target_importance`. Explicit Kernel importance remains authoritative. The current node-type prior and LLM fallback must be evaluated rather than silently accepted or removed. OPEN_NEW importance/jurisdiction must be specified separately because target is null.

**10D.6D — Combined Shadow / Promotion Gate.** Combine only components that individually passed their gates, run the production-grade shadow path on frozen real-web worlds and sentinel cases, and promote only with no critical semantic regression or uncontrolled Attention inflation.

## 10D.6B controlled experiment

Input cases: real-web A, D, X, N4 from the exact Phase 10D.4 frozen audited worlds and modal Locate fixtures. Both arms consume the same audited-units-to-`ExtractionResult` adapter, same Kernel, same Locate, same `ModelProvider` deterministic grounding, same current importance resolver, and the same `pareto-multidelta-magnitude-free-anchored-open-new` decision strategy.

Arms:
- **P0:** current deployed Impact prompt.
- **P1:** reconciled Impact prompt vNext.

Sampling is interleaved P0/P1 by case. Initial N=6 per arm per case. No outcome-dependent prompt editing. Any expansion requires a new preregistration amendment.

Primary observables: legal relation topology, Decision-Causal Core, and article Attention distribution. Secondary diagnostics: schema failures, OPEN_NEW frequency, effect count, latency/tokens.

Promotion is **not** decided by agreement with P0. P1 must instead preserve known semantic invariants while removing obsolete cardinal/single-winner instructions. Critical failures include loss of RS05-like direct CHALLENGE behavior, spurious broad GOAL/PROJECT updates, free-floating OPEN_NEW, systematic false DROP, or uncontrolled ENGAGE inflation.

## Guardrails

- Phase 9A remains paused; no Kernel-evolution outcome sampling while the cognition path is under reconciliation.
- Production default is unchanged during 10D.6A–C.
- Do not remove production grounding/scope/runtime safeguards merely because native research prompts are newer.
- Do not reintroduce raw LLM `change_magnitude` as decision authority.
- Do not tune the vNext prompt after observing 10D.6B outcomes.
