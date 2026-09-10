# Phase 8C.10 — Auditor Topology Stability Gate 2A Result

Status: GATE 2A COMPLETE / GATE 2B REQUIRED
Date: 2026-09-10

## Frozen condition

Exact Phase 7A Sensor v0.2.6 non-event candidate units were reused for RS05 / RS15 / RS11 / RS12. Sensor was not regenerated. Semantic Evidence Auditor v0.1.1 (`deepseek-v4-flash`) independently re-audited the same candidates four times. Historical Phase 7A audit artifacts were external references only.

Measurement SHA: `94e228a7f6bf914b914e22be6aea664d6e94f150`.

Artifact: `eval/live/results/phase8c10_auditor_topology_stability_v0_1/phase8c10_auditor_topology_stability_v0.1_20260910T034034Z.json`

SHA256: `bf535061ac92bec498816b932454be5bba9e4ab390e1572d88b9a68c52fcd69e`

## Fresh-repeat stability

| Case | Candidates | Exact modal rate | Pairwise Jaccard | Entropy bits |
|---|---:|---:|---:|---:|
| RS05 | 10 | 0.75 | 0.929 | 0.811 |
| RS15 | 10 | 1.00 | 1.000 | 0.000 |
| RS11 | 12 | 0.75 | 0.944 | 0.811 |
| RS12 | 12 | 1.00 | 1.000 | 0.000 |

Fresh stochastic variance is narrow rather than wholesale: RS05 has one minority realization that additionally admits U03; RS11 has one minority realization that additionally admits N1. RS15 and RS12 are internally invariant across all four fresh repeats.

## Historical-reference drift

Fresh stability does not imply historical identity. Relative to the exact Phase 7A frozen Auditor references:

- RS05 historical admitted set = `{U01,U05,U07,U09}`; current modal additionally admits U06/U08. Mean reference Jaccard = 0.643.
- RS15 current 4/4 set additionally admits NEU4. Reference Jaccard = 0.875.
- RS11 current modal equals historical reference; one fresh repeat additionally admits N1. Mean reference Jaccard = 0.972.
- RS12 current 4/4 set additionally admits N11. Reference Jaccard = 0.917.

This separates two phenomena:

\[
\boxed{V_{Auditor}^{within-run} \neq V_{Auditor}^{historical-basin}}
\]

The first is repeat-to-repeat stochastic admission jitter. The second is a shift in the modal admission boundary relative to an earlier frozen run. The experiment does not attribute the historical shift to a particular provider/model mechanism.

## Interpretation

Gate 2A establishes that `V_Auditor` is non-zero, but mostly localized to boundary semantic units. It does **not** establish product-level instability. A one-unit admitted-set difference matters only if it changes decision-bearing Cognitive Topology or final Attention.

Therefore Gate 2B is required. Only distinct current admitted worlds that differ from the Phase 8C.8 historical audited-world baseline will be propagated through the frozen experimental downstream:

`Locate -> Cognitive Impact -> Anchored OPEN_NEW Admission -> Magnitude-Free -> Pareto -> Article Join`.

No Auditor prompt or threshold is changed before Gate 2B.
