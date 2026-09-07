# DeepSeek Pro High-Thinking Raw Observability Checkpoint

Status: **ATTRIBUTED / WORKING BASELINE SELECTED / MODEL-CAPABILITY FRONTIER DEFERRED**  
Date: 2026-09-08

## Final controlled result

RS05 explicit non-thinking reference:

```text
model                         deepseek-v4-pro
thinking                      disabled (wire explicit)
non_event_units               36
completion_tokens             8917
finish_reason                 stop
reasoning_content             absent
```

RS05 explicit high-thinking probe:

```text
model                         deepseek-v4-pro
thinking                      enabled (wire explicit)
reasoning_effort              high
max_tokens                    32768
prompt_tokens                 9708
prompt_cache_hit_tokens       9600
prompt_cache_miss_tokens      108
completion_tokens             13421
reasoning_tokens              3660
visible_output_tokens         9761
finish_reason                 stop
reasoning_content_chars       15943
final_content_chars           25604
JSON parse                    PASS
strict schema                 FAIL only because one unit had 5 supports > provenance cap 4
apparent top-level units      29 (RS05-U01 ... RS05-U29)
```

The output completed normally with substantial transport headroom. Therefore:

```text
transport truncation          NOT CAUSAL
JSON-mode completion          PASS
high-thinking activation      CONFIRMED
```

The strict schema failure is a provenance guardrail violation, not evidence that the semantic completion failed.

## Attribution

Explicit high-effort reasoning appears to reduce top-level semantic fragmentation:

```text
non-thinking                  36 units
high-thinking                 ~29 units
```

This is a moderate consolidation improvement, not a solution to the minimal-semantic-basis problem.

The strongest current attribution is:

> **DeepSeek Pro is strong at proposition extraction, but its hierarchical semantic abstraction and global representation budgeting remain materially weaker than the manual GPT-5.6 Sol upper-bound probe on RS05 (~10 cohesive semantic clusters).**

Thinking helps local consolidation, but does not close the abstraction-level gap.

Important distinction:

```text
more reasoning
    !=
automatically choosing a higher semantic abstraction level
```

The model must not only know which propositions are independently true; it must know **at what semantic level independence should be judged**.

## Current engineering decision

Do not continue tuning this frontier now.

Use DeepSeek as the executable Semantic Sensor baseline so the full RAOS pipeline can continue to be integrated and measured.

Preferred working baseline for the current research phase:

```text
model                         deepseek-v4-pro
sensor                        v0.2.3 bounded minimal-sufficient candidate
thinking                      disabled unless a downstream experiment explicitly requires otherwise
status                        WORKING_BASELINE_WITH_KNOWN_ABSTRACTION_LIMITATION
```

Why:
- v0.2.3 is structurally reliable and bounded;
- Pro showed better global coverage than Flash under the same bounded contract;
- high-thinking increases latency/output cost substantially while only partially improving fragmentation;
- the remaining gap is now sufficiently attributed to justify deferral rather than further prompt churn.

Do not reinterpret this baseline as a claim that 12 semantic units are universally sufficient. The numeric bound remains an engineering compromise, not the semantic law.

## Deferred frontier

Future work may revisit hierarchical abstraction through one or more of:

```text
stronger future model
better abstraction-aware prompt / representation theory
second-pass hierarchical consolidation
multi-turn refinement
local/open-source model after capability improves
distillation from a stronger semantic-basis teacher
```

A second LLM pass may improve abstraction, but it adds another model round and is therefore intentionally deferred until end-to-end RAOS evidence shows that the current Sensor limitation is a real downstream bottleneck.

## Role of GPT-5.6 Sol during development

GPT-5.6 Sol may continue to serve as a **development upper-bound / adjudication oracle**, not as an implicit runtime dependency.

Use it to answer questions such as:
- what would a stronger hierarchical semantic basis look like?
- is a DeepSeek omission or fragmentation materially important?
- does a proposed representation change improve semantic sufficiency?

The executable RAOS pipeline should remain reproducible without depending on the current chat session.

## Methodology

> **研发阶段买清晰度，生产阶段买效率。**

And for this frontier:

> **Do not keep optimizing an attributed model-capability residual when the current baseline is already sufficient to unlock the next system-level experiment.**
