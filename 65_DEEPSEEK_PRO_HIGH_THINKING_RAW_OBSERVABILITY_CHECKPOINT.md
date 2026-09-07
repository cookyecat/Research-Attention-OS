# DeepSeek Pro High-Thinking Raw Observability Checkpoint

Status: **ACTIVE DEVELOPMENT / HIGH-THINKING RESULT NOT YET ATTRIBUTED**

## Why this checkpoint exists

The first explicit-thinking A/B on RS05 produced a valid explicit-disabled result but an unscorable explicit-enabled/high result because malformed final JSON caused the probe to discard provider diagnostics.

That run therefore established only:

```text
EXPLICIT_DISABLED
36 semantic units
finish_reason = stop
reasoning_content = absent
```

which independently reproduced DeepSeek Pro's proposition-level semantic fragmentation under confirmed non-thinking mode.

The high-thinking branch remained unresolved.

## Instrumentation correction

The new v0.2 probe captures provider observability before attempting final JSON parsing.

Recorded fields include:

```text
prompt_tokens
prompt_cache_hit_tokens
prompt_cache_miss_tokens
completion_tokens
completion_tokens_details.reasoning_tokens
total_tokens
finish_reason
reasoning_content presence / character count / SHA256
final content character count / SHA256 / diagnostic head+tail
JSON parse status
schema validation status
```

Reasoning text itself is not persisted.

## Frozen semantic comparison

The semantic prompt remains the RS05 open-stop prompt from v0.1:

```text
same source = RS05
same open semantic stopping contract
same Semantic Independence Test
same hierarchical-abstraction instruction
same provenance / temporal / epistemic rules
same JSON field family
model = deepseek-v4-pro
```

The high-thinking condition is explicit at the provider wire level:

```text
thinking = enabled
reasoning_effort = high
```

## Transport headroom

For this capability probe only:

```text
max_tokens = 32768
```

This is a measurement choice, not a production recommendation. It exists to avoid confusing a reasoning+final-answer generation ceiling with semantic capability.

## Attribution questions

The next result should distinguish:

1. **Thinking improves hierarchical abstraction**
   - materially fewer top-level units than the explicit-disabled 36-unit reference;
   - semantic coverage preserved;
   - final JSON complete.

2. **Thinking does not materially improve hierarchical abstraction**
   - top-level unit count remains near the mid/high 30s with complete output.

3. **Reasoning consumes the generation budget**
   - finish_reason=length or completion_tokens approaches max_tokens;
   - reasoning_tokens consume a large fraction of generation;
   - final JSON is truncated.

4. **Thinking + JSON output stability issue**
   - finish_reason=stop with substantial headroom;
   - final JSON still malformed.

## Current theoretical frontier

Current evidence supports:

> **DeepSeek Pro is strong at proposition extraction but tends to represent too many propositions as separate top-level semantic units.**

The open capability question is whether explicit high-effort reasoning can improve:

> **hierarchical semantic abstraction + global representation budgeting**

Memorable methodology remains:

> **研发阶段买清晰度，生产阶段买效率。**
