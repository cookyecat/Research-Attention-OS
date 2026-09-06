# Research Attention OS — Material Consequence Reference Scale

Status: **S SEMANTIC CONTRACT — FROZEN FOR ESTIMATOR INSTRUMENTATION**  
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

## 2. Canonical physical interpretation

The strongest current human formulation is:

> **S measures the disturbance an event creates to consequential shared systems such as the nation, society, an industry/field, or the public.**

Canonical intuitive definition remains:

$$
\boxed{S:\text{这件事本身有没有实质后果？}}
$$

Operational intuition:

> **How much does this event disturb a consequential shared reference system, rather than merely changing a small local/private unit?**

This is close to editorial **selection / news judgment**: is the underlying event important enough, in its own right, to deserve general or beat-level coverage rather than remain a local/private/routine matter?

The mainstream-media analogy is useful but not identical to S. Observed coverage, virality, and current discussion belong to `P`; personal/geographic relevance belongs to `D`. For S, use the editor's consequence judgment while conceptually hiding current attention.

A useful annotation question is:

> **If I were a serious national or industry editor, and I did not know whether this event was already trending, would the event itself be important enough to enter the editorial selection pool because it materially perturbs a consequential shared system?**

This is an elicitation aid, not the formal definition.

---

## 3. Formal reference-system disturbance model

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

Then:

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

## 4. What “disturbance” can mean

A material disturbance can be a change in a shared system's:

- rules, law, or institutional constraints;
- control / authority state;
- technical capability or cost frontier;
- accepted knowledge or evidence state;
- industry/market structure or standard practice;
- public risk or social structure;
- broad cultural behavior or meaning.

These are consequence forms, not separate S variables.

Importantly, disturbance need not mean an already-realized downstream outcome. A change in the control or option structure of a consequential system may itself be material. MS6 supports this: replacing the minister changes the top control state of a national ministry even before a new policy is announced.

---

## 5. Negative invariants supported by calibration

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

$$
\boxed{ObservedMediaCoverage\neq S}
$$

Coverage and virality belong to P. Media selection is only an analogy / noisy proxy for the underlying significance judgment.

---

## 6. Calibration v2 result

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

The MATERIAL cases all perturb a consequential shared system:

- **MS4** — local dispute becomes nationwide legal precedent;
- **MS6** — top control state of a national ministry changes;
- **MS8** — regulation changes the operating constraints of an entire niche industry despite only ~60 firms;
- **MS10** — independently reproduced method changes standard engineering practice across a sector.

The NOT_MATERIAL cases remain bounded local/private/routine changes or have large raw scope without meaningful state change.

---

## 7. Rejected models

### Smallest-system normalization — rejected

$$
Large\ consequence\ relative\ to\ any\ affected\ local\ system
\not\Rightarrow
S=1
$$

### Absolute severity OR systemic impact — rejected

The previous candidate was:

$$
S(E)=1
\quad\text{if}\quad
AbsoluteSeverity(E)\text{ high}
\lor
SystemicImpact(E)\text{ high}
$$

MS2 falsifies absolute local severity as an independent sufficient route.

### Raw scope — rejected

MS7 shows that very large population reach with negligible causal change remains NOT_MATERIAL.

The better abstraction is therefore:

```text
material disturbance of a consequential shared reference system
```

Severity, reach, persistence, authority, replication, precedent, and other features are evidence for this disturbance. They are not separate S variables and should not be combined into a weighted score at this stage.

---

## 8. Relation to D and P

RAOS preserves the decomposition:

$$
\boxed{D=D(E,u)}
$$

> Is the event inside the user's standing attention jurisdiction?

$$
\boxed{S=S(E)}
$$

> Does the event materially disturb a consequential shared reference system?

$$
\boxed{P=P(E,t)}
$$

> Has the event entered or begun entering public/industry attention at time $t$?

For the no-cognitive-change AWARE gap:

$$
\boxed{
AWARE(E,u,t)=S(E)\land\bigl(D(E,u)\lor P(E,t)\bigr)
}
$$

---

## 9. Frozen research decision

Current S semantic baseline:

> **S asks whether the underlying event creates a material disturbance to at least one consequential shared/public reference system—national, social, industry/field, market, scientific/technical, or cultural—rather than merely creating a large relative change inside a small bounded local/private unit.**

This is now frozen for estimator instrumentation.

Do not introduce:

- numeric disturbance weights;
- a fixed hierarchy of geography or administrative rank;
- a large ontology of consequence types;
- an ordinal S scale;
- observed media coverage as the definition.

If future fresh validation exposes a repeated semantic failure, attribute it before changing this contract.

---

## 10. Next step

Proceed in this order:

```text
S semantic contract              FROZEN
  -> implement eval-only S estimator from this contract
  -> freeze estimator/prompt
  -> author fresh S validation after estimator freeze
  -> elicit Human Gold before model predictions
  -> first scored measurement
  -> residual attribution
  -> P study
```

Do not reuse MC1-MC10 or MS1-MS10 as fresh performance evidence.
