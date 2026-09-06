# Collective Attention Salience (P) — Estimator v1 Freeze

Status: **P ESTIMATOR v1 — FROZEN / FRESH HOLDOUT NEXT**  
Date: 2026-09-07  
Semantic baseline: `22_COLLECTIVE_ATTENTION_SALIENCE.md`  
Evidence interface freeze: `25_COLLECTIVE_ATTENTION_EVIDENCE_INTERFACE_V1_FREEZE.md`

> Purpose: freeze the first direct engineering estimator of the already-frozen theoretical P variable before any fresh scored P holdout is authored or measured.

## 1. Frozen estimator identity

```text
estimator_version          collective-attention-estimator-v1
prompt_version             collective-attention-v1
profile_id                 collective-attention-profile-v1
evidence_interface_version collective-attention-evidence-packet-v1
```

Implementation:

```text
eval/live/collective_attention_v1.py
```

Estimator implementation commit:

```text
cea9fa3dd3763977be578046106817a47b6b6794
```

Profile:

```text
eval/live/collective_attention_profile.v1.yaml
```

Final profile plumbing-fix commit:

```text
0093f8fb471d16e9b13265b4737f8dd1a06f3118
```

Evidence Packet v1 freeze declaration commit:

```text
4a858a82693767d001f06952f8f48eba702d33a2
```

Prompt SHA256:

```text
0fbc1c9c935e5cf31a98b77a0a6a9f5b99ff7473906a7e438e834f278d193b67
```

## 2. Frozen model-call parameters

```text
thinking            disabled
reasoning_effort    null
timeout_seconds     60.0
temperature         0.1
response_format     json_object
structured_schema   CollectiveAttentionV1Response
```

The concrete provider/model identity is recorded by the future invocation manifest/result artifact and must be held fixed for the first scored run.

## 3. Estimator architecture

The estimator consumes only a validated frozen Evidence Packet v1:

```text
Event
ConstituencyPrior
CollectionContext
CurrentAttentionEvidence
RecentAttentionHistory
        ↓
direct joint semantic judgment
        ↓
SALIENT / NOT_SALIENT
```

It does **not** implement a mandatory numeric penetration formula, a weighted attention score, or hard symbolic gates for constituency, evidence type, or temporal state.

The theoretical model remains:

$$
P(E,t)=LatentSalience(R_E(\le t))
$$

The estimator is only an approximation:

$$
\hat P=Estimator(EvidencePacket_v1)
$$

## 4. Frozen semantic behavior in the prompt

Estimator v1 must preserve these principles:

- constituency is determined from event semantics, not user preference or post-hoc denominator shrinking;
- attention is interpreted relative to the correct constituency scale;
- raw volume, impressions, views, bots, duplicates, or forced exposure do not automatically imply genuine attention;
- structural field/community uptake can establish attention without exact population telemetry;
- stable high attention can remain SALIENT without positive velocity;
- clearly emerging attention can be SALIENT before absolute volume is large;
- short-term decline does not by itself erase established salience;
- sustained decay can end salience;
- unavailable evidence is unknown, not zero;
- D, S, sentiment, stance, event importance, and downstream attention action are excluded;
- controlled evaluation uses only the supplied frozen packet and does not browse for unstated current evidence.

## 5. Measurement-status separation

The semantic target remains binary:

```text
SALIENT / NOT_SALIENT
```

Estimator observability is separate:

```text
measurement_status:
scorable / insufficient_evidence
```

Technical/input failures are also non-scorable.

Critical invariant:

> `insufficient_evidence` must not be silently converted into `NOT_SALIENT`.

The response schema requires a P label iff `measurement_status=scorable` and forbids a semantic label when `measurement_status=insufficient_evidence`.

## 6. Evidence-boundary validation

The implementation validates Evidence Packet v1 before any model call with Pydantic `extra=forbid` at the packet and nested-block levels.

This makes the documented sensor boundary executable: extra fields such as `D`, `S`, `material_consequence`, or `predicted_P` cannot silently enter controlled evaluation packets.

Invalid packets fail before the model is called.

## 7. Regression status before freeze

Test file:

```text
backend/tests/eval/test_collective_attention_v1.py
```

Test commit:

```text
e784c4570091d422a3841e56767d67f829f22247
```

GitHub Actions run:

```text
34053156614
```

At freeze preparation time:

```text
backend-sqlite Test step    SUCCESS
frontend Typecheck/Build    SUCCESS
backend-postgres            still running
```

No live P model measurement has been performed by these tests.

## 8. Development-data firewall

PC1–PC24 are semantic/interface calibration evidence only.

They are now development data and must not be reported as fresh estimator generalization evidence.

The estimator prompt/profile contain no PC case IDs or case text.

Strict next sequence:

```text
P semantics frozen
Evidence Packet v1 frozen
Estimator v1 frozen
        ↓
AUTHOR NEW FRESH P HOLDOUT
        ↓
Human labels before predictions
        ↓
freeze Human Gold
        ↓
first scored estimator run exactly once
        ↓
residual attribution
```

## 9. Change policy

From this freeze forward, do not alter the estimator prompt, profile, Evidence Packet v1, model parameters, or decision semantics after seeing fresh-case labels/predictions merely to improve score.

If a fresh first-run failure appears, first attribute it as one of:

```text
semantic-definition failure
constituency-application failure
attention-evidence interpretation failure
inertia/history interpretation failure
insufficient-evidence policy failure
sensor/interface failure
measurement/plumbing failure
human-policy boundary / noisy Gold
```

Only then decide whether a v2 is justified.

## 10. Current pointer

```text
P semantic contract         FROZEN
Evidence Packet v1          FROZEN
P estimator v1              FROZEN
Fresh P holdout              NOT YET AUTHORED
Fresh Human Gold             NOT YET ELICITED
Scored P predictions         UNSEEN / NOT RUN

              ↓
       FRESH HOLDOUT AUTHORING
```
