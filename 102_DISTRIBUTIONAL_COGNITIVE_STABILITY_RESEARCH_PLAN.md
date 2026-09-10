# Distributional Cognitive Stability Research Plan v1.0

**Status:** PLANNED / CONSTRUCTION BASELINE — 2026-09-10  
**Immediate next gate:** Phase 8C.12 — Cognitive Mapping Longitudinal Stability  
**Production default:** `one-delta-v1` (unchanged)

## 1. Research question

RAOS need not return an exactly identical Cognitive Topology on every LLM realization. The stronger and more useful requirement is:

> **Random cognitive realizations should remain distributed around a stable decision-preserving structure.**

For a frozen source/article `E` and frozen Cognitive Kernel `K`, repeated topology realizations are written as:

$$
T^{(i)} \sim P(T\mid E,K)
$$

`T` is the decision-oriented Cognitive Topology: the set of cognitive relations such as `REINFORCE(Q2)`, `CHALLENGE(B1)`, or an anchored `OPEN_NEW`. It is a projection of the audited semantic world onto the current Kernel, not a complete representation of the article.

## 2. Theory boundary: do not confuse D/S/P with S/A/L/R

`D / S / P` remain the frozen, approximately orthogonal **judgment dimensions** used by Attention-world reasoning. This plan does not add a fourth D/S/P variable.

For stability attribution, the processing chain is instead decomposed into **causal stages**:

$$
E \xrightarrow{S} S_E \xrightarrow{A} A_E \xrightarrow{L_K} L_E \xrightarrow{R_K} T_E
$$

where:

- `S` — Sensor: candidate semantic world extracted from the source.
- `A` — Auditor: evidence-supported semantic world admitted downstream.
- `L` — Locate: candidate Kernel jurisdictions / nodes where the information may matter.
- `R` — Relation Mapping: cognitive relation from admitted meaning to Kernel (`REINFORCE / CHALLENGE / OPEN_NEW`).

These stages are **not statistically independent and are not claimed to be orthogonal coordinates**. They are useful because they can be frozen, replayed, and intervened on separately.

The earlier shorthand `T=T(S,A,C)` remains a coarse causal mnemonic only. Formal stability work should prefer `S/A/L/R`, with the old `Cognitive Mapping` label understood as the downstream `L+R` region rather than a primitive dimension.

## 3. Working concept: Cognitive Attractor

`Cognitive Attractor` is retained as a **working analogy / hypothesis**, not yet a formal dynamical-systems claim.

The analogy is useful: individual realizations may vary, while a stable family of topologies, causal cores, and Attention decisions forms a persistent basin. A true dynamical-systems attractor would require an explicit evolving state and evidence of convergence/invariance under a state transition. Repeated independent samples from fixed `E,K` are not sufficient by themselves.

Until that stronger evidence exists, preferred formal language is:

$$
\boxed{\text{Distributional Structural Stability}}
$$

and preferred descriptive language is **cognitive distribution / cognitive basin**.

## 4. Do not replace Jaccard; separate metric spaces

Jaccard answers a representation question:

> How similar are two topology edge sets?

It does **not** answer:

> Will the current Decision Policy make the same decision?

This mismatch is expected under winner-take-all, Pareto, or article-level max/join policies. One added edge can be decision-dominant while the overall set remains 94% similar.

Therefore the plan keeps representation metrics and adds policy-relative causal metrics rather than trying to force Jaccard to predict Attention.

## 5. Decision-Causal Core — the load-bearing walls

Let `Π(T)` denote the frozen downstream decision projection for topology `T` under a specified strategy. For v0.1 it should at least include Article disposition; where practical it should also retain urgency / expected output so that two plans are not called equivalent merely because both say `ENGAGE`.

A relation `r` is a single-edge load-bearing relation when:

$$
r \in Core_\Pi(T)
\iff
\Pi(T\setminus\{r\}) \neq \Pi(T)
$$

Human meaning:

> **Remove the relation; if the decision changes, that relation was a load-bearing wall.**

This core is explicitly **policy-relative**. Changing one-delta / Pareto / admission rules may change which edges are load-bearing.

v0.1 uses single-edge ablation only. This can miss redundant or synergistic groups of relations. Pairwise/minimal-cut causal search is deferred unless evidence shows single-edge ablation produces an empty core while group-level causality is clearly present.

## 6. Three stability layers

### 6.1 Representation stability

Already implemented by `topology-stability-metrics-v0.1`:

1. Critical Relation Recall
2. Exact Topology Match / modal rate
3. Pairwise Jaccard
4. Topology Entropy

These are descriptive and diagnostic.

### 6.2 Causal-core stability

For repeated samples:

$$
p_{core}(r)=P\big(r\in Core_\Pi(T)\big)
$$

This estimates how often a relation becomes a decision load-bearing wall.

A high-frequency topology edge can be non-causal; a lower-frequency edge can be highly decision-causal. This is why raw relation frequency and causal-core frequency must be reported separately.

### 6.3 Product-decision stability

For Attention action `a`:

$$
p_A(a)=P(\Pi(T)=a)
$$

At minimum:

`P(DROP), P(AWARE), P(WATCH), P(ENGAGE)`.

A system may have moderate topology entropy while having a sharply concentrated causal core and Attention distribution. That is an acceptable form of robustness.

## 7. Pluggable chip architecture

All chips are measurement/research-only until separately promoted.

### Chip D0 — Deterministic Causal Core

Proposed id: `decision-causal-core-v0.1`

Input: one frozen CognitiveEffect topology + frozen Decision Strategy / Admission / Calibration.  
Method: deterministic single-edge ablation; no LLM calls.  
Output: baseline decision, per-edge counterfactual decision, `Core_Π(T)`.

Purpose: answer **which walls carry this particular decision?**

### Chip P1 — Static Probabilistic Cognitive Map

Proposed id: `probabilistic-topology-map-v0.1`

Input: repeated realizations under identical `E,K`, prompt/configuration, and bounded measurement epoch.  
Output: empirical relation probabilities, empirical causal-core probabilities, Attention distribution, confidence intervals, topology metrics.

Purpose: estimate a local stationary approximation to:

$$
P(T\mid E,K)
$$

v0.1 should be empirical and non-parametric. Do not fit a sophisticated generative distribution over the combinatorial topology space unless the observed support requires it.

### Chip T1 — Temporal Distribution Drift

Proposed id: `topology-temporal-drift-v0.1`

Input: two or more independently frozen probability snapshots from identical `E,K` and identical declared execution configuration.  
Output: distribution-shift diagnostics.

Primary simple comparisons:

- Jensen-Shannon divergence of the 4-way Attention distribution.
- Per-relation Bernoulli drift for `P(r in T)`.
- Per-relation causal-core drift for `P(r in Core_Π(T))`.
- Aggregate / core-weighted summaries of those relation drifts.

Exact-topology JSD may be reported as exploratory because sparse combinatorial support can make it sample-hungry.

### Chip T2 — Stochastic Process Model (conditional only)

Do **not** implement initially.

Only open this gate if repeated time snapshots show systematic nonstationarity that exceeds sampling uncertainty and cannot be explained by input/prompt/configuration changes. Candidate first tools should be change-point / regime-shift models before a full Markov/HMM/state-space model.

Purpose: model a real evolving cognitive basin only if the simpler stationary model fails.

## 8. Immediate construction: Phase 8C.12 — Cognitive Mapping Longitudinal Stability

Goal: determine whether the current downstream mapping has moved to a different basin from Phase 8C.8 under the **same audited semantic world**.

### Gate 8C.12A — Locate longitudinal replay

For RS05 / RS15 / RS11 / RS12 first:

- freeze exact Phase 8C.8 audited units;
- freeze Kernel fixtures;
- repeat current Locate using the same declared model/config;
- compare against the historical Phase 8C.8 Locate distribution using the existing metrics chip.

Question: **did the location/jurisdiction basin move?**

### Gate 8C.12B — Relation Mapping longitudinal replay

Construct an exact replayable frozen Locate fixture from the Phase 8C.8 stored match records wherever all required fields can be reconstructed faithfully. Then:

- exact same audited units;
- exact same Kernel;
- exact frozen Locate fixture;
- repeat only Relation Mapping / Impact.

Question: **with both semantic world and jurisdiction frozen, did the relation/effect basin move?**

If historical Locate cannot be reconstructed exactly, label the experiment as partially controlled; do not claim pure `R` attribution.

### Gate 8C.12C — Controls

After canonical cases, use A/X as real-web non-empty controls and C/D as empty/negative controls if cost remains reasonable. No Sensor or Auditor reruns are required for this gate.

Exit condition: identify whether the historical→current drift primarily enters through `L`, `R`, or remains unresolved. No policy tuning during this phase.

## 9. Phase 8C.13 — Decision-Causal Core Chip

Implement Chip D0 only after 8C.12 attribution is frozen.

Initial validation set:

- RS05: known critical CHALLENGE positive control.
- RS15: multi-channel / redundant-relation case.
- RS11: peripheral-association case.
- RS12: boundary case.
- D: prior free-floating OPEN_NEW failure replay.

Report topology frequency separately from causal-core membership. Do not call a high-frequency edge "critical" merely because it is common.

## 10. Phase 10A — Static Probabilistic Topology Pilot

Phase 10 should open only after the deterministic attribution machinery above is trustworthy.

First pilot:

- freeze `E`, `K`, Sensor/Auditor artifact where the research question is downstream stochasticity;
- freeze prompt SHA, model alias, temperature, reasoning settings, schemas, code SHA and strategy fingerprints;
- collect repeated `L/R -> T -> Core -> Attention` samples inside one bounded epoch;
- start with a preregistered modest sample count (e.g. 12) and use a preregistered precision-based expansion rule rather than expanding only when results look interesting.

For relation/core Bernoulli probabilities, report empirical frequency plus a simple confidence interval. For the 4-way Attention distribution, report counts/proportions and entropy. Avoid pseudo-precision from small `N`.

The first Cognitive Map is therefore:

$$
\mathcal M_t(E,K)
=
\big(
P_t(r\in T),
P_t(r\in Core_\Pi),
P_t(A)
\big)
$$

This factorized empirical map is deliberately simpler than attempting to estimate the full combinatorial `P(T)` from few samples.

## 11. Phase 10B — Temporal Basin-Shift Measurement

At later independently frozen checkpoints, repeat the same static measurement under exact input/configuration controls.

Separate two quantities:

### Within-epoch uncertainty

How dispersed is the current distribution? Examples: relation Bernoulli uncertainty, topology entropy, Attention entropy.

### Cross-epoch drift

How different is the new distribution from the previous one? Use JSD / relation-frequency drift / core-frequency drift.

Do not write the old intuition `V = V_local + V_temporal` as literal variance addition. The two are different statistical objects: one describes dispersion inside a snapshot; the other describes distance between snapshots.

## 12. When is "Cognitive Attractor" promoted from analogy to model?

Require evidence for all of the following before using attractor terminology formally:

1. repeated realizations concentrate around one or a small number of decision-equivalent structural basins;
2. the decision-causal core distribution is substantially more stable than peripheral topology;
3. small stochastic perturbations do not eject the system into unrelated decision basins;
4. multiple time snapshots show either persistence of the basin or interpretable regime shifts;
5. if a dynamical attractor is claimed, an explicit state evolution / transition process is defined rather than merely repeated iid-style sampling.

Until then, call it a **Cognitive Basin / Distributional Structural Stability** hypothesis.

## 13. Basin-shift attribution checklist

Before attributing any temporal shift to "LLM randomness" or model drift, freeze/log:

- source/artifact SHA;
- Kernel fixture SHA / node identities;
- prompt version + SHA;
- code / measurement SHA;
- model alias and any returned model metadata;
- temperature / reasoning configuration;
- schema / repair path;
- unit ordering and support packet geometry;
- decision/admission/calibration strategy fingerprints.

A basin shift is a residual after these observable causes are held fixed or explicitly accounted for.

## 14. Boundary with Phase 9

This plan initially studies **fixed `K`**. That is a null experiment for internal RAOS stochasticity.

Phase 9 intentionally allows cognition to change:

$$
K_t \to K_{t+1}
$$

Then a topology shift may be legitimate because the user's Kernel truly evolved. Phase 9 must therefore distinguish:

- legitimate change caused by `K_t -> K_{t+1}`;
- external-world/source change;
- internal RAOS distribution drift under otherwise fixed conditions.

The fixed-`E,K` probability map developed here becomes the noise/drift baseline needed to interpret genuine longitudinal cognitive alignment later.

## 15. Research gates / stop rules

1. **Do not jump to a stochastic-process model** if a stationary empirical distribution explains the observed variation.
2. **Do not tune Auditor/Sensor to reproduce historical verdicts**; stability is not correctness.
3. **Do not tune Jaccard to mimic the decision policy**; keep representation similarity and decision causality separate.
4. **Do not reintroduce raw pseudo-cardinal magnitude** to solve topology uncertainty.
5. **Do not promote Pareto / Magnitude-Free / Anchored admission to production** from stability evidence alone.
6. Escalate from single-edge causal core to pairwise/group causal cuts only if redundancy is empirically shown to hide load-bearing structure.
7. Escalate from static probability to temporal stochastic models only after repeated snapshot evidence demonstrates real basin drift.

## 16. Construction order

```text
8C.11 archive                         COMPLETE
        ↓
8C.12 Locate vs Relation longitudinal attribution
        ↓
8C.13 Decision-Causal Core chip
        ↓
Phase 10A Static Probabilistic Cognitive Map chip
        ↓
Phase 10B Temporal JSD / basin-shift chip
        ↓ only if necessary
Phase 10C change-point / stochastic-process model
```

The governing principle is:

> **Do not stabilize every realization. Stabilize the decision-bearing distribution.**

Chinese working formulation:

> **RAOS 不要求每一次认知结果逐字一致；它要求随机认知结果围绕一个稳定的决策骨架分布。皮肉可以变化，承重墙和最终 Attention 的概率结构不能无故漂移。**
