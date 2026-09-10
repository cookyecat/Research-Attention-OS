# Semantic Topology Stability — Measurement Model v0.1

Status: RESEARCH MEASUREMENT FOUNDATION
Date: 2026-09-10

## 1. Object of measurement

For a fixed Source and Cognitive Kernel, define the decision-relation topology

\[
T(E,K)=\{(operation,target)\}.
\]

`change_magnitude`, epistemic strength, target importance and Attention are attributes or downstream decisions; they are not part of topology identity. Distinct `OPEN_NEW` branches may use a measurement-only branch signature when needed so unrelated new branches are not collapsed into the same `OPEN_NEW(null)` edge.

## 2. Causal realization model

The observed topology is generated through three stochastic/LLM-bearing stages:

\[
oxed{T=T(S,A,C)}
\]

where `S` is Sensor realization, `A` is Auditor realization conditioned on Sensor output, and `C` is Cognitive Mapping realization conditioned on the admitted semantic world and Kernel localization.

A useful research shorthand is

\[
oxed{V_T pprox V_{Sensor}+V_{Auditor}+V_{Cognition}}.
\]

This is **not** an assumption of additive Euclidean variance and is not an ANOVA claim. `V` denotes attributable discrete instability. Controlled freezing/opening of one stage at a time is the causal method.

## 3. Stability metrics

Primary ordering of evidential importance:

\[
oxed{
CriticalRelationRecall > ExactTopologyMatch > PairwiseJaccard > TopologyEntropy
}
\]

### Critical Relation Recall

For a preregistered decision-bearing relation `r*`:

\[
Recall(r^*)=rac{\#\{i:r^*\in T_i\}}{N}.
\]

This is the highest-priority metric because a topology can have high aggregate similarity while intermittently dropping the one relation that matters to the decision.

### Exact Topology Match

\[
S_{exact}=rac{\max_T count(T)}{N}.
\]

It measures how often the complete relation set equals the modal topology.

### Pairwise Jaccard

\[
J(T_i,T_j)=rac{|T_i\cap T_j|}{|T_i\cup T_j|}.
\]

Mean pairwise Jaccard distinguishes small peripheral edge jitter from wholesale topology change.

### Topology Entropy

\[
H(T)=-\sum_k p_k\log_2 p_k.
\]

Entropy measures realization diversity, but does not identify whether the varying relation is important. It is therefore diagnostic, not the leading KPI.

## 4. Product-level separation

Always report Cognitive Topology stability separately from Attention stability:

\[
oxed{TopologyVariance 
ot\Rightarrow AttentionVariance}.
\]

A robust RAOS may tolerate peripheral cognitive-edge jitter while preserving critical relations and the final Attention action.

## 5. Measurement chip

Reusable deterministic implementation:

`eval/live/topology_stability_metrics_v0_1.py`

Version: `topology-stability-metrics-v0.1`.

The chip canonicalizes topology as a set, computes critical-relation recall, modal exact-match rate, mean pairwise Jaccard, entropy, relation frequency, and a descriptive `1 - mode_rate` instability. The latter is explicitly not treated as physical variance.

## 6. Causal attribution protocol

Open stochastic stages from downstream to upstream:

```text
Frozen Audited World + frozen Locate → repeat Cognitive Mapping
Frozen Sensor Candidates             → repeat Auditor → frozen downstream
Raw Source                           → repeat Sensor → Auditor → frozen downstream
```

Stop at the earliest stage that explains the observed instability before broadening upstream. This preserves the project discipline: attribute first, optimize second.
