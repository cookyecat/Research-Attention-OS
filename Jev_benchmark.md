# Jev Benchmark Specification

## RAOS Phase17 Longitudinal Event State Benchmark

Version: v0.1

---

# 1. Benchmark Purpose

Jev Benchmark 用于验证 RAOS Dynamic Event Engine 在真实信息流环境中的能力。

核心问题：

> 当一个真实世界事件持续产生新的 evidence 时，RAOS 是否能够保持稳定的 EventState，并正确更新 attention-relevant representation？

---

# 2. Benchmark Motivation

传统信息系统：

```text
new document

↓

new summary

```

存在问题：

- 无法保持长期状态
- 无法区分新事实和重复传播
- 无法处理修正与冲突
- 无法形成稳定认知轨迹

RAOS：

```text
Event

↓

History

↓

Recursive EventState

↓

Decision / Attention

```

---

# 3. Benchmark Object

事件：

```text
Jev Model Release Event

```

类型：

AI model release / technology event

---

# 4. Event Timeline

Benchmark 以真实 Jev 传播过程作为 longitudinal trace。

时间序列：

```text
T0

Initial discovery

↓

T1

Community spread

↓

T2

Technical discussion

↓

T3

First-party information

↓

T4

Independent evaluation

↓

T5

Long-term assessment

```

每一个时间点：

对应：

```text
Observation

```

---

# 5. Observation Model

每条 observation：

```json
{
  "observation_id": "",
  "event_id": "jev",
  "world_time": "",
  "evidence_time": "",
  "ingest_time": "",
  "source": "",
  "semantic_units": []
}

```

---

# 6. Three Time Semantics

严格区分：

## world_time

事情发生时间。

例如：

模型发布。

---

## evidence_time

信息被公开时间。

例如：

论文、博客、测试结果公开。

---

## ingest_time

RAOS 获取时间。

例如：

crawler 时间。

---

# 7. Evaluation Goal

Benchmark 不评价：

“模型是否知道 Jev”。

评价：

RAOS 是否能形成：

```text
stable recursive understanding

```

---

# 8. Core Evaluation Dimensions

## 8.1 State Consistency

问题：

新 evidence 是否正确更新已有 State？

例如：

已有：

```text
Jev is released

```

新：

```text
Jev technical report published

```

正确：

增加 technical evidence。

错误：

重新创建一个新事件。

---

# 8.2 Semantic Delta Quality

评价：

新 evidence 是否产生正确 Delta。

例如：

新 evidence：

```text
independent benchmark result

```

应该：

QUALITY ↑

而不是：

IDENTITY change。

---

# 8.3 Key Stability

评价：

Key 是否稳定。

错误：

不断产生：

```text
performance_speed
performance_latency
performance_fast

```

正确：

形成稳定 semantic coordinate。

---

# 8.4 Replay Consistency

要求：

同一 History：

```text
H

```

无论：

- incremental update
- full replay

最终：

必须得到：

```text
same EventState

```

即：

Replay(H)=CurrentStateReplay(H)=CurrentState

---

# 9. Benchmark Scenarios

## Scenario A: Initial Emergence

测试：

弱 evidence 是否产生过度 attention。

---

## Scenario B: Viral Spread

大量讨论：

测试：

Source count ≠ information innovation。

---

## Scenario C: First Party Evidence

作者发布：

测试：

Evidence quality update。

---

## Scenario D: Independent Validation

第三方测试：

测试：

QUALITY / DISPOSITION 更新。

---

## Scenario E: Contradiction

不同结果：

测试：

CONTESTED state。

---

# 10. RAOS Expected Behavior

Jev EventState 示例：

初始：

```text
status:
emerging

world:
unknown capability

evidence:
weak

```

传播阶段：

```text
status:
active

attention:
watch

```

技术资料：

```text
PROCESS ↑

STRUCTURE ↑

```

独立测试：

```text
QUALITY ↑

DISPOSITION ↑

```

---

# 11. Benchmark Metrics

## State Accuracy

State 是否正确。

---

## Delta Precision

新增信息是否必要。

---

## Key Stability

长期运行：

Key 数量是否稳定。

---

## Replay Determinism

同一 History：

结果是否一致。

---

## Attention Stability

是否避免：

```text
WATCH

↓

AWARE

↓

WATCH

```

震荡。

---

# 12. Why Jev is Suitable

Jev 具有：

- 短时间爆发
- 多来源传播
- 技术信息逐渐补充
- 第一方 evidence 后出现
- 后续验证过程

因此非常适合测试：

```text
EventState recursive evolution

```

---

# 13. Benchmark Role in RAOS

Jev Benchmark 不是模型能力测试。

不是：

```text
Can LLM answer Jev questions?

```

而是：

```text
Can RAOS maintain a living event model
under continuous evidence updates?

```

它验证：

Ht+1=Ht⊕et+1H_{t+1}=H_t\oplus e_{t+1}St+1=U(St,et+1)S_{t+1}=U(S_t,e_{t+1})

是否能够在真实信息流中稳定运行。