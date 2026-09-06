# Collective Attention Salience (P) — Estimator v1 Final Fresh Validation

Status: **FRESH TEMPLATE FROZEN / HUMAN GOLD NEXT**  
Date: 2026-09-07  
Semantic baseline: `22_COLLECTIVE_ATTENTION_SALIENCE.md`  
Evidence interface freeze: `25_COLLECTIVE_ATTENTION_EVIDENCE_INTERFACE_V1_FREEZE.md`  
Estimator freeze: `26_COLLECTIVE_ATTENTION_ESTIMATOR_V1_FREEZE.md`

> Purpose: preserve a clean post-freeze, pre-prediction final validation of P estimator v1. The fresh Evidence Packets were authored only after the P semantic contract, Evidence Packet v1, prompt/profile, and estimator were frozen.

---

## 1. Frozen fresh template

Template:

```text
eval/live/manifest.collective_attention_final_fresh_validation.v1.template.yaml
```

Template freeze commit:

```text
e57b403fcacb1ff8f49aad23fe78a7266859c06a
```

Fresh case IDs:

```text
PF1-PF12
```

PC1-PC24 are development/calibration evidence and are excluded from fresh reporting.

The template contains:

- frozen Event semantics;
- frozen Objective Attention Constituency prior;
- frozen collection coverage / missingness;
- frozen current attention observations;
- frozen recent attention history;
- no Human label;
- no estimator prediction.

The expected first-run artifact did not exist before fresh authoring:

```text
eval/live/results/collective_attention_v1_final_fresh_first_run.json
```

---

## 2. Estimator identity frozen before holdout authoring

```text
estimator_version          collective-attention-estimator-v1
prompt_version             collective-attention-v1
profile_id                 collective-attention-profile-v1
evidence_interface_version collective-attention-evidence-packet-v1
```

Estimator freeze declaration commit:

```text
5a08a0d8ab2700a56d91437797b664a53f842ea0
```

Estimator implementation commit:

```text
cea9fa3dd3763977be578046106817a47b6b6794
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

No PF1-PF12 case text or label existed when these estimator artifacts were frozen.

---

## 3. Human Gold protocol

The Human annotator must judge the frozen packet only.

Question:

> **Ignoring whether the event is intrinsically important and ignoring whether the user personally cares, does the supplied evidence indicate that, at the stated time, the event has already formed or is clearly forming a salient state of genuine collective attention within its objective attention constituency?**

Allowed semantic labels:

```text
SALIENT
NOT_SALIENT
```

The Human should use the event's objective constituency as the reference scale, not total population by default.

The Human should distinguish genuine attention from paid/forced exposure, bot/duplicate activity, and raw volume.

The Human should preserve temporal inertia: a short-term decline is not automatically loss of salience, while sustained return to ordinary baseline can support NOT_SALIENT.

The Human should treat unavailable channels as unknown rather than zero.

Do not consider:

```text
D / user interest / standing radar
S / event importance / material consequence
sentiment / stance / approval
AWARE / DROP / WATCH / ENGAGE
```

Labels must be elicited before any scored estimator prediction on PF1-PF12.

---

## 4. Pre-registered success criterion

Primary set size:

```text
12 cases
```

The fresh packets are intentionally authored to be scorable rather than to probe the estimator's insufficient-evidence escape hatch.

Pre-registered gate:

```text
Exact accuracy                  >= 10/12 = 0.8333333333
SALIENT recall                  >= 0.80
NOT_SALIENT recall              >= 0.80
insufficient_evidence outputs   0
technical failures              0
clear repeated semantic failure none
```

The class balance is **not assumed before Human elicitation**.

If the Human Gold later happens to be balanced 6/6, each class recall threshold requires at least 5/6 correct in that class. Do not use this possibility to modify the case set after labels are seen.

---

## 5. Fresh-set coverage design

The fresh set was authored to cover the frozen P semantics using new scenarios rather than reusing PC development cases.

Coverage includes:

```text
reference-scale normalization
specialist-domain attention
broad-field low penetration
forced/paid exposure vs genuine attention
stable established salience
sustained attention decay
clearly emerging salience
isolated source attention without community uptake
missing channel != zero
structural field penetration without platform telemetry
bot/duplicate volume vs organic human uptake
```

These are design dimensions, not Human labels and not expected predictions.

---

## 6. Packet-integrity check

Test:

```text
backend/tests/eval/test_collective_attention_fresh_template_v1.py
```

Commit:

```text
18c72bfa3ce9ca5782500e6c16d0a301b949f2de
```

The test performs no model call and contains no Human Gold. It checks only:

- exact estimator/profile/interface provenance;
- 12 unique PF cases;
- no Human-Gold fields in the template;
- every packet validates against frozen Evidence Packet v1;
- every primary packet contains enough explicit current observations to be intended as scorable.

This is measurement plumbing, not estimator evidence.

---

## 7. Strict next sequence

```text
P semantic contract              FROZEN
Evidence Packet v1               FROZEN
P estimator v1                   FROZEN
Fresh PF1-PF12 template          FROZEN
Scored P predictions             UNSEEN / NOT RUN
        ↓
HUMAN LABEL PF1-PF12             NEXT
        ↓
freeze Human Gold manifest
        ↓
validate provenance / dry-run only
        ↓
run first scored estimator measurement exactly once
        ↓
write-once first-run artifact
        ↓
score against pre-registered gate
        ↓
residual attribution before any estimator change
```

No estimator prompt/profile/interface change is allowed after Human Gold or first-run results merely to improve the score.

---

## 8. Residual attribution taxonomy

For every first-run residual, classify before changing implementation:

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

If the gate passes with no repeated semantic failure mode, P estimator v1 is eligible for acceptance for Phase II-B and the project can move to full `S AND (D OR P)` no-Delta AWARE validation.
