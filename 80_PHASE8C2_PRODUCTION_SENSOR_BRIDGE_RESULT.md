# Phase 8C.2 — Production Sensor Bridge Result

Status: **ACTIVE / TIER-2 PASS / DECISION-STABILITY RESIDUAL ATTRIBUTED / PRODUCTION PROMOTION BLOCKED**
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

## 6. Packaging v0.3 validation and repaired Tier-2 pass

Measurement SHA: `d9e0dc15eca9ce7986b7d6cb8232c5f2e75f5f0a`

A Sensor-only live probe on the exact Azure A source passed without repair after URL provenance packaging v0.3: 38 stable PARA blocks, maximum payload 563 characters, one event frame, 12 non-event units, and no schema events.

The full A/C/D/X real-world continuity run then passed on the first pair with no confirmation required. Artifact: `eval/live/results/phase8c2_real_world_continuity_ab_v0_1/phase8c2_real_world_continuity_ab_v0_1_20260908T205328Z.json`; SHA256: `9b1804290de9bff55316d9622250f908356d68b2bf0d3b65383c2cef1431eeb9`. All four production-normalized hashes and character counts matched Phase 8C.1. Legacy and Sensor arms preserved `C SECONDARY -> KEEP_ACTIVE`, `X unrelated -> ordinary analysis`, `D INDEPENDENT -> PROMOTED`, a single Watch obligation, identical WATCH history, and final `PROMOTED` state. All four analysis identities were distinct across arms and Sensor event-frame counts were fully observable.

Exact-SHA relevant regression after the measurement passed `70 passed, 1 deselected, 1 warning`; the deselected test is the pre-existing Case K residual already causally excluded from Phase 8C.2.

## 7. Post-gate diagnostic — ExtractionResult separation fidelity

The Tier-2 methodology preregistered ungolded cognitive differences on A/C/D/X as diagnostics rather than pass/fail gates. One such difference remains important: on initial Azure A, legacy produced `AWARE / SUMMARY` while Sensor produced `DROP / NONE`; C, X, and D were cognitively identical.

Attribution shows both arms had no Kernel match. Legacy produced an `OPEN_NEW` candidate with reason `No current Kernel target; possible new question or model candidate.` and contained one `technical_claims` entry. The audited-units adapter, however, reconstructs only `claims / observations / inferences` and hard-codes source claims as `FACTUAL`; it leaves production separation fields such as `technical_claims` empty. Those fields are decision-active in Impact/Scheduler/Delta.

Therefore the A-initial difference is a bridge schema-translation fidelity gap, not evidence that the compact Sensor representation is intrinsically too small. The next remediation must restore production separation fields only from Auditor-admitted claim statements, without allowing raw unaudited source text back into downstream cognition. Sensor v0.2.6, Auditor v0.1.1, Delta, D/S/P, WATCH, and Attention remain frozen.


## 8. Bridge v0.2 separation restoration and final Tier-2 pass

The production bridge was upgraded to `phase8c2-production-sensor-bridge-v0.2` by rebuilding production decision-active separations exclusively from Auditor-admitted claims. The legacy Phase 6B adapter remained unchanged.

A targeted Azure-A causal retest restored the same `OPEN_NEW -> AWARE / SUMMARY` landing as legacy while preserving Auditor authority. The remaining `future_plans` field difference was traced to a legacy rhetorical `will be` classification and was not forced into field equality.

The full Tier-2 A/C/D/X continuity rerun at measurement SHA `0622bc4be9b5b80782522e0a81a234eb77713969` passed all structural gates and matched cognitive diagnostics at every point. Artifact: `eval/live/results/phase8c2_real_world_continuity_ab_v0_1/phase8c2_real_world_continuity_ab_v0_1_20260908T211120Z.json`; SHA256: `73f6a1d9a60b1daf365435b894e2fefa03ea38fcc28f8dd2a58056f378a5e66b`.

```text
A_initial   legacy AWARE/SUMMARY   sensor AWARE/SUMMARY
C_recheck   legacy WATCH/WATCH     sensor WATCH/WATCH
X_ordinary  legacy DROP/NONE       sensor DROP/NONE
D_recheck   legacy AWARE/SUMMARY   sensor AWARE/SUMMARY
```

Tier 2 therefore validates real-web acquisition, audited Sensor transport, event observability, continuous WATCH continuity, and the bridge v0.2 separation projection on this supervised continuity set.

## 9. Tier-1 RS15 stability attribution

A fresh Tier-1 sentinel rerun at the same bridge-v0.2 SHA produced `REINFORCE(B2) -> WATCH` for RS15 in 3/3 confirmation pairs instead of canonical `REINFORCE(Q2)`. Subsequent controlled attribution showed that this should **not** be interpreted as a deterministic event-projection or bridge-only regression.

The complete attribution is archived in `81_PHASE8C2_DECISION_STABILITY_ATTRIBUTION_RESULT.md`. Key findings:

```text
RS15 fixed exact semantic input:  Q2 3/6, B2 3/6
RS15 six fresh Flash realizations: Q2 / B2 / OPEN_NEW all observed
RS05 fresh end-to-end:             canonical 3/6, DROP 3/6
RS05 frozen Phase7A semantics:     canonical 6/6
RS11 fresh end-to-end:             DROP 6/6
```

The critical RS15 Q2 predicate remained Auditor-admitted; the instability is not a simple loss of that relation. Current evidence supports a compound mechanism:

$$
\boxed{\text{Representation Variance}\times\text{Decision Sensitivity}\rightarrow\text{Landing Instability}}
$$

This does not reopen the Phase 7A formula `Decision-Sufficient Semantic Precision = Evidence Fidelity + Scope Fidelity + Relational Fidelity`. Stability is a production measurement/readiness property of the stochastic implementation.

## 10. Current decision

Phase 8C.2 remains ACTIVE. The production default remains legacy. Do not tune Sensor v0.2.6, Auditor v0.1.1, Delta, or Attention Policy from RS15 alone. Before production promotion, broaden the repeated decision-stability / representation-robustness gate across multiple canonical decision-bearing and negative-control cases.

After the attribution runners were added, the broader relevant regression passed `72 passed, 1 deselected, 1 warning`; the deselected Case K residual remains pre-existing and causally outside Phase 8C.2.
