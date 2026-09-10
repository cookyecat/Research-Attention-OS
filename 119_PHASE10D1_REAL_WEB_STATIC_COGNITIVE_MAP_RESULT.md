# Phase 10D.1 — Real-Web Static Probabilistic Cognitive Map Result

Status: COMPLETE / EXTERNAL-SAMPLE VALIDATION

## Frozen measurement

Measurement SHA: `200dd71a4a2d58962c3d1de16ae28c3adb5bbb47`

Artifact:
`eval/live/results/phase10d1_real_web_static_cognitive_map_v0_1/phase10d1_real_web_static_cognitive_map_v0.1_20260910T094646Z.json`

SHA256: `9afb38a1373f3bbb14ae274930e4e861496a7d7c2beb009fd1e468b2b606ccdc`

Decision stack remained frozen as `Anchored OPEN_NEW Admission + Magnitude-Free + Pareto`; production default remained `one-delta-v1`.

## Acquisition / perception boundary

A, D, and X preserved the Phase 8C.7 source hash and character count. C changed materially: the same OpenAI Deployment Safety URL now returns the full Astra System Card (~184k chars) instead of the older ~5.95k-char narrow extraction. C was therefore classified before model calls as `NEW_SNAPSHOT` and carries no longitudinal claim against the old C snapshot.

Each source received exactly one fresh Sensor v0.2.6 + Auditor v0.1.1 pass, after which the complete admitted world was frozen. Admitted-unit counts were A=20, C=26, D=34, X=18. Locate was repeated 3 times and the target set was identical 3/3 for every source; Relation Mapping was then the only repeatedly sampled stage.

## Static probability maps

| Source | N | Attention distribution | Dominant concentration | H(Topology) | H(Load-bearing) |
|---|---:|---|---:|---:|---:|
| A | 24 | WATCH 14 / DROP 6 / AWARE 4 | 0.583 | 1.520 | 1.384 |
| C | 12 | DROP 12 / 12 | 1.000 | 0.000 | 0.000 |
| D | 24 | WATCH 22 / AWARE 2 | 0.917 | 2.617 | 1.637 |
| X | 12 | ENGAGE 11 / WATCH 1 | 0.917 | 1.189 | 0.414 |

A and D triggered only the preregistered Wilson precision expansion from N=12 to N=24. C and X did not.

## Structural findings

C is a clean real-web negative control: no material CognitiveEffect was emitted in 12/12 Relation samples and Attention stayed DROP 12/12.

X is a clean positive load-bearing example. `CHALLENGE(BT1)` appeared and was load-bearing in 11/12 samples, matching the 11/12 ENGAGE concentration. Peripheral topology varied more than the decision core.

D is the strongest real-web example of internal stochasticity being absorbed downstream. Topology entropy was ~2.62 bits while Attention remained WATCH in 22/24 samples. The dominant load-bearing class was OPEN_NEW, but branch identity is incompletely resolved (see limitation below).

A is deliberately not summarized as a single deterministic label. Its empirical map is multimodal: WATCH 0.583, DROP 0.250, AWARE 0.167. Offline inspection shows two distinct mechanisms: some Relation realizations emit no effect set at all (DROP), while otherwise similar coarse topologies cross the Magnitude-Free epistemic band for OPEN_NEW (`epistemic_strength` around 0.35–0.40 vs ~0.60), producing AWARE vs WATCH. This is a new attribution target, not a reason to retune thresholds from this case alone.

## Eight-case expansion summary

Combining Phase 10A canonical maps with this phase yields 8 case-level maps and 144 frozen-world Relation realizations (72 canonical + 72 real-web).

Descriptively:

- 7/8 cases have dominant Attention concentration >= 0.8;
- 4/8 are fully concentrated at one Attention action;
- 6/8 have at least one relation with load-bearing probability >= 0.8;
- 7/8 have Topology entropy greater than Attention entropy.

These counts are descriptive external-sample support, not a population estimate or significance claim. The recurring pattern remains: internal topology can be materially more variable than the downstream Attention distribution.

## Important limitation: OPEN_NEW identity

For A and D, many OPEN_NEW reasons do not explicitly cite admitted unit ids. The preregistered identity rule correctly preserves these as `OPEN_NEW[UNRESOLVED]` rather than guessing semantic equivalence. Therefore Attention distributions are fully interpretable, but A/D branch-level load-bearing probabilities are coarser than desired and must not be read as proof that all unresolved OPEN_NEW realizations are the same semantic branch.

## Bounded conclusion

Phase 10D.1 supports the feasibility of the Static Probabilistic Cognitive Map outside the canonical fixtures. Real-web sources exhibit multiple regimes: deterministic negative control (C), stable load-bearing positive basin (X), high-topology/low-Attention-entropy basin (D), and genuinely multimodal Attention behavior (A).

The evidence is strong enough to continue probability-based measurement, but not to promote a universal theory or modify production policy. The next useful attribution is not another magnitude experiment: it is to separate remaining decision-band stochasticity (especially epistemic/importance bands) from topology presence/absence, while continuing to broaden source diversity before any theory rewrite.
