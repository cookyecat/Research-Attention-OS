# Semantic Sensor Front-End — E0 Input Integrity Result

Status: **DEVELOPMENT RESULT / SENSOR INPUT ATTRIBUTION**  
Date: 2026-09-07  
Corpus: `eval/live/manifest.semantic_evidence_dev_corpus.v0.1.yaml`  
Measurement command: `backend/.venv/bin/python eval/live/run_semantic_source_inventory_v0_1.py`

> E0 asks only whether the pinned raw sources can be faithfully surfaced as textual sensor input. It does not call an LLM and does not evaluate D, S, P, Delta, or Attention Action.

---

## 1. Result summary

All 12 pinned development files were located and their Git blob identities matched the manifest. The corpus includes five PDFs (`RS01`, `RS03`, `RS04`, `RS07`, `RS08`) and seven direct-text sources. PDF media type itself is not a failure mode: four of the five PDFs expose usable text layers through the current `pypdf` sensor. The corpus naturally separates into three input regimes.

### A. PDF text-layer extraction failure

| Source | Type | Pages | Rendered chars | Decision |
|---|---|---:|---:|---|
| RS01 | PDF | 2 | 25 | **TEXT-LAYER UNUSABLE** |

The 25 rendered characters are effectively only page-pointer scaffolding / negligible extracted payload. E0 therefore treats RS01 as a text-layer observability failure for the current `pypdf`-based PDF sensor, not as evidence that PDF files in general are unsupported.

The other four PDFs are text-layer usable:

```text
RS03  15 pages   78,167 chars
RS04   4 pages   13,833 chars
RS07  29 pages  119,937 chars
RS08  17 pages   85,750 chars
```

Do not silently repair RS01 with OCR, vision extraction, or external knowledge inside the v0.1 measurement. A future PDF-render / vision fallback is a new sensor capability and must be evaluated separately.

### B. Whole-source / moderate-context candidates

| Source | Type | Rendered chars |
|---|---|---:|
| RS02 | TXT | 1,132 |
| RS04 | PDF | 13,833 |
| RS05 | TXT | 17,278 |
| RS06 | TXT | 17,276 |
| RS09 | MD | 11,386 |
| RS10 | TXT | 8,804 |
| RS11 | TXT | 10,297 |
| RS12 | TXT | 7,697 |

These are suitable for first whole-source Semantic Extraction development without introducing chunking yet. Note that RS04 is a healthy PDF text-layer case and belongs here despite being PDF media.

### C. Long-context, text-layer-usable PDF sources

| Source | Type | Pages | Rendered chars |
|---|---|---:|---:|
| RS03 | PDF | 15 | 78,167 |
| RS07 | PDF | 29 | 119,937 |
| RS08 | PDF | 17 | 85,750 |

These are not PDF parsing failures. Their text layers are usable; the problem is source length / context management. They should not be silently truncated. They define a later explicit long-source / hierarchical extraction study.

---

## 2. Research interpretation

The development corpus has already exposed two independent sensor-front-end problems before any semantic model call:

```text
raw source
   |
   +-- modality / text-layer observability
   |
   +-- context-size / source segmentation
   |
   +-- semantic extraction
```

Therefore:

```text
PDF != modality failure
TextLayerFailure != SemanticExtractionFailure
LongContextProblem != D/S/PProblem
```

This preserves the same systems discipline used elsewhere in RAOS: attribute the failure to the earliest layer that causally explains it.

---

## 3. Immediate development decision

First semantic extraction pair:

```text
RS02 — mixed factual + methodological workflow summary
RS09 — multi-participant discussion / non-event epistemic content
```

Why this pair:

- both have healthy direct text input;
- neither requires chunking;
- they deliberately stress the source-to-semantic-unit boundary;
- RS02 may contain event-like facts plus method claims;
- RS09 should test whether the extractor can avoid forcing a discussion thread into one artificial event.

Do not run RS03/RS07/RS08 until long-source behavior is explicitly designed.

---

## 4. Current status

```text
E0 corpus provenance       PASS — 12/12 files resolved / blob-verified
PDF files                  5 total
PDF text-layer usable      4/5 — RS03, RS04, RS07, RS08
PDF text-layer unusable    RS01
Overall text-layer usable  11/12
Long-context deferred      RS03, RS07, RS08
First semantic dev pair    RS02, RS09
Fresh-validation status    NONE — development only
```
