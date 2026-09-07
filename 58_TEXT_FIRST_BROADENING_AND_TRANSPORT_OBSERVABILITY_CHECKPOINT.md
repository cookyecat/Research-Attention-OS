# Semantic Sensor / Auditor — Text-First Broadening Checkpoint

Status: **ACTIVE DEVELOPMENT / PDF DEFERRED / TEXT TRANSPORT ATTRIBUTION NEXT**  
Date: 2026-09-08

## 1. Priority correction

Current research priority is not PDF ingestion quality.

> **媒介解析问题可以替换输入源绕开；语义抽取主链的失败不能绕开。**

PDF support remains useful, but mature PDF readers/parsers can be integrated later. Do not spend the current Semantic Sensor / Auditor frontier budget on PDF-specific handling unless future evidence makes it unavoidable.

Current scope:

```text
PDF ingestion / RS04           DEFERRED_NOT_CURRENT_FRONTIER
Pure-text semantic broadening  ACTIVE
Long-source model completion   OPEN / PRIMARY ENGINEERING RESIDUAL
```

The successful RS04 v0.2.2 result remains archived as development evidence but must not drive current mechanism changes.

## 2. Revised broadening round

Machine-readable preregistration:

```text
eval/live/manifest.semantic_sensor_auditor_broadening_v0_1_1.yaml
```

Commit:

```text
62c62c1e7c05a0c10ac12919187d580cb12adcac
eval: preregister text-first semantic broadening round v0.1.1
```

Round sources:

```text
RS11 — news/release-like text
RS05 — technical tutorial/method text
RS06 — long mixed interview text
RS12 — industry/technical interview text
```

Reserved sources remain untouched:

```text
RS13 / RS14 = RESERVED_UNCONSUMED
```

RS02 remains:

```text
SATURATED_DEVELOPMENT / REGRESSION ONLY
```

## 3. Frozen semantic mechanisms

Do not change because of the transport residual:

```text
Semantic Sensor v0.2.2
prompt SHA 52bae84a3d06bbaa597cdbf43460c8945dcd13cb53616390c05a6a40995dfbe9

Semantic Evidence Auditor v0.1.1
prompt SHA d22540217a0bec35468e327c6b6df8041eee7fb1c79dd676cfa38935774b81bb

Evidence policy = BASELINE_CITED_EVIDENCE_ONLY
```

## 4. What the first broadening run actually showed

Artifact:

```text
semantic_evidence_dev_v0_2_2_20260907T153131Z.json
```

Observed:

```text
RS11  NOT SCORABLE — malformed JSON / model_call
RS05  NOT SCORABLE — malformed JSON / model_call
RS06  NOT SCORABLE — malformed JSON / model_call
RS04  SCORABLE — first-pass valid
```

The three pure-text failures all broke around roughly 28–29K raw JSON characters according to parse-error positions.

This is a repeated transport/output-completion residual, not yet a semantic failure.

Do not conclude:

```text
Sensor cannot understand RS11/05/06
PDF is better than text
schema does not generalize
```

Root cause is still OPEN because the existing chat_json instrumentation loses finish_reason, usage, raw completion length, and raw tail when JSON parsing fails.

## 5. Transport observability instrument

New diagnostic runner:

```text
eval/live/run_semantic_evidence_transport_diagnostic_v0_1.py
```

Commit:

```text
21c1ecffa23b15848cc587a45e78c9768412d4d4
eval: add raw semantic completion transport diagnostics
```

It preserves the exact frozen Sensor prompt/model settings but records before JSON validation:

```text
finish_reason
prompt_tokens
completion_tokens
total_tokens
raw_content_chars
raw_content_sha256
raw_content_tail
json_parse_ok / parse_error
latency
actual_model
```

This is instrumentation only. It does not repair, chunk, summarize, change schema, change prompt, or change semantic rules.

## 6. Exact next experiment

Sync:

```bash
git pull --rebase
```

Run raw completion diagnostics on the text-first round:

```bash
backend/.venv/bin/python \
  eval/live/run_semantic_evidence_transport_diagnostic_v0_1.py \
  --source RS11 \
  --source RS05 \
  --source RS06 \
  --source RS12 \
  --as-of 2026-09-07
```

Inspect first:

```text
finish_reason
completion_tokens
raw_content_chars
raw_content_tail
```

Primary attribution question:

> **Are the long-text malformed JSON outputs actually hitting a reproducible provider/model completion boundary, or is another transport/output pathology responsible?**

Only after that attribution should we decide whether a minimal output-control change is needed.

## 7. Recovery compression

```text
Do not spend current effort on PDF.
RS04 is archived and deferred.

Main frontier:
pure-text long-source Semantic Sensor completion reliability.

Do not change Sensor semantics yet.
Observe raw completion first.

NEXT:
run transport diagnostic on RS11 / RS05 / RS06 / RS12.
```
