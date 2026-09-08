# Phase 8C.1 — Real-Web Dogfood Acquisition Result

Status: **CLOSED / ACQUISITION SUFFICIENT**
Date: 2026-09-09
Measurement SHA: `e5093cd8592c4c05bfb67e7c7acf9dceb0f329ad`

## 1. Question

Can the narrow continuous loop operate on real public-web pages rather than controlled text fixtures, while keeping event/relevance relations supervised and auditable?

This experiment intentionally did **not** claim that the Phase 7A Sensor v0.2.6 was already in production. The current production `run_pipeline()` still used its legacy extraction path.
## 2. Real sources

The canonical dogfood used four real public pages:

```text
A  Microsoft Azure — GPT-6 Astra in Microsoft Foundry
C  OpenAI Deployment Safety Hub — GPT-6 Astra system-card material
D  The Verge — independent GPT-6 Astra release coverage
X  Google Research — AgentHands (unrelated control)
```

All four selected pages produced non-empty extracted text through the production URLConnector.
## 3. Canonical result

The real-web continuous sequence passed every preregistered condition:

```text
C secondary same-event material
-> SECONDARY
-> independent_sources = 1
-> KEEP_ACTIVE

X unrelated real source
-> no Watch match
-> ordinary analysis

D independent same-event source
-> INDEPENDENT
-> independent_sources = 2
-> PROMOTED
```

The Watch obligation remained singular and cumulative.
## 4. Real acquisition residuals observed during preflight

Real-web dogfood immediately exposed three distinct acquisition failure modes:

```text
transport blocked:          openai.com main-site pages returned HTTP 403
parser-empty success:       Microsoft Community Hub fetched but extracted 0 chars
slow successful acquisition: Azure article fetch took about 12.1 s in the canonical run
```

These are operational perception failures, not Attention Policy failures. They should remain separately observable rather than being collapsed into one generic ingestion error.
## 5. Decision

Phase 8C.1 is sufficient for real acquisition. Do not broaden the crawler yet.

A newly discovered integration gap becomes the next target:

> **Phase 7A Sensor v0.2.6 is still an eval/live working baseline; production `run_pipeline()` continues to use legacy provider extraction.**

Therefore Phase 8C.2 will build a narrow production Sensor bridge and controlled A/B before changing any default path.
