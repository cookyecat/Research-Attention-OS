# Phase 10D.6L.4J — OPEN_NEW Jurisdiction Capacity Result

**Status:** CLOSED / INPUT-CONTRACT DIAGNOSIS CONFIRMED
**Date:** 2026-09-12

Measurement SHA: `7e3d65fce8f44e34eac6b59dcf7a7e482720510a`.

Artifact: `eval/live/results/phase10d6l4j_open_new_jurisdiction_capacity_v0_1/phase10d6l4j_open_new_jurisdiction_capacity_v0.1_20260911T213653Z.json`
SHA256: `9f865d5ff2dc73a80fe67abe81c9134bad215f1cac49afe69bdb39ec50718aa1`.

All 3 batch calls were structurally successful. Both frozen OPEN_NEW items were stable 3/3 as `INSUFFICIENT_JURISDICTION`, exactly matching the frozen strong reference. Critical modal errors: 0.
## Interpretation

The two critical OPEN_NEW errors in 10D.6L.4 v0.1 were not evidence that the architecture was wrong. The weak evaluator had been given only anchor codes, not the full anchor semantics required to judge jurisdiction.

Once full Kernel anchor title/proposition/type semantics were supplied, the weak evaluator correctly rejected both broad/mismatched jurisdictions.

Therefore targeted relation-support grounding and OPEN_NEW jurisdiction admission should remain separate semantic checks. The latter requires full jurisdiction semantics, not opaque IDs/codes alone.
