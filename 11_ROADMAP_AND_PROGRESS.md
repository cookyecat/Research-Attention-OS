# Research Attention OS — Roadmap and Progress

Status: **ACTIVE PROJECT ROADMAP**  
Date: 2026-09-11
Current integrated baseline referenced: Phase 10D.4 production dogfood checkpoint (tag: `phase10d4-production-dogfood-v1`)
Semantic baseline: `08_COGNITIVE_TRANSITION_MODEL_V2.1.md` + Phase II-B AWARE semantics in `10_ATTENTION_POLICY_ELICITATION_AND_CALIBRATION.md`  
D semantic baseline: `16_STANDING_ATTENTION_JURISDICTION.md`  
D final validation: `17_STANDING_RADAR_FIT_V3_FINAL_VALIDATION.md`  
S semantic baseline: `19_MATERIAL_CONSEQUENCE_REFERENCE_SCALE.md`  
S final validation: `21_MATERIAL_CONSEQUENCE_V1_FINAL_VALIDATION.md`  
P semantic baseline: `22_COLLECTIVE_ATTENTION_SALIENCE.md`  
P estimator modeling: `23_COLLECTIVE_ATTENTION_ESTIMATOR_MODELING.md`  
Product/recommender boundary: `13_RAOS_VS_RECOMMENDATION_SYSTEMS.md`

> Purpose: preserve the long-horizon research position of RAOS so that individual experiments, implementation sessions, or conversation loss cannot erase what is closed, what is active, and what happens next.

---

## 1. North star

RAOS exists because external information volume has exceeded what a human can read, understand, and digest directly.

$$
\boxed{
Massive\ Information
\rightarrow
Minimal\ Human\ Attention
\rightarrow
Maximum\ Useful\ Cognitive\ Progress
}
$$

Canonical product definition:

> **RAOS estimates how new information changes the user's current cognition, then allocates bounded human attention accordingly.**

Long-term requirement:

> **Continuously keep that estimate aligned as the user's cognition changes.**

Directional objective:

$$
CROA = \frac{Useful\ Cognitive\ Change}{Human\ Attention\ Cost}
$$

CROA is directional, not a prematurely precise scalar objective.

Product contrast recorded in `13_RAOS_VS_RECOMMENDATION_SYSTEMS.md`:

> **Recommendation systems compete for attention; RAOS budgets attention.**

More rigorously, RAOS optimizes attention efficiency rather than assuming that more consumption / engagement is the desired outcome.

---

## 2. Constitutional loop

$$
(I_t,K_t)
\rightarrow
\Delta_t
\rightarrow
A_t
\rightarrow
HumanFeedback
\rightarrow
K_{t+1}
$$

Kernel mutation remains human-authorized:

$$
K_t\xrightarrow{accepted\ KernelPatch}K_{t+1}
$$

Core invariants:

- `CognitiveChange != AttentionAction`
- `Location != UpdateTarget`
- `Claim != Observation != Inference`
- AI may propose cognition change; it may not silently commit protected cognition
- WATCH transfers future attention responsibility to the system
- do not replace the system with one relevance score

---

## 3. Phase map

| Phase | Objective | Status |
|---|---|---|
| Phase I — Constitutional Vertical Slice | Information objects, cognitive transition, AttentionPlan, KernelPatch, provenance, human commit boundary | **CLOSED** |
| Phase II-A — Cognitive Transition Model | Reliable `Extract -> Locate -> Impact -> Delta`; freeze cognitive semantics | **FROZEN / CLOSED BASELINE** |
| Phase II-B — Attention Policy Calibration | Determine how frozen cognitive judgment plus legitimate non-cognitive signals allocate DROP/AWARE/WATCH/ENGAGE | **CLOSED / INTEGRATED BASELINE** |
| Phase 6 — Integrated Cognitive Attention Loop | Raw Source → Sensor/Auditor → D/S/P + Δ → four Attention Actions → human-gated Kernel proposal | **CLOSED** |
| Phase 7 — Perception Fidelity | External World Model fidelity, dynamic P evidence, minimal trusted Brain World Model | **CLOSED / WORKING BASELINE** |
| Phase 8 — Narrow Continuous Attention Loop | Narrow real ingest/cluster/route plus real WATCH re-check responsibility | **CLOSED / OPERATIONAL BASELINE ESTABLISHED** |
| Phase 9 — Longitudinal Cognitive Alignment | Keep Kernel and future decisions aligned as cognition changes | **9A PREREGISTERED / OUTCOME SAMPLING PAUSED FOR PARITY GATE** |
| Phase 10 — Distributional Cognitive Stability | Decision-causal core, static Cognitive Probability Map, temporal basin/regime analysis, real-web persistence | **10D.6E CLOSED / 10D.6F SUPPORT-BINDING NEXT** |
| Phase 11 — Personalization / Scale | Questionnaire prior + trajectory residuals + multi-user/product validation | **NOT STARTED** |

Current strategic position:

$$
\boxed{Phase\ 10D.4:\ Real\text{-}Web\ Basin\ Persistence\ COMPLETE}
$$

$$
\boxed{RAOS\ Distributional\ Cognitive\ Stability\ Theory\ V1.0\ FORMALIZED}
$$

Current research position: `Phase 10D.6E authority-band calibration closed → Phase 10D.6F support-binding/evidence-class authority next; Phase 9A remains preregistered and paused`. Phase 9A now tests whether explicit accepted Kernel changes produce directionally correct shifts beyond the fixed-K stochastic basin. The frozen `one-delta-v1` strategy remains preserved for historical replay and rollback.

D semantic research is closed. The v3 D estimator has attributable implementation residuals and is not certified as a passed estimator; do not expand D into another offline synthetic benchmark now.

S semantic research is closed. The frozen S estimator v1 passed its fresh first-run validation 12/12 with both class recalls at 1.0 and zero technical failures; further synthetic S benchmark work is stopped.

P semantic calibration is now closed/frozen. Current work is to approximate the frozen theoretical P variable from realistically available evidence without redefining the variable around present data limitations.

The project is still answering:

> **Can RAOS reason about attention reliably enough for genuine personal use?**

Do not move to broad continuous monitoring until this is good enough; do not over-polish offline policy once the phase exit condition is met.

---

## 4. Closed / frozen baselines

### 4.1 Cognitive Transition Model v2.1 — FROZEN

`08_COGNITIVE_TRANSITION_MODEL_V2.1.md` is the cognitive baseline.

$$
E_t=Extract(I_t)
$$

$$
L_t=Locate(E_t,K_t)
$$

$$
\Delta_t=F_\theta(E_t,K_t,L_t)
$$

$$
\Delta_t\in\{\varnothing,REINFORCE,CHALLENGE,OPEN\_NEW\}
$$

The transition model is not to be redesigned merely to improve Attention Policy results.

### 4.2 AttentionPlan semantics — CLOSED

AttentionPlan is allocation, not a second cognitive judgment.

A frozen AnalysisRun may yield different plans under different runtime contexts without changing $\Delta$.

### 4.3 Phase II evaluation protocol — FROZEN

$$
\boxed{
Formalize
\rightarrow
Calibrate\ instrument
\rightarrow
Freeze\ Gold
\rightarrow
Measure
\rightarrow
Attribute
\rightarrow
Improve
}
$$

Human Gold must be elicited before seeing the system prediction used as measurement.

### 4.4 Oracle-$\Delta$ policy baseline — RECORDED

After the targeted policy fixes:

```text
Exact Accuracy       0.5333333333
Mean Distance        0.5
False DROP           0.1333333333
Over-attention       0.1666666667
Under-attention      0.3
Critical Under       0
```

Key representational result:

$$
\boxed{\Delta=\varnothing
ot\Rightarrow DROP}
$$

### 4.5 Oracle-Awareness wiring / provenance — CLOSED

Baseline commit:

```text
354d2b5011a868f0295e2ac2750822275c83db51
```

Synthetic truth-table results and Human-elicited results remain provenance-separated. Synthetic 8/8 is a wiring test, not Human Gold generalization evidence.

Production does not yet estimate the real-world awareness signals.

---

## 5. Phase II-B AWARE semantic baseline — FROZEN FOR MEASUREMENT

Scope:

$$
\Delta_t=\varnothing
$$

AWARE means:

$$
\boxed{AWARE=Situational\ Awareness\ without\ Cognitive\ Commitment}
$$

No Kernel write. No continuing WATCH obligation. Low-cost human awareness only.

Current candidate no-$\Delta$ gate:

$$
\boxed{AWARE\iff S\land(D\lor P)}
$$

where:

$$
\boxed{D=D(E,u)=\mathbf 1[E\in\mathcal J_u]}
$$

$$
\boxed{S=Material\ consequence\ of\ the\ underlying\ event,\ independent\ of\ user\ interest\ and\ collective\ attention}
$$

$$
\boxed{P=P(E,t)=Collective\ Attention\ Salience}
$$

Human-language P contract:

> **P judges whether, at the current time, an event has already formed, or is clearly forming, a salient state of genuine collective attention within the event's objective attention constituency. Attention is interpreted relative to the scale of that constituency and has temporal inertia.**

Objective Attention Constituency:

$$
\boxed{\mathcal G_E=Constituency(Sem(E))}
$$

with the anti-gaming rule that `G_E` is selected from event semantics independently of observed attention and independently of user preference.

The three variables use different reference frames:

$$
\boxed{
D:\ user
\qquad
S:\ consequential\ shared\ systems
\qquad
P:\ objective\ attention\ constituency
}
$$

Physical interpretation:

- `D` = standing personal-attention field / jurisdiction;
- `S` = material shared-world-state disturbance;
- `P` = collective-attention-state salience.

Important invariants:

- `D != S`
- `S != P`
- `D != P`
- incidental mention/use of a radar technology does not create D membership
- technical novelty is not S
- artifact quality is not S
- raw population/reach is not S
- raw attention volume is not P
- total-population normalization is not P
- exposure / autoplay views / bot activity are not automatically genuine attention
- public sentiment / stance are not P
- P may be salient inside a professional, geographic, niche, or genuinely event-internal constituency without broad social salience

---

## 6. D study — SEMANTICS CLOSED / ESTIMATOR RESIDUALS PRESERVED

### 6.1 Canonical D definition

`16_STANDING_ATTENTION_JURISDICTION.md` is the frozen D semantic baseline.

$$
\boxed{
\mathcal J_u
=
\{E\mid\exists\rho_i\in\mathcal R_u,\rho_i(Sem(E),u)=1\}
}
$$

$$
\boxed{D(E,u)=\mathbf 1[E\in\mathcal J_u]}
$$

Standing Radar Clauses are applicability conditions, not domain weights. Clauses may concern a substantive topic, actor/entity/person, work/content object, place/governance scope, or stable affiliation. These semantic forms do not justify separate D sub-variables or a typed ontology.

Exclusions remain:

$$
\boxed{Exclusion=ScopeGuard,\quad Exclusion
eq Veto}
$$

### 6.2 Historical v1 measurement

First blind holdout:

```text
ExactAccuracy       0.90
BalancedAccuracy    0.9333333333333333
IN recall           0.8666666666666667
OUT recall          1.0
False-IN            0
False-OUT           FD6, FD16
Technical failures  0
```

This supported compact natural-language Standing Radar representation and argued against building a giant domain ontology.

### 6.3 Intersection diagnostic

The v1 intersection diagnostic failed its pre-registered criterion at 6/8 and exposed semantic-composition/scope problems. That evidence led to the substantive-facet, scope-guard, and later Standing-Attention-Jurisdiction formalization. Historical results remain preserved and must not be rewritten as fresh evidence.

### 6.4 Final v3 fresh measurement

Artifact:

`eval/live/results/standing_radar_fit_v3_final_fresh_first_run.json`

Result commit:

```text
07ae4b3
```

Observed:

```text
Exact accuracy       0.70
IN recall            0.50
OUT recall           0.8333333333
Balanced accuracy    0.6666666667
False-IN             FJ2
False-OUT            FJ4, FJ6
Technical failures   0
```

The v3 estimator **failed the pre-registered final-validation gate** and is not certified as a passed estimator.

Residual attribution is recorded in `17_STANDING_RADAR_FIT_V3_FINAL_VALIDATION.md`:

- FJ2 is internally consistent with the frozen AI-Agent clause and is treated as a human-policy boundary / possible noisy-label residual rather than evidence for changing D semantics.
- FJ4 is a real clause-application failure: the model recognized OpenAI as a substantive actor but imposed an extra significance/topic-development condition not present in the clause.
- FJ6 is a real stable-affiliation extraction/application failure despite an explicit direct-family clause.

The formal model is more general than the diagnostic `substantive anchor -> clause match` implementation view. Future integrated implementation may evaluate clauses more directly over `Sem(E),u`.

Research decision:

```text
D semantic definition                  CLOSED / FROZEN
D clause representation                SUPPORTED
D v3 estimator                         NOT CERTIFIED
Known estimator residuals              ATTRIBUTABLE
Further synthetic D benchmark work     STOP
```

Do not introduce domain weights or a large ontology from this result. Revisit implementation only if integrated dogfooding exposes a repeated real-world failure pattern.

---

## 7. S study — CLOSED / ESTIMATOR v1 ACCEPTED

### 7.1 Canonical S definition

`19_MATERIAL_CONSEQUENCE_REFERENCE_SCALE.md` is the frozen S semantic baseline.

$$
\boxed{
S(E)=1
\iff
\exists G,\tau:\ MaterialDisturbance_G(E,\tau)=1
}
$$

Human-language contract:

> **S asks whether the underlying event creates a material disturbance to at least one consequential shared/public reference system—national, social, industry/field, market, scientific/technical, or cultural—rather than merely creating a large relative change inside a small bounded local/private unit.**

Key invariants include:

```text
ActorProminence != S
TechnicalNovelty != S
ArtifactQuality != S
PopulationCount != S
LargePrivateGain != S
LocalSeverity != S
ObservedMediaCoverage != S
```

### 7.2 Frozen estimator and fresh validation

Estimator freeze commit:

```text
99b8c96e54102c3befd04d931156645a5b77d8e1
```

Fresh template commit:

```text
51f983d0a2aeaa2a5eb730fa913657b0e127925b
```

Fresh Human Gold commit:

```text
cbd41ca62c0b3ed5d0fdba07fd77515d63e48c8a
```

First-run artifact:

`eval/live/results/material_consequence_v1_final_fresh_first_run.json`

Measurement code HEAD:

```text
10e40a934759000100aa98629bba09a0f912823e
```

Result commit:

```text
7ae0fd07b11f1fad5e2f6b155e9cba1a1eba6b76
```

Actual model:

```text
deepseek-v4-flash
thinking = disabled
temperature = 0.1
```

Fresh first-run result:

```text
n_scored                    12
Gold MATERIAL               6
Gold NOT_MATERIAL           6
Pred MATERIAL               6
Pred NOT_MATERIAL           6
Exact accuracy              1.0
MATERIAL recall             1.0
NOT_MATERIAL recall         1.0
Balanced accuracy           1.0
Technical failures          0
Transport retries           0
Repeated semantic failure   none
```

This passes every pre-registered gate.

Research decision:

```text
S semantic definition                  CLOSED / FROZEN
S estimator v1                         ACCEPTED FOR PHASE II-B
Fresh validation                       PASS — 12/12
Known semantic residuals               NONE ON FRESH SET
Further synthetic S benchmark work     STOP
```

The 12/12 result is evidence that the frozen semantic contract was cleanly implemented on a fresh controlled holdout; it is not a claim of 100% open-world accuracy.

---

## 8. P study — SEMANTICS CLOSED / ESTIMATOR MODELING ACTIVE

### 8.1 Canonical P definition

`22_COLLECTIVE_ATTENTION_SALIENCE.md` is the frozen P semantic baseline.

$$
\boxed{
\mathcal G_E=Constituency(Sem(E))
}
$$

Conceptual reference-normalized attention penetration:

$$
\boxed{
R_E(t)=\frac{1}{|\mathcal G_E|}\sum_{i\in\mathcal G_E}a_i(E,t)
}
$$

Latent attention state:

$$
\boxed{
P(E,t)=LatentSalience(R_E(\le t))
}
$$

This conceptual equation is a theoretical model, not a requirement for exact direct measurement.

Frozen principles:

```text
Objective Attention Constituency       selected from Sem(E), not user preference
Reference-scale normalization          YES
Raw absolute volume                    NOT P
Exposure / synthetic activity          NOT automatically attention
Current OR emerging salience            YES
Temporal inertia                        YES
General-public-only interpretation      REJECTED
Sentiment / stance                      NOT P
```

Two Human calibration rounds PC1–PC24 established the core boundaries. These are development/calibration evidence and must never be reused as fresh P holdout evidence.

### 8.2 Theory / engineering separation

The frozen theoretical target is:

$$
\boxed{
Theory:\quad P(E,t)=LatentSalience(R_E(\le t))
}
$$

The current engineering approximation target is:

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

Estimator modeling is recorded in `23_COLLECTIVE_ATTENTION_ESTIMATOR_MODELING.md`.

Important engineering distinction:

- LLM prior knowledge is useful for constituency identity and coarse reference scale;
- current attention numerator is time-dependent and requires current observable evidence;
- a small lookup/prior table may cache stable constituency-scale knowledge;
- exact denominator counts are not required;
- diagnostics should not become mandatory symbolic gates without evidence;
- insufficient current evidence is a measurement-status problem, not a third semantic P state.

Current research decision:

```text
P semantic definition                  CLOSED / FROZEN
Objective Attention Constituency       CLOSED / FROZEN CONCEPT
Reference-scale normalization          CLOSED / FROZEN PRINCIPLE
Temporal inertia                       CLOSED / FROZEN PRINCIPLE
P estimator architecture               ACTIVE MODELING
Fresh P Human Gold                     NOT CREATED
First scored P measurement             NOT RUN
```

---

## 9. Immediate next steps

Execute in this order:

```text
Phase 7A — External World Model Fidelity
  ↓
Measure whether Sensor/Auditor representation preserves downstream decision-sufficient meaning
  ↓
Attribute causal representation failures before tuning Sensor
  ↓
Phase 7B — Dynamic P evidence interface using controlled/simulated time-varying evidence first
  ↓
Phase 7C — Minimal Trusted Brain World Model with explicit value/source/authority boundaries
  ↓
Phase 8 — Narrow Continuous Attention Loop / real WATCH re-check dogfooding
```

Do not wait for perception perfection. Move to Phase 8 once remaining errors are bounded, observable, and attributable.

## 10. Phase II-B exit condition

Phase II-B is complete when Attention Policy is reliable enough for real personal dogfooding, not when every synthetic benchmark reaches 100%.

Required qualitative properties:

- clear cognitive change is not silently dropped;
- no-cognitive-change AWARE has a defensible, measurable basis;
- D/S/P can be estimated sufficiently well from real information;
- WATCH remains a real future-attention obligation rather than a label;
- runtime may alter allocation without rewriting frozen cognition;
- residual policy errors are attributable rather than mysterious.

Then move to Phase III.

---

## 11. Phase III — Continuous Attention OS

Next major product step:

```text
discover
  -> ingest
  -> deduplicate
  -> cluster events
  -> extract / locate / impact
  -> allocate attention
  -> create / update WATCH
  -> re-check future evidence
  -> surface only when policy conditions are met
```

Key principle:

> **WATCH means RAOS has accepted future attention responsibility.**

Start with a narrow measurable real-source loop, not a giant crawler or recommendation feed.

---

## 12. Phase IV — Longitudinal Cognitive Alignment

Once continuous information flow exists:

$$
K_t\rightarrow K_{t+1}\rightarrow K_{t+2}\rightarrow\cdots
$$

Test whether accepted Kernel changes correctly alter future Locate/Impact/Attention decisions, whether WATCH obligations become stale, and whether standing preference remains distinct from temporary project context.

---

## 13. Phase V — Personalization

Only after real trajectories exist should personalization move beyond initial calibration.

Candidate architecture:

$$
\boxed{
AttentionPolicy_u
=
SharedPolicyPrior
+
QuestionnaireCalibration_u
+
TrajectoryResidual_u
}
$$

Do not train personal policy from noisy click behavior before the controlled variables and causal semantics are understood.

---

## 14. Working discipline

For every open research question:

$$
\boxed{
Formalize
\rightarrow
Calibrate\ instrument
\rightarrow
Freeze\ Gold
\rightarrow
Measure
\rightarrow
Attribute
\rightarrow
Improve
}
$$

Rules:

1. Do not optimize a black box.
2. Do not add ontology because one boundary case is awkward.
3. Do not convert development cases into holdout evidence after discussing their labels.
4. Do not let Attention Policy manufacture cognitive change.
5. Prefer residual evidence over a cosmetically perfect score.
6. When a phase exit condition is met, move forward rather than overfitting the current benchmark.
7. Do not redefine a frozen theoretical variable merely because the current system cannot observe it directly.

---

## 15. Perception-before-decision discipline

Phase 6 integration exposed a useful system-level framing: RAOS depends on both an External World Model and a Brain / Cognitive World Model. See `68_RAOS_DUAL_WORLD_MODEL_AND_PERCEPTION_DISCIPLINE.md`.

Add these permanent debugging rules:

1. **不能因为传感器差，就修改物理定律。**
2. **在质疑决策之前，先检查系统看到的是不是同一个世界。**
3. Attribute end-to-end failures from the earliest causal layer before changing downstream policy.
4. Treat memorable language that faithfully compresses a hard-won insight as research memory, not decoration.

Operational implication:

```text
Raw source → Sensor → Auditor → represented world → Delta / D/S/P → Attention Policy
```

A surprising final action is not, by itself, evidence that the policy or Delta semantics are wrong.
---

## 15. Phase 6B integrated cognitive-attention status — 2026-09-08

The raw-source cognitive path is now connected through audited semantics, Kernel localization, frozen Delta, and the production Attention Policy.

Same-SHA development runs repeatedly exercised:

```text
NONE → AWARE
NONE → DROP
REINFORCE → WATCH
CHALLENGE → ENGAGE
```

All four attention actions were reached without automatic Kernel mutation.

`OPEN_NEW` was not forced merely because no legal update target existed; this preserves the frozen rule that OPEN_NEW is a genuine new cognitive branch, not a fallback.

Current next step:

```text
Phase 6C
Human Feedback / Kernel authorization boundary
```
## Phase 6C — Human authorization boundary and Brain/Runtime authority

Status: CLOSED / canonical development result.

Validated:

```text
CHALLENGE → ENGAGE → KERNEL_PATCH proposal
PROPOSED → no Kernel mutation
REJECT → no Kernel mutation
ACCEPT/MODIFY → KernelVersion committed_by USER
protected direct AI write → blocked
```

Integration also found and fixed a Brain World Model authority bug: LLM-inferred `threatens_active_work` could previously trigger PREEMPT without trusted runtime evidence.

New engineering rule:

> **A model inference about the user is not automatically an authoritative user/runtime state.**

Phase 6B weak-Δ boundary jitter is recorded as a probabilistic calibration residual and does not reopen frozen Δ semantics.
---

## Phase 7A — External World Model Fidelity

Status: **SUFFICIENT / WORKING BASELINE SELECTED**

Selected Sensor baseline:

```text
semantic-evidence-extractor-v0.2.6
predicate-explicit context-bearing
```

Key formulation:

> **Decision-Sufficient Semantic Precision = Evidence Fidelity + Scope Fidelity + Relational Fidelity.**

Phase 7A found and attributed real world-model losses, demonstrated an overfitting failure in v0.2.4, and selected v0.2.6 only after heterogeneous downstream-causal regression.

Current execution frontier:

```text
Phase 7B — Dynamic P / simulated collective-attention evidence
```
## Phase 7B dynamic P — CLOSED 2026-09-08

Dynamic P simulation is now sufficient for Phase 7. Same-SHA repeated runs preserved the expected time-varying P state and final DROP/AWARE action at all 30 measured time points.

Key validated behaviors:

```text
formation / establishment / inertia / sustained decay / rebound
paid exposure != genuine attention
synthetic trend volume != genuine attention
organic attention can enter SALIENT and drive AWARE
```

Current work moves to **Phase 7C — Minimal Trusted Brain World Model**. Do not reopen P semantics or extend synthetic P benchmarking absent a repeated attributable failure.
## Phase 7C minimal trusted Brain World Model — CLOSED 2026-09-08

`brain-world-model-v0.1` is sufficient to move forward. Production AttentionPlan decisions now record an auditable Brain snapshot with trusted runtime facts, Kernel identity, active WATCH obligations, authority, provenance, and freshness.

Controlled authority probes passed 4/4 and relevant exact-SHA regression passed 131 tests.

Current phase is now **Phase 8 — Narrow Continuous Attention Loop**.

Do not expand Brain World Model inference breadth before live dogfooding reveals repeated attributable gaps. Likewise, probabilistic Decision Fidelity / uncertainty calibration remains a later Phase 10 research track; Phase 8 should run with the current 7A/7B/7C working models first.
## Phase 8A WATCH responsibility loop — CLOSED 2026-09-08

WATCH now has a cumulative responsibility loop with auditable `WatchCheck` history. Existing WATCH obligations re-evaluate prior plus new evidence, remain ACTIVE when evidence is still insufficient, and become PROMOTED when AWARE/ENGAGE is reached. Rechecks do not create duplicate Watch obligations.

Current work moves to **Phase 8B — Narrow Continuous Ingestion / Dogfooding**.
## Phase 8B continuous source arrival — CLOSED 2026-09-09

Continuous source arrival now distinguishes article novelty from evidence novelty before spending additional WATCH analysis budget.

Research memory:

> **The system's input unit is an article, but its cognitive unit is not an article.**

> **Article count is not evidence count.**

Current work moves to **Phase 8C — Narrow Real Dogfood Loop** using a small auditable source inbox/feed. Broad crawling and open-world semantic clustering remain deferred until repeated real failures justify them.
## Phase 8C.1 real-web acquisition — CLOSED 2026-09-09

A narrow real public-web dogfood sequence has now exercised URL fetch, readable-text extraction, Source persistence, supervised event relations, continuous arrival routing, WATCH recheck, and promotion.

Current integration gap: production `run_pipeline()` still uses legacy provider extraction rather than the Phase 7A v0.2.6 Semantic Sensor working baseline.

Current work therefore moves to **Phase 8C.2 — Production Sensor Bridge** before broader dogfooding.
## Phase 8C.2 production Sensor bridge — ACTIVE / PREREGISTERED 2026-09-09

Production now has a narrow injectable `ExtractionResult` bridge seam while the default path remains legacy. `backend/app` does not import the research Sensor implementation.

Candidate composition reuses validated interfaces rather than inventing new semantics:

```text
event_frames     -> Phase 6A audited event projection
non_event_units  -> Phase 6B audited epistemic-unit admission
both             -> existing production ExtractionResult
```

The bridge execution fingerprint enters `AnalysisRun` execution identity so legacy and candidate arms cannot collide in cache.
Controlled A/B is preregistered on RS05 / RS15 / RS11 / RS12. Each pair uses the same Source UUID, Kernel UUIDs, relational context, and initial persistence state; A and B execute inside rollback SAVEPOINTs.

Established decision-bearing sentinels remain:

```text
RS05 -> CHALLENGE(CF-B-PERF) -> ENGAGE
RS15 -> REINFORCE(Q2)
RS11 -> NONE / DROP control
RS12 -> weak-positive boundary control; require repeated bridge-driven divergence before attribution
```

No live Phase 8C.2 result has yet been used to tune Sensor, Auditor, Delta, or Attention Policy. Current next step is exact-SHA live controlled A/B followed by regression and default-path decision.

### Phase 8C.2 live bridge evidence — 2026-09-09

Tier-1 exact-SHA production A/B passed the canonical decision-bearing sentinels: RS05 preserved `CHALLENGE(CF-B-PERF) -> ENGAGE`, RS15 preserved `REINFORCE(Q2) -> WATCH`, and RS11 preserved `NONE -> DROP`. RS12 reproduced the previously observed weak boundary jitter without stable directional bridge regression. Relevant regression passed 64 tests with the pre-existing Case K residual explicitly excluded.

Tier-2 re-acquired the exact Phase 8C.1 A/C/D/X pages. All four matched their Phase 8C.1 production-normalized `content_hash` and extracted character count, and legacy replay again reproduced `C SECONDARY -> KEEP_ACTIVE`, `X unrelated -> ordinary analysis`, and `D INDEPENDENT -> PROMOTED`.

The first Sensor continuity run failed 3/3 before Auditor/downstream on Azure A with the same schema-validation failure. Attribution found a production packaging defect: URLConnector emitted meaningful newline-separated blocks, but the bridge's blank-line renderer collapsed the full 6614-character page into one `[PARA 0001]`, causing overlong provenance excerpts. The failure is attributed to source-packaging geometry, not Sensor/Auditor/Delta/WATCH semantics.

Current remediation is `production-source-to-semantic-sensor-v0.3-url-provenance-blocks`: URL sources preserve non-empty connector blocks as stable provenance units and split only oversized blocks at sentence boundaries (word-boundary fallback). Sensor v0.2.6, Auditor v0.1.1, schema limits, Delta, D/S/P, WATCH, and Attention remain frozen. Production default remains legacy until the repaired exact-SHA Tier-2 continuity run and regression pass.


Post-gate Tier-2 diagnostic found one remaining bridge-fidelity residual on initial real-web source A: legacy `AWARE / SUMMARY` vs Sensor `DROP / NONE`. Both had no Kernel match. Attribution showed the legacy `ExtractionResult` contained a decision-active `technical_claims` separation that can support OPEN_NEW, while the audited-units adapter reconstructed only claim/observation/inference and left production separation fields empty.

The remediation is bridge-only and Auditor-preserving: production claim type and separation fields are reconstructed exclusively from Auditor-admitted claim statements using the existing production classifier. Raw unaudited source text is excluded. This restores `ClaimType`, `current_facts`, `future_plans`, `technical_claims`, `promotional_framing`, `marketing_heavy`, and derived `evidence_maturity` without changing Sensor v0.2.6, Auditor v0.1.1, Delta, D/S/P, WATCH, or Attention semantics. The bridge execution version is bumped before new measurement.


### Phase 8C.2 decision-stability attribution — 2026-09-09

Bridge v0.2 restored production decision-active extraction separations from Auditor-admitted claims only, and the final A/C/D/X Tier-2 real-world continuity rerun passed all structural and cognitive diagnostics.

A subsequent Tier-1 RS15 rerun exposed a deeper production-readiness residual. Controlled attribution is archived in `81_PHASE8C2_DECISION_STABILITY_ATTRIBUTION_RESULT.md`.

Current evidence separates three regimes:

```text
RS11 — robust basin
  fresh current Sensor/Auditor/downstream -> NONE / DROP 6/6

RS05 — upstream representation instability
  frozen Phase7A audited semantics -> canonical CHALLENGE / ENGAGE 6/6
  fresh current path              -> canonical 3/6, DROP 3/6

RS15 — compound boundary amplification
  same exact semantic input -> Q2 3/6, B2 3/6
  fresh Sensor/Auditor realizations add further Q2/B2/OPEN_NEW variation
```

The critical RS15 Q2 relation remains present after Auditor admission. Event projection is not a deterministic root cause, and a one-pair Pro/Flash probe does not support a simple stronger-model explanation.

Working causal summary:

$$
\boxed{\text{Representation Variance}\times\text{Decision Sensitivity}\rightarrow\text{Landing Instability}}
$$

This is a production stability/readiness finding, not evidence to replace the Phase 7A working formulation:

$$
\boxed{\text{Decision-Sufficient Semantic Precision}=\text{Evidence Fidelity}+\text{Scope Fidelity}+\text{Relational Fidelity}}
$$

Phase 8C.2 therefore remains ACTIVE and production default remains legacy. RS15 full-path Attention remained WATCH 6/6 despite cognitive-target jitter; the more product-critical residual is RS05 crossing DROP/ENGAGE 3/6 vs 3/6 while its frozen Phase7A semantics remain ENGAGE 6/6. Immediate next research gate: broaden repeated decision-stability / representation-robustness measurement across multiple canonical decision-bearing and negative-control cases before any Sensor-path promotion, reporting cognitive-target stability separately from Attention-action stability. Probabilistic redesign of Delta/Attention remains deferred to Phase 10 unless broader evidence proves it necessary.

## Phase 8C.3 native canonical Multi-Delta probe — EXPERIMENTALLY COMPLETE 2026-09-09

Five-step measurement sequence is archived in `82_PHASE8C3_NATIVE_CANONICAL_MULTI_DELTA_EXPERIMENT_LOG.md`; consolidated result is `83_PHASE8C3_NATIVE_CANONICAL_MULTI_DELTA_RESULT.md`.

Measured sequence:
`temperature A/B -> native canonical interface -> Multi-Delta -> per-channel Attention -> article Attention aggregation`.

Key measured facts: native canonical RS15 preserved Q2 and B2 simultaneously 3/3, removing forced single-target competition at the effect-set level. RS05 preserved its core CHALLENGE 3/3. Weak incidental RS11/RS12 effects were removed by the frozen materiality gate. However, RS15 effect magnitude remained variable enough that article Attention was `DROP 2/3, ENGAGE 1/3`; Multi-Delta alone is therefore not a complete stability solution.

No threshold was tuned after outcomes. No production default was changed. Phase 7A Decision-Sufficient Semantic Precision remains the working semantic formulation.

## Phase 8C.4 decision-strategy plug-in architecture — IMPLEMENTED 2026-09-10

Architecture record: `84_PHASE8C4_DECISION_STRATEGY_PLUGIN_ARCHITECTURE.md`.

The decision algorithm is now an explicit injectable/versioned strategy seam. Production default remains `one-delta-v1`; historical runs without a strategy fingerprint resolve to that baseline. Strategy identity enters AnalysisRun execution identity and score_debug, so future one-Delta / Multi-Delta / Pareto experiments can change one decision algorithm at a time without rewriting scheduler control flow or colliding in cache.

This change does not solve calibration by itself. `change_magnitude` remains a raw LLM estimate even after full production grounding; target importance and epistemic strength receive deterministic grounding/caps. Next research step: implement a Pareto/partial-order candidate behind the new seam, leaving `one-delta-v1` untouched for A/B recovery.

## Phase 8C.5 Pareto / partial-order decision strategy — EXPERIMENTALLY COMPLETE 2026-09-10

Preregistration: `85_PHASE8C5_PARETO_DECISION_STRATEGY_PREREGISTRATION.md`. Result: `86_PHASE8C5_PARETO_DECISION_STRATEGY_RESULT.md`.

`pareto-multidelta-v0.1` is now an experimental Decision Strategy chip. A frozen 12-run A/B against `one-delta-v1` used the Phase 8C.3 native canonical CognitiveEffect artifact and made no LLM calls.

Article-level Attention was unchanged in all 12 runs. Pareto materially changed decision geometry, preserving simultaneous RS15 channels on the Attention frontier instead of collapsing immediately to one primary winner, but it did not remove RS15 AWARE/ENGAGE variation because the frozen raw `change_magnitude` values still crossed Attention bands.

Conclusion: Pareto addresses lossy single-winner compression, not pseudo-cardinal calibration. Production default remains `one-delta-v1`; Pareto v0.1 is frozen as an experimental baseline. Next gate: a calibration/margin strategy chip, tested independently before any further Pareto tuning.

## Phase 8C.6 magnitude-free calibration — EXPERIMENTALLY COMPLETE 2026-09-10

Design: `87_PHASE8C6_MAGNITUDE_FREE_CALIBRATION_DESIGN.md`; result: `88_PHASE8C6_MAGNITUDE_FREE_CALIBRATION_RESULT.md`.

`magnitude-free-v0.1` removes raw LLM `change_magnitude` from Pareto dominance, per-channel Attention, article aggregation and compatibility representative selection. Controlled magnitude perturbation was decision/frontier invariant 12/12 while raw-cardinal decisions changed 12/12. Frozen real-realization A/B: RS05 `ENGAGE 3/3`, RS15 stabilized to `WATCH 3/3`, RS11 `AWARE 3/3`; RS12 moved to `WATCH 3/3` and remains the calibration boundary case. Production default remains `one-delta-v1`.


## Phase 8C.7 real-web magnitude-free validation — EXPERIMENTALLY COMPLETE 2026-09-10

Preregistration: `89_PHASE8C7_REAL_WEB_MAGNITUDE_FREE_VALIDATION_PREREGISTRATION.md`; result: `90_PHASE8C7_REAL_WEB_MAGNITUDE_FREE_VALIDATION_RESULT.md`.

The four exact Phase 8C.1 public-web URLs were reacquired through the production URLConnector and passed the frozen production-normalized content-hash and character-count gate 4/4 before model calls. Fresh native processing used `Sensor v0.2.6 -> Auditor v0.1.1 -> canonical admitted units -> native Locate -> native multi-effect cognition`, without the legacy bridge as the cognitive interface.

Natural fresh decisions were A=`AWARE`, C=`DROP`, D=`DROP`, X=`AWARE` under both raw-cardinal and magnitude-free calibration. The important robustness result came from deterministic perturbation of the frozen real-web CognitiveEffects: on the two non-empty topologies (A and X), changing only raw `change_magnitude` moved Raw Cardinal from `AWARE` to `ENGAGE`, while Magnitude-Free remained `AWARE` for all four variants. Empty-topology controls C/D remained `DROP`.

Conclusion: the pseudo-cardinal magnitude failure mode generalizes to real-web sources. With Semantic Topology frozen, raw magnitude alone can create an artificial Attention boundary; Magnitude-Free removes that authority. This does not solve Semantic Topology variance itself. Production default remains `one-delta-v1`; next research target is Semantic Topology stability / preservation of decision-bearing relations rather than further continuous magnitude tuning. Full backend regression after this measurement was 576 passed / 63 skipped with only the pre-existing Case K PREEMPT-vs-PRIORITY residual failing.


## Phase 8C.8 Semantic Topology stability attribution — EXPERIMENTALLY COMPLETE 2026-09-10

Preregistration: `91_PHASE8C8_SEMANTIC_TOPOLOGY_STABILITY_PREREGISTRATION.md`; result: `92_PHASE8C8_SEMANTIC_TOPOLOGY_STABILITY_RESULT.md`.

Frozen-audited-world attribution separated Locate from Cognitive Impact. RS05 critical CHALLENGE and RS15 Q2/B2 relations remained 6/6, and Magnitude-Free Attention was stable for RS05/RS15/RS11/RS12/A/C/X despite peripheral topology variance. D was the only product-level failure: with modal Locate frozen empty, Cognitive Impact spontaneously emitted five OPEN_NEW effects in 1/6 and moved DROP→ENGAGE.

Current next target is therefore OPEN_NEW jurisdiction/materiality admission inside Cognitive Impact, not Auditor/Sensor variance. Production default remains `one-delta-v1`.


## Phase 8C.9 anchored OPEN_NEW admission — EXPERIMENTALLY COMPLETE 2026-09-10

Preregistration: `93_PHASE8C9_ANCHORED_OPEN_NEW_ADMISSION_PREREGISTRATION.md`; result: `94_PHASE8C9_ANCHORED_OPEN_NEW_ADMISSION_RESULT.md`.

`anchored-open-new-v0.1` adds a deterministic Effect Admission slot to the Pareto experimental stack. Frozen replay of all Phase 8C.8 Impact outputs removed the sole D free-floating OPEN_NEW `DROP→ENGAGE` failure (`DROP 5/6 + ENGAGE 1/6` -> `DROP 6/6`) while leaving article Attention unchanged for RS05/RS15/RS11/RS12/A/C/X. RS05 anchored OPEN_NEW candidates and the critical CHALLENGE remain preserved.

The structural working invariant is `OPEN_NEW may have target=null, but should not have jurisdiction=null`. Full backend regression: 581 passed, 63 skipped, only the pre-existing Case K urgency residual failed. Production default remains `one-delta-v1`.


## Phase 8C.10 Auditor topology stability — GATE 2A COMPLETE 2026-09-10

Measurement foundation: `95_SEMANTIC_TOPOLOGY_STABILITY_METRICS.md`. Preregistration: `96_PHASE8C10_AUDITOR_TOPOLOGY_STABILITY_PREREGISTRATION.md`; Gate 2A result: `97_PHASE8C10_AUDITOR_TOPOLOGY_STABILITY_GATE2A_RESULT.md`.

With Phase 7A Sensor candidate units frozen, fresh Auditor v0.1.1 repeats show narrow admitted-set jitter: RS05 and RS11 each have one single-unit minority variant, while RS15 and RS12 are fresh-repeat invariant 4/4. However the current modal admitted worlds differ from the historical Phase 7A audit for RS05, RS15 and RS12, separating within-run stochastic variance from historical admission-boundary drift.

Gate 2B is now required: propagate only distinct changed admitted worlds through the frozen experimental downstream (`Anchored OPEN_NEW + Magnitude-Free + Pareto`) and compare critical Cognitive Topology / Article Attention against the Phase 8C.8 historical audited-world baseline. Production default remains `one-delta-v1`.

### Phase 8C.10 Gate 2B — downstream propagation COMPLETE 2026-09-10

Gate 2B propagated only changed Auditor admitted worlds through the frozen experimental decision stack. RS05 Auditor variance was absorbed: critical `CHALLENGE(CF-B-PERF)` and `ENGAGE` remained stable. RS15's stable +NEU4 admission preserved Q2/B2 but added decision-bearing CHALLENGE relations and moved `WATCH -> ENGAGE 4/4`. RS11's one-repeat +N1 admission moved historical `AWARE -> ENGAGE 4/4`. RS12's stable +N11 admission moved historical `WATCH` to `ENGAGE 3/4, WATCH 1/4`.

Therefore admitted-set similarity alone is insufficient: a single boundary unit can be decision-causal. However historical disagreement is not equivalent to Auditor error; packet inspection suggests RS15 NEU4 may be an earlier false negative, RS11 N1 is a stronger current false-positive candidate, and RS12 N11 remains genuinely boundary-like. Next gate is paired same-SHA boundary-unit ablation before any Auditor redesign.


## Phase 8C.11 boundary-unit causal ablation — EXPERIMENTALLY COMPLETE 2026-09-10

Preregistration: `100_PHASE8C11_AUDITOR_BOUNDARY_UNIT_ABLATION_PREREGISTRATION.md`; result: `101_PHASE8C11_AUDITOR_BOUNDARY_UNIT_ABLATION_RESULT.md`.

Same-SHA paired ablation did not support the simple hypothesis that newly admitted Auditor boundary units were necessary causes of the Gate 2B Attention shifts. RS05 remained `ENGAGE 6/6` with or without U06/U08; RS15 remained in the current ENGAGE basin after removing NEU4 (`full ENGAGE 5/6 + WATCH 1/6`, `-NEU4 ENGAGE 6/6`); RS11 remained `ENGAGE 6/6` after removing N1; RS12 remained `WATCH 6/6` after removing N11.

The next attributable target is therefore longitudinal Cognitive Mapping stability under frozen audited semantics, not Auditor retuning. Production default remains `one-delta-v1`.


## Distributional Cognitive Stability construction plan — 2026-09-10

Formal construction plan: `102_DISTRIBUTIONAL_COGNITIVE_STABILITY_RESEARCH_PLAN.md`.

The stability program now separates descriptive topology similarity from policy-relative causal structure. `topology-stability-metrics-v0.1` remains the descriptive measurement chip; the next planned chips are deterministic Decision-Causal Core, a static empirical Probabilistic Cognitive Map, and only if evidence requires it a temporal distribution-drift / stochastic-process layer.

Immediate next gate is Phase 8C.12: under exact frozen audited semantics, separate longitudinal Locate drift from Relation-Mapping/Impact drift. Phase 10 probabilistic work remains gated behind this deterministic attribution. `Cognitive Attractor` is retained only as a working analogy until distributional concentration and, if claimed dynamically, state-evolution/convergence evidence exist.


## Phase 8C.12 Locate vs Relation Mapping longitudinal attribution — EXPERIMENTALLY COMPLETE 2026-09-10

Result: `104_PHASE8C12_LOCATE_RELATION_LONGITUDINAL_RESULT.md`. With exact historical audited semantic worlds and Kernel fixtures frozen, Locate target sets were substantially more stable than relevance-type labels. Reconstructing and freezing the exact historical modal Locate fixture still produced strong current Relation Mapping shifts: RS15 historical `WATCH 6/6` became `ENGAGE 4/6 + WATCH 2/6`, RS11 historical `AWARE 6/6` became `WATCH 6/6`, while RS12 topology changed but remained `WATCH 6/6`. RS05 remained the stable positive control. Current principal longitudinal residual is therefore attributed to Relation Mapping rather than Sensor/Auditor/current-Locate. Next gate: deterministic Decision-Causal Core measurement. Production default remains `one-delta-v1`.


## Phase 8C.13 Decision-Causal Core — EXPERIMENTALLY COMPLETE 2026-09-10

Result: `106_PHASE8C13_DECISION_CAUSAL_CORE_RESULT.md`. First-order counterfactual replay separates semantic/topology frequency from policy causality. RS05 `CHALLENGE(CF-B-PERF)` is the stable load-bearing positive control; RS15 ENGAGE is redundantly sustained by B1/Q1 challenge relations while always-present BT1 challenge is peripheral; RS11 current WATCH is singularly carried by the coarse `OPEN_NEW(null)` relation class; RS12 WATCH is stably supported by `REINFORCE(BT1)` with optional redundant OPEN_NEW. D confirms free-floating OPEN_NEW is peripheral under Anchored admission. Next gate: OPEN_NEW branch-level causal identity before probabilistic modeling or admission redesign. Production default remains `one-delta-v1`.


## Phase 8C.14 OPEN_NEW branch-level causal attribution — EXPERIMENTALLY COMPLETE 2026-09-10

Result: `108_PHASE8C14_OPEN_NEW_BRANCH_CAUSAL_ATTRIBUTION_RESULT.md`. Coarse `OPEN_NEW(null)` stability can hide load-bearing branch drift. RS11 WATCH is carried mainly by the N11 infrastructure branch but one realization switches singular support to N10; RS12 remains structurally robust because `REINFORCE(BT1)` is a stable sufficient support while OPEN_NEW branches are redundant. The current anchored admission is global-jurisdiction only, not effect-specific binding. Next gate is the static probabilistic cognitive-map pilot using existing frozen samples; no temporal stochastic-process model yet. Production default remains `one-delta-v1`.

## Phase 10A — Static Probabilistic Cognitive Map — EXPERIMENTALLY COMPLETE 2026-09-10

Preregistration: `109_PHASE10A_STATIC_PROBABILISTIC_COGNITIVE_MAP_PREREGISTRATION.md`; result: `110_PHASE10A_STATIC_PROBABILISTIC_COGNITIVE_MAP_RESULT.md`.

`static-probabilistic-cognitive-map-v0.1` measures one bounded-epoch empirical Cognitive Map as `P(r in T)`, `P(r in B_pi(T))`, and `P(A)`, where `B_pi(T)` is the union of necessary and individually sufficient decision supports. Wilson-95 intervals are reported for Bernoulli relation/core probabilities; topology/core and Attention entropy remain descriptive measurement only.

Canonical results: RS05 N=12 stayed ENGAGE 12/12 with `CHALLENGE(CF-B-PERF)` load-bearing 12/12. RS15 triggered the preregistered precision expansion to N=24 and remained bimodal at ENGAGE 20/24 vs WATCH 4/24; `CHALLENGE(B1/Q1)` each carried P(B)=0.833. RS11 stayed WATCH 12/12 while its dominant load-bearing OPEN_NEW branch was `RS11-N11` at 11/12. RS12 expanded to N=24 for core-probability precision, stayed WATCH 24/24, and preserved `REINFORCE(BT1)` as load-bearing 24/24 despite high peripheral topology diversity.

The working conclusion is `Topology variability != Decision instability`: distributional stability is better characterized by the load-bearing core and Attention distribution than by exact topology equality alone. Phase 10B may now compare independently frozen epochs with distribution-distance metrics; do not introduce a temporal stochastic-process model unless cross-epoch drift is materially demonstrated. Full backend regression was 598 passed / 63 skipped / 1 historical Case K urgency residual. Production default remains `one-delta-v1`.


## Phase 10B — Temporal Cognitive Basin Shift — NULL-CALIBRATED 2026-09-10

Cross-epoch cognitive-map distances were calibrated with 5000 fixed-seed permutation nulls. RS15 and RS11 show supported drift at topology, load-bearing, and Attention levels. RS12 shows supported topology/load-bearing drift but zero Attention drift, demonstrating downstream absorption. RS05 preserves Attention and topology basin with some load-bearing participation drift. Do not fit a stochastic process yet; next gate is an independent current `t2` persistence checkpoint. Production default remains `one-delta-v1`.


## Phase 10B.2 — Current Basin Persistence — COMPLETE 2026-09-10

A fresh t2 Relation-Mapping checkpoint (N=12 per canonical case) was collected with requested/response model identity separately recorded. Null-calibrated triangular comparison shows persistent new-basin patterns at all three levels for RS15 and RS11; RS12 shows persistent topology/load-bearing shift with stable WATCH Attention; RS05 remains decision/topology stable and its earlier load-bearing signal does not persist. This supports a distributional basin interpretation but still does not justify a stochastic-process fit. Next: deterministic temporal regime/change-point chip. Production default remains `one-delta-v1`.


## Phase 10C — Temporal Regime Classifier — COMPLETE 2026-09-10

A deterministic three-checkpoint regime chip now classifies null-calibrated drift patterns without fitting a stochastic process. RS15 and RS11 are PERSISTENT_SHIFT at Attention, load-bearing, and topology levels. RS12 is STABLE at Attention but PERSISTENT_SHIFT internally at topology/load-bearing. RS05 is STABLE at Attention/topology and INDETERMINATE at load-bearing. This supports the Cognitive Basin / Distributional Structural Stability working model but is not yet a dynamical-attractor claim. Production default remains `one-delta-v1`.

Phase 10C full backend regression: `615 passed / 63 skipped / 1 historical Case K failure`; no new regression.


## Phase 10D.1 — Real-Web Static Probabilistic Cognitive Map — COMPLETE 2026-09-10

Expanded the static probability-map program from four canonical cases to four additional real-web sources. Each real-web source used one fresh Sensor+Auditor perception pass, then exact frozen semantic world + modal Locate with repeated Relation Mapping under Anchored + Magnitude-Free + Pareto. Final maps: A WATCH 14/24, DROP 6/24, AWARE 4/24; C DROP 12/12; D WATCH 22/24, AWARE 2/24; X ENGAGE 11/12, WATCH 1/12. Across Phase 10A + 10D.1 there are now 8 case-level maps and 144 Relation realizations. 7/8 cases have dominant Attention concentration >=0.8 and 7/8 have Topology entropy above Attention entropy. A/D expose unresolved OPEN_NEW branch identity and A additionally exposes epistemic-band crossing as a remaining decision-axis instability. No theory or production policy was changed; production default remains `one-delta-v1`.

## Phase 10D.2 — Real-Web Source-Diversity Broadening — COMPLETE 2026-09-10

Preregistered six real-web sources across Near-Kernel / Boundary / Far-Control strata before observing any RAOS outcome. Three sources produced complete maps: N2 Google Research `ENGAGE 12/12` with `CHALLENGE(B2)` load-bearing 12/12; B1 Anthropic `DROP 12/12`; F2 NASA `DROP 12/12` with empty Locate 3/3. Three failures were retained without substitution: N1 DeepMind first Sensor call malformed/truncated JSON and was not retried; B2 OpenAI and F1 NIH were blocked by URLConnector 403. Cumulative successful distributional maps: 11 cases / 180 frozen-world Relation Mapping realizations. No theory or production policy change. Next broadening batch should use acquisition-only preflight before preregistration to reduce access-bias waste without conditioning on cognitive outcomes. Production default remains `one-delta-v1`.

## Phase 10D.3 — Real-Web Static Cognitive Map Batch-3 — COMPLETE 2026-09-10

Acquisition-only preflight selected two fetchable sources per preregistered Near-Kernel / Boundary / Far-Control stratum without observing cognitive outcomes. Five full maps completed; N3 retained a first-pass Sensor truncation failure without retry. N4 produced a persistent non-degenerate static map at N=24 (`ENGAGE 15 / WATCH 9`) with `H(Topology)=3.939 > H(Load-bearing)=2.551 > H(Attention)=0.954`; B3/B4/F3/F4 were all `DROP 12/12`, with F3/F4 empty Locate 3/3. Cumulative evidence is now 16 successful maps / 252 frozen-world Relation realizations; all 9 non-empty maps observed so far have `H(Topology) > H(Attention)`. No theory or production policy changed. Next: real-web probability-basin persistence using exact frozen worlds and existing JSD + permutation-null chips. Production default remains `one-delta-v1`.

## Phase 10D.4 — Real-Web Basin Persistence — COMPLETE 2026-09-10

Objectively selected every existing real-web static map with >=2 observed Attention actions (A/D/X/N4), then froze each exact audited semantic world, Kernel, historical modal Locate, Anchored admission, Magnitude-Free calibration, Pareto strategy, and Decision-Causal Core machinery. Fresh t2 Relation-Mapping samples matched original t1 sample counts: A 24, D 24, X 12, N4 24. Null-calibrated comparison found no Attention-basin shift in all 4/4 cases. A/X/N4 also retained load-bearing and topology basins; D showed supported raw-topology drift while load-bearing and Attention remained in the same basin. N4 independently reproduced its non-degenerate distribution from ENGAGE 15/WATCH 9 to ENGAGE 14/WATCH 10 (`Attention JSD=0.00131`). Phase 10D.4 adds 84 fresh Relation realizations; cumulative distributional sampling is now 336 Relation-Mapping realizations across 16 established successful static maps/checkpoints. Focused contracts: 36 passed; full backend regression: 615 passed / 63 skipped / 1 historical Case K failure. No theory or production policy change; production default remains `one-delta-v1`.

## RAOS Distributional Cognitive Stability Theory V1.0 — FORMALIZED 2026-09-11

Theory reference: `128_RAOS_DISTRIBUTIONAL_COGNITIVE_STABILITY_THEORY.md`; Phase 10D.4 implementation audit: `127_PHASE10D4_CODE_AUDIT_AND_SAMPLING_SEMANTICS.md`. The stability model now explicitly separates one stochastic realization from the empirical Cognitive Probability Map `M_t(E,K) = (P(r in T), P(r in B_pi(T)), P(A))`. Distributional Structural Stability and Cognitive Probability Basin are promoted to experimentally supported RAOS stability concepts; Cognitive Attractor remains analogy/hypothesis only. Interference-pattern and spectrum analogies are retained with strict semantic boundaries. Code audit independently reproduced all Phase 10D.4 Attention JSD values and found no evidence of caching or cross-metric calculation error. Production default remains `one-delta-v1`.

## Phase 10D.4 production dogfood rollout — COMPLETE 2026-09-11

Promotion / handoff record: `129_PHASE10D4_PRODUCTION_PROMOTION_AND_PHASE9_HANDOFF.md`.

The combined research strategy `Anchored OPEN_NEW + Magnitude-Free + Pareto Multi-Delta` is now enabled for the active Mac dogfood runtime through `RAOS_DECISION_STRATEGY_ID=pareto-multidelta-magnitude-free-anchored-open-new`. The repository compatibility default remains `one-delta-v1`, preserving historical replay and a one-line rollback path.

A fresh live API smoke analysis confirmed the running `AnalysisRun.execution_snapshot.decision_strategy` is `pareto-multidelta-magnitude-free-anchored-open-new-v0.1`, with `magnitude-free-v0.1` and `anchored-open-new-v0.1` recorded explicitly. Focused regression: `78 passed / 1 warning`. Full backend regression: `616 passed / 63 skipped / 1 historical Case K failure`; no new regression.

Current handoff is now **Phase 9A — Kernel Causal Alignment**. First question: after an explicit human-authorized `K0 -> K1` change, does the same frozen information interaction move from `M(E,K0)` to `M(E,K1)` in a semantically expected way that exceeds the fixed-K stochastic basin? Do not introduce Markov/HMM/attractor machinery at this gate.

## Phase 9A Kernel Causal Alignment — PREREGISTERED 2026-09-11

Preregistration: `130_PHASE9A_KERNEL_CAUSAL_ALIGNMENT_PREREGISTRATION.md`. Parent rollback checkpoint: `phase10d4-production-dogfood-v1` at `7054029599b5e3302e6748c3dc7e90ef0473b278`.

The first controlled pilot uses frozen RS05 information with three isolated Kernel arms: unchanged K0; K1-S semantic assimilation through an accepted MODIFY KernelPatch; and K1-I importance-only downshift through an accepted MODIFY KernelPatch. Sensor, Auditor and Locate target identity remain frozen. Primary question: can RAOS distinguish legitimate `K0 -> K1` change from fixed-K stochastic variation using the existing Cognitive Probability Map, Decision-Causal Core, JSD and permutation-null chips? Pre-measurement audit `131_PHASE9A_INSTRUMENT_AUDIT_AND_PREREGISTRATION_AMENDMENT.md` found that the Phase 10 native research converter did not bind explicit Kernel importance; Phase 9A will apply production `resolve_target_importance` identically across all arms before decision analysis and will build a fresh K0 map under this corrected longitudinal instrument.

## Phase 10D.5 Production Semantic Parity Audit — FORMAL REPLAY PLAN LOCKED 2026-09-11

Preregistration / audit plan: `132_PHASE10D5_PRODUCTION_SEMANTIC_PARITY_PREREGISTRATION.md`. Phase 9A outcome sampling remains paused. A pre-formal diagnostic discovered that Phase-10 native research cognition copied LLM `target_importance` directly, while deployed production `ModelProvider` resolves targeted importance through explicit Kernel importance/priority, then node-type prior, then LLM estimate.

The 10D.5 formal audit will deterministically replay the exact 168 stored Phase 10D.4 real-web samples. Arm R must reproduce historical Attention and Decision-Causal Core exactly before Arm P rebinds only targeted importance with production authority. No acquisition, Sensor, Auditor, Locate, or LLM call is permitted.

Pre-measurement scope amendment: `133_PHASE10D5_SCOPE_AUDIT_AND_REPLAY_BOUNDARY.md`. Static code audit also found production-only Impact prompting and `ground_effects`; therefore v0.1 isolates only the discovered target-importance authority seam. Full native-vs-production prompt/grounding parity is explicitly not claimed by this replay.

## Phase 10D.5 Production Semantic Parity Audit — COMPLETE 2026-09-11

Result: `134_PHASE10D5_PRODUCTION_SEMANTIC_PARITY_RESULT.md`; scope amendment: `133_PHASE10D5_SCOPE_AUDIT_AND_REPLAY_BOUNDARY.md`. Measurement SHA `e71e99f8a0450567069d5f83a557ce9dbe4dfa82`; canonical artifact SHA256 `e2ef93617f48e8d296e63eb6b0075b00986e764f8b46a46023837b2c0e5eb6af`.

Historical Arm R reproduced all 168 stored Phase 10D.4 topology/core/Attention samples exactly. Rebinding only targeted `target_importance` through deployed `resolve_target_importance` changed individual decisions materially (A 32/48, D 48/48, X 3/24, N4 0/48), but all 4/4 cases remained null-compatible at the Attention layer. D's load-bearing basin changed from compatible to supported drift; its raw topology drift remains supported.

Interpretation: 10D.4's exact Attention frequencies belong to the native research path, but its product-level `4/4 same Attention basin` conclusion survives deployed target-importance authority. The live dogfood pipeline itself uses production `ModelProvider`; the mismatch was in research-to-production transfer semantics, not a newly introduced live production bug. Full native-vs-production Impact prompt / `ground_effects` parity remains a separate future gate before claiming exact production distribution equivalence. Phase 9A remains preregistered with no outcome samples collected.

## Phase 10D.6 Cognitive Path Reconciliation — PREREGISTERED 2026-09-11

Preregistration: `135_PHASE10D6_COGNITIVE_PATH_RECONCILIATION_PREREGISTRATION.md`. Re-review established that deployed `ModelProvider` contains important post-v2.1 safeguards and is not replaced wholesale by `native_assess()`, while its Impact prompt still contains stale pre-Pareto/pre-Magnitude-Free single-winner/cardinal instructions. 10D.6 therefore reconciles the paths sequentially: A authority contract, B prompt-only shadow A/B, C target-importance authority calibration, D combined promotion gate. Phase 9A remains paused.

## Phase 10D.6B Prompt Reconciliation — CLOSED / NOT PROMOTED 2026-09-11

Result: `136_PHASE10D6B_PROMPT_RECONCILIATION_RESULT.md`. Prompt-only shadow A/B on frozen real-web A/D/X/N4 found that removing stale single-winner/cardinal instructions is necessary but not sufficient. P1 over-suppressed X to DROP 6/6, while both P0 and P1 produced empty effects / DROP 6/6 on A and D. N4 remained WATCH 6/6. Attribution moved upstream: the audited-units -> `ExtractionResult` seam flattens Phase-10 canonical unit/support structure before Impact. Do not promote P1 and do not calibrate importance yet. Next: 10D.6C Canonical Input Reconciliation with production grounding/safeguards preserved.

## Phase 10D.6C Canonical Input Reconciliation — PREREGISTERED 2026-09-11

Preregistration: `137_PHASE10D6C_CANONICAL_INPUT_RECONCILIATION_PREREGISTRATION.md`. After 10D.6B exposed empty-effect DROP on A/D in both prompt arms, the next controlled gate moves to the earlier representation seam. B0 uses the audited-units -> `ExtractionResult` Impact payload; C1 gives the same Auditor-admitted canonical units directly to Relation Mapping. The production system prompt, grounding, importance resolver, feature projection, decision strategy and runtime remain frozen. Raw pre-grounding and grounded effects are both persisted for causal attribution.

## Phase 10D.6C first execution — TECHNICAL SCHEMA FAILURE / AMENDMENT LOCKED 2026-09-11

First execution at SHA `08963a4` yielded 0/24 valid C1 outcomes because the experimental canonical user payload omitted the explicit JSON response skeleton that production `impact_user_prompt` includes. This is a runner plumbing asymmetry, not a semantic result. Amendment `138_PHASE10D6C_SCHEMA_PLUMBING_FAILURE_AND_AMENDMENT.md` permits only restoring the exact output-shape instruction; all semantic and decision variables remain frozen. Failed artifact is retained.

## Phase 10D.6C Canonical Input Reconciliation — CLOSED 2026-09-11

Result: `139_PHASE10D6C_CANONICAL_INPUT_RECONCILIATION_RESULT.md`. Valid rerun at SHA `cd809fd` shows direct canonical audited units are decision-bearing: A recovers WATCH in 2/6 from B0 DROP 6/6; D recovers AWARE/WATCH in 4/6 from B0 DROP 6/6; X removes the single B0 DROP; N4 remains WATCH 6/6. Recovered A/D raw effects generally survive production grounding, attributing the main measured difference upstream to Impact input representation. Canonical input alone still does not reproduce the richer Phase-10 targeted topology. Next gate: prompt × input interaction; importance remains frozen.

## Phase 10D.6D Canonical Input × Reconciled Prompt — PREREGISTERED 2026-09-11

Preregistration: `140_PHASE10D6D_CANONICAL_PROMPT_INTERACTION_PREREGISTRATION.md`. C0/C1 both consume direct canonical audited units and preserve production grounding/importance/runtime/decision semantics; only the Impact system prompt differs. This completes the representation × prompt interaction test before any target-importance redesign or production promotion.

## Phase 10D.6D Canonical Input × Reconciled Prompt — CLOSED / NOT PROMOTED 2026-09-11

Result: `141_PHASE10D6D_CANONICAL_PROMPT_INTERACTION_RESULT.md`. Combined canonical input + reconciled prompt did not produce a promotable candidate: A remained DROP 6/6, D became more DROP-heavy, X gained richer topology but less stable Attention, and N4 remained WATCH 6/6. Raw/grounded attribution exposed a deeper legacy coupling: production `ground_effects` can delete canonical targeted relations and caps single-source/no-observation epistemic strength at 0.35, directly forcing the Magnitude-Free epistemic band low. Next gate shifts from prompt tuning to canonical authority enrichment for both importance and epistemic bands.

## Phase 10D.6E Canonical Authority Enrichment — PREREGISTERED 2026-09-11

Preregistration: `142_PHASE10D6E_CANONICAL_AUTHORITY_ENRICHMENT_PREREGISTRATION.md`. 10D.6D exposed that remaining divergence is no longer safely described as a prompt problem: production grounding can delete canonical targeted relations and forces single-source/no-observation epistemic values to 0.35, while the current importance resolver also collapses most update-eligible node-type priors above the Magnitude-Free 0.55 high/low boundary. 10D.6E therefore moves LLM responsibility toward semantic-only operation/target/support references/reason and requires authoritative deterministic enrichment for importance and epistemic bands before any production promotion.

## Phase 10D.6E Authority Band Calibration — CLOSED / NO PROMOTION 2026-09-11

Result: `144_PHASE10D6E_AUTHORITY_BAND_CALIBRATION_RESULT.md`. Exact 168-sample offline replay passed both fail-closed references: historical Phase 10D.4 outputs and Phase 10D.5 production-importance projections. C2 (treat every Auditor-admitted relation as epistemically sufficient) produced 46 new ENGAGE decisions and a supported D Attention-basin shift, so it is rejected. C1 removed production-importance ENGAGE inflation without introducing any new DROP or ENGAGE and retained all four Attention basins, but collapsed N4 to WATCH 24/24. Attribution shows the bottleneck is epistemic representation: `SOURCE_CLAIM` currently conflates announcements/media claims with primary technical measurements, including RS05 profiler evidence and N4 robotics evaluations. Importance authority remains on the C1 direction; epistemic authority must become support-bound and evidence-class-aware. Next: 10D.6F Effect Support Binding / Evidence-Class Authority. Production defaults unchanged; Phase 9A stays paused.

## Phase 10D.6F Effect Support Binding — COMPLETE / NOT PROMOTED 2026-09-11

Result: `147_PHASE10D6F_EFFECT_SUPPORT_BINDING_RESULT.md`; pre-semantic plumbing amendment: `146_PHASE10D6F_ENV_LOADING_FAILURE_AND_AMENDMENT.md`. Valid measurement at SHA `8422271` completed 24/24 fresh calls. A/D emitted empty effects 6/6; X produced 35/35 legal support-bound effects (OPEN_NEW only); N4 produced 33/33 legal effects and recovered stable targeted relations, including `REINFORCE(BT1)` 6/6 bound to `neu-002` 6/6. Explicit `support_unit_ids` / jurisdiction binding is therefore feasible, but the 10D.6F contract also changed prompt/schema semantics and cannot be promoted as a pure provenance change. Duplicate OPEN_NEW support signatures also require deterministic normalization. Next: 10D.6G native-semantics support-binding parity shadow; Phase 9A remains paused and production defaults remain unchanged.

## Phase 10D.6G Native-Semantics Support-Binding Parity — COMPLETE 2026-09-11

Result: `149_PHASE10D6G_NATIVE_SEMANTICS_SUPPORT_BINDING_PARITY_RESULT.md`. Measurement at SHA `754a783` completed 24/24 calls and emitted 144 raw effects, 136 of which passed deterministic legality. The eight rejected effects were X attempts to update location-only G1/P1 nodes. Retaining historical native semantics while adding `support_unit_ids` / jurisdiction anchors restored most historical relation families (sentinel recovery A 3/4, D 7/7, X 3/5, N4 5/7), proving provenance binding itself does not force the 10D.6F topology collapse. Concrete technical relations showed highly stable support binding (e.g. N4 `REINFORCE(BT1)` -> `neu-002` 6/6). Next: 10D.6H removes only the three compatibility cardinal effect fields while preserving native semantics + provenance; no production promotion yet. Phase 9A remains paused.

## Phase 10D.6H Cardinal-Field Removal Parity — COMPLETE 2026-09-11

Result: `151_PHASE10D6H_CARDINAL_FIELD_REMOVAL_PARITY_RESULT.md`. At measurement SHA `e449001`, 24/24 fresh calls removed `change_magnitude`, `epistemic_strength`, and `target_importance` entirely from the effect schema while retaining native semantics + relation-level support/jurisdiction provenance. Stable 10D.6G relation families broadly survived (majority recovery A 3/4, D 6/7, X 5/5, N4 5/5; N4 core 5/5 was 6/6). 141 raw effects -> 133 deterministic-legal effects; remaining failures were explicit target-legality violations, not missing numeric scores. The cardinal-free support-bound relation contract is now the leading research contract. Next: 10D.6I effect-specific evidence-class authority; production default unchanged and Phase 9A remains paused.
## Phase 10D.6I Effect-Specific Evidence-Form Authority — CLOSED / NEAR-PASS 2026-09-11

Result: `153_PHASE10D6I_EFFECT_SPECIFIC_EVIDENCE_FORM_AUTHORITY_RESULT.md`. A frozen 18-unit manual research reference tested categorical provenance role and evidence form with six batch classifications. Provenance role was exact and stable 18/18; evidence form was stable 18/18 but exact on 16/18 (88.9%), missing the preregistered 90% gate with zero critical measurement/assertion or primary/secondary confusions. Both disagreements were genuinely mixed units, so single-form classification is not promoted. Next: compositional evidence-form representation on fresh held-out B3/B4/F3/F4 units. Production defaults unchanged; Phase 9A remains paused.

## Phase 10D.6I.1 Compositional Evidence Form Fresh Holdout — CLOSED / NOT PROMOTED 2026-09-11

Result: `155_PHASE10D6I1_COMPOSITIONAL_EVIDENCE_FORM_FRESH_HOLDOUT_RESULT.md`. Fresh B3/B4/F3/F4 holdout preserved perfect provenance-role classification but full multi-form exact-set agreement was only 70% (mean Jaccard 0.842) despite 90% stability and zero critical confusions. The remaining disagreements are mostly companion forms, so exhaustive evidence-form taxonomy is not promoted as an Attention authority. Next: relation-specific support directness/scope grounding. Production defaults unchanged; Phase 9A remains paused.

## Phase 10D.6J Relation-Support Directness — CLOSED / INSTRUMENT NOT PROMOTED 2026-09-11

Result: `157_PHASE10D6J_RELATION_SUPPORT_DIRECTNESS_RESULT.md`. Measurement SHA `342b4b9`; artifact SHA256 `1db72a6e068384d7eadd17fb01d22a36a4f81019a5dd21de789c17fa78fcd7c8`. Six repeated audits were structurally successful and all 16 items were stable at >=5/6 with zero critical confusions, but exact agreement was 13/16 (81.25%), below the preregistered 14/16 gate. The instrument is not promoted as a truth oracle. The next gate may use it only conservatively: DIRECT can qualify for strong epistemic authority subject to provenance; PARTIAL remains weak; INSUFFICIENT/CONTRADICTS_OPERATION are rejected. Production defaults unchanged; Phase 9A remains paused.

## Phase 10D.6K Conservative Authoritative Attention Replay — PREREGISTERED 2026-09-11

Preregistration: `158_PHASE10D6K_CONSERVATIVE_AUTHORITATIVE_ATTENTION_REPLAY_PREREGISTRATION.md`. Frozen input is the 24-sample 10D.6H cardinal-free/support-bound artifact. The gate reconnects authoritative importance/epistemic bands to the unchanged Anchored + Magnitude-Free + Pareto stack. Three same-topology arms isolate epistemic authority: all-support sufficient upper bound, single-source-weak conservative baseline, and canonical directness+provenance authority. No production promotion is permitted from this gate; Phase 9A remains paused.

## Phase 10D.6K first execution — TECHNICAL CARDINAL-FREE LEGALITY FAILURE / AMENDMENT LOCKED 2026-09-11

First execution at SHA `2053ad0` produced all-DROP because shared `legal_public_effects()` still requires `change_magnitude > 0` before the Magnitude-Free/Pareto stack. Failed artifact SHA256 `bed036e39041f296c0b1b88234daa910f9de65021f6c60191e4a26a363072bbf` is retained and is not a cognitive result. Amendment `159_PHASE10D6K_CARDINAL_FREE_LEGALITY_FAILURE_AND_AMENDMENT.md` forbids injecting a fake positive magnitude. Existing Magnitude-Free v0.1 remains unchanged; a separately versioned experimental semantic-effect-existence strategy will be introduced for the valid rerun. Production defaults unchanged; Phase 9A remains paused.

## Phase 10D.6K second execution — CAUSAL-CORE LEGALITY PLUMBING FAILURE / AMENDMENT LOCKED 2026-09-11

The new cardinal-free strategy itself was correct, but `Decision-Causal Core` independently applied legacy `legal_public_effects()` before invoking it, again producing all-DROP. Failed artifact SHA256 `3661c32c1dd9eb493e74d55e830aa9b84ee8f08e1522c8f4f5d544c19fe26423` is retained and is not a cognitive result. Amendment `160_PHASE10D6K_CAUSAL_CORE_LEGALITY_PLUMBING_FAILURE_AND_AMENDMENT.md` centralizes effect-existence legality in the decision strategy so route and causal ablation share one contract. Existing production strategy semantics remain unchanged.

## Phase 10D.6L End-to-End Business Logic Integrity Audit — ACTIVE 2026-09-11

Audit: `161_PHASE10D6L_END_TO_END_BUSINESS_LOGIC_INTEGRITY_AUDIT.md`. New cognitive outcome sampling remains paused. Repaired and regression-locked: strategy-owned effect legality/Causal-Core parity; `Decision Cause = Public Update Cause = authorized ModelDelta/KernelPatch Cause`; Impact prompt/contract + decision strategy in execution identity; explicit strategy/provider preservation through runtime reschedule; causal WATCH/AttentionPlan scope; Impact Replay separation of legacy primary from strategy decision cause; and actual fallback-provider provenance. Current OPEN_NEW global-Locate jurisdiction is explicitly marked as an approximation, not exact effect provenance. Full backend regression after these repairs is 666 passed / 63 skipped / 1 historical Case-K failure / 1 warning, with no new failures. The remaining semantic blocker is the default production `IMPACT_SYSTEM`, which still contains OPEN_NEW magnitude-threshold and single-winner instructions that conflict with Pareto. `IMPACT_SYSTEM_PARETO_COMPAT` exists as an experimental minimal deletion-only contract; next gate is 10D.6L.1 controlled shadow. Production default unchanged; Phase 9A remains paused.

Evaluator-capacity rule added 2026-09-12: DeepSeek-Flash is a weak-model robustness lower bound; strong-model manual adjudication provides an architecture-capability upper-bound reference. Isolated weak-model errors do not justify architecture changes without strong-model confirmation or deterministic invariant failure. Strong reference: `164_PHASE10D6L2_MODEL_CAPACITY_BRACKETING_STRONG_REFERENCE.md`.

## Phase 10D.6L.1 Minimal Prompt Authority Removal Shadow — CLOSED / NOT PROMOTED 2026-09-11

Result: `163_PHASE10D6L1_MINIMAL_PROMPT_AUTHORITY_REMOVAL_RESULT.md`. Measurement SHA `f757402`; artifact SHA256 `444fe8bb7e0d7670411983167fade62fd638dd7f7e8ba7599303e45a5c2fd8cf`. 48/48 production-style prompt-shadow calls succeeded. Deleting only the stale OPEN_NEW magnitude-threshold and single-winner instructions did not cause global collapse (A unchanged DROP6; N4 unchanged WATCH6) but materially changed D/X/N4 relation topology and D Attention (P0 DROP6 vs P1 DROP3/WATCH2/AWARE1). The two prompt lines are therefore genuinely upstream decision-bearing, but deletion-only P1 is not promoted because weak D relations are released. Next: preregistered same-arm support/jurisdiction-binding diagnostic; production default unchanged, 10D.6K and Phase 9A remain paused.


## Phase 10D.6L.2 Model-Capacity Bracketing / 10D.6L.3 Decoupled Support Binding — ACTIVE 2026-09-12

Strong-model manual reference is frozen in `164_PHASE10D6L2_MODEL_CAPACITY_BRACKETING_STRONG_REFERENCE.md`. Combined relation+support binding under DeepSeek-Flash is closed as instruction-coupled and not promoted (`165_PHASE10D6L1_SUPPORT_BINDING_DIAGNOSTIC_RESULT.md`). Next gate `166_PHASE10D6L3_DECOUPLED_SUPPORT_BINDING_PREREGISTRATION.md` freezes Relation Mapping first and allows the binder only to attach provenance; it cannot alter relation topology.

## Phase 10D.6L.3 Decoupled Support Binding — CLOSED / STRUCTURAL PASS / STRICT STABILITY GATE FAIL 2026-09-12

Result: `168_PHASE10D6L3_DECOUPLED_SUPPORT_BINDING_RESULT.md`. Valid rerun at SHA `ae0c4e9` completed 42/42 binding calls with 100% frozen relation-id preservation and zero unknown identifiers. Because Binding had no operation/target fields, Relation Mapping topology was immutable by construction. Exact support-signature stability reached 24/28 relation instances at >=2/3, below the preregistered all-item gate, so the weak binder is not promoted as a stable provenance oracle. The four misses separate into weak/upstream relation errors or optional companion evidence rather than a single architecture failure. Next: 10D.6L.4 Grounding capacity bracketing.

## Phase 10D.6L.4 Grounding Capacity Bracketing — PREREGISTERED 2026-09-12

Preregistration: `169_PHASE10D6L4_GROUNDING_CAPACITY_BRACKETING_PREREGISTRATION.md`. Strong-model manual reference frozen before Flash outcomes in `170_PHASE10D6L4_STRONG_GROUNDING_REFERENCE.md` and `eval/live/phase10d6l4_strong_grounding_reference_v0_1.json`: 28 items = 11 DIRECT, 12 PARTIAL, 5 INSUFFICIENT. Flash is evaluated only as robustness lower bound; isolated weak-model disagreement does not justify architecture changes. Production defaults unchanged; 10D.6K and Phase 9A remain paused.

## Phase 10D.6L.4 Grounding Capacity Bracketing — CLOSED / WEAK EVALUATOR NOT AUTHORITATIVE 2026-09-12

Result: `171_PHASE10D6L4_GROUNDING_CAPACITY_BRACKETING_RESULT.md`. At measurement SHA `8de852d`, all 9 Flash batches and all 28 items were stable, but modal exact agreement with the frozen strong reference was 8/28. Flash showed a stable permissive bias: 12 strong-reference PARTIAL items were called DIRECT, and three strong-reference INSUFFICIENT items were initially called DIRECT. Two of the three critical cases were OPEN_NEW jurisdiction judgments whose L4 input exposed only anchor codes, not full anchor semantics; these were therefore instrument-under-specification candidates rather than clean evaluator errors.

## Phase 10D.6L.4J OPEN_NEW Jurisdiction Capacity — CLOSED / INPUT-SUFFICIENCY CONFIRMED 2026-09-12

Result: `173_PHASE10D6L4J_OPEN_NEW_JURISDICTION_CAPACITY_RESULT.md`. With complete jurisdiction-anchor semantics supplied, the two D OPEN_NEW cases were classified `INSUFFICIENT_JURISDICTION` by Flash in 3/3 draws each, exactly matching the frozen strong reference with zero critical error. Conclusion: task-state sufficiency is a first-order condition for fair evaluator assessment. Flash remains useful as a stable lower-bound reviewer with a permissive bias; it is not dismissed as incapable. Relation-support fit remains Grounding responsibility, while OPEN_NEW jurisdiction fit belongs to Anchored admission. Production is **not** required to make two model calls; one evaluator call may return separately owned structured judgments.

## Phase 10D.6L End-to-End Business Logic Integrity Audit — CLOSED / PRODUCTION PROMOTION DEFERRED 2026-09-12

Closure: `174_PHASE10D6L_END_TO_END_BUSINESS_LOGIC_INTEGRITY_RESULT.md`. Full backend regression after the audit is `682 passed, 63 skipped, 1 failed, 1 warning`; the sole failure remains historical Case K (`PREEMPT` expected, `PRIORITY` actual), with zero new regression failures. The audit now distinguishes architecture/contract bugs, evaluator-policy/capability boundaries, and instrument/input insufficiency. Next: resume 10D.6K authoritative Attention replay with evaluator-capacity bracketing; Phase 9A remains paused.

## Phase 10D.6K Evaluator-Capacity Authoritative Attention Replay — CLOSED 2026-09-12

Amendment: `175_PHASE10D6K_EVALUATOR_CAPACITY_BRACKETING_AMENDMENT.md`. Result: `176_PHASE10D6K_EVALUATOR_CAPACITY_BRACKET_RESULT.md`. Valid measurement SHA `520faa4`; artifact SHA256 `7313d7bf0984a1e2db0cb9f5f8fd6cf5fca23479a18ea3c75c8a71004fb75339`.

On the same 24 frozen 10D.6H realizations, K2 DeepSeek-Flash and K3 strong authority differed on 18/24 final Attention decisions, but N4 remained WATCH 6/6 under every arm. Strong authority produced A DROP6, D DROP6, X WATCH6, N4 WATCH6; weak authority produced A AWARE6, D WATCH6, X ENGAGE6, N4 WATCH6. This demonstrates that evaluator policy materially affects boundary cases while direct technical evidence can remain Attention-stable.

The K3 direction passes the amended research gate: no A/D ENGAGE inflation, no false DROP on direct N4 evidence, and repaired Decision Cause provenance is preserved. Production is not promoted. N4 attribution shows its remaining WATCH is not a Grounding failure: direct B1/M1 evidence is SUFFICIENT but low-importance, while high-importance BT1/Q1 effects are only PARTIAL/WEAK. If N4 is later judged too conservative, the next question belongs to importance/Attention policy, not Grounding.

Next: Phase 9A may resume, but its old preregistered instrument must first be audited against the frozen post-10D.6L cognition contract before any outcome sampling.
Regression checkpoint after 10D.6K v0.2: `686 passed, 63 skipped, 1 historical Case-K failure, 1 warning`; zero new failures.
## Research spinout — RAOS Cognitive Evaluator Benchmark paper seed — 2026-09-12

Paper/motivation seed: `178_RAOS_COGNITIVE_EVALUATOR_BENCHMARK_PAPER_SEED.md`. The proposed benchmark grows out of RAOS causal failure analysis and targets state-conditioned, evidence-grounded cognitive reasoning plus downstream decision consequences. Current draft includes Abstract, Introduction, Related Work (FEVER/AVeriTeC/ALCE/FACTS Grounding/Evidence Sufficiency/JudgeBench), benchmark task skeleton, and a frozen research-origin narrative. This is a parallel research asset and does **not** interrupt Phase 9A; Phase 9A's Kernel counterfactual is expected to provide a central benchmark result.
## Phase 9A Kernel Causal Alignment — ACTIVE / v0.2 PREREGISTERED 2026-09-13

Post-10D.6L amendment: `177_PHASE9A_POST_10D6L_INSTRUMENT_AMENDMENT.md`. The original scientific question is unchanged (`E` fixed, accepted `K0 -> K1`, measure `M(E,K)`), but the unfinished v0.1 runner is invalid because it predates cardinal-free legality and the frozen Relation Mapping / Support Binding / Grounding / Authority boundaries.

The v0.2 design freezes RS05 evidence and Locate, uses relation-only cardinal-free stochastic Relation Mapping, deterministic `RS05-U01` support binding, preregistered strong Grounding, Kernel-authoritative importance, and the repaired cardinal-free Magnitude-Free/Pareto/Attention path. K0 and K1-S receive fresh interleaved Relation-Mapping samples; K1-I replays each K0 relation realization exactly so the importance-only intervention cannot be confounded by semantic stochasticity.

Primary semantic gate: K0 vs K1-S raw target polarity must move from CHALLENGE-dominant to REINFORCE-dominant and pass the frozen 5000-permutation JSD gate. Primary allocation gate: K0 vs K1-I must preserve exact target topology while HIGH->LOW Kernel importance drives the paired mechanistic Attention transition `ENGAGE -> AWARE` whenever the target CHALLENGE is retained. No Phase 9A outcome has yet been sampled.
## Phase 9A v0.2 deterministic instrument preflight — CLOSED 2026-09-13

Result: `179_PHASE9A_V02_DETERMINISTIC_PREFLIGHT_RESULT.md`. No LLM outcome was sampled. K0 and K1-I produce byte-equivalent Relation-Mapping payloads when importance/version metadata is excluded as preregistered; K1-S differs only through the semantic proposition. Deterministic cardinal-free routing confirms the preregistered downstream channels: K0 CHALLENGE/HIGH/SUFFICIENT -> ENGAGE, K1-S REINFORCE/HIGH/SUFFICIENT -> AWARE, and K1-I CHALLENGE/LOW/SUFFICIENT -> AWARE. Next: implement and test the v0.2 stochastic Relation-Mapping runner before any outcome collection.

## Phase 9A Kernel Causal Alignment — CLOSED / CAUSAL ALIGNMENT SUPPORTED 2026-09-13

Result: `180_PHASE9A_KERNEL_CAUSAL_ALIGNMENT_RESULT.md`. Valid v0.2 measurement SHA `fcf684ad33fb3de3215ce6b163f6cdb5ded50d7c`; artifact SHA256 `025e0777d1146ce3e2720bd9bd1b42bf34a969a9faa2fea13b5b36c8237860ea`.

With identical frozen RS05 evidence, K0 produced `CHALLENGE_ONLY 12/12 -> ENGAGE 12/12`, while semantic assimilation K1-S produced `REINFORCE_ONLY 12/12 -> AWARE 12/12`. Raw-polarity JSD=`1.0`; 5000-permutation null p95=`0.081704`; tail probability=`0.00019996`; preregistered semantic gate PASS. The primary endpoint is raw Relation Mapping, so deterministic Grounding cannot manufacture the relation reversal.

The importance-only K1-I arm replayed the exact K0 relation realization in every pair: topology/load-bearing JSD=`0.0`, zero topology invariant violations, while authoritative importance `0.9 -> 0.2` changed Attention `ENGAGE -> AWARE` in `12/12` retained-CHALLENGE pairs. This cleanly separates semantic assimilation from attention allocation. Full regression: `693 passed, 63 skipped, 1 historical Case-K failure, 1 warning`; zero new failures. Production defaults unchanged.

## Research == Production Developer Dogfood Alignment — CLOSED / ACTIVE 2026-09-13

Result: `181_RESEARCH_PRODUCTION_ALIGNMENT_DOGFOOD_ROLLOUT_RESULT.md`.

Because RAOS has no external production users yet, the Mac runtime is treated as developer dogfood rather than a separate semantic tier. New dogfood AnalysisRuns now execute the validated research contract directly: Phase 8C.2 Sensor/Auditor representation, Phase 9A relation-only mapping, 10D.6L.3 Support Binding, 10D.6L.4 Grounding, 10D.6L.4J OPEN_NEW jurisdiction, deterministic ordinal Authority, semantic cardinal-free effect existence, Magnitude-Free/Pareto Attention, and exact Decision Cause downstream projection.

Active local dogfood identity is `research-aligned-cognition-v1` with decision strategy `pareto-multidelta-cardinal-free-effect-anchored-open-new-v0.2`. Legacy cognition remains only for explicit historical replay / rollback compatibility.

A real Mac HTTP smoke completed successfully with `fallback_used=false`, `extraction_path.mode=bridge`, three support-bound relations, Grounding `DIRECT/DIRECT/PARTIAL`, and a final `WATCH` whose public update and persisted Watch matched the same `REINFORCE(BOTTLENECK)` Decision Cause. Repeating `/analysis/run` after final backend restart hit the same completed run in 0.066s, confirming the running server uses the aligned execution identity.

Dogfood also exposed and repaired two deployment residuals: the local SQLite schema was upgraded from Alembic `0003` to current head `0008`, and poisoned-transaction failure recovery now rolls back before marking persisted AnalysisRuns `FAILED`, preventing orphan `RUNNING` identities.

Final regression: `701 passed, 63 skipped, 1 historical Case-K failure, 1 warning`; zero new failures. Next work should come from actual dogfood residuals or a newly motivated research question rather than maintaining a separate production-only cognition path.

## Acquisition Plane v0.1 — TOP-LEVEL DESIGN FROZEN / IMPLEMENTATION STARTED 2026-09-13

Design: `182_ACQUISITION_PLANE_V01_TOP_LEVEL_DESIGN.md`. Acquisition extends RAOS to the external-world boundary and answers only “what became observable?”, while the existing Information/Cognitive planes retain all semantic judgment. The v0.1 ontology is deliberately limited to four objects: Source, Observation, Information Object, and Snapshot. Core invariant: Source selection defines observation scope, never item-level cognitive relevance.

Implementation scope is intentionally minimal: prove `Source -> Observation -> Information Object -> Snapshot -> existing RAOS Source ingestion -> existing research-aligned analysis` using RSS as the first transport. X, authenticated crawling, complex anti-bot behavior, adaptive acquisition, and other corner cases are deferred until dogfood produces concrete residuals.
