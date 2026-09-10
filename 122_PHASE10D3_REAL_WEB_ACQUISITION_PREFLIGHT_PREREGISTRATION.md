# Phase 10D.3 — Real-Web Acquisition Preflight Preregistration

Status: PREREGISTERED / ACQUISITION-ONLY SELECTION

## Purpose

Expand the external-sample probability-map program without treating website anti-bot/access failures as cognitive-model failures.

The preflight is deliberately outside Sensor / Auditor / Locate / Relation Mapping. It asks only whether the current URLConnector can obtain a non-empty textual snapshot.

## Selection rule

A frozen ordered candidate pool is defined before preflight. Candidates are divided into `NEAR`, `BOUNDARY`, and `FAR_CONTROL` strata.

Within each stratum, select the first two candidates in manifest order that satisfy the acquisition viability gate. No Sensor, Auditor, Kernel, CognitiveEffect, Attention, or probability-map output may be observed before selection.
## Acquisition viability gate

A candidate is `PREFLIGHT_PASS` iff:

- `ingest_url()` completes without exception;
- canonical text is non-blank;
- `content_chars >= 1000`.

HTTP 403, parser/fetch failure, blank content, or sub-1000-character snapshots are `PREFLIGHT_FAIL` and are skipped without replacement outside the frozen pool.

Content length and hash are recorded for reproducibility but are not used to rank passing candidates.

## Candidate strata

`NEAR` intentionally targets embodied AI / multi-agent systems close to the current Kernel. `BOUNDARY` targets adjacent agent/AI workflows without an a priori material cognitive effect. `FAR_CONTROL` targets high-quality scientific information outside the active Kernel.
