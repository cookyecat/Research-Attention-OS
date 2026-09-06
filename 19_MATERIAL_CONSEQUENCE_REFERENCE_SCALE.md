# Research Attention OS — Material Consequence Reference Scale

Status: **ACTIVE S CALIBRATION — CANDIDATE MODEL**  
Date: 2026-09-06  
Phase: II-B Attention Policy Calibration  
Predecessor: `18_MATERIAL_CONSEQUENCE_STUDY.md`

---

## 1. Why MC6 matters

Human calibration rejected the rule that an event becomes MATERIAL merely because it radically changes a very small local system.

Examples supplied by the user make the boundary intuitive:

- a family dispute can structurally change one household yet remain socially bounded;
- a fight in one class can remove a teacher yet remain a routine local affair;
- a small-town groundwater rule can substantially change that town while remaining too narrow to matter at a broader reference scale.

Therefore:

$$
\boxed{
Large\ local\ relative\ effect\not\Rightarrow S=1
}
$$

S must contain some notion of consequence at a sufficiently consequential reference scale rather than normalizing to the smallest affected system.

---

## 2. Mainstream-media analogy: useful but not identical

The user observed that mainstream media already performs a similar filtering function: routine neighborhood, family, low-level personnel, and tiny-company events are usually not selected for general audiences, while social, national-government, industry, scientific, market, or culturally consequential events are much more likely to be selected.

This is a useful external intuition for S, but RAOS must not define S by observed media coverage itself.

Why:

- observed coverage / virality / discussion level belongs to `P`;
- audience proximity / beat relevance resembles `D`;
- event consequence / significance is the part most analogous to `S`;
- timeliness and urgency belong to runtime allocation rather than S itself.

Thus mainstream editorial selection is a mixed policy, while RAOS deliberately decomposes it:

$$
\boxed{S=consequence/significance}
$$

$$
\boxed{D=standing audience relevance}
$$

$$
\boxed{P=current public-attention state}
$$

A media editor's instinct is therefore useful as a calibration prior for S, but `was widely reported` must not be used as the causal definition of S.

---

## 3. Simpler candidate S model

The qualitative evidence suggests that the four-lens `Magnitude / Scope / Persistence / Generalizability` description may be more detailed than necessary for the current stage.

A simpler candidate is a two-route materiality frontier.

Let:

- $V(E)$ = absolute severity / intrinsic consequence of the event;
- $R(E)$ = broader reach / systemic spillover / shared-state consequence.

Candidate:

$$
\boxed{
S(E)=1
\quad\text{when}\quad
V(E)\text{ is sufficiently high}
\;\lor\;
R(E)\text{ is sufficiently high}
}
$$

This is not yet a frozen formula or weighted score.

Physical interpretation:

### Route A — absolute severity

A geographically narrow event may still be MATERIAL if the direct consequence is severe enough in absolute terms, for example catastrophic loss of life or similarly extreme irreversible harm.

### Route B — systemic/shared-state impact

An event may be MATERIAL because it changes a wider shared state even when the origin is small, for example:

- national legal precedent;
- industry-wide engineering practice;
- accepted scientific knowledge;
- capability frontier;
- market structure;
- broad cultural behavior;
- national-level institutional control or policy direction.

Bounded local/private affairs remain NOT_MATERIAL when neither route crosses the materiality frontier.

---

## 4. Important distinction: raw scope is not impact

A large affected population does not automatically imply S.

Example:

```text
80 million customers receive a visually redesigned bank statement
but rights, cost, access, behavior, and risk do not change
```

Raw scope is huge, but causal consequence can remain trivial.

Therefore:

$$
\boxed{PopulationCount\neq S}
$$

Likewise, actor rank or fame is not itself S. A high-authority actor matters only insofar as the event changes control of a consequential system or creates broader downstream consequence.

---

## 5. Social-event transformation

A local incident can cross from NOT_MATERIAL to MATERIAL without becoming geographically large at the origin.

The key transition is not `local -> national news` as such. The underlying event becomes material when it starts to represent or cause a broader consequence, for example:

- extreme severity;
- evidence of a repeated/systemic social problem;
- wider institutional response;
- policy or legal precedent;
- replicated pattern beyond the immediate participants.

Media attention may follow this transition, but that attention is evidence for P, not the definition of S.

---

## 6. Revised calibration v2 design

The second controlled calibration was revised before Human labels were elicited.

Artifact:

`eval/live/manifest.material_consequence_calibration.v2.yaml`

It now contains five controlled pairs:

```text
MS1 / MS2   bounded routine local event vs extreme local severity
MS3 / MS4   local structural policy vs national precedent
MS5 / MS6   low-level local personnel vs cabinet-level authority change
MS7 / MS8   huge population but trivial effect vs small niche industry structural effect
MS9 / MS10  private company gain vs independently reproduced field-level practice change
```

The cases intentionally omit whether media covered the event so that P cannot leak into the S calibration.

---

## 7. Current research hypothesis

Current best candidate:

> **S is not importance relative to the smallest affected unit. S asks whether an event crosses a general materiality frontier through sufficiently severe absolute consequence or sufficiently broad/systemic/shared-state consequence.**

This remains a calibration hypothesis.

Do not yet introduce:

- numeric weights;
- an ordinal S scale;
- a fixed hierarchy of geography or organization levels;
- mainstream-media coverage as a label;
- a new ontology of consequence types.

The next step is Human labeling of MS1-MS10, then inspect whether the two-route model survives.