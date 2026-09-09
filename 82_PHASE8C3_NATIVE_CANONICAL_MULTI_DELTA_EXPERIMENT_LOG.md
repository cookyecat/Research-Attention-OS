# Phase 8C.3 — Native Canonical Multi-Delta Experiment Log

Status: **ACTIVE — STEP 1 TEMPERATURE A/B PREREGISTERED**
Date: 2026-09-09

## Purpose

Test the next RAOS architecture without treating the Phase 8C.2 legacy `ExtractionResult` bridge as the final production language.

Working sequence:

```text
1. Temperature 0.1 vs 0
2. Native Canonical Semantic Interface
3. Multi-Locate / Multi-Delta
4. Per-channel Attention
5. Article-level Attention aggregation and RS05/RS15/RS11/RS12 rerun
```

Phase 7A remains the semantic working baseline:

$$
\boxed{Decision\text{-}Sufficient\ Semantic\ Precision=Evidence\ Fidelity+Scope\ Fidelity+Relational\ Fidelity}
$$

Do not replace this formulation without controlled contrary evidence.
## Step 1 — Temperature stability A/B

Question: how much of the observed instability can be reduced by removing intentional sampling variance?

Freeze the perception layer completely:

```text
Sensor + Auditor + Audited Semantic Representation = fixed
```

Repeat only the cognitive decision modules:

```text
Locate / match_kernel
→ Cognitive Impact / Delta
→ Attention Policy
```

Cases:
- RS15 fixed semantic world from the prior boundary attribution.
- RS05 frozen Phase 7A canonical four-unit world as a stable control.

Conditions: `temperature=0.1` versus `temperature=0.0`, 6 repeats each, interleaved. Production defaults remain unchanged. The new client parameter preserves `0.1` as the default and exists only to make the A/B controllable.
