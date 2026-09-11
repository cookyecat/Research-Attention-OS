# Phase 10D.6B — Prompt Reconciliation Shadow Result

**Status:** CLOSED / PROMPT FIX NECESSARY BUT INSUFFICIENT / VNEXT NOT PROMOTED  
**Measurement SHA:** `9ed3fad8599455c77c270853a2d12ca5f9367810`  
**Artifact:** `eval/live/results/phase10d6b_prompt_reconciliation_shadow_v0_1/phase10d6b_prompt_reconciliation_shadow_v0.1_20260911T033831Z.json`  
**SHA256:** `3b3702ce6b89f48f6cbf856ae072a42e68a1947d58def724e740a4657163bcca`

## Controlled variable

P0 and P1 used the same frozen real-web audited world, Kernel, modal Locate, audited-units-to-`ExtractionResult` adapter, production `ModelProvider` post-processing/grounding, current importance resolver, epistemic handling, runtime and `pareto-multidelta-magnitude-free-anchored-open-new` strategy. Only the Impact system prompt changed.

P1 removed the stale single-winner `change_magnitude * target_importance` instruction and the `OPEN_NEW change_magnitude >= 0.55` gate, and instructed the LLM to preserve distinct legal effects without vote/rank/argmax.

## Result

| Case | P0 Attention, N=6 | P1 Attention, N=6 | Main observation |
|---|---|---|---|
| A | DROP 6/6 | DROP 6/6 | both prompts produce empty effects |
| D | DROP 6/6 | DROP 6/6 | both prompts produce empty effects |
| X | WATCH 4/6, AWARE 2/6 | DROP 6/6 | P1 over-suppresses this case |
| N4 | WATCH 6/6 | WATCH 6/6 | P1 preserves Attention and adds stable Q1 reinforcement |

All 48 calls were valid `deepseek-flash` structured outputs. No schema-failure explanation is available for the A/D empty-effect regime.

## Attribution

The result rejects a simple "fix one stale prompt and promote" story. P1 is not promotable because X regresses to DROP 6/6. More importantly, A and D are already DROP 6/6 under P0, whereas their Phase-10 native cognitive maps contain multiple legal relations. Therefore the dominant discrepancy lies upstream of the final decision strategy and is not explained by the stale single-winner sentence alone.

Deterministic inspection of the frozen worlds shows the audited-units adapter flattens A/D/X/N4 almost entirely into `claims`, with `evidence=[]`; unit identity, epistemic structure and support relations are no longer first-class Impact inputs. Phase-10 native cognition instead consumes canonical semantic units with their `unit_id`, `epistemic_status`, confidence and supports directly.

This does **not** invalidate Phase 8C.2. That bridge was validated against the then-current production contract and supervised continuity cases, and it already documented representation-fidelity limitations. The new finding is that the richer Phase-10 cognitive contract has exceeded the information-preservation guarantee of the old `ExtractionResult` seam for some real-web worlds.

## Decision

- Keep production default unchanged.
- Do not promote `IMPACT_SYSTEM_VNEXT` v0.1.
- Preserve the vNext prompt as an experimental contract; do not tune it from these outcomes.
- Do not move to target-importance calibration yet: an earlier causal layer is unresolved.
- Next gate: **10D.6C — Canonical Input Reconciliation**, comparing the same production safeguards with canonical audited semantic units delivered directly to Relation Mapping versus the `ExtractionResult` bridge.
- Phase 9A remains paused.
