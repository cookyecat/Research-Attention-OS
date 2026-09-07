# DeepSeek Pro Open Semantic Stop Probe — Checkpoint

Status: **IMPLEMENTED / DEVELOPMENT-ONLY / RUN PENDING**  
Date: 2026-09-08

## Purpose

Attribute the remaining Semantic Sensor v0.2.3 residual between:

```text
model capability
vs
numeric stopping / task formulation
```

Prior observations:

```text
DeepSeek Flash + v0.2.3 hard cap 12 -> 12 RS05 units
DeepSeek Pro   + v0.2.3 hard cap 12 -> 12 RS05 units
GPT-5.6 Sol manual upper-bound probe -> natural stop at 10 semantic clusters
```

The GPT-5.6 Sol probe suggests that hierarchical abstraction plus global semantic-budget allocation may be a substantial model-capability component, while the repeated 12/12 saturation indicates task formulation remains confounded.

## Frozen research principle

> **研发阶段买清晰度，生产阶段买效率。**

Research uses stronger remote models to discover the correct semantic target and capability frontier. Production may later migrate the stable target to cheaper/local models.

Canonical strategy:

```text
61_SEMANTIC_SENSOR_RESEARCH_PRODUCTION_MODEL_STRATEGY.md
```

## Probe design

Source:

```text
RS05 — PyTorch performance profiling tutorial
```

Model:

```text
deepseek-v4-pro
thinking = disabled
temperature = 0.1
```

Unchanged from v0.2.3:

```text
source grounding
Semantic Independence Test
epistemic-status semantics
confidence semantics
temporal anchoring
minimal sufficient provenance
D/S/P/Delta/Attention exclusion
v0.2 semantic field family
```

Changed intentionally:

```text
REMOVE preferred unit range 6..10
REMOVE semantic hard cap 12
REMOVE numeric stopping as a semantic criterion

ADD open semantic stopping:
stop only when every remaining substantive passage is either
1. subsumed by an existing semantic unit,
2. evidence/example/measurement for an existing unit, or
3. non-independent metadata/background/page chrome.

ADD explicit transport headroom:
max_tokens = 16384
```

The transport increase is measurement headroom, not a production solution.

## Hypotheses

### H1 — Task formulation dominates

If Pro open-stop naturally converges near ~10–12 high-level clusters, materially improves coverage/abstraction, and does not simply continue enumerating adjacent points, then numeric cap/prompt formulation caused much of the prior residual.

### H2 — Model capability remains a major frontier

If Pro open-stop emits many more units (for example, repeatedly separates examples/measurements that GPT-5.6 Sol merged into principles) while GPT-5.6 Sol remains near the 10-cluster basis, then hierarchical semantic abstraction is strongly model-capability limited.

### H3 — Both matter

If open-stop improves some groupings but Pro still over-enumerates or misses important cross-section abstractions, the residual remains mixed.

## Evaluation dimensions

Do not judge by unit count alone.

Inspect:

```text
semantic coverage
hierarchical abstraction
independence of units
whole-source coverage
omissions
redundancy
provenance sufficiency
statement compactness
completion tokens
finish_reason
```

Particular RS05 diagnostics:

```text
Can 64x64 overhead-bound + 4096x4096 compute-bound become one general workload-regime principle?

Can cold-start + profiler schedule + warmup observations become one measurement-isolation principle?

Is the torch.compile pipeline (Dynamo -> FX -> AOTAutograd -> Inductor) preserved?

Are torch.compile runtime/fusion findings preserved without exploding into sentence-level units?
```

## Instrumentation

Files:

```text
eval/live/semantic_evidence_open_stop_probe_v0_1.py
eval/live/open_stop_chat_transport_v0_1.py
eval/live/run_semantic_evidence_open_stop_probe_v0_1.py
backend/tests/eval/test_semantic_evidence_open_stop_probe_v0_1.py
```

The experimental transport is intentionally isolated from production `chat_json()`.

## Next commands

```bash
git pull --rebase

cd backend
.venv/bin/pytest tests/eval/test_semantic_evidence_open_stop_probe_v0_1.py -q
cd ..

RAOS_LLM_MODEL=deepseek-v4-pro \
backend/.venv/bin/python \
  eval/live/run_semantic_evidence_open_stop_probe_v0_1.py
```

Expected artifact directory:

```text
eval/live/results/semantic_evidence_open_stop_probe_v0_1/
```

## Interpretation discipline

This is a **development-only model-capability probe**.

It is not:

```text
fresh validation
Human Gold
production policy
proof that GPT-5.6 Sol's 10 clusters are uniquely correct
```

The key output is causal evidence about whether DeepSeek Pro can perform natural hierarchical semantic stopping once numeric caps and transport ceilings are removed.
