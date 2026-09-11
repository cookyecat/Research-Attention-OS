# Phase 10D.6L.1 — Minimal Prompt Authority Removal Shadow Result

**Status:** CLOSED / INTERPRETABLE / NOT PROMOTED
**Date:** 2026-09-11

## Frozen measurement

Measurement SHA: `f757402c9210f05b0e24d7872154e35168ca21a0`  
Artifact: `eval/live/results/phase10d6l1_minimal_prompt_authority_shadow_v0_1/phase10d6l1_minimal_prompt_authority_shadow_v0.1_20260911T124905Z.json`  
SHA256: `444fe8bb7e0d7670411983167fade62fd638dd7f7e8ba7599303e45a5c2fd8cf`

48/48 calls succeeded. P0 was current `IMPACT_SYSTEM`; P1 deleted only the preregistered OPEN_NEW magnitude-threshold instruction and single-winner `change_magnitude × target_importance` instruction.

## Attention outcome

- A: P0 `DROP 6/6`; P1 `DROP 6/6`.
- D: P0 `DROP 6/6`; P1 `DROP 3/6`, `WATCH 2/6`, `AWARE 1/6`.
- X: P0 `AWARE 3/6`, `WATCH 3/6`; P1 `AWARE 4/6`, `WATCH 1/6`, `DROP 1/6`.
- N4: P0 `WATCH 6/6`; P1 `WATCH 6/6`.

P1 therefore does not cause global topology/Attention collapse, but the deleted policy instructions are decision-bearing upstream: relation topology changes materially in D/X/N4.

## Stage attribution

A is unchanged at raw/grounded/legal = 0 throughout. D P0 is also empty throughout; D P1 emits raw effects in 5/6 draws, with several removed by grounding, leaving weak `REINFORCE(Q1)` and `OPEN_NEW` relations in 3/6 draws. X remains mostly grounded/legal but shifts from a mixed M1/OPEN_NEW topology toward M1. N4 P0 is raw 3 -> grounded/legal 2 in every draw; P1 is raw 4 -> grounded/legal 3 in every draw and stably adds `REINFORCE(Q1)`.

No duplicate legal relation family was observed in either arm.

## Decision

Do not promote P1 to production unchanged. The experiment confirms the architectural diagnosis: the two production prompt lines improperly assign downstream decision-policy authority to Relation Mapping. Removing them is structurally necessary, but deletion alone also releases weak relations, especially in D. The preregistered support/jurisdiction binding diagnostic is therefore warranted to determine whether those released relations have exact evidence provenance and whether later canonical grounding can safely contain them.

Production default remains P0. 10D.6K and Phase 9A outcome sampling remain paused.
