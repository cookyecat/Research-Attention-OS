# Semantic Sensor — Hierarchical Abstraction & Thinking A/B Checkpoint

Status: **ACTIVE RESEARCH / DEVELOPMENT-ONLY**  
Date: 2026-09-08

## Current attribution

DeepSeek Pro open-stop on RS05 produced 39 non-event semantic units and stopped naturally at 9260 completion tokens under 16K transport headroom.

This rules out transport truncation as the cause of the 39-unit representation.

The observed residual is best characterized as:

> **semantic fragmentation caused by insufficient hierarchical semantic abstraction and global representation budgeting.**

DeepSeek Pro is good at identifying source-grounded propositions, but tends to promote too many independently true propositions into top-level semantic units.

Working distinction:

```text
Independent propositions
        ↓
cohesive higher-level semantic clusters
        ↓
minimal semantic basis
```

Semantic Independence is therefore necessary but not sufficient. The Sensor also needs a notion of semantic cohesion / hierarchical abstraction.

Current qualitative attribution:

```text
Model capability component                         SUBSTANTIAL
Hierarchical abstraction / global budgeting        OPEN FRONTIER
Transport ceiling                                  NOT CAUSAL for RS05 open-stop
Auditor                                             NOT CURRENT BOTTLENECK
```

Memorable formulation:

> **The model must not only know which propositions are independent; it must know at what semantic level independence should be judged.**

## Thinking-mode instrumentation residual

The RAOS code expressed a `thinking=disabled` intent in prior Sensor probes. However, the generic request helper only emits DeepSeek thinking fields when `RAOS_LLM_THINKING_PROTOCOL=deepseek`; otherwise the wire field is omitted.

DeepSeek currently documents thinking as enabled by default. Therefore historical artifacts that merely record `thinking=disabled` do not by themselves prove that the provider wire state was disabled unless the protocol configuration is known.

Next controlled diagnostic uses explicit wire-level conditions:

```text
A. thinking = disabled
B. thinking = enabled, reasoning_effort = high
```

Both use:

```text
RS05
DeepSeek v4 Pro
same open-stop prompt
same schema
same provenance rules
same temporal/epistemic rules
max_tokens = 16384
```

The experimental transport bypasses `RAOS_LLM_THINKING_PROTOCOL` so the wire state is unambiguous.

Primary outcome:

> Does explicit high-effort thinking reduce semantic fragmentation by producing fewer, more cohesive top-level semantic clusters without materially losing coverage?

## Development-source quality

The current text corpus contains raw web/article copies with realistic noise such as image placeholders, editorial framing, URLs, promotional language, repetition, secondary-source paraphrase, and source claims mixed with interpretation.

This is useful rather than accidental for Sensor development:

> **Raw web noise is part of the Sensor problem, not merely dirty data.**

However, ecological realism and clean semantic evaluation are different goals.

Recommended long-term split:

```text
RAW ECOLOGICAL CORPUS
- copied web/news/interview/tutorial inputs
- realistic page/article noise
- tests perception robustness and epistemic discipline

CLEAN CANONICAL CORPUS
- carefully curated source text
- minimal chrome/noise
- tests semantic coverage, abstraction and provenance more directly
```

RS05 is relatively clean and is currently useful for hierarchical-abstraction probes.

RS11 / RS12 / RS15 are valuable mixed promotional/media cases because they require separating technical claims, quoted/company assertions, editorial interpretation, and hype.

RS15 has already been inspected during development and therefore belongs to development data, not future fresh holdout evidence. RS13 / RS14 remain reserved and unconsumed.

## Research / production model strategy

> **研发阶段买清晰度，生产阶段买效率。**

Use strong remote models during research to establish the target representation and capability upper bound. Only after the semantic contract is understood should production work optimize toward local/open-source inference, routing, distillation, caching, or other cost controls.
