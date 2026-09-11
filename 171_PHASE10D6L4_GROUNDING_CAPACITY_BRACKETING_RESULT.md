# Phase 10D.6L.4 — Grounding Capacity Bracketing Result

**Status:** CLOSED / WEAK GROUNDER NOT PROMOTED / JURISDICTION FOLLOW-UP REQUIRED
**Date:** 2026-09-12

## Frozen setup

Strong grounding reference was frozen before any weak-model grounding outcome. Measurement SHA: `8de852d4dc068d0490a505d2938a4bd5f3dcfca3`.

Artifact: `eval/live/results/phase10d6l4_grounding_capacity_bracketing_v0_1/phase10d6l4_grounding_capacity_bracketing_v0.1_20260911T201703Z.json`
SHA256: `f75addfb6b613bfa9f722327af73e21a84164c0554b2a7808ea49f2482c9cd2c`.

All 9 weak-model batch calls were structurally successful; all 28 items were stable at >=2/3.
## Weak-bound result

Overall modal exact agreement with the strong reference was `8/28 = 28.6%`.

Confusion summary:
- `DIRECT -> DIRECT`: 6
- `DIRECT -> PARTIAL`: 5
- `PARTIAL -> DIRECT`: 12
- `INSUFFICIENT -> INSUFFICIENT`: 2
- `INSUFFICIENT -> DIRECT`: 3

The weak evaluator is therefore systematically permissive rather than unstable. It frequently upgrades `PARTIAL` to `DIRECT`.
## Attribution

For targeted relations only (`n=26`), exact agreement was `8/26 = 30.8%` with one critical `INSUFFICIENT -> DIRECT` error. Most remaining disagreement is `PARTIAL -> DIRECT`, i.e. scope over-permissiveness under the weak evaluator.

For `OPEN_NEW` (`n=2`), both strong `INSUFFICIENT` items were called `DIRECT` by the weak evaluator. However the v0.1 prompt supplied only jurisdiction anchor codes, not the full anchor semantics/propositions. These two outcomes therefore confound evaluator weakness with an under-specified jurisdiction input contract.

Conclusion: do not promote DeepSeek-Flash as Grounding authority. Preserve the strong/weak capacity bracket. Split targeted support-fit from OPEN_NEW jurisdiction admission instead of relaxing the preregistered gate.
