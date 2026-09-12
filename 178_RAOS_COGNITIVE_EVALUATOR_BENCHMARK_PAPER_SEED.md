# RAOS Cognitive Evaluator Benchmark — Paper Seed

**Status:** RESEARCH SEED / ABSTRACT + INTRODUCTION + RELATED WORK DRAFT  
**Date:** 2026-09-12  
**Origin:** Derived from RAOS failure analysis and evaluator-capacity experiments, especially Phase 10D.6L / 10D.6K; intended to evolve independently from the RAOS system paper.  
**Working scope:** state-conditioned, evidence-grounded cognitive reasoning and downstream decision consequences.

## 0. Working titles

1. **What Does This Evidence Mean to Me Now? Benchmarking State-Conditioned Cognitive Reasoning in LLMs**
2. **From Evidence to Attention: Benchmarking State-Conditioned, Evidence-Grounded Cognitive Reasoning**
3. **Beyond Fact Verification: Benchmarking Evidence Interpretation under Persistent Cognitive State**
4. **RAOS-CogEval: A Benchmark for State-Conditioned Evidence Reasoning and Decision Consequences**

The benchmark name is deliberately provisional. The paper should not depend on the RAOS implementation name; RAOS is the empirical origin and one downstream decision environment, not a required runtime for benchmark participants.

## 1. Research origin — why this benchmark exists

This benchmark was not designed top-down by inventing a list of desirable LLM skills. It emerged bottom-up while debugging a real cognitive information system. RAOS repeatedly produced cases in which the final Attention decision looked wrong or unstable. To localize the cause, the end-to-end path was decomposed into progressively narrower responsibilities:

```text
Evidence
  -> Relation Mapping
  -> Support Binding
  -> Grounding
  -> Jurisdiction / Authority
  -> Attention
```
Each decomposition step exposed a distinct capability that can be evaluated independently. Relation Mapping became a task of deciding whether evidence REINFORCES, CHALLENGES, opens a new branch, or has no material relation to a cognitive proposition. Support Binding became a provenance task: given a frozen relation, identify the exact evidence units that license it. Grounding became an evidence-sufficiency task: determine whether the bound support is DIRECT, PARTIAL, INSUFFICIENT, or contradicts the claimed operation. OPEN_NEW admission exposed a separate jurisdiction question: even if a new branch is evidentially real, does it belong to the receiver's current cognitive domain?

The key methodological lesson from this debugging process is that benchmark tasks should correspond to **failure-bearing responsibilities**. Every proposed task has a concrete downstream failure mode if solved incorrectly: false relation creation, unsupported provenance, overconfident grounding, spurious domain admission, attention inflation, false dropping, or an unjustified cognitive update.

This origin matters. The benchmark is therefore not a generic checklist of LLM capabilities. It is an attempt to evaluate the specific reasoning chain required by systems that maintain persistent cognitive state and must decide what new evidence means relative to that state.

### 1.1 A central empirical lesson from Phase 10D.6L

A weak evaluator initially appeared simply "too permissive": it repeatedly mapped strong-reference PARTIAL judgments to DIRECT. However, two apparently critical OPEN_NEW errors disappeared completely once the evaluator was given the full semantics of the candidate jurisdiction anchors rather than opaque anchor IDs. This led to the working principle:

```math
Evaluator\ Quality
=
Model\ Capability
+
Task\ Information
+
Decision\ Policy
```

This should be preserved as a benchmark-design principle. A model should not be declared incapable when the task withholds information necessary for the judgment. Conversely, supplying sufficient task state does not eliminate evaluator-policy bias: models may still exhibit stable liberal, conservative, or otherwise asymmetric decision policies near uncertain boundaries.

### 1.2 Stable evaluator bias is signal, not only noise

DeepSeek-Flash behaved non-randomly. Under incomplete or borderline evidence it showed a stable permissive tendency, often granting DIRECT where the stronger reference judged PARTIAL. This is analogous to variation among human reviewers: some grant the benefit of the doubt, while others reject when proof is incomplete.
A permissive evaluator is not necessarily useless. It may provide high recall in candidate-generation or SCAN settings, while a stricter evaluator may be preferable for high-risk authorization, ENGAGE escalation, or Kernel mutation. The benchmark should therefore characterize evaluator profiles rather than compress every behavior into one scalar accuracy score.

This motivates a strict separation:

```text
Architecture Contract
  = stable task semantics and authority boundaries

Evaluator
  = replaceable model or human judge

Execution Policy
  = how evaluators are deployed under cost / latency / risk constraints
```

A model-specific "personality" must never be written into the architecture contract. Models can change; the contract should not. This is the same RAOS discipline summarized as: **do not change the physical law because the sensor is weak.**

## 2. Core benchmark thesis

Most existing evaluations ask whether a model can answer a question, verify a claim, cite evidence, or judge another response. A persistent cognitive system must answer a different question:

> **What does this evidence mean relative to what the receiver currently knows, believes, prioritizes, and is trying to resolve?**

We represent the core problem as:

```math
(E, K_t) \rightarrow R_t \rightarrow D_t
```

where `E` is new evidence, `K_t` is the receiver's current cognitive state, `R_t` is the cognitive relation induced by the evidence, and `D_t` is a downstream decision such as attention allocation.

The central counterfactual is:

```math
E\ \text{fixed},\quad K_0 \ne K_1
\quad\Rightarrow\quad
R(E,K_0) \ne R(E,K_1)
```
A concrete example is the RS05 counterfactual now being prepared in Phase 9A. The same observation — that a small 64x64 bf16 matmul+add workload is overhead-bound — should CHALLENGE a state that believes computation dominates runtime, but REINFORCE a later state that has assimilated the overhead-dominated explanation. The external evidence is unchanged; the receiver has changed. A benchmark that does not represent `K_t` cannot express this distinction.

A second core dimension is **decision consequence**. Evaluator disagreement matters differently depending on whether it is absorbed downstream or changes behavior:

```math
Evaluator\ Error \rightarrow Decision\ Consequence
```

Phase 10D.6K already showed both regimes: reviewer-policy disagreement changed final Attention on boundary cases, while a strong direct technical case remained behaviorally stable across weak and strong evaluators. This suggests that a useful benchmark should measure not only local judgment accuracy but also the downstream sensitivity of a cognitive decision system to those errors.

## 3. Draft Abstract

Large language models are increasingly used not only to answer questions but also to evaluate evidence, judge other model outputs, and mediate decisions in systems with persistent state. Existing benchmarks separately study fact verification, citation attribution, grounded generation, evidence sufficiency, and LLM-as-a-judge reliability. However, they largely evaluate evidence against a fixed claim or request. In a persistent cognitive system, the meaning of new evidence is **state-conditioned**: the same observation may challenge one cognitive state, reinforce a later state that has assimilated it, or be irrelevant to another.

We propose **RAOS-CogEval** (working name), a benchmark for state-conditioned, evidence-grounded cognitive reasoning and its downstream decision consequences. The benchmark is derived from causal failure analysis of a real research-attention system rather than from a top-down capability checklist. It decomposes evaluation into relation mapping, support binding, evidence-sufficiency grounding, cognitive-jurisdiction admission, state counterfactuals, and decision robustness. This decomposition enables us to distinguish model capability from missing task information and from stable evaluator policy biases such as permissive or conservative judgment.
Preliminary RAOS studies motivate two hypotheses that the benchmark is designed to test systematically. First, evaluator quality is a joint function of model capability, task information, and decision policy rather than model scale alone. Second, evaluator errors are not equally consequential: disagreements may strongly perturb attention on boundary cases yet be absorbed for direct, high-signal evidence. The benchmark therefore evaluates both **local cognitive judgments** and their **behavioral consequences** under controlled changes to cognitive state and evaluator policy. We aim to provide a model-independent testbed for selecting and composing LLM evaluators in persistent cognitive systems, and for studying when stronger evaluation is actually necessary.

> **Abstract status:** wording is intentionally conservative. Replace “preliminary RAOS studies” with final quantitative claims only after the benchmark dataset, model panel, and held-out evaluation are frozen.

## 4. Draft Introduction

### 4.1 From answering questions to interpreting evidence for a persistent mind

The standard evaluation picture for large language models is largely stateless. A model receives a question, claim, document, or candidate answer and is scored against a fixed target. This abstraction has enabled rapid progress in knowledge, reasoning, factuality, retrieval, and evaluation. Yet an emerging class of AI systems maintains persistent state about a user, project, organization, or agent: what is currently believed, what remains uncertain, what goals are active, and which questions are unresolved.

For such systems, the central problem is not merely whether a new statement is true. It is whether that statement changes anything **relative to the current state of cognition**. A paper reporting that launch overhead dominates a small GPU workload may be highly salient when the system currently believes computation dominates, but much less cognitively novel after that finding has already been assimilated. The information source is identical; the correct interpretation is not.

This motivates a state-conditioned view of cognitive reasoning. Let `E` denote incoming evidence and `K_t` a persistent cognitive state. Rather than predicting a fixed label from `E` alone, a cognitive evaluator must estimate a relation `R(E,K_t)` such as reinforcement, challenge, new-branch creation, or no material relation. Downstream systems may then use this relation to allocate attention, request verification, update state, or defer action.

### 4.2 Why existing evaluation slices are necessary but insufficient

Several established benchmark families evaluate important pieces of this problem. Fact-verification benchmarks test whether claims are supported, refuted, or lack sufficient evidence. Citation and grounded-generation benchmarks test whether outputs are attributable to source material. Evidence-sufficiency benchmarks test whether models know when context is partial, irrelevant, absent, or conflicting. LLM-as-a-judge benchmarks test whether models can reliably evaluate other model outputs.
These lines of work provide crucial primitives, but they usually hold the proposition or user request fixed. They do not ask whether the *same evidence* should induce a different relation after the receiver's persistent cognitive state changes. Nor do they typically measure how a local evaluator error propagates into an attention or state-update decision.

We argue that these omissions matter for deployed cognitive systems. A model can achieve high static fact-verification accuracy yet fail to use current cognitive state. Conversely, two evaluators can disagree substantially on evidence sufficiency while inducing the same downstream decision for strong-signal cases. Evaluator selection therefore requires more than a leaderboard score: it requires understanding **what kind of error a model makes, under what information conditions, and whether that error matters downstream**.

### 4.3 Benchmark from failure analysis, not capability brainstorming

RAOS-CogEval originates from a sequence of controlled debugging experiments in a persistent research-attention system. When end-to-end decisions appeared wrong, we progressively isolated the earliest causal layer responsible for the discrepancy. This process produced a natural task decomposition:

1. **Relation Mapping:** given evidence and cognitive state, identify material cognitive relations.
2. **Support Binding:** given a frozen relation, identify the evidence units that license it.
3. **Grounding / Evidence Sufficiency:** judge whether the bound evidence directly, partially, insufficiently, or contradictorily supports the relation.
4. **Jurisdiction:** for a genuinely new branch, determine whether it belongs to the supplied cognitive domain.
5. **State Counterfactual:** hold evidence fixed while changing cognitive state, and test whether relation topology changes in the preregistered direction.
6. **Decision Consequence:** measure whether evaluator differences propagate into downstream attention or other authorized actions.

This decomposition is intentionally model-independent. It specifies what must be judged and which information must be available, but not how many LLM calls, agents, rules, or ensembles an implementation must use.

### 4.4 Evaluator quality has three sources

A recurring empirical finding is that evaluator behavior cannot be interpreted as model capability in isolation. In one RAOS study, a weak evaluator appeared to make serious jurisdiction errors when shown only opaque anchor identifiers. Once the full anchor semantics were supplied, it matched the strong reference on every repeated jurisdiction trial. In other tasks, however, the same evaluator retained a stable permissive bias near evidence-sufficiency boundaries even when task information was complete.
We summarize this distinction as:

```math
Evaluator\ Quality
=
Model\ Capability
+
Task\ Information
+
Decision\ Policy.
```

This formulation has practical consequences for benchmark construction. Missing task state should be treated as an instrumentation defect, not evidence of model incapability. At the same time, systematic liberal or conservative evaluator tendencies should be measured rather than averaged away as noise. Such tendencies may be useful under different execution policies: a recall-oriented evaluator may be desirable for candidate discovery, while a precision-oriented evaluator may be preferable before costly or irreversible actions.

### 4.5 From local accuracy to behavioral robustness

The final benchmark layer asks whether evaluator errors matter. We define this as a controlled propagation problem:

```math
Evaluator\ output
\rightarrow
Cognitive\ decision
```

Preliminary RAOS measurements provide both possible outcomes. On boundary cases, a permissive evaluator can inflate final attention relative to a stronger evaluator. On a direct technical case with strong evidence, weak and strong evaluators can disagree internally yet converge to the same final attention. This distinction motivates **decision robustness** as a first-class metric rather than an afterthought.

### 4.6 Intended contributions

The paper currently targets the following contributions; these should be narrowed after full dataset construction and experiments:

- A benchmark formulation for **state-conditioned evidence interpretation**, where the correct cognitive relation depends on a persistent and mutable cognitive state.
- A failure-derived task decomposition spanning relation mapping, provenance binding, evidence sufficiency, jurisdiction, state counterfactuals, and downstream decision robustness.
- An evaluation framework that separates **model capability**, **task-information sufficiency**, and **evaluator decision policy**.
- Metrics that characterize evaluator profiles (e.g., permissiveness, abstention, precision/recall asymmetry, stability) in addition to aggregate accuracy.
- A downstream robustness protocol that measures whether local evaluator disagreements actually change attention or authorized cognitive actions.
- A multi-model empirical study to determine which current LLMs are suitable for different evaluator roles in persistent cognitive systems.
## 5. Draft Related Work

### 5.1 Fact verification: FEVER and AVeriTeC

**FEVER** (Thorne et al., 2018) established a large-scale formulation of textual fact verification in which claims are labeled `SUPPORTED`, `REFUTED`, or `NOT ENOUGH INFO`, with evidence sentences recorded for supported/refuted claims. This is closely related to RAOS targeted Grounding: an incoming evidence unit may reinforce or challenge an existing proposition, or fail to justify either relation. FEVER also makes an important methodological point for our setting: verdict accuracy alone is not enough when the supporting evidence is wrong.

**AVeriTeC** extends automated fact checking toward real-world claims and web evidence. Its evaluation considers a claim correctly verified only when both the verdict is correct and the retrieved evidence passes a quality threshold. This joint treatment of verdict and evidence is particularly relevant to the RAOS separation between Relation Mapping, Support Binding, and Grounding.

The key difference is the object being verified. FEVER/AVeriTeC ask whether evidence supports a claim whose semantics are fixed for the example. RAOS-CogEval asks what relation evidence bears to a **persistent receiver state**, and includes counterfactual pairs where the same evidence should challenge `K0` but reinforce `K1`. Thus the benchmark is not merely claim verification with different labels; the reference state itself is an experimental variable.

### 5.2 Citation attribution: ALCE

**ALCE** (Gao et al., 2023) evaluates end-to-end systems that retrieve supporting evidence and generate answers with citations, using metrics for fluency, correctness, and citation quality. ALCE is strongly related to the Support Binding component of RAOS-CogEval: a semantic judgment should be inspectable through explicit provenance rather than justified only by free-form model rationale.

Our focus differs in two ways. First, Support Binding is deliberately downstream of a frozen cognitive relation, allowing provenance quality to be measured without permitting the binder to silently create, delete, or retarget the relation. Second, citation correctness is not the endpoint: bound support is subsequently evaluated for sufficiency and can affect downstream cognitive decisions.

### 5.3 Grounded generation: FACTS Grounding

**FACTS Grounding** (Google DeepMind, 2024; later incorporated into the FACTS Benchmark Suite) evaluates whether long-form model responses remain fully attributable to provided documents. Its evaluation design is especially relevant because it uses multiple frontier LLM judges and aggregates their judgments to reduce single-judge bias.
FACTS is therefore relevant both technically and methodologically: it treats grounding as a first-class capability and acknowledges that evaluator choice can itself bias benchmark outcomes. RAOS-CogEval adopts the same caution but studies a different target: not whether a generated answer is grounded in a document, but whether a proposed cognitive relation is grounded in evidence relative to a persistent state.

### 5.4 Evidence sufficiency and abstention calibration

The 2026 **Evidence Sufficiency Benchmark** (Zhang and Wu, 2026) directly studies whether LLMs know when provided evidence is sufficient to answer. It constructs five conditions: full support, partial support, irrelevant evidence, no context, and conflicting evidence, and evaluates answer/abstention behavior. The reported results show substantial over-answering under insufficient and conflicting evidence and systematic difficulty near the sufficiency boundary.

This work is extremely close to the RAOS Grounding problem. Our `DIRECT / PARTIAL / INSUFFICIENT / CONTRADICTS_OPERATION` taxonomy likewise separates evidence that fully licenses a relation from evidence that is merely suggestive, inadequate, or directionally inconsistent. The stable permissive behavior observed in our Flash experiments — especially `PARTIAL -> DIRECT` inflation — should be interpreted in this broader context of evidence-sufficiency calibration rather than as an isolated model quirk.

RAOS-CogEval extends this idea in two directions. First, sufficiency is evaluated for a **cognitive relation to a current state**, not only whether a question should be answered. Second, we measure the cost of over-acceptance downstream: does a permissive sufficiency judgment merely change an internal label, or does it inflate Attention, authorize a patch, or suppress abstention?

### 5.5 LLM-as-a-judge: JudgeBench and evaluator-policy bias

**JudgeBench** (Tan et al., ICLR 2025) evaluates LLM-based judges on challenging response pairs spanning knowledge, reasoning, mathematics, and coding, emphasizing objective correctness rather than only agreement with human preference. Its central premise — that model capability and judge capability are distinct — directly motivates RAOS-CogEval's evaluator layer.

Our experiments add a complementary concern: a judge can be internally consistent yet systematically permissive or conservative. Such behavior should be characterized as an evaluator policy profile, not automatically dismissed as noise. In persistent cognitive systems, the same bias can have different value under different execution policies: permissiveness may improve recall during scanning, while strictness may reduce false-positive authorization before costly actions.

RAOS-CogEval therefore treats judge reliability not only as pairwise ranking accuracy but as **calibrated evidence judgment under explicit task state**, together with downstream behavioral consequences.

### 5.6 What remains missing across these benchmarks

Taken together, FEVER/AVeriTeC, ALCE, FACTS Grounding, Evidence Sufficiency Benchmark, and JudgeBench cover much of the local capability surface required by RAOS. However, they do not jointly capture the two dimensions that motivate this work:

1. **State-conditioned correctness:** the same evidence can have a different correct cognitive relation after the receiver's state changes.
2. **Decision consequence:** evaluator errors can be amplified, absorbed, or transformed by downstream cognitive policy.
A compact positioning table for the eventual paper:

| Benchmark / family | Evidence support | Provenance / citation | Sufficiency / abstention | Judge reliability | Mutable cognitive state | Downstream decision consequence |
|---|---:|---:|---:|---:|---:|---:|
| FEVER | Yes | Yes | NEI | No | No | No |
| AVeriTeC | Yes | Yes | Evidence-quality gate | No | No | No |
| ALCE | Yes | Strong | Indirect | No | No | No |
| FACTS Grounding | Strong | Grounding attribution | Eligibility + grounding | Multi-judge methodology | No | No |
| Evidence Sufficiency Benchmark | Yes | Context given | Strong | No | No | No |
| JudgeBench | Indirect | No | No | Strong | No | No |
| **RAOS-CogEval (proposed)** | Strong | Explicit Support Binding | Strong | Evaluator-profile analysis | **Yes** | **Yes** |

**Novelty caution:** this table reflects the closest benchmarks identified in the current survey, not an exhaustive novelty proof. Before paper submission, run a dedicated literature review on personalized agents, belief-state tracking, longitudinal memory evaluation, belief revision, epistemic reasoning, user-model-conditioned QA, and decision-focused evaluation. The contribution should be narrowed if prior work already covers state-conditioned relation reversal or evaluator-to-decision propagation.

## 6. Benchmark task skeleton — to become Method

### Task A — Relation Mapping

Input:

```text
Audited evidence units E
Current cognitive state K
Candidate / located cognitive propositions
```

Output:

```text
REINFORCE(target)
CHALLENGE(target)
OPEN_NEW
NONE
```

Primary metrics: exact relation set, target accuracy, operation confusion, false relation rate, OPEN_NEW precision/recall, repeated-sample stability.

### Task B — Support Binding

Freeze the relation first. The model may only attach evidence IDs and optional jurisdiction anchors. It may not create, delete, merge, retarget, or change relation polarity. Metrics include exact support-set accuracy, core-support recall, unknown-ID rate, topology-preservation invariants, and repeated-signature stability.
### Task C — Grounding / Evidence Sufficiency

Input: frozen relation, exact support units, and target proposition when applicable. Output:

```text
DIRECT
PARTIAL
INSUFFICIENT
CONTRADICTS_OPERATION
```

Metrics should include macro accuracy, ordinal confusion, `PARTIAL -> DIRECT` over-acceptance, `DIRECT -> INSUFFICIENT` over-rejection, abstention behavior, and stability. This task should explicitly distinguish a model that is wrong randomly from one that has a stable permissive or conservative policy.

### Task D — OPEN_NEW Jurisdiction

Input: frozen OPEN_NEW branch semantics plus **full semantic descriptions** of candidate cognitive anchors. Opaque IDs alone are invalid instrumentation. Output: admitted jurisdiction or insufficient jurisdiction. This task is logically separate from Grounding even if a production implementation evaluates both fields in one model call.

### Task E — Kernel Counterfactual / State-Conditioned Cognition

Construct paired or triplet examples that hold evidence fixed while changing only the cognitive state:

```text
(E, K0) -> CHALLENGE
(E, K1 after assimilation) -> REINFORCE
```

Additional interventions can change standing importance while preserving proposition semantics, testing whether relation topology stays fixed while downstream attention changes. Metrics should test directional counterfactual consistency, not merely independent accuracy on each arm.

### Task F — Downstream Decision Robustness

Feed controlled evaluator outputs into the same frozen downstream policy and measure whether local disagreement changes final behavior. Candidate outputs include `DROP / AWARE / WATCH / ENGAGE`, patch authorization, or other explicitly versioned actions.

Important quantities include evaluator-to-decision sensitivity, false ENGAGE inflation, false DROP rate, and robustness on strong-signal cases.

## 7. Experimental design skeleton

The benchmark should deliberately include both **micro-capability evaluation** and **system-level propagation**. A likely experimental matrix is:

```text
Models x Tasks x Information Conditions x Reviewer Policy Conditions
```

Candidate model panel: strongest available frontier models, mid-tier/fast models, representative open models, and optionally human expert adjudication on a bounded subset. The exact panel must be frozen near submission time because model availability changes rapidly.
Key controlled axes should include:

- **Task-information sufficiency:** full semantic context vs intentionally under-specified context, with the latter treated as a diagnostic condition rather than the benchmark default.
- **Evaluator policy:** natural model behavior plus carefully designed strict/permissive prompting only if preregistered; avoid conflating prompt policy with intrinsic model capability.
- **Cognitive state:** frozen `K0`, semantically assimilated `K1-S`, importance-only `K1-I`, and later broader state counterfactuals.
- **Evidence quality:** direct, partial, irrelevant, missing, and conflicting support, while preserving realistic task semantics.
- **Downstream risk:** low-cost awareness versus high-cost engagement or state mutation.

### 7.1 Results already motivating the benchmark

These are **motivation results**, not yet the final benchmark table:

- In Phase 10D.6L.3, decoupled Support Binding preserved frozen relation identity in 42/42 weak-model calls, demonstrating that architectural responsibility separation can prevent the binder from rewriting upstream semantics even when evidence selection is imperfect.
- In Phase 10D.6L.4, the weak evaluator was highly stable but permissive, with many strong-reference `PARTIAL` items classified as `DIRECT`. Stability therefore did not imply calibrated strictness.
- In Phase 10D.6L.4J, two apparent critical jurisdiction failures disappeared when full anchor semantics were provided: both cases matched the strong reference in 3/3 repeats. This is the empirical origin of the `Model Capability + Task Information + Decision Policy` decomposition.
- In Phase 10D.6K, weak-vs-strong evaluator policy changed final Attention on boundary cases but converged on the strong N4 technical case. This motivates measuring downstream consequence rather than only local evaluator agreement.
- Phase 9A supplied the first explicit Kernel counterfactual. With identical frozen RS05 evidence, K0 produced `CHALLENGE_ONLY 12/12`, while an accepted semantic-assimilation Kernel K1-S produced `REINFORCE_ONLY 12/12`. Raw-polarity JSD was `1.0` bit and exceeded the preregistered 5000-permutation null gate (`p=0.00019996`). A separate importance-only K1-I replay preserved relation topology exactly while changing Attention `ENGAGE -> AWARE` in `12/12` pairs. This is the first controlled evidence for state-conditioned relation reversal plus downstream causal separation.

### 7.2 Important negative result to preserve

Do **not** define the benchmark as “strong model = gold, weak model = wrong.” Strong-model/manual judgments are currently architecture-capability references, not infallible truth. Gold construction for the eventual benchmark should use explicit adjudication procedures, complete task state, provenance inspection, and where possible deterministic or domain-expert validation.

The benchmark should be able to discover useful weak-model profiles. A high-recall permissive model can be desirable in candidate-generation settings even if it should not be the sole authority before irreversible decisions.

## 8. Paper narrative in one paragraph

Modern LLM benchmarks ask whether a model knows facts, reasons correctly, cites evidence, stays grounded, or judges another answer. Persistent cognitive agents face an additional problem: **the meaning of new evidence depends on the state of the receiver**. We discovered this not by inventing a benchmark but by debugging a real research-attention system. Each causal failure exposed a distinct evaluator responsibility, and model disagreements revealed that evaluator quality depends jointly on model capability, information supplied by the task, and decision policy. The resulting benchmark evaluates local evidence reasoning, counterfactual changes under mutable cognitive state, and whether evaluator errors actually propagate into downstream decisions. In short: the benchmark asks not only “Is this evidence true?” but “What does this evidence mean to me now, and what happens if the evaluator gets that meaning wrong?”
## 9. Motivation freeze — 中文研究笔记（不要在后续 polished paper 中丢掉）

这篇 benchmark 最初不是因为“我们想做一个 benchmark”，而是因为 RAOS 在真实调试中不断出现：**最终 Attention 看起来不对，但不知道究竟是哪一层错了。** 为了归因，我们才把 cognition path 一层层拆开。结果每拆开一层，就自然得到一个可独立评测的模型能力。

真正让我认为它值得单独写论文的转折点有三个。

第一，Flash 并不是随机出错，而是稳定偏宽松。这意味着 evaluator 可能像人类 reviewer 一样存在稳定 decision policy。宽松不一定是坏事：它可能意味着高 recall，适合 SCAN / candidate discovery；严格 reviewer 则可能更适合高风险 authorization。因此 benchmark 不应只给一个总 accuracy，而应刻画 evaluator profile。

第二，我们差点把 Flash 的两个 OPEN_NEW jurisdiction 错误判成“弱模型能力不行”，但继续追查发现输入只给了 `P2/G1` 这样的 opaque code，没有给完整认知区语义。补齐情报后，Flash 两个 case 都 3/3 判断正确。这个过程给出了一个非常重要的 benchmark 方法论：

```math
Evaluator\ Quality
=
Model\ Capability
+
Task\ Information
+
Decision\ Policy
```

所以，**也不能不给传感器必要输入，然后怪传感器测错。** Benchmark 自己必须先保证任务信息充分。

第三，也是最重要的一点，是 Phase 9A 所代表的 Kernel counterfactual：同一条外界 evidence 不变，仅仅因为“我已经改变了”，正确 relation 就应该从 CHALLENGE 变成 REINFORCE。这说明我们真正要测的不是 static fact verification，而是：

> **这条信息，对现在的我意味着什么？**

如果这个 benchmark 最终成立，它研究的不是一个孤立 LLM 技能，而是一种更接近长期智能体/认知系统的能力：Evidence 必须相对于 persistent cognitive state 被解释，而且 evaluator 的局部误差还要继续追踪到真实 downstream consequence。

因此论文最值得坚持的主线不是“RAOS 有很多模块”，而是：

```text
Static evaluation asks:
  Is this claim supported?

State-conditioned cognitive evaluation asks:
  Given what I currently know/believe/care about,
  what does this evidence change?
```
## 10. Related-work references verified for this seed

- Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). **FEVER: a Large-scale Dataset for Fact Extraction and VERification.** NAACL 2018. ACL Anthology: https://aclanthology.org/N18-1074/
- Schlichtkrull, M., Chen, Y., Whitehouse, C., Deng, Z., Akhtar, M., Aly, R., Guo, Z., Christodoulopoulos, C., Cocarascu, O., Mittal, A., Thorne, J., & Vlachos, A. (2024). **The Automated Verification of Textual Claims (AVeriTeC) Shared Task.** FEVER 2024. https://aclanthology.org/2024.fever-1.1/
- Gao, T., Yen, H., Yu, J., & Chen, D. (2023). **Enabling Large Language Models to Generate Text with Citations.** EMNLP 2023. https://aclanthology.org/2023.emnlp-main.398/
- Google DeepMind FACTS Team. (2024). **FACTS Grounding: A new benchmark for evaluating the factuality of large language models.** https://deepmind.google/blog/facts-grounding-a-new-benchmark-for-evaluating-the-factuality-of-large-language-models/
- Google DeepMind. (2025). **FACTS Benchmark Suite: Systematically evaluating the factuality of large language models.** https://deepmind.google/blog/facts-benchmark-suite-systematically-evaluating-the-factuality-of-large-language-models/
- Zhang, H., & Wu, W. (2026). **Do LLMs Know When Evidence is Insufficient? An Evidence Sufficiency Benchmark for Answer-Abstention Calibration in Retrieval-Augmented Generation.** Computers, Materials & Continua, 89(1), 69. DOI: 10.32604/cmc.2026.086343.
- Tan, S., Zhuang, S., Montgomery, K., Tang, W., Cuadron, A., Wang, C., Popa, R., & Stoica, I. (2025). **JudgeBench: A Benchmark for Evaluating LLM-Based Judges.** ICLR 2025. https://proceedings.iclr.cc/paper_files/paper/2025/hash/9e720fce64f91114c49cfd640d821da3-Abstract-Conference.html

## 11. Next paper work — intentionally deferred

Do not interrupt Phase 9A merely to polish this draft. The next high-value evidence for the benchmark paper is the preregistered Kernel counterfactual itself. After Phase 9A, update this document with the first controlled `E fixed, K changed` result.

Before claiming novelty or preparing submission:

1. Run a systematic literature search on longitudinal/persistent-memory agents, belief revision, user modeling, personalized QA, epistemic-state tracking, and decision-focused evaluation.
2. Define benchmark dataset construction independently of RAOS implementation internals.
3. Freeze gold/adjudication protocol and held-out split before broad model evaluation.
4. Evaluate a diverse model panel and characterize evaluator profiles rather than only ranking by one aggregate score.
5. Separate benchmark paper claims from RAOS system paper claims; RAOS is the source of failure-derived tasks and one downstream decision environment, not the benchmark's required architecture.
