# Research Attention OS — Mathematical Language Registry

Status: **CANONICAL QUICK-REFERENCE / ACTIVE MAINTENANCE CONTRACT**  
Date: 2026-09-07  
Purpose: provide one stable entry point for the current mathematical language of RAOS so that symbol meaning does not drift across research iterations, implementation work, or human memory.

> This file is the RAOS mathematical dictionary. It summarizes—not replaces—the canonical semantic documents. When a frozen semantic definition changes, this registry MUST be updated in the same research change.

---

## 0. Maintenance invariant

RAOS has accumulated multiple rounds of semantic calibration. Human memory is not a reliable version-control system.

Therefore:

```text
Any change to a canonical variable's:
- mathematical definition,
- dependency structure,
- physical interpretation,
- human-language contract,
- or theory/estimator boundary

MUST update this registry in the same research change.
```

Core notation discipline:

$$
\boxed{Theory\ state\neq Engineering\ estimate}
$$

Use an un-hatted symbol for the theoretical / semantic variable and a hatted symbol for an engineering estimate whenever the distinction matters:

$$
D\neq\hat D,\qquad S\neq\hat S,\qquad P\neq\hat P
$$

Likewise for event semantics:

$$
Sem^*(E)\neq \widehat{Sem}(E)
$$

Do not alter a theoretical definition merely because its engineering sensor or estimator is imperfect.

---

# 1. One-screen core map

```text
REAL WORLD / INFORMATION

I_t
 ↓ Extract / Semantic Sensor
E_t / SemHat(E)
 ↓
+---------------------------+
|                           |
v                           v
Cognitive path          Attention-world path
                         D-hat / S-hat / P-hat
K_t                     |
 ↓ Locate                |
L_t                     |
 ↓                      |
Delta_t                 |
+------------+-----------+
             ↓
        Attention Policy
             ↓
            A_t
             ↓
            H_t
             ↓ human-authorized patch only
          K_{t+1}
```

For the current no-cognitive-change AWARE study:

$$
\boxed{
\Delta_t=\varnothing
\quad\Longrightarrow\quad
AWARE(E,u,t)=S(E)\land\bigl(D(E,u)\lor P(E,t)\bigr)
}
$$

Engineering approximation:

$$
\boxed{
\hat A
=
FrozenPolicy(\hat D,\hat S,\hat P)
}
$$

with partial determinacy allowed when an unknown component cannot change the Boolean result.

---

# 2. Core mathematical language table

| Symbol | Canonical name | Dependency | Mathematical language | Physical meaning | One-sentence plain language |
|---|---|---|---|---|---|
| $I_t$ | Information | time $t$ | external information object | raw information reaching RAOS | **现在进来了一条什么原始信息？** |
| $E_t$ | Epistemic Representation | $I_t$ | $E_t=Extract(I_t)$ | claims, observations, inferences and evidence recovered from the source | **这条信息实际上说了什么，哪些是事实、观察、推断和证据？** |
| $Sem^*(E)$ | True Event Semantics | real event $E$ | latent / unobservable | the real semantic state of the event independent of RAOS extraction | **现实中这件事究竟是什么。** |
| $\widehat{Sem}(E)$ | Extracted Semantic Evidence | raw source $I$ | $\widehat{Sem}(E)=ExtractSemanticEvidence(I)$ | engineering estimate of event semantics | **RAOS 从文章里读出来“这件事是什么”。** |
| $K_t$ | Cognitive Kernel | user, time | explicit committed user state | reviewable projection of the user's current cognition | **我现在已经知道、相信、在问、在做什么。** |
| $L_t$ | Location Candidates | $E_t,K_t$ | $L_t=Locate(E_t,K_t)$ | where in the current Kernel the information may matter | **它可能落在我已有认知的哪个位置。** |
| $\Delta_t$ | Potential Cognitive Change | $E_t,K_t,L_t$ | $\Delta_t=F_\theta(E_t,K_t,L_t)$ | predicted change to user cognition if the information is correctly absorbed | **如果我真正理解这条信息，我的认知会不会发生变化、怎么变？** |
| $D(E,u)$ | Standing Attention Jurisdiction | event + user | $D(E,u)=\mathbf1[E\in\mathcal J_u]$ | whether the event belongs to a world the user wants monitored on a standing basis | **这是不是我长期希望 RAOS 替我盯着的世界里的事？** |
| $S(E)$ | Material Consequence | event | $S(E)=1$ iff some consequential shared system is materially disturbed | material disturbance to consequential shared/public systems | **这件事本身有没有实质后果？** |
| $P(E,t)$ | Collective Attention Salience | event + time | $P(E,t)=LatentSalience(R_E(\le t))$ | genuine collective-attention state within the event's objective constituency | **在它真正相关的人群里，这件事现在是不是已经明显形成了真实共同注意？** |
| $\mathcal G_E$ | Objective Attention Constituency | $Sem(E)$ | $\mathcal G_E=Constituency(Sem(E))$ | natural reference audience for judging attention penetration | **判断“大家是否在关注”时，到底应该拿哪群人当分母？** |
| $R_E(t)$ | Reference-normalized Attention Penetration | $\mathcal G_E,t$ | $R_E(t)=\frac{1}{|\mathcal G_E|}\sum_{i\in\mathcal G_E}a_i(E,t)$ | conceptual genuine-attention penetration within the correct constituency | **相关人群中，有多大比例真的把注意力放到了这件事上？** |
| $R_t$ | Runtime Context | user + time | runtime state | current task, interruption state, deadline, capacity and available attention | **现在这个时刻，我有没有条件把注意力花在它上面？** |
| $A_t$ | Attention Action / Disposition | $\Delta_t,K_t,R_t$ plus policy evidence | $A_t=\pi(\Delta_t,K_t,R_t)$ | allocation of scarce human attention | **我现在应该忽略、知道一下、继续盯着，还是认真投入？** |
| $H_t$ | Human Feedback | user interaction | observed human judgment / authorization | correction, confirmation, acceptance, rejection or modification | **人最终怎么判断、纠正和授权。** |
| $K_{t+1}$ | Next Cognitive Kernel | $K_t,H_t$ | accepted patch only | next committed cognitive state | **只有人确认过的认知变化，才真正写进下一版“我”。** |

---

# 3. Cognitive-transition language

Canonical source: `08_COGNITIVE_TRANSITION_MODEL_V2.1.md`.

## 3.1 Epistemic extraction

$$
\boxed{E_t=Extract(I_t)}
$$

with:

$$
E_t=\{Claims,Observations,Inferences,Evidence\}
$$

Physical meaning:

> Convert a raw information object into epistemically typed content rather than treating the whole document as one undifferentiated statement.

Plain language:

> **先搞清楚文章到底说了什么，而且要区分“别人说的”“我看到的”“系统推出来的”。**

---

## 3.2 Localization

$$
\boxed{L_t=Locate(E_t,K_t)}
$$

Invariant:

$$
\boxed{L_t\neq\Delta_t}
$$

Physical meaning:

> Localization identifies a cognitive neighborhood; it does not itself assert that cognition changes.

Plain language:

> **找到“这事跟我哪部分认知有关”，不等于“这部分认知已经被改变”。**

---

## 3.3 Potential cognitive change

$$
\boxed{\Delta_t=F_\theta(E_t,K_t,L_t)}
$$

$$
\Delta_t\in
\{\varnothing,
REINFORCE(k),
CHALLENGE(k),
OPEN\_NEW\}
$$

### $\varnothing$ / NONE

Physical meaning: no material cognitive change to the current Kernel.

Plain language:

> **我知道这事也可以，但它并没有改变我现在的理解。**

### $REINFORCE(k)$

Physical meaning: existing cognition remains valid and becomes stronger, richer or better supported.

Plain language:

> **我原来这么想，现在证据让我更确信、理解更扎实。**

### $CHALLENGE(k)$

Physical meaning: existing cognition should be weakened, qualified, restricted, modified or overturned.

Plain language:

> **这条信息让我原来的看法需要改。**

### $OPEN\_NEW$

Physical meaning: no existing Kernel node is the right landing point, but a meaningful new cognitive branch should be proposed.

Plain language:

> **这不是改旧认知，而是值得在脑子里新开一条分支。**

Invariant:

$$
\boxed{CognitiveChange\neq AttentionAction}
$$

---

# 4. D — Standing Attention Jurisdiction

Canonical source: `16_STANDING_ATTENTION_JURISDICTION.md`.

## 4.1 Definition

Let the user's stable Standing Radar Clauses be:

$$
\mathcal R_u=\{\rho_1,\rho_2,\ldots,\rho_n\}
$$

Then:

$$
\boxed{
\mathcal J_u
=
\{E\mid\exists\rho_i\in\mathcal R_u,\rho_i(Sem(E),u)=1\}
}
$$

and:

$$
\boxed{D(E,u)=\mathbf1[E\in\mathcal J_u]}
$$

### Physical meaning

> **Standing personal-attention field / jurisdiction.**

D asks whether the event lies inside a world the user wants RAOS to monitor continuously as a standing responsibility.

### One-sentence plain language

> **不管这条新闻今天大不大、火不火：它是不是属于我长期希望系统替我盯着的那类事？**

### D is NOT

```text
D != current importance
D != virality
D != S
D != P
D != temporary project relevance
D != keyword mention
```

Key invariants:

$$
\boxed{Mention(anchor)\neq SubstantiveMatch(anchor)}
$$

$$
\boxed{Using\ AI\ method\neq Being\ an\ AI\ event}
$$

$$
\boxed{Exclusion=ScopeGuard,\quad Exclusion\neq Veto}
$$

## 4.2 Theory vs user parameter

Very important:

$$
\boxed{D\ semantic\ law\neq\ user's\ current\ \mathcal R_u}
$$

The D definition can remain frozen while the user's Standing Radar Clauses are calibrated.

Current clarified user-profile examples from integrated adjudication:

```text
Pure power-grid / energy event
    -> OUT by default

Power-grid / energy event substantively coupled to AI/data-center compute supply
    -> may satisfy an independent AI/compute standing clause

OpenAI / DeepMind
    -> monitored for substantive research/product/model/governance/company-level events
    -> trivial internal clerical/catering/office-detail events are not automatically IN
```

These are **user-specific Standing Radar Clause calibration**, not a redefinition of D itself.

Engineering estimate:

$$
\boxed{\hat D=D\_Estimator(\widehat{Sem}(E),\mathcal R_u)}
$$

---

# 5. S — Material Consequence

Canonical source: `19_MATERIAL_CONSEQUENCE_REFERENCE_SCALE.md`.

## 5.1 Definition

Let $\mathcal G$ be the class of consequential shared/public reference systems.

Conceptually:

$$
\Delta_G(E,\tau)
=
Diff(State_G(W^E_{t+\tau}),State_G(W^{\neg E}_{t+\tau}))
$$

Then:

$$
\boxed{
S(E)=1
\iff
\exists G\in\mathcal G,\exists\tau:\
MaterialDisturbance_G(E,\tau)=1
}
$$

### Physical meaning

> **Material disturbance of consequential shared world systems.**

Possible reference systems include national/social institutions, markets, industries/fields, shared scientific/technical state, or broad culture.

### One-sentence plain language

> **把“大家关不关注”和“我关不关心”都遮住，只看这件事本身：它有没有真的改变一个值得在意的共享系统？**

Short compression:

> **这件事本身有没有实质后果？**

### S is NOT

```text
PopulationCount != S
ActorProminence != S
LargePrivateGain != S
LocalSeverity != S
ObservedMediaCoverage != S
TechnicalNovelty != S
ArtifactQuality != S
PublicAttention != S
UserInterest != S
```

Engineering estimate:

$$
\boxed{\hat S=S\_Estimator(\widehat{Sem}(E))}
$$

---

# 6. P — Collective Attention Salience

Canonical source: `22_COLLECTIVE_ATTENTION_SALIENCE.md`.

## 6.1 Objective constituency

$$
\boxed{\mathcal G_E=Constituency(Sem(E))}
$$

`\mathcal G_E` is the audience/community implied by the event semantics and must be chosen before observing current attention.

Plain language:

> **先决定“这件事本来是给谁看的/跟谁相关”，再判断这群人到底有没有在关注。**

Anti-gaming invariant:

> Never choose the denominator after seeing who is discussing the event merely to maximize apparent penetration.

## 6.2 Reference-normalized genuine attention

Conceptually:

$$
\boxed{
R_E(t)=\frac{1}{|\mathcal G_E|}\sum_{i\in\mathcal G_E}a_i(E,t)
}
$$

where $a_i$ represents genuine attention, not raw exposure.

Therefore:

$$
AbsoluteAttention\neq P
$$

$$
Exposure\neq Attention
$$

$$
ViewCount\neq Attention
$$

$$
SyntheticActivity\neq Attention
$$

## 6.3 Salience state

$$
\boxed{P(E,t)=LatentSalience(R_E(\le t))}
$$

with:

$$
\boxed{P=CurrentSalience\lor EmergingSalience}
$$

and temporal inertia:

$$
\boxed{ShortTermNegativeDerivative\neq AttentionLoss}
$$

### Physical meaning

> **Latent collective-attention state inside the event's natural reference constituency.**

### One-sentence plain language

> **在真正相关的那群人里，这件事现在是不是已经明显“占住大家的注意力”，或者正在迅速形成这种状态？**

### P is NOT

```text
P != raw views
P != raw post count
P != total-population popularity
P != sentiment
P != agreement
P != controversy
P != intrinsic importance
P != user interest
P != S
P != D
```

## 6.4 Theory vs engineering

Theory:

$$
\boxed{P(E,t)=LatentSalience(R_E(\le t))}
$$

Engineering:

$$
\boxed{
\hat P
=
Estimator(
\widehat{Sem}(E),
ConstituencyPrior,
ObservableAttentionEvidence,
History
)
}
$$

Sensor quality may change; P does not.

---

# 7. D / S / P — three reference frames

This is the shortest memory aid for the entire no-Delta AWARE model:

$$
\boxed{
D:\ user
\qquad
S:\ shared\ world
\qquad
P:\ collective\ attention
}
$$

More precisely:

| Variable | Reference frame | Ask this question |
|---|---|---|
| **D** | user's standing attention jurisdiction | **Is it in my standing world?** |
| **S** | consequential shared systems | **Did the world materially change?** |
| **P** | event's objective attention constituency | **Are the relevant people genuinely paying attention?** |

Ultra-short Chinese mnemonic:

```text
D：是不是“我的世界”
S：是不是“真有后果”
P：是不是“大家真在看”
```

Do not let one variable answer another variable's question.

---

# 8. no-$\Delta$ AWARE gate

Current frozen Phase II-B semantic gate:

$$
\boxed{
AWARE(E,u,t)
=
S(E)\land\bigl(D(E,u)\lor P(E,t)\bigr)
}
$$

### Physical meaning

> Spend a small amount of human attention on a no-cognitive-change event only if the event has real material consequence and it either belongs to the user's standing monitored world or has become genuinely salient in its natural constituency.

### One-sentence plain language

> **这事本身得真有点分量，而且要么是我长期关心的世界里的事，要么已经成为相关人群正在共同关注的大事；满足这些才值得让我“知道一下”。**

### AWARE means

```text
Situational awareness
without cognitive commitment
without Kernel write
without continuing WATCH obligation
with low human attention cost
```

---

# 9. Attention actions

Canonical cognitive source: `08_COGNITIVE_TRANSITION_MODEL_V2.1.md`.

| Action | Physical meaning | Plain language |
|---|---|---|
| `DROP` | allocate no further human attention now | **不用管。** |
| `AWARE` | low-cost situational awareness, no cognitive commitment | **知道有这回事就够了。** |
| `WATCH` | preserve future option value; RAOS assumes monitoring responsibility | **现在不用深看，但系统替我继续盯着。** |
| `ENGAGE` | serious present human cognitive investment | **现在值得认真读、想、验证或行动。** |

Invariant:

$$
\boxed{WATCH\neq MediumImportance}
$$

Useful interpretation:

$$
\boxed{WATCH=Preserve\ Valuable\ Optionality}
$$

---

# 10. Human authority and cognition state

RAOS may estimate cognitive change but may not silently commit it.

If no reviewed patch is accepted:

$$
K_{t+1}=K_t
$$

If a reviewed KernelPatch is accepted/modified:

$$
K_{t+1}=ApplyAcceptedPatch(K_t)
$$

Plain language:

> **RAOS 可以说“我认为你应该改变这个认知”，但只有你确认后，它才能成为下一版你的正式认知状态。**

---

# 11. Sensor Front-End language

Canonical source: `33_SEMANTIC_EVIDENCE_EXTRACTION_FRONT_END.md`.

The real event has latent semantics:

$$
\boxed{Sem^*(E)}
$$

RAOS only observes raw information $I$ and constructs:

$$
\boxed{\widehat{Sem}(E)=ExtractSemanticEvidence(I)}
$$

Current candidate `SemanticEvidenceFrame` contains evidence-oriented fields such as:

```text
EventIdentity
EventSummary
SubstantiveActorsObjects
ActionsAndChanges
AffectedSystemsOrPopulations
ScopeEvidence
TemporalContext
SourceSupport
UncertaintyAndMissingness
```

Important separation:

```text
SemanticEvidenceFrame contains evidence.
It does NOT contain D/S/P answers.
```

Engineering chain:

$$
\boxed{
I
\rightarrow
\widehat{Sem}(E)
\rightarrow
(\hat D,\hat S,\hat P)
\rightarrow
\hat A
}
$$

Current research question:

> **How much decision quality is lost when RAOS must recover the semantic evidence itself from raw articles/posts/papers rather than receiving clean human-written event facts?**

---

# 12. Theory / user state / sensor / estimator / policy — do not mix these layers

| Layer | Examples | Can change without changing the others? |
|---|---|---|
| **Theory / semantic variable** | $D,S,P,\Delta$ | Yes, but only with explicit semantic re-open and evidence |
| **User state / parameters** | $K_t,\mathcal R_u$ | Yes; personalization normally happens here |
| **Sensor representation** | $\widehat{Sem}(E)$, P Evidence Packet | Yes; better extraction/telemetry must not redefine theory |
| **Estimator** | $\hat D,\hat S,\hat P$ | Yes; prompts/models/algorithms may improve |
| **Policy** | $A_t$, frozen no-$\Delta$ AWARE gate | Yes, but policy changes require separate evidence |
| **Human committed state** | $K_{t+1}$ | Changes only through human-authorized Kernel evolution |

Key meta-invariant:

$$
\boxed{
BadSensor\not\Rightarrow ChangePhysics
}
$$

and:

$$
\boxed{
EstimatorError\not\Rightarrow SemanticError
}
$$

and:

$$
\boxed{
UserCalibration\not\Rightarrow UniversalTheoryChange
}
$$

---

# 13. Current status snapshot

```text
Cognitive Transition v2.1        FROZEN / CLOSED BASELINE
Delta semantics                  FROZEN
D semantic definition            FROZEN / CLOSED
User Standing Radar clauses      ACTIVE CALIBRATION
S semantic definition            FROZEN / CLOSED
S estimator v1                   ACCEPTED in controlled validation
P semantic definition            FROZEN / CLOSED
P estimator v1                   ACCEPTED in controlled validation
no-Delta AWARE gate              FROZEN semantic baseline
Partial UNKNOWN determinacy      v1.1 implemented
Semantic Evidence Extraction     ACTIVE — CURRENT FRONTIER
```

Do not infer open-world production accuracy from controlled clean-semantic validation.

---

# 14. Canonical source index

| Concept | Canonical source |
|---|---|
| Cognitive Kernel / $E_t,L_t,\Delta_t,A_t$ | `08_COGNITIVE_TRANSITION_MODEL_V2.1.md` |
| Attention-policy elicitation / AWARE semantics | `10_ATTENTION_POLICY_ELICITATION_AND_CALIBRATION.md` |
| D — Standing Attention Jurisdiction | `16_STANDING_ATTENTION_JURISDICTION.md` |
| S — Material Consequence | `19_MATERIAL_CONSEQUENCE_REFERENCE_SCALE.md` |
| P — Collective Attention Salience | `22_COLLECTIVE_ATTENTION_SALIENCE.md` |
| P Evidence Packet / estimator modeling | `23_COLLECTIVE_ATTENTION_ESTIMATOR_MODELING.md`, `24_COLLECTIVE_ATTENTION_EVIDENCE_INTERFACE.md` |
| Semantic Evidence Extraction | `33_SEMANTIC_EVIDENCE_EXTRACTION_FRONT_END.md` |
| Current integrated adjudication history | `34_INTEGRATED_NO_DELTA_AWARE_ROUND2_ADJUDICATION.md` |

---

# 15. The three lines to remember when everything else is forgotten

If only three things survive human memory, remember these:

$$
\boxed{\Delta:\ \text{这条信息会怎么改变我的认知？}}
$$

$$
\boxed{D/S/P:\ \text{我的世界？真有后果？大家真在看？}}
$$

$$
\boxed{A:\ \text{我现在应该花多少注意力？}}
$$

And for the engineering philosophy:

$$
\boxed{\text{不能因为传感器差，就修改物理定律。}}
$$
