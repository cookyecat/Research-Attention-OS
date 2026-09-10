# Phase 10D.2 — Real-Web Source-Diversity Broadening Result

Status: COMPLETE / PARTIAL-MAP BATCH WITH RETAINED TECHNICAL FAILURES

## Frozen measurement

Final measurement SHA: `c6e9e6f33fc5067cf82b023a19dcf27778ccd8d6`

Artifact:
`eval/live/results/phase10d2_real_web_source_diversity_broadening_v0_1/phase10d2_real_web_source_diversity_broadening_v0.1_20260910T110410Z.json`

SHA256: `215eed8ef395e51895d5078128a04afb21705f441ca084f4b9ac3b5c6d8371b4`

Decision stack remained frozen as `Anchored OPEN_NEW Admission + Magnitude-Free + Pareto`; production default remained `one-delta-v1`.

## Preregistered source strata

Batch-2 froze six sources before any RAOS outcome was observed: two Near-Kernel, two Boundary, and two Far-Control sources, with six distinct publishers.

No failed source was substituted after seeing acquisition or model outcomes.
## Technical / acquisition outcomes

| Label | Stratum | Outcome |
|---|---|---|
| N1 | Near-Kernel | URL acquired; first Sensor call returned malformed/truncated JSON; retained as technical failure; no retry |
| N2 | Near-Kernel | Full probability map completed |
| B1 | Boundary | Full probability map completed |
| B2 | Boundary | URLConnector `403 Forbidden`; retained as acquisition failure |
| F1 | Far-Control | URLConnector `403 Forbidden`; retained as acquisition failure |
| F2 | Far-Control | Full probability map completed |

The N1 technical failure occurred on the first Batch-2 execution at `d7cd5accc80b180f79cfe9300446f3a5b2bac2ac` and was explicitly carried forward into the final artifact without within-batch retry. This prevents technical success-rate inflation.

The two `403` failures expose acquisition-access bias in the current observable web surface. They are system evidence, not missing-data rows to be silently replaced.

## Successful static maps

| Label | Stratum | N | Attention | H(Topology) | H(Load-bearing) |
|---|---|---:|---|---:|---:|
| N2 | Near-Kernel | 12 | ENGAGE 12/12 | 0.414 | 0.414 |
| B1 | Boundary | 12 | DROP 12/12 | 0.000 | 0.000 |
| F2 | Far-Control | 12 | DROP 12/12 | 0.000 | 0.000 |
## Structural findings

N2 is a strong Near-Kernel positive control. `CHALLENGE(B2)` appeared and was load-bearing in 12/12 Relation samples, while Attention stayed ENGAGE 12/12. Occasional OPEN_NEW branches were redundant rather than replacing the primary decision-causal relation.

B1 is a useful Boundary control: despite agent-related language and a non-empty Locate target set, Relation Mapping emitted no material CognitiveEffect in 12/12 samples and Attention stayed DROP 12/12.

F2 is a clean Far-Control control. Locate itself was empty 3/3; Relation Mapping stayed empty and Attention stayed DROP 12/12.

Across the three successful maps, the expected qualitative distance ordering was respected without any policy tuning: a directly relevant multi-agent architecture result produced a stable high-attention basin, an agent-governance article produced no material Delta for this Kernel, and unrelated astronomy produced no cognitive topology at all.

## Cumulative sample status

Phase 10A contributed 4 canonical maps / 72 Relation samples. Phase 10D.1 contributed 4 real-web maps / 72 Relation samples. Phase 10D.2 adds 3 successful real-web maps / 36 Relation samples plus 3 retained technical/acquisition failures.

Cumulative successful maps are now `11`, with `180` frozen-world Relation Mapping realizations.

## Bounded conclusion

Batch-2 continues to support the feasibility of distributional cognitive measurement outside the canonical fixtures, while also exposing two production-relevant observability limits: URL acquisition access bias and long-output Sensor/schema reliability.

No theory rewrite is justified from Batch-2 alone. The next broadening batch should use acquisition-only preflight before preregistration so source accessibility is known without observing any RAOS cognitive outcome. This is an engineering sampling improvement, not outcome-based source selection.

## Regression

Full backend regression, run with repository root on `PYTHONPATH`: `615 passed / 63 skipped / 1 failed`.

The sole failure remains historical Case K: expected urgency `PREEMPT`, actual `PRIORITY`. No new regression was introduced by Phase 10D.2. An immediately preceding pytest invocation without `PYTHONPATH=.` failed during collection on top-level `eval` imports; that command-environment error is not a code regression and is excluded from the regression result.
