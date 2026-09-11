# Phase 10D.6L.3 — Decoupled Support Binding Preregistration

**Status:** PREREGISTERED / NO OUTCOME YET
**Date:** 2026-09-12

## Research question

Can a weak evaluator bind exact support/jurisdiction provenance to **already frozen** Relation Mapping outputs without being allowed to create, suppress, retarget, or redirect relations?

## Frozen relation source

Use only P1 relations from the closed 10D.6L.1 primary prompt-shadow artifact:
`phase10d6l1_minimal_prompt_authority_shadow_v0.1_20260911T124905Z.json`, SHA256 `444fe8bb7e0d7670411983167fade62fd638dd7f7e8ba7599303e45a5c2fd8cf`.

A/D/X/N4 frozen audited units, Kernel fixture and modal Locate remain unchanged. No Relation Mapping call is allowed in this gate.

## Binding contract

Each frozen relation receives a deterministic `relation_id`. The binder may output only:

```text
relation_id
support_unit_ids[]
jurisdiction_anchor_ids[]
reason
```

It may not output operation, target, Attention, authority scores, or a replacement relation. Empty support/anchor lists are legal and preferable to invented provenance.

Deterministic validation requires: exactly one binding for every frozen relation_id; no extra relation_id; every support ID exists in the frozen audited world; every jurisdiction anchor exists in frozen Locate. Binding output can never mutate relation topology by construction.

## Measurement

For each non-empty P1 sample relation set, run three independent binding draws with DeepSeek-Flash under the frozen binder prompt. Expected non-empty samples: D=3, X=5, N4=6, A=0; total expected calls = 42.

Primary metrics:
- structured success rate;
- exact relation-id preservation = 100% required;
- unknown support/anchor identifier rate = 0 required;
- per-relation support-signature and anchor-signature repeatability;
- empty-support / empty-anchor rates;
- descriptive comparison with the frozen strong-model reference, never treating Flash as Gold.

Promotion gate for the binding stage: all deterministic integrity checks must pass, and each relation instance should have a modal support signature present in at least 2/3 draws. Failure of a weak-model semantic binding is a robustness finding, not automatically an architecture failure.

No Attention policy or production switch is evaluated here. Grounding remains a separate downstream gate. Phase 9A remains paused.
