# Phase 6 — Raw Source → Attention Action Vertical Slice

Status: **ACTIVE RESEARCH / PREREGISTERED DEVELOPMENT INTEGRATION**  
Date: 2026-09-08

## 1. Phase objective

RAOS has separately developed and frozen the semantic roles of Sensor, Auditor, D, S, P,
Delta, and Attention Policy. The next frontier is system composition, not another isolated
component benchmark.

Target vertical slice:

```text
Raw Source
  → Semantic Sensor v0.2.3
  → Semantic Evidence Auditor v0.1.1
  → audited event semantics
  → D v4 / S v1 / P v1
  → frozen no-Delta gate
  → DROP / AWARE
```

Primary question: can a real article reach a causal, reviewable attention action without
silently changing any frozen semantic law?
## 2. D v4 uplift preflight

A development-only IA1–IA12 regression was run before raw-source integration.
Those cases are already consumed and are not fresh validation evidence.

Flash with D v4/profile v4 reproduced the old D pattern: 75% exact, with IA5/IA6/IA9
mismatching the old labels. Pro improved clause application on IA5 but still classified
IA6 as OUT.

Interpretation:

```text
D semantics                         CLOSED / FROZEN
D v4 user profile                   ACTIVE CALIBRATED PROFILE
D clause application                KNOWN MODEL/ESTIMATOR RESIDUAL
IA9 old Human Gold                  SUPERSEDED BY LATER USER PROFILE CALIBRATION
IA5 market-structure recognition    IMPROVED WITH PRO
IA6 energy × market boundary        STILL OPEN / NON-BLOCKING
```

Do not attribute this known D boundary residual to the Semantic Sensor.
The Phase 6 raw-source development set uses strong AI/robotics anchors and does not depend
on the IA6 boundary.
## 3. Routing boundary

D/S/P operate on events. The Sensor also emits non-event epistemic units.
Phase 6A therefore routes **Audited Event Frames only** into the no-Delta attention-world
path. A source with no event frame is not forced into D/S/P; it is marked for the later
Delta/cognitive path.

Downstream event text must be built from semantic subobjects whose cited evidence passed
the Auditor. The unaudited convenience `event.summary` must not silently bypass the gate.

Auditor remains bounded:

```text
Review != Retrieval != Repair
INSUFFICIENT != FALSE
```

Rejected objects remain diagnostic evidence and are omitted from the audited downstream
projection; the Auditor never searches the raw source for replacements.

## 4. P boundary

P cannot be inferred from article wording. Phase 6A accepts an explicit external P Evidence
Packet template per event. Event semantics are injected from the audited event projection;
constituency/attention observations remain a separate sensor input.

For the first vertical slice, controlled development P packets are allowed. They test the
wiring and attribution path, not real-world current-attention accuracy.
## 5. Development sources and stopping rule

Initial raw-source set:

```text
RS11 — AI release/news-style article
RS12 — robotics industry interview
RS15 — promotional robotics media article
RS05 — technical tutorial control; expected to exercise non-event / Delta routing
```

RS13/RS14 remain RESERVED and unconsumed.

Run order:

1. Sensor v0.2.3 with DeepSeek Pro working baseline.
2. Audit event-frame provenance edges with Auditor v0.1.1.
3. Build deterministic audited event projections.
4. Run D v4 + S v1 + controlled P v1 packet through the real Scheduler.
5. Attribute failures before changing any component.
6. Only after 6A is executable, connect Delta and four-way Attention Policy.

Methodology:

> **Do not optimize a known component residual unless it becomes causal for the vertical slice.**

> **A vertical slice is successful when its failures are attributable, not when every output is flattering.**
