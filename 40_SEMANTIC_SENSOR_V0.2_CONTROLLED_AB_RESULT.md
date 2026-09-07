# Semantic Sensor Front-End — v0.2 Controlled A/B Result

Status: **DEVELOPMENT RESULT / INTERFACE A-B ATTRIBUTION**  
Date: 2026-09-07  
Sources: `RS02`, `RS09`  
Model: `deepseek-v4-flash`  
Thinking: disabled  
Temperature: 0.1

> This is development evidence, not fresh validation. The same sources were intentionally reused to isolate interface changes between v0.1 and v0.2.

---

## 1. Executive result

v0.2 removes the dominant v0.1 structural/interface failure mode on the two development sources:

```text
v0.1 first-pass valid    0 / 2
v0.2 first-pass valid    2 / 2

v0.1 final scorable      1 / 2
v0.2 final scorable      2 / 2

v0.1 repair required     RS09; RS02 still failed after repair
v0.2 repair required     none
```

This strongly supports the attribution that v0.1's exact-contract / provenance representation was a major cause of structural failure. It does not certify the extractor; semantic residuals remain.

---

## 2. RS09 — compression with evidence preservation

### v0.1

```text
event_frames          0
non_event_units      28
support pointers     28
repair               yes
latency              39.743 s
prompt tokens        41,693  # cumulative across initial + repair call
completion tokens     9,085  # cumulative across initial + repair call
```

### v0.2

```text
event_frames          0
non_event_units      15
support records      28
unique support ptrs  26
multi-support units   5
repair               no
latency              14.814 s
prompt tokens         5,379
completion tokens     3,009
```

The important causal signature is not merely `28 -> 15` units. v0.2 preserves roughly the same evidence volume while allowing multiple passages to support one higher-level semantic statement:

```text
v0.1: 28 semantic units / 28 one-to-one supports
v0.2: 15 semantic units / 28 supports
```

Twenty-four of the twenty-eight v0.1 support pointers are retained by v0.2; v0.2 adds two nearby pointers while dropping several low-value/redundant discussion fragments. This is consistent with semantic aggregation rather than evidence deletion.

The dominant Gemma discussion is now represented as one aggregate unit with eight source supports instead of many comment-level units.

### Interpretation

```text
Raw discussion thread
    -> no artificial world event
    -> source-claim semantic units
    -> multi-evidence aggregation
```

This supports the source-level batch design:

```text
RawSource -> {EventFrames, NonEventEpistemicUnits}
```

and rejects the stronger assumption:

```text
RawSource == OneEvent
```

---

## 3. RS02 — semantic fidelity

v0.2 returns:

```text
event_frames          2
non_event_units      12
repair               no
```

The extractor covers the substantive source paragraphs `PARA 0003` through `PARA 0012`, while omitting low-value handle/URL scaffolding.

The two event-like frames are source-grounded:

1. Lauren Tan's reported PR merge volume.
2. Her reported use of coding agents to auto-merge PRs, including the reported 20-PR morning example.

The remaining content is kept as attributed methodological/background claims rather than promoted to world facts. This includes the verification-bottleneck thesis, agent verification capabilities, skill creation/testing, and the engineering-management framing.

### Positive findings

```text
source claim attribution             PASS
support excerpts                     present
support pointers                     present
confidence as extraction support     HIGH where source is explicit
policy leakage D/S/P/A               none observed
```

---

## 4. New semantic residual — deictic time anchoring

RS02 contains source-relative expressions:

```text
"last month"
"this month has only been 12 days"
```

The source publication time is unknown. v0.2 nevertheless writes:

```text
"previous month and first 12 days of current month relative to measurement date"
```

This is incorrect.

`measurement as_of` is the RAOS observation/measurement time. It is not automatically the source's publication-time anchor.

Correct semantics are closer to:

```text
source-relative previous/current month
absolute calendar dates unresolved
source publication time unknown
```

Therefore:

```text
MeasurementTime != SourceTimeAnchor
```

and:

```text
DeicticTime("this month", source)
```

must remain unresolved unless the source supplies, or trusted source metadata supplies, a publication/capture time sufficient to resolve it.

This is a genuine Semantic Sensor residual and should be corrected before expanding the development corpus.

---

## 5. Current status

```text
v0.2 structural contract            SUPPORTED
first-pass structural validity      2/2 on current dev pair
repair dependency                   REMOVED on current dev pair
multi-support provenance            SUPPORTED
RS09 event/non-event discrimination PASS
RS09 semantic aggregation           IMPROVED / SUPPORTED
RS02 semantic coverage              STRONG
RS02 temporal deictic handling      RESIDUAL FOUND
fresh-validation status             NONE
```

Do not freeze v0.2 yet.

---

## 6. Immediate next step

Before consuming more development sources, make one minimal semantic correction:

1. Keep the current v0.2 schema.
2. Do not change D/S/P or Attention policy.
3. Clarify in the extractor contract that `measurement as_of` is not a source-time anchor.
4. Relative source phrases such as `today`, `yesterday`, `this month`, `last week`, `just now` must be resolved only from explicit/trusted source-time metadata; otherwise preserve them as source-relative and record unresolved absolute time.
5. Re-run RS02 as development regression and verify the temporal residual is removed without regressing first-pass structural validity.

After that, expand to additional moderate-context development sources such as RS10/RS11/RS12 and RS04/RS05/RS06 to stress event-heavy news, tutorial, interview, and PDF-text cases.
