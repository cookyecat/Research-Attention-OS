# Collective Attention Salience (P) — Estimator Modeling

Status: **ACTIVE ESTIMATOR MODELING — SEMANTICS ALREADY FROZEN**  
Date: 2026-09-07  
Semantic baseline: `22_COLLECTIVE_ATTENTION_SALIENCE.md`

> Purpose: design an engineering approximation `P_hat` to the frozen theoretical P variable. This document may evolve during estimator development. It must not redefine the semantic contract merely to accommodate current data limitations.

---

## 1. Frozen estimand

The theoretical target is fixed:

$$
\boxed{
P(E,t)=LatentSalience(R_E(\le t))
}
$$

with:

$$
\boxed{
R_E(t)
=
\frac{1}{|\mathcal G_E|}
\sum_{i\in\mathcal G_E}a_i(E,t)
}
$$

and:

$$
\boxed{
\mathcal G_E=Constituency(Sem(E))
}
$$

The engineering problem is not to redefine these quantities. It is to approximate them from incomplete observations.

Therefore:

$$
\boxed{
\hat P
=
Estimator(
Sem(E),
ConstituencyPrior,
ObservableAttentionEvidence,
History
)
}
$$

---

## 2. Fundamental observability split

The denominator and numerator have different engineering properties.

### 2.1 Denominator: `|G_E|`

The objective constituency is often relatively stable compared with moment-to-moment attention.

Examples:

- active researchers in a scientific subfield;
- users of a particular product or game;
- employees affected by an internal system;
- commuters of a city transit system;
- practitioners in an industry segment;
- broad social public.

Exact counts may be unavailable, but coarse reference scale is often inferable from long-lived knowledge.

This makes `|G_E|` suitable for:

- LLM semantic estimation;
- a small, maintainable lookup/prior table;
- coarse order-of-magnitude estimates;
- cached constituency descriptors that change slowly.

The estimator should prefer **correct scale** over false numeric precision.

### 2.2 Numerator: current genuine attention

The hard quantity is:

$$
\sum_{i\in\mathcal G_E}a_i(E,t)
$$

because current attention is dynamic and platform-specific.

Ideal telemetry would include:

- unique attentive users;
- active search volume;
- sustained read/view time;
- comments / replies / discussion;
- saves / shares / voluntary propagation;
- independent institutional follow-up;
- cross-source / cross-platform propagation;
- bot / paid-exposure diagnostics;
- time history and decay.

RAOS does not currently have platform-scale access to these signals.

This observability limitation belongs to the estimator, not the semantic model.

---

## 3. What the LLM can and cannot supply

### 3.1 Appropriate use of LLM prior knowledge

LLMs have broad learned world knowledge and are well suited to infer a coarse objective constituency from event semantics.

Candidate task:

```text
Event semantics
    ↓
LLM
    ↓
constituency description
reference scale / order of magnitude
reason
```

Example diagnostic output:

```json
{
  "constituency": "active AI-safety research and industry community",
  "reference_scale": "tens of thousands globally",
  "reason": "the event is a specialist AI-safety technical development rather than a mass-consumer event"
}
```

Exact population numbers should not be treated as factual truth unless supported by an external source.

### 3.2 Current numerator cannot come from stale model memory alone

Current P is time-dependent:

$$
P=P(E,t)
$$

Therefore an LLM's pretrained world knowledge is not sufficient evidence for the **current** attention numerator of a new or rapidly changing event.

The LLM may map current observable evidence to an estimated penetration state, but it should not manufacture current attention ex nihilo.

Principle:

$$
\boxed{
LLM\ prior\ knowledge\ is\ useful\ for\ constituency/scale;
\ current\ attention\ requires\ current\ evidence.
}
$$

---

## 4. Constituency prior / lookup design

A lookup/prior layer is promising because objective constituency scale often changes slowly.

However it should be a **prior, not a hard ontology and not the final decision rule**.

Candidate representation:

```yaml
constituency_priors:
  - key: ai_safety_global
    description: active AI-safety research and industry community
    approximate_scale: 10^4
    evidence_date: ...
    source/provenance: ...

  - key: example_game_active_players
    description: active players of a specific game
    approximate_scale: 10^3-10^4
    evidence_date: ...
    source/provenance: ...
```

Possible roles:

1. provide a scale prior to the LLM;
2. avoid repeatedly estimating stable populations;
3. allow provenance / refresh dates;
4. support later calibration against real telemetry.

Non-goals:

- do not enumerate every possible audience in advance;
- do not force every event into one taxonomy node;
- do not let lookup membership determine P directly;
- do not use user preference to choose the constituency.

Fallback:

> If no lookup entry exists, the LLM estimates the objective constituency directly from event semantics.

---

## 5. Observable attention evidence

The estimator should consume evidence about current collective attention rather than raw volume alone.

Candidate evidence families:

### 5.1 Direct attention evidence

- active searches;
- meaningful views / reads;
- dwell / completion signals;
- comments, replies, saves, shares;
- explicit discussion volume from distinct humans.

### 5.2 Structural penetration evidence

Useful when exact counts are unavailable:

- most major labs / firms / institutions in the relevant constituency have responded;
- major domain media are covering the event;
- dominant community channels have shifted discussion toward the event;
- multiple independent groups are allocating attention to it;
- domain conferences / forums are reorganizing discussion around it.

PC24 demonstrates that humans can infer high penetration from such structural evidence without exact audience counts.

### 5.3 Emergence evidence

- sharp increase relative to historical baseline;
- rapid search growth;
- simultaneous independent uptake;
- cross-platform expansion;
- multiple real-time reports / live coverage.

These are especially useful when total current attention is still modest but the event is clearly entering salience.

### 5.4 Weak / contaminated evidence

- paid impressions;
- forced/autoplay exposure with little engagement;
- duplicate bot activity;
- one-off synthetic trend manipulation;
- raw post counts without evidence of genuine human attention.

The estimator should distinguish these from genuine attention.

---

## 6. History and inertia

Because P is a state rather than a snapshot, the estimator should eventually consume event-level history.

Candidate history object:

```json
{
  "previous_p": "SALIENT",
  "previous_attention_summary": "high domain-wide discussion",
  "time_since_previous_measurement": "6h",
  "trend": "down ~30%, still far above normal",
  "time_since_last_clear_salience": "6h"
}
```

The semantic contract does not freeze a particular state equation.

Potential engineering approximations include:

### 6.1 Exponential memory

$$
A_t=\lambda A_{t-1}+(1-\lambda)\hat a_t
$$

### 6.2 Hysteresis

$$
\theta_{on}>\theta_{off}
$$

### 6.3 Direct LLM state judgment

The LLM receives current evidence plus recent history and directly judges whether salience is active, clearly emerging, or decayed.

For v1, direct semantic judgment may be preferable to premature numeric dynamics, provided diagnostics remain non-binding and the final scored label stays binary.

---

## 7. Candidate estimator v1 architecture

A minimal research estimator should separate inference stages conceptually without forcing a brittle mandatory pipeline.

```text
Sem(E)
  │
  ├─→ constituency prior / lookup (optional)
  │
  └─→ LLM constituency inference
           ↓
     G_E descriptor + coarse scale

Current external evidence
           ↓
    attention evidence summary

Recent event history (if available)
           ↓
        inertia context

        all together
           ↓
     P estimator v1
           ↓
SALIENT / NOT_SALIENT
+ explanatory diagnostics
```

Recommended principle:

> **The final estimator should judge P directly from the joint semantics/evidence/history, while constituency and attention diagnostics remain explanatory rather than hard gates.**

This mirrors the successful S estimator discipline: do not turn useful explanatory concepts into a brittle mandatory symbolic pipeline unless evidence requires it.

---

## 8. Candidate output schema

Only the final binary P label should be scored.

Candidate research output:

```json
{
  "collective_attention_salience": "SALIENT | NOT_SALIENT",
  "objective_constituency": "short description",
  "reference_scale": "coarse estimate / unknown",
  "attention_evidence": ["..."],
  "inertia_evidence": ["..."],
  "reason": "brief explanation"
}
```

Important:

- `objective_constituency` is diagnostic;
- `reference_scale` is diagnostic;
- `attention_evidence` is diagnostic;
- `inertia_evidence` is diagnostic;
- none is a mandatory intermediate gate unless future evidence justifies one;
- only `collective_attention_salience` is the semantic prediction.

---

## 9. Insufficient-evidence handling

The theoretical variable remains binary, but the estimator may sometimes lack enough current evidence to produce a defensible observation.

Do **not** create a third semantic P state merely because the estimator is uncertain.

Instead separate semantic label from measurement status:

```text
semantic target:       SALIENT / NOT_SALIENT
measurement status:    scorable / insufficient_evidence / technical_failure
```

On insufficient current evidence, the estimator should fail closed as a measurement rather than invent current attention.

This is especially important for new events where model training data cannot contain the current attention state.

---

## 10. Near-term evaluation strategy

The next measurement should test whether an estimator can implement the frozen semantic contract under controlled evidence descriptions before attempting noisy real-world collection.

Recommended sequence:

```text
1. Freeze estimator/profile v1
2. Create fresh P cases AFTER estimator freeze
3. Cases must include enough current attention evidence to make P observable
4. Human labels first
5. Freeze Human Gold
6. Run estimator exactly once
7. Attribute residuals
```

Fresh cases should attack at least:

- same absolute attention / different constituency scale;
- small legitimate constituency vs improperly narrowed denominator;
- high passive exposure vs lower genuine attention;
- stable high salience vs emerging salience;
- short-term decline vs sustained decay;
- specialist-domain salience vs mass-public salience;
- synthetic/bot activity;
- constituency-selection ambiguity.

Development cases PC1–PC24 must remain calibration evidence and must not be reused as fresh holdout evidence.

---

## 11. Real-world approximation path

After controlled estimator validation, real-world P will require an evidence-gathering layer.

Possible future evidence sources include:

- news/source-cluster breadth;
- search-trend signals;
- public social discussion where accessible;
- domain-specific feeds/forums;
- institution/actor follow-up;
- RAOS's own aggregate telemetry after deployment.

At large deployment scale, RAOS may gradually observe a meaningful portion of its own users' attention and improve estimates of both constituency and penetration.

However:

> **Better telemetry improves `P_hat`; it does not redefine P.**

---

## 12. Current decisions / open questions

Frozen from semantic work:

```text
P meaning                              FROZEN
G_E objective constituency concept    FROZEN
reference-scale normalization         FROZEN
real attention vs exposure            FROZEN
current OR emerging                   FROZEN
attention inertia                     FROZEN
```

Estimator-design decisions currently favored:

```text
LLM constituency inference            YES
coarse constituency lookup prior      YES / OPTIONAL FALLBACK
exact denominator requirement         NO
current evidence required for numerator YES
history/inertia context               YES WHEN AVAILABLE
direct binary final judgment          FAVORED
explanatory diagnostics               YES
mandatory symbolic sub-gates          NO
```

Still open:

```text
specific evidence collectors
lookup-table schema / refresh policy
whether v1 should estimate a numeric penetration diagnostic
how to summarize current evidence reproducibly
how to calibrate insufficient-evidence behavior
exact fresh-validation gate
```

---

## 13. Immediate next step

Before coding, decide the smallest reproducible evidence interface for estimator v1.

The core design question is now:

> **What evidence object can RAOS realistically provide to P estimator v1 such that the model can approximate current genuine attention without pretending to have platform-internal telemetry?**

Once that interface is frozen, implement the estimator without changing `22_COLLECTIVE_ATTENTION_SALIENCE.md`.
