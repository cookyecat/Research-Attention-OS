# Phase 10D.6L.3 — Decoupled Support Binding Result

**Status:** CLOSED / STRUCTURAL DECOUPLING PASS / STRICT STABILITY GATE FAIL
**Date:** 2026-09-12

## Result

Valid rerun measurement SHA: `ae0c4e927d4d6496e2dda791a8944dc8f46dc7d4`.
Artifact SHA256: `67a97a323ac426693ffb96d9ff57cf7141faf8af29f73c38aafb18857d90448f`.

The binder consumed only frozen P1 relations from the closed 10D.6L.1 primary shadow. No Relation Mapping call occurred, and the binding schema exposed no operation/target field.

- 42/42 calls structurally succeeded.
- exact relation-id preservation: 100%.
- unknown support/anchor identifiers: 0.
- 28 frozen relation instances were bound.
- 24/28 relation instances had an exact support signature repeated in at least 2/3 draws.

## Attribution of the four unstable support signatures

The four strict-gate misses do not form one architecture-level failure mode:

- D `P1-1 OPEN_NEW`: strong-model reference rejects the branch under the current frozen Kernel jurisdiction; the binder varied over companion safety/hack units and often returned no jurisdiction anchor.
- D `P1-6 REINFORCE(Q1)`: strong-model reference rejects the upstream relation itself; Flash varied over weakly related Astra announcement units.
- X `P1-6 REINFORCE(M1)`: strong-model reference accepts the relation. All three draws included the core architectural unit `neu-0005`; exact-set instability came from optional companion units.
- N4 `P1-4 REINFORCE(Q1)`: the core `neu-002` + direct-control evidence remained present while optional companion units varied; Q1 is not part of the strong-model core relation set.

Thus the preregistered exact-signature promotion gate fails and the weak-model binder is not promoted as a fully stable provenance oracle. However, the architectural goal of decoupling succeeds: provenance binding can no longer create, suppress, retarget, or redirect Relation Mapping output.

## Decision

Keep the two-stage architecture:

`Relation Mapping -> frozen relations -> Support Binding`.

Do not merge relation generation and provenance binding back into one weak-model prompt. Do not tune the binder against the four exact-set misses. Grounding is the next gate and must be evaluated with model-capacity bracketing: strong-model manual adjudication as the architecture ceiling, DeepSeek-Flash as the robustness lower bound.

Production defaults remain unchanged. 10D.6K and Phase 9A remain paused.