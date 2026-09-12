# Phase 10D.6L — End-to-End Business Logic Integrity Result

**Status:** CLOSED / PRODUCTION PROMOTION DEFERRED
**Date:** 2026-09-12

## Closure decision

The end-to-end integrity audit is closed. Hidden business-logic defects that could change effect existence, decision cause, public update, authorized side effects, WATCH responsibility, replay attribution, fallback provenance, cache identity or reschedule semantics were repaired and regression-locked.

Known remaining gaps are now explicit research/production boundaries rather than hidden semantics. New cognitive outcome sampling may resume only on the frozen experimental path; production defaults remain unchanged until a later promotion gate.
## Architecture conclusions

1. Relation Mapping is a semantic matching task only. It must not threshold OPEN_NEW by magnitude, rank effects, choose a single public winner, or decide Attention.
2. Support Binding is a separate stage. It may attach provenance to frozen relations but cannot create, delete, retarget or redirect them.
3. Grounding owns relation-support fit. `Anchored OPEN_NEW` separately owns jurisdiction admission for new branches. A single capable evaluator may physically return both structured judgments in one call, but authority ownership remains separate. Jurisdiction admission requires full anchor semantics, not opaque IDs/codes alone.
4. Evaluator capacity must be bracketed. DeepSeek-Flash is a robustness lower bound; strong-model adjudication is an architecture-capability upper bound. Weak-model-only disagreement is not sufficient evidence to change RAOS architecture.
5. Decision cause is authoritative provenance for Public Update, WATCH and KernelPatch side effects.
## Final regression checkpoint

Correct full-suite invocation from repository root:

```text
PYTHONPATH=backend:. backend/.venv/bin/pytest -q backend/tests
```

Result after the 10D.6L audit work: `682 passed, 63 skipped, 1 failed, 1 warning`.

The sole failure remains the historical Case K urgency mismatch (`PREEMPT` expected, `PRIORITY` actual). No new regression failure was introduced, and Case K remains intentionally untouched.
## Explicitly deferred production boundaries

- Default production Relation Mapping Prompt still contains two legacy downstream-policy instructions. The deletion-only Pareto-compatible prompt is the leading semantic correction, but it is not yet the production default.
- Exact effect-specific `jurisdiction_anchor_ids` remain a research-contract capability; current production OPEN_NEW scope is explicitly labeled as a global-Locate jurisdiction approximation.
- DeepSeek-Flash is not promoted as authoritative Grounding. The experimental path may instead use the frozen strong reference for an upper-bound replay and weak-model modal judgments for robustness comparison.

## Next gate

Resume Phase 10D.6K on the repaired cardinal-free strategy/Causal-Core path, but amend the epistemic authority replay to preserve evaluator-capacity bracketing. Phase 9A remains paused until the Attention replay closes.

## Grounding design review after L4 / L4J

The L4 process is recorded as a methodological finding, not merely a model ranking. DeepSeek-Flash was highly stable but systematically permissive under incomplete/ambiguous grounding context: it often mapped strong-reference `PARTIAL` to `DIRECT`. This is a reproducible evaluator bias rather than random noise and can be treated like a reviewer-policy characteristic.

Crucially, two apparent `OPEN_NEW` critical errors were later traced to **instrument input under-specification**: Flash saw jurisdiction codes such as `P2/G1` but not their full Kernel semantics. In the jurisdiction-only L4J follow-up, once the complete anchor semantics were supplied, both cases became `INSUFFICIENT_JURISDICTION` in 3/3 draws, matching the frozen strong reference with zero critical error. Therefore the correct lesson is not "Flash cannot Ground" but "the evaluator must receive the task state necessary for the judgment."

This motivates a three-way distinction for future experiments: (1) architecture/contract failure, (2) evaluator-policy/capability boundary, and (3) instrument/input insufficiency. Do not modify RAOS architecture merely to compensate for (2) or (3).

The production design is consequently **not** frozen as two Grounding calls. Relation-support fit belongs to Grounding; OPEN_NEW jurisdiction fit belongs to Anchored admission. A strong production evaluator may return both structured judgments in one physical call and route each output to its owning stage. Research or high-risk operation may split them or use multiple reviewers for attribution, calibration, or consensus. `one stage = one responsibility` constrains authority; it does not prescribe RPC count.
