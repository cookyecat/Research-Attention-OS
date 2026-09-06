# Research Attention OS — Material Consequence Reference Scale

Status: **ACTIVE S CALIBRATION — REFERENCE-SYSTEM DISTURBANCE MODEL**  
Date: 2026-09-06  
Phase: II-B Attention Policy Calibration  
Predecessor: `18_MATERIAL_CONSEQUENCE_STUDY.md`

---

## 1. Why MC6 and MS2 matter

Human calibration rejected two overly broad candidate rules:

1. an event is not MATERIAL merely because it radically changes a very small local system;
2. high local severity alone is not sufficient when the event remains a bounded local incident with no broader social/systemic consequence.

Examples supplied by the user make the boundary intuitive:

- a family dispute can structurally change one household yet remain socially bounded;
- a fight in one class can remove a teacher yet remain a routine local affair;
- a small-town groundwater rule can substantially change that town while remaining too narrow to matter at a broader reference scale;
- even a severe violent event at one remote school can remain NOT_MATERIAL if it is only a bounded local tragedy and does not reflect or produce a wider social/institutional disturbance.

Therefore:

$$
\boxed{Large\ local\ relative\ effect\not\Rightarrow S=1}
$$

and calibration v2 further falsifies:

$$
\boxed{High\ local\ severity\not\Rightarrow S=1}
$$

The relevant question is not how dramatically the smallest affected unit changes. The event must disturb a sufficiently consequential shared/public reference system.

---

## 2. User's concise physical interpretation

The strongest current human formulation is:

> **S measures the disturbance an event creates to consequential shared systems such as the nation, society, an industry/field, or the public.**

This is close to editorial **selection / news judgment**: is the underlying event important enough, in its own right, to deserve general or beat-level coverage rather than remain a local/private/routine matter?

The mainstream-media analogy is useful but not identical to S. Observed coverage, virality, and current discussion belong to `P`; personal/geographic relevance belongs to `D`. For S, use the editor's consequence judgment while conceptually hiding current attention.

A useful annotation question is:

> **If I were a serious national or industry editor, and I did not know whether this event was already trending, would the event itself be important enough to enter the editorial selection pool because it materially perturbs a consequential shared system?**

This is an elicitation aid, not the formal definition.

---

## 3. Reference-system disturbance model

Let $\mathcal G$ denote the class of consequential shared/public reference systems. Examples may include:

- national/state institutions and control;
- society/public welfare and social structure;
- industries, technical fields, professions, or markets;
- shared scientific knowledge or capability frontiers;
- broad cultural states or practices.

These are examples, not a fixed ontology.

For a reference system $G\in\mathcal G$, compare its state with and without event $E$ over a relevant horizon $\tau$:

$$
\boxed{
\Delta_G(E,\tau)
=
Diff\left(
State_G(W^E_{t+\tau}),
State_G(W^{\neg E}_{t+\tau})
\right)
}
$$

Then the current candidate semantic model is:

$$
\boxed{
S(E)=1
\iff
\exists G\in\mathcal G,\exists\tau\in H:\
MaterialDisturbance_G(E,\tau)=1
}
$$

Physical meaning:

> **Does the event materially perturb at least one consequential shared reference system?**

The reference system is deliberately not the smallest affected household, class, school, town, team, or company merely because the event is large relative to that unit.

---

## 4. Raw size, fame, and local severity are not S

Calibration now supports several negative invariants:

$$
\boxed{PopulationCount\neq S}
$$

MS7 affects 80 million bank customers but changes only statement layout; rights, cost, access, security, and behavior remain unchanged, so `S=0`.

$$
\boxed{ActorProminence\neq S}
$$

A famous actor or company can generate trivial events.

$$
\boxed{LargePrivateGain\neq S}
$$

MS9 cuts one firm's energy use by 70%, but the method remains private and does not alter industry practice, so `S=0`.

$$
\boxed{LocalSeverity\neq S}
$$

MS2 has multiple deaths and serious injuries but remains a bounded local tragedy with no stated broader institutional/social consequence, so `S=0` under the current human calibration.

This does not mean casualties are never material. A local incident can become `S=1` if it reveals or creates a broader social problem, systemic pattern, institutional response, policy change, precedent, or other shared-system disturbance.

---

## 5. What calibration v2 supports positively

Human labels:

```text
MS1   NOT_MATERIAL
MS2   NOT_MATERIAL
MS3   NOT_MATERIAL
MS4   MATERIAL
MS5   NOT_MATERIAL
MS6   MATERIAL
MS7   NOT_MATERIAL
MS8   MATERIAL
MS9   NOT_MATERIAL
MS10  MATERIAL
```

Artifact:

`eval/live/manifest.material_consequence_calibration.v2.human.yaml`

The four MATERIAL cases all perturb a consequential shared system:

### MS4 — national legal precedent

A local dispute becomes a nationwide legal rule affecting water-use rights across regions.

### MS6 — national control-state change

A cabinet-level ministry changes its top executive controller. No new policy is required for S to be MATERIAL because the control state of a nationally consequential institution itself changes.

This is important: S can include a change in **control / option structure**, not only an already-realized downstream policy outcome.

### MS8 — niche-industry structural constraint

Only ~60 firms are directly affected, but the regulation changes the operating constraints of the entire niche industry, forcing redesign or exit.

Therefore raw headcount is not the correct scale. The relevant reference system is the industry itself.

### MS10 — field-level engineering practice change

A reproducible 70% energy reduction propagates across manufacturers and begins changing standard sector practice.

Again, the material consequence is the change to a shared industry state, not the private gain of one firm.

---

## 6. Why the earlier two-route model is rejected

The previous candidate was:

$$
S(E)=1
\quad\text{if}\quad
AbsoluteSeverity(E)\text{ high}
\lor
SystemicImpact(E)\text{ high}
$$

MS2 falsifies the first route as an independent sufficient condition.

The better model is not:

```text
severity OR scope
```

but:

```text
material disturbance of a consequential shared reference system
```

Severity, reach, persistence, authority, replication, precedent, and other features are possible evidence for that disturbance. They are not yet separate S variables and should not be combined into a weighted score.

---

## 7. Relation to media selection

The user's editorial analogy is now a central calibration aid:

```text
local/private/routine matter
    -> usually editorially filtered out

national / social / industry / scientific / market / cultural disturbance
    -> candidate general-interest or beat-level selection
```

But RAOS preserves the decomposition:

$$
\boxed{S=underlying\ consequence/significance}
$$

$$
\boxed{D=standing\ personal\ jurisdiction}
$$

$$
\boxed{P=current\ public\ attention}
$$

So `mainstream media reported it` is not an S label. It may be evidence for P and noisy evidence for S. The formal S estimator must reason from the underlying event, not from coverage count.

---

## 8. Current candidate definition

The intuitive definition remains:

$$
\boxed{S:\text{这件事本身有没有实质后果？}}
$$

The current formal interpretation is now:

> **S asks whether the event creates a material disturbance in at least one consequential shared/public reference system, rather than merely producing a large relative change inside a small bounded local/private unit.**

This model is more consistent with MC1-MC10 and MS1-MS10 than the earlier smallest-system normalization or absolute-severity-OR-systemic-impact models.

Do not yet introduce:

- numeric disturbance weights;
- a fixed hierarchy of geography/administrative rank;
- an ontology of consequence types;
- an ordinal S scale;
- observed media coverage as the definition.

---

## 9. Next probe

The next small calibration should focus only on the remaining ambiguity:

1. **control / option-state change versus realized consequence** — e.g. high-level institutional leadership or credible frontier capability before downstream adoption;
2. **local incident versus social/systemic signal** — same local origin, but one remains isolated while another evidences a repeated social problem or triggers broader institutional change;
3. **major private actor versus industry/shared state** — when a large company event is important because of spillover rather than mere company size.

If those boundaries are stable, freeze the S semantic contract and only then implement the first S estimator.
