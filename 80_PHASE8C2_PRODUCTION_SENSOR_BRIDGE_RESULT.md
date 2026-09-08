# Phase 8C.2 — Production Sensor Bridge Result

Status: **ACTIVE / TIER-1 PASS / TIER-2 PACKAGING FAILURE ATTRIBUTED**
Date: 2026-09-09

## 1. Research question

Can the validated Phase 7A Sensor v0.2.6 + Auditor v0.1.1 path replace legacy production extraction at the `ExtractionResult` seam without changing frozen downstream cognition or Attention semantics?

The integration is evaluated in two layers:

```text
Tier 1 — canonical causal sentinels
RS05 / RS15 / RS11 / RS12

Tier 2 — Phase 8C.1 real-world continuity
A / C / D / X through the full arrival/WATCH responsibility loop
```

The production default remains legacy while Phase 8C.2 is active.
## 2. Tier-1 production decision-fidelity result

Valid measurement SHA: `934ff6a42ab480446b637765ca1139994e38ca01`

Artifact:
`eval/live/results/phase8c2_production_sensor_bridge_ab_v0_1/phase8c2_production_sensor_bridge_ab_v0_1_20260908T194708Z.json`

SHA256: `c605cf190615330e83d24899b59f2870dd57b94be2bd844ccd7f154521cf229b`

```text
RS05  legacy CHALLENGE(CF-B-PERF) / ENGAGE
      sensor CHALLENGE(CF-B-PERF) / ENGAGE          PASS

RS15  legacy REINFORCE(Q2) / WATCH
      sensor REINFORCE(Q2) / WATCH                  PASS

RS11  legacy NONE / DROP
      sensor NONE / DROP                            PASS

RS12  boundary jitter with direction reversal; no stable bridge-attributable divergence
```
Tier 1 also produced the first production-pipeline evidence for decision-bearing compression:

```text
RS05 legacy: 90 claims + 7 observations + 12 inferences
RS05 sensor: 8 Auditor-admitted units
final decision: identical

RS15 legacy: 19 claims + 2 observations + 2 inferences
RS15 sensor: 13 Auditor-admitted units
final decision: identical
```

This supports the engineering principle:

> **好的 Sensor 不是把事实灌满下游，而是在决策真正依赖的地方，精准交付正确的语义状态。**

> **A smaller representation is sufficient when it preserves the relation that the downstream decision actually depends on.**

This is positive production evidence, not yet a universal theorem about all sources or decisions.
## 3. Tier-2 real-world continuity — first run

Measurement SHA: `98d2bbf6c1beb2e32c17f642106431ac4228bdbe`

Artifact:
`eval/live/results/phase8c2_real_world_continuity_ab_v0_1/phase8c2_real_world_continuity_ab_v0_1_20260908T201947Z.json`

SHA256: `599e5ef27bfd1191e28839f27542c81ef2a86693f021d5a912b9e6e364f876f7`

The production-normalized continuity gate passed for all four Phase 8C.1 pages. Both `content_hash` and extracted character count matched the canonical acquisition:

```text
A  6614  4ed8f2d6...e27853
C  5950  5eee6de6...93fac
D  6375  942a9a81...0328
X  6064  054ff33b...3147
```

Therefore the Tier-2 failure is not attributable to real-web content drift.
The legacy arm reproduced the Phase 8C.1 responsibility sequence on all three confirmation pairs:

```text
C  SECONDARY   -> KEEP_ACTIVE
X  unrelated   -> ordinary analysis
D  INDEPENDENT -> PROMOTED
final Watch status = PROMOTED
```

The Sensor arm failed before Auditor/WATCH/downstream on the initial Azure source in all three pairs:

```text
ProductionSensorBridgeError
-> Sensor failure
-> failure_kind = schema_validation
-> SemanticExtractionBatchV0_2 invalid after minimal-sufficient repair
```

Thus this first Tier-2 run is **not** evidence that Sensor semantics regress real-world WATCH behavior. The candidate never reached the decision system.
## 4. Attribution — production source packaging granularity

A direct Sensor-only diagnostic on the exact same Azure A source exposed the concrete validation errors on both initial and repair attempts:

```text
non_event_units[8].supports[0].support_excerpt  > 600 chars
non_event_units[11].supports[0].support_excerpt > 600 chars
```

The production URLConnector had extracted 38 meaningful newline-separated blocks from the page, but the bridge reused `_render_text_paragraphs()`, whose paragraph splitter only recognizes blank-line separation. The acquired URL text contains single newlines rather than blank lines, so the whole 6614-character article became one provenance unit:

```text
[PARA 0001]
<entire article>
```

This made minimal source-grounded excerpts unnecessarily coarse and caused the Sensor to violate the existing `support_excerpt <= 600` contract even after repair.
The causal layer is therefore:

```text
URLConnector text shape
        ↓
production Sensor source packaging
        ↓
provenance granularity collapse
        ↓
excerpt-length schema failure
```

Not:

```text
Sensor semantic reasoning
Auditor
Locate / Delta
WATCH / Attention Policy
```

## 5. Optimization decision

Do **not** relax the 600-character evidence contract and do **not** tune Sensor v0.2.6 from this residual. Change only the production bridge packaging layer:

```text
URL source
-> preserve connector newline blocks as provenance blocks
-> split long blocks at sentence boundaries where possible
-> only use word-boundary fallback for a single overlong sentence
-> assign stable sequential PARA markers
```

Non-URL source packaging remains on the existing development-compatible paragraph renderer. The packaging version must change so the new candidate has a distinct execution fingerprint before rerunning Tier 2.
