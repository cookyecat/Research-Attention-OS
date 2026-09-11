# Phase 10D.6C — Schema Plumbing Failure and Preregistered Amendment

**Status:** TECHNICAL FAILURE / ZERO VALID C1 OUTCOMES / AMENDMENT LOCKED  
**Date:** 2026-09-11

## Failure

The first 10D.6C execution at measurement SHA `08963a4` produced valid B0 controls but C1 failed schema validation after repair on all 24/24 canonical-input calls. Therefore C1 produced **zero valid cognitive outcomes** and cannot support any semantic conclusion about canonical input.

## Attribution

Inspection found an instrumentation asymmetry introduced by the experimental runner. Production B0 uses `impact_user_prompt(...)`, which explicitly prints the complete JSON response shape. The C1 canonical payload only said `Return the CognitiveImpactResponse JSON schema` and did not print that shape. `chat_json_schema(...)` validates the response but does not itself guarantee that the textual schema is included in the model prompt.

This is a measurement plumbing defect, not evidence against canonical semantic units.

## Allowed amendment

Change **only** C1 output-format instruction by appending the exact same CognitiveImpactResponse JSON skeleton/field names used by production `impact_user_prompt`:
`effects[target_kernel_node_id, operation, change_magnitude, epistemic_strength, target_importance, reason, exploration_candidate]`, plus article-level diagnostic fields.

No semantic instruction, canonical unit content, Kernel/Locate input, system prompt, importance resolver, grounding, strategy, sample size, order or model may change.

Rerun the original interleaved N=6 B0/C1 experiment. The failed artifact remains retained and must not be substituted silently.
