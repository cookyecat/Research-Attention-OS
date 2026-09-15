# RAOS Canonical Architecture — HEAD Contract

Status: **AUTHORITATIVE LIVING DOCUMENT**

This file describes the architecture that the current repository HEAD is intended to execute.
It is not a historical result log. Numbered research documents explain *why* the architecture changed; this file states *what the architecture is now*.

## Maintenance rule

Any commit that changes a RAOS module, responsibility boundary, main data flow, Attention decision path, or research/online semantic contract **must update this file in the same commit**.

If code and this document disagree, the mismatch is an architecture defect to be resolved explicitly; neither side silently wins.

## 1. System objective

RAOS maintains a changing model of the outside information world and allocates scarce human attention relative to a changing cognitive state.

### 1.1 Product operating doctrine

RAOS should observe the world as broadly as practical, understand genuinely new arrivals automatically, and disturb the human as little as possible.

```text
Observe broadly.
Understand automatically.
Interrupt sparsely.
```

Canonical product loop:

```text
External World
→ Acquisition
→ Automatic Canonical Cognition for genuine new arrivals
→ Attention allocation
→ User only when warranted
```

The objective is not to reduce how much information RAOS sees. The objective is to increase what the system can observe and process while reducing what must enter human attention. In shorthand:

```text
RAOS should see more than the user,
understand more than the user must read,
and surface only the small residue that deserves human attention.

中文就是：
RAOS 应该比人看到更多，替人理解更多，但只把极少数真正值得的东西交还给人。
```

This implies three distinct product layers:

```text
Inbox      = what RAOS has observed / preserved
Attention  = what RAOS currently judges deserves some attention state
Today      = what should enter the user's consciousness now
```

Acquisition volume and LLM spending are therefore separable engineering quantities, but this separation must never redefine the normal cognitive contract: after baseline establishment, a genuinely new arrival should normally be routed automatically through the canonical cognition path. Manual `Analyze with RAOS` is a recovery/explicit-action mechanism, not the ordinary operating model. Merely opening or reading a Source must never be an implicit cognition trigger.

Historical backlog is different from a genuine new arrival. When a SourceDefinition is first attached, backlog may be persisted as a baseline without cognition so it does not masquerade as newly arrived information. After that baseline, subsequent arrivals enter automatic cognition unless an explicit failure/defer policy says otherwise.

```text
External World W_t
      ↓
Acquisition
      ↓
Observable Information I_t
      ↓
Information / Evidence Representation
      ↓
Cognition relative to K_t
      ↓
Attention / Authorized Action
      ↓
K_{t+1} when explicitly authorized
```



## 2. Canonical HEAD dataflow

```text
Sources / Feeds / APIs / Manual Input
        ↓
──────────────── Acquisition Plane ────────────────
Source Registry → independent Source Poller → Adapter
                                     ├─ RSS / Atom
                                     ├─ WEIBO_PUBLIC / X_PUBLIC
                                     ├─ HACKERNEWS_SEARCH
                                     ├─ BILIBILI_SEARCH / BILIBILI_CREATOR
                                     ├─ SOGOU_SEARCH (blocked residual when public DOM unavailable)
                                     └─ ACTIVE_QUERY_BUNDLE ← WATCH observation intent
                                              ↓ query expansion
                                        child discovery adapters
                                              ↓ retrieval-scope guard
        ↓
SourceDefinition → Observation → Information Object → Snapshot
        ↓
RAOS Source / Raw Information Boundary
        ↓
──────────── Information / Evidence Plane ─────────
Semantic Sensor → Semantic Evidence Auditor
        ↓
Audited World Representation
        │
        ├──────────────── Cognitive Transition Path ───────────────┐
        │                                                          │
        │  Locate(K_t) → Relation Mapping → Support Binding         │
        │  → Grounding / OPEN_NEW Jurisdiction → Authority          │
        │  → Cardinal-Free Effect Existence → Magnitude-Free        │
        │  → Pareto                                                  │
        │                                                          │
        └──────────────── No-Delta Awareness Path ─────────────────┤
                                                                   │
           Audited Event Projection → D / S / P                    │
           → AWARE iff S AND (D OR P)                               │
                                                                   ↓
──────────────── Attention / Action Plane ────────────────
DROP / AWARE / WATCH / ENGAGE
        ↓
Decision Cause → Public Update / WATCH / authorized KernelPatch
```

The two Attention branches are orthogonal. D/S/P is not a substitute for cognitive effects, and cognitive relevance is not a substitute for situational awareness.

## 3. Attention authority split



### 3.1 Cognitive-effect branch

When one or more legal cognitive effects survive the research-aligned cognition contract, D/S/P has no authority over that decision.

```text
REINFORCE / CHALLENGE / OPEN_NEW
→ Grounding / Authority
→ Magnitude-Free / Pareto
→ cognitive Attention
```

This branch may produce AWARE, WATCH, or ENGAGE according to the selected semantic effect and frozen policy. It may authorize public cognitive update, WATCH responsibility, or KernelPatch only from the exact Decision Cause.

### 3.2 No-Delta branch

When no legal cognitive effect survives:

```text
Δ = NONE
→ evaluate audited event(s)
→ D / S / P
→ DROP or AWARE
```

Frozen semantic gate:

```text
AWARE iff S AND (D OR P)
```

D = Standing Attention Jurisdiction / Standing Radar Fit.
S = Material Consequence to a consequential shared reference system.
P = Collective Attention Salience inside the event's objective constituency.

P must come from external attention evidence. Article wording, topic similarity, fame, and model prior must not manufacture current P.
When direct platform statistics are unavailable, an engineering estimator or explicitly labelled simulation may approximate P for dogfood/counterfactual analysis, but it must remain provenance-distinct from observed attention evidence and must not redefine the frozen P semantics.
UNKNOWN is not False. If missing components prevent the Boolean result from being logically determined, the no-Delta decision is unresolved rather than silently coerced to DROP.

## 4. Current contract versions

```text
Acquisition Plane              acquisition-plane-v0.3 / Phase 11A–11B active acquisition
Semantic Sensor                semantic-evidence-extractor-v0.2.6
Semantic Evidence Auditor      semantic-evidence-auditor-v0.1.1
Cognition                      research-aligned-cognition-v1
Relation Mapping               Phase 9A v0.2 frozen contract
Support Binding                Phase 10D.6L.3 frozen contract
Grounding                      Phase 10D.6L.4 frozen contract
OPEN_NEW Jurisdiction          Phase 10D.6L.4J frozen contract
Effect existence               semantic-cardinal-free
Effect calibration             magnitude-free-v0.1
Decision strategy              pareto-multidelta-cardinal-free-effect-anchored-open-new-v0.2
D                              standing-radar-fit-estimator-v4 / profile-v4
S                              material-consequence-estimator-v1
P                              collective-attention-estimator-v1
No-Delta gate                  aware-iff-s-and-d-or-p-v1
Unknown composition            no-delta-awareness-integration-v1.1 semantics
```



## 5. Core invariants

1. Acquisition observes; it does not judge cognitive relevance or importance.
2. Sensor/Auditor is the shared evidence boundary for both cognition and no-Delta awareness.
3. D/S/P operates on audited event semantics, not arbitrary whole-article topic text.
4. P is a latent collective-attention state estimated from attention evidence, not article prose.
5. D/S/P has authority only when no legal cognitive Decision Cause exists.
6. Attention Policy must not manufacture cognitive change.
7. Decision Cause = Public Update Cause = Authorized Side-Effect Cause.
8. UNKNOWN / unavailable evidence is not negative evidence.
9. Historical snapshots and execution identity are immutable; replay must preserve the frozen contract.
10. Research and active developer dogfood should execute the same validated semantic contract unless an explicit versioned experiment says otherwise.
11. A newly registered Acquisition Source establishes a present-time baseline before cognitive analysis; historical feed backlog must not masquerade as newly arrived information.
12. Failure of one Acquisition Source must not terminate polling of independent Sources; failure of one discovered item must not terminate sibling items in that Source.
13. Acquisition transport and cognition are orthogonal: a Source may be persisted and read without an AnalysisRun; acquisition volume must not imply cognition spending volume.
14. Genuine post-baseline new arrivals should normally enter automatic canonical cognition; baseline backlog, explicit defer policy, or technical failure are exceptions, not the normal product path.
15. Reading/opening a Source is never an implicit cognition trigger. Manual `Analyze with RAOS` is recovery/explicit action, not ordinary scheduling.
16. The system should maximize observable-world coverage while minimizing human interruption: high acquisition/cognition throughput is compatible with a quiet Attention surface.
17. Anonymous public-social adapters may consume only publicly observable material. Authenticated account/following access is a separate explicitly authorized transport layer.
18. Discovery adapters may preserve raw engagement/rank/platform telemetry, but raw popularity is evidence only; it has no D/S/P or Attention authority.
19. Platform-native content with materially incomplete semantics may be persisted under an explicit cognition-defer policy rather than analyzed as if the full content had been observed.
20. Query-bearing Source locators in Phase 11A are fixed observation scope; automatic Query Expansion is a separate Phase 11B capability and may not become cognition authority.
21. Query Expansion and Retrieval Scope Guard are Acquisition-side observation machinery only; neither may assign D/S/P, Delta, or Attention.
22. A WATCH may activate external search only when it projects to a self-contained observation intent; generic trigger labels without sufficient origin context must fail closed rather than broaden silently.
23. Multiple query/adaptor hits for the same canonical ref merge provenance into one external information identity rather than multiplying facts.



## 6. Architecture-change checklist

Before merging an architectural change, check this document against:

```text
module inventory
main dataflow
branching / authority boundaries
versioned contracts
execution identity
online wiring
research ↔ dogfood parity
```

A module that exists only in research code but is required by this diagram is an explicit wiring gap, not an implicit future feature.

---



## 附录: Raw Answer



我真正想要的设计哲学不是“抓很多文章，但都不分析，让用户自己点 Analyze”。那样 RAOS 就退化成了一个 RSS 阅读器，确实违背“注意力操作系统”的核心。

真正应该是下面这套。

External World→Acquisition→Automatic Cognition→Attention→User\boxed{ \text{External World} \rightarrow \text{Acquisition} \rightarrow \text{Automatic Cognition} \rightarrow \text{Attention} \rightarrow \text{User} } 

### 1. Acquisition 的职责：尽可能广地“看见世界”

Acquisition 只回答：

> **外界发生了什么？**

所以它可以大胆抓：

- The Verge
- OpenAI
- DeepMind
- arXiv
- 微博
- X
- 以后更多 RSS、论坛、论文、公众号……

这一层不应该因为 DeepSeek 贵就少抓。

所以我说：

Acquisition volume≠LLM spending\boxed{\text{Acquisition volume} \neq \text{LLM spending}}

更准确的意思是：

> **把一条信息保存进 RAOS，不等于必须立刻花一次完整 LLM cognition 的钱。**

但这句话绝对不等于：

> “RAOS 不自动分析信息。”

---

### 2. 新到的信息，RAOS 应该后台自动判断

这才是 RAOS 的核心。

例如明天上午突然来了 100 条新信息：

```text
微博            25
X               20
新闻/RSS        30
arXiv            20
其他              5
```

理想情况下你根本不应该去 Inbox 一篇篇点：

> Analyze with RAOS

而应该后台自动：

```text
100 new Sources
       ↓
RAOS cognition
       ↓
DROP      72
AWARE     19
WATCH      7
ENGAGE     2
```

最后你打开 Today，只看到：

```text
2 件需要你认真看
7 件 RAOS 替你盯着
19 件知道一下即可
72 件根本不用管
```

这才是：

当外界信息大量涌入时， Attention 仍然保持安静\boxed{ \text{当外界信息大量涌入时， Attention 仍然保持安静} }

这里“安静”不是：

> 什么都不分析，所以什么都不显示。

而是：

> **系统看了很多，但只把极少数东西推到你面前。**

这其实就是 RAOS 最核心的价值。

---

### 3. 那为什么刚才微博 5 条 baseline 没有调用 DeepSeek？

因为那 5 条不是“新发生的东西”，而是我们**刚注册一个新 Source 时，为了建立当前位置而抓回来的历史存量**。

这叫 baseline。

比如我们晚上 9 点第一次接入“斌叔OKmath”。

微博 API 一上来返回最近 5 条：

```text
20:47
20:42
20:41
20:37
20:36
```

这五条其实在 RAOS 开始监控以前就已经存在。

如果一注册一个源，就把：

```text
最近 20 条
最近 100 条
最近 7 天
```

全部当成“刚刚发生的新事件”丢给 cognition，那么每添加一个源都会瞬间制造一场假的信息爆炸。

所以 baseline 的规则是：

Historical backlog→建立当前状态→不伪装成新到信息\boxed{ \text{Historical backlog} \rightarrow \text{建立当前状态} \rightarrow \text{不伪装成新到信息} }

但从 baseline **之后**开始，比如斌叔 21:05 又发了一条：

```text
21:05 NEW POST
```

这才是真正的：

new arrival\boxed{\text{new arrival}}

它应该自动进入 RAOS cognition。

所以：

```text
第一次接源
最近 5 条旧微博
→ library baseline
→ 默认不自动分析
```

而：

```text
接源之后新发的微博
→ new observation
→ 自动 cognition
→ DROP / AWARE / WATCH / ENGAGE
```

这两个必须区别开。

---

### 4. “Reading a Source ≠ Running cognition” 又是什么意思？

这个是另外一件事。

之前我们的 UI 有个很怪的行为：

> 用户点击一篇文章 → 前端发现没有 AnalysisRun → 自动调用 DeepSeek。

这不合理。

因为：

阅读≠分析触发器\boxed{ \text{阅读} \neq \text{分析触发器} }

你只是想打开一篇文章看看，为什么这个鼠标点击动作就应该偷偷烧一次模型？

正确关系应该是：

```text
后台系统决定什么时候 cognition
```

而不是：

```text
用户什么时候点开文章
决定什么时候 cognition
```

所以正常情况应该是：

```text
新信息到达
      ↓
后台已经自动分析
      ↓
用户以后打开文章
      ↓
直接读 + 看已有 RAOS 判断
```

而 `Not analyzed yet` 主要用于几类特殊情况：

- baseline 历史信息；
- 某次 cognition 失败；
- 手工保存但尚未处理的 Source；
- 用户明确要求暂不分析的内容。

所以按钮：

> Analyze with RAOS

应该是一个**补救/主动操作入口**，而不是 RAOS 正常工作流。

---

## 5. 所以整个产品应该有三层，而不是两层

我现在会把它理解成：

World Intake→Cognitive Filtering→Human Attention\boxed{ \textbf{World Intake} \rightarrow \textbf{Cognitive Filtering} \rightarrow \textbf{Human Attention} }

具体就是：

```text
                  外部世界
                     │
     ┌───────────────┼────────────────┐
     │               │                │
   RSS             微博               X
 arXiv            News              APIs
     │               │                │
     └──────────── Acquisition ────────┘
                     │
              大量原始信息
                     │
                     ▼
              RAOS Cognition
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
      DROP         AWARE         WATCH / ENGAGE
      70%           20%             10%
       │             │               │
   不打扰你       Brief 中出现       真正进入你的注意力
```

所以 RAOS 的目标不是：

> 少抓信息。

恰恰相反，是：

抓得越广，用户看到得越少。\boxed{\text{抓得越广，用户看到得越少。}}

这句话其实最接近我真正的设计理念。

---

## 6. 那“LLM spending”怎么办？

这里以后还有一层工程优化，但不能污染理论。

理论模型应该始终是：

每一个新信息都应有机会被 RAOS 判断\boxed{ \text{每一个新信息都应有机会被 RAOS 判断} }

工程上，为了省钱，可以以后增加一个 cheap gate：

```text
1000 new items
      ↓
cheap deterministic / embedding / metadata triage
      ↓
200 plausible candidates
      ↓
full Semantic Sensor + Auditor + cognition
      ↓
Attention
```

但这里要非常小心。

cheap gate 只能回答：

> **“这个东西值得花更贵的 cognition 去看吗？”**

不能提前替代 RAOS 做：

> DROP / WATCH / ENGAGE

否则又会出现第二套认知系统。

所以未来更合理的是：

Acquisition→cheap admission control→canonical cognition→Attention\boxed{ \text{Acquisition} \rightarrow \text{cheap admission control} \rightarrow \text{canonical cognition} \rightarrow \text{Attention} }

但目前你还剩 5 元 DeepSeek，而且实测很便宜，我反而不急着做这层。现在更有研究价值的是：

> **先让所有真正的新 arrival 都跑 canonical cognition。**

看看真实信息流量下，RAOS 到底能不能压住噪声。

---

所以把我前面那些话重新压缩成一句：

RAOS 应该尽可能多地观察世界， 尽可能自动地理解世界， 但尽可能少地打扰人。\boxed{ \text{RAOS 应该尽可能多地观察世界， 尽可能自动地理解世界， 但尽可能少地打扰人。} }

这才是我的核心设计理念。

而 Inbox、Attention、Today 三个页面其实也应该对应这三个层级：

```text
Inbox
= RAOS 看见了什么

Attention
= RAOS 判断什么值得占用你的认知

Today
= 此刻真正需要进入你意识的是什么
```

这样一来，整个产品结构就顺了。



RAOS 不是因为外界信息更多而让用户看到更多，\boxed{ \text{RAOS 不是因为外界信息更多而让用户看到更多，} }

而恰恰应该：

系统越忙，人越安静。\boxed{ \text{系统越忙，人越安静。} }

我觉得这句话其实非常接近 RAOS 的产品灵魂。

---

