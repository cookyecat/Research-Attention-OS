# Phase 10D.6D — Canonical Input × Reconciled Prompt Interaction Result

**Status:** CLOSED / COMBINED CANDIDATE NOT PROMOTED  
**Measurement SHA:** `2ed3d5f`  
**Artifact:** `eval/live/results/phase10d6d_canonical_prompt_interaction_v0_1/phase10d6d_canonical_prompt_interaction_v0.1_20260911T035248Z.json`  
**SHA256:** `6475df7a23378a372cd2ebb2dc102773f8a2b06fabb0fc009b537e4e7490274b`

## Result

| Case | C0 current prompt | C1 reconciled prompt | Interpretation |
|---|---|---|---|
| A | DROP 6/6 | DROP 6/6 | canonical input + prompt change still fails to recover stable relation |
| D | AWARE 4, DROP 2 | AWARE 1, DROP 5 | C1 produces bursts of rich raw effects but production grounding deletes most targeted effects |
| X | WATCH 6/6 | WATCH 2, AWARE 3, DROP 1 | C1 topology is richer but final Attention less stable |
| N4 | WATCH 6/6 | WATCH 6/6 | C1 robustly preserves Attention while expanding relation topology |

C1 is therefore not promotable.

## Grounding attribution

The decisive new observation is the gap between raw and grounded effects. On D/C1 repeat 2, Relation Mapping emitted CHALLENGE(Q2), CHALLENGE(B2), REINFORCE(B1), CHALLENGE(Q1), CHALLENGE(M1), and OPEN_NEW; current production grounding retained only OPEN_NEW. On X/N4, more targeted effects survive because their Locate/structural patterns fit the old grounding heuristics.

The current grounding implementation also applies `epistemic_cap`: with one source and no `ExtractionResult.observations`, epistemic strength is capped at `0.35`. In the valid C1 samples, surviving X/N4 effects are therefore uniformly projected to 0.35 despite the canonical Auditor world having already passed support sufficiency. This is directly decision-bearing because Magnitude-Free uses `epistemic_band`.

This does not imply "remove grounding". It shows that **the production grounding implementation is coupled to the legacy `ExtractionResult` representation**. Constitutional safeguards such as Location != Update, legal target membership, scope fidelity, evidence authority and trusted runtime must remain, but their canonical implementation must use canonical semantic/evidence provenance rather than re-running legacy lexical/separation heuristics.

## Decision

- Do not promote C1.
- Stop hand-tuning the Impact prompt.
- Do not yet tune target importance in isolation; epistemic authority is now equally decision-bearing.
- Next gate: **10D.6E — Canonical Authority Enrichment**, defining authoritative ordinal `importance_band` and `epistemic_band` sources before any combined production promotion.
- Relation Mapping should trend toward semantic-only output: operation, target/jurisdiction, cited canonical support, reason. Raw LLM cardinal values remain compatibility/debug data only.
- Phase 9A remains paused.
