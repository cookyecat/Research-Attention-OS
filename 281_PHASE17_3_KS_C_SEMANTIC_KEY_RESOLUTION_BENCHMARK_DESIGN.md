# Phase17.3-KS-C Semantic Key Resolution Benchmark Design

## Purpose

验证 RAOS Semantic Key Resolver 是否实现 semantic continuity，而不是 surface similarity matching。

核心问题：

ResolveKey(EventIdentity, CurrentSlots, NewEvidence)

输出：

- REUSE(existing key)
- CREATE(new key)

## Benchmark Boundary

输入：

- Current EventState schema
- Typed Semantic Proposition
- New evidence

输出：

- resolved key
- reuse/create decision
- confidence

不测试：

- evidence extraction
- primitive classification
- state apply

## Case Taxonomy

1. Paraphrase convergence

不同表达是否进入同一 semantic key。

2. Primitive family boundary

验证 PROCESS / QUALITY / RELATION 不发生错误迁移。

3. Temporal evolution

同一 dimension 随时间更新，而不是产生新 key。

4. New dimension emergence

验证合理 CREATE。

5. Correction

验证 same key replacement。

6. Conflict

验证 multi-source coexistence。

## Metrics

- Key Resolution Accuracy
- Primitive Violation Rate
- Slot Fragmentation Rate
- Merge Error Rate
- Replay Determinism

## Evaluation Hypotheses

H1: Primitive type constraints reduce semantic merge errors.

H2: Temporal continuity reduces unnecessary CREATE.

H3: Schema-aware resolution outperforms embedding-only matching.

H4: Open-ended state growth is possible without slot explosion.

## Phase17.3-KS-C Implementation Note (2026-09-23)

The first executable gold harness has been created:

```
eval/live/run_phase17_3_ks_c_semantic_key_resolution_benchmark_v0_1.py
```

The benchmark is frozen as a semantic continuity test. A lexical slot matching baseline was added only as a lower-bound diagnostic:

```
eval/live/run_phase17_3_ks_c_semantic_key_resolution_baselines_v0_1.py
```

Observed baseline behavior:

- basic reuse cases can pass through lexical overlap;
- conflict handling fails because lexical matching cannot distinguish REUSE from REUSE_CONTEST;
- therefore the benchmark contains decision dimensions beyond similarity matching.

This confirms the benchmark boundary: the target resolver must reason over semantic state continuity, primitive constraints, and evidence conflict.


## v0.2 Expansion Plan

The benchmark remains focused on semantic state coordinate resolution.

Next expansion:

1. Jev longitudinal replay integration

Input:
- N8 materialized state
- N20 new evidence

Measure:
- slot reuse
- slot fragmentation
- unnecessary CREATE
- conflict preservation

2. Resolver baseline ladder

- lexical matching baseline
- embedding similarity baseline
- schema-aware semantic resolver

3. Resolver output contract

The final resolver should return the semantic coordinate explanation together with the decision.
