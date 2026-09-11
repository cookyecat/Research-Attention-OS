# Phase 10D.6F — Effect Support Binding Preregistration

**Status:** PREREGISTERED / NO OUTCOMES SAMPLED
**Date:** 2026-09-11

## Research question

Can Relation Mapping express each cognitive relation as an auditable semantic claim over the frozen canonical world, with explicit support-unit and jurisdiction bindings, without asking the LLM for decision-bearing cardinal values?

## Frozen input

Reuse exact A/D/X/N4 frozen Auditor-admitted worlds, frozen Phase-10 modal Locate, and deterministic Kernel fixtures. No acquisition, Sensor, Auditor, or Locate call is allowed.

## Candidate relation contract v0.2

Each relation returns only:

- `operation`: `REINFORCE | CHALLENGE | OPEN_NEW`;
- `target_kernel_node_id`: existing eligible target for REINFORCE/CHALLENGE, null for OPEN_NEW;
- `support_unit_ids`: one or more exact IDs from the supplied canonical semantic units;
- `jurisdiction_anchor_ids`: zero or more exact IDs from frozen Locate; OPEN_NEW requires at least one anchor;
- `reason`: semantic explanation.

No `change_magnitude`, `target_importance`, or `epistemic_strength` is requested. These values have zero place in this contract.

## Deterministic validation

Fail closed on any effect whose support ID is absent from the frozen world, whose targeted node is not an eligible frozen Locate target, or whose jurisdiction anchor is absent from frozen Locate. OPEN_NEW additionally requires null target and at least one legal jurisdiction anchor.

Validation must not rewrite an illegal targeted relation into OPEN_NEW.

## Measurement

Run N=6 fresh Relation-Mapping realizations for each of A/D/X/N4 using the same model/runtime settings used by recent canonical shadows. Persist raw structured output and validated effects separately.

Primary measurements:
- structured-output success rate;
- valid-effect rate;
- support-binding legality;
- target/jurisdiction legality;
- support-unit coverage and binding stability;
- relation topology distribution after deterministic validation.

This phase does not promote an Attention policy and does not yet define the final evidence-class-to-epistemic-band mapping. Production defaults remain unchanged; Phase 9A remains paused.
