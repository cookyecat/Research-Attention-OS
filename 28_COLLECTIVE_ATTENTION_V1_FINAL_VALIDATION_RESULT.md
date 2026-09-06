# Collective Attention Salience (P) — Estimator v1 Final Validation Result

Status: **CLOSED / PASS — ESTIMATOR v1 ACCEPTED FOR PHASE II-B**  
Date: 2026-09-07  
Semantic baseline: `22_COLLECTIVE_ATTENTION_SALIENCE.md`  
Evidence interface freeze: `25_COLLECTIVE_ATTENTION_EVIDENCE_INTERFACE_V1_FREEZE.md`  
Estimator freeze: `26_COLLECTIVE_ATTENTION_ESTIMATOR_V1_FREEZE.md`  
Fresh validation protocol: `27_COLLECTIVE_ATTENTION_V1_FINAL_VALIDATION.md`

> Decision: P estimator v1 passed its post-freeze first-run controlled validation with all pre-registered gates satisfied. Stop further synthetic P tuning and move to integrated no-Delta AWARE validation.

---

## 1. Frozen provenance

```text
estimator_version                  collective-attention-estimator-v1
prompt_version                     collective-attention-v1
profile_id                         collective-attention-profile-v1
evidence_interface_version         collective-attention-evidence-packet-v1
estimator_freeze_declaration       5a08a0d8ab2700a56d91437797b664a53f842ea0
fresh_template_commit              e57b403fcacb1ff8f49aad23fe78a7266859c06a
human_gold_commit                  1b6bfb23a84411701cbee84caecf271e672e807b
measurement_git_head               550088ec4e9fafd1e39ca7017bd0dc2b5f5fad87
prompt_sha256                      0fbc1c9c935e5cf31a98b77a0a6a9f5b99ff7473906a7e438e834f278d193b67
actual_model                       deepseek-v4-flash
thinking                           disabled
temperature                        0.1
```

Local first-run artifact:

```text
eval/live/results/collective_attention_v1_final_fresh_first_run.json
```

Artifact SHA256 from the measured file supplied for archival:

```text
90fcae3dedebd25763f64ee13cf5f39ccbdb53b94a94f4aa36f14f433ab300f5
```

The result artifact should be committed unchanged from the first-run file; do not regenerate or overwrite it.

---

## 2. Pre-registered gate and result

| Metric | Gate | Result |
|---|---:|---:|
| Exact accuracy | >= 10/12 | **12/12 = 1.0** |
| SALIENT recall | >= 0.80 | **6/6 = 1.0** |
| NOT_SALIENT recall | >= 0.80 | **6/6 = 1.0** |
| Insufficient-evidence outputs | 0 | **0** |
| Technical failures | 0 | **0** |
| Clear repeated semantic failure | none | **none observed** |

Prediction balance matched Human Gold exactly:

```text
Human Gold       6 SALIENT / 6 NOT_SALIENT
Estimator        6 SALIENT / 6 NOT_SALIENT
False SALIENT    0
False NOT        0
```

All 12 cases were scorable. No transport retry was required.

---

## 3. Semantic coverage observed in the first run

The first run correctly preserved all principal frozen P boundaries represented in PF1-PF12.

### 3.1 Reference-scale normalization

PF1 vs PF2 preserved the distinction between the same approximate absolute attention count inside a ~400-person specialist constituency versus a several-hundred-thousand-person broad field.

Observed behavior supports:

$$
\boxed{AbsoluteAttention \neq P}
$$

and constituency-relative penetration as the relevant reference frame.

### 3.2 Exposure is not genuine attention

PF3 rejected large paid/autoplay exposure with negligible meaningful engagement/search/spread, while PF4 accepted broad voluntary viewing, engagement, search, and independent spread.

Observed behavior supports:

```text
Exposure != Attention
ViewCount != P
Paid/forced reach != genuine collective attention
```

### 3.3 Temporal inertia

PF5 remained SALIENT under stable high attention without positive growth. PF6 exited salience only after sustained multi-week decay and return to baseline.

Observed behavior supports:

$$
\boxed{ShortTermNegativeVelocity \neq AttentionLoss}
$$

while allowing sustained decay to end salience.

### 3.4 Emerging salience

PF7 was correctly judged SALIENT from rapidly forming specialist attention despite modest absolute volume, based on high constituency-relative institutional/forum/search uptake.

### 3.5 Missing channel is not zero

PF9 was correctly judged from strong structural field evidence despite unavailable social-platform telemetry; PF10 was NOT_SALIENT because the channels that were actually checked showed no meaningful uptake.

Observed behavior supports:

$$
\boxed{Unavailable \neq Zero}
$$

### 3.6 Synthetic activity is not genuine attention

PF11 rejected bot/duplicate-dominated raw volume; PF12 accepted smaller but broad independent human participation plus search/community/trend evidence.

---

## 4. What this establishes

This result supports the following bounded claim:

> The frozen P semantic contract, represented through frozen Evidence Packet v1, was implemented cleanly by P estimator v1 on a balanced post-freeze controlled holdout.

It does **not** establish 100% open-world accuracy.

PF1-PF12 are controlled frozen Evidence Packets. Future product risk moves increasingly toward real sensor/evidence acquisition quality: event clustering, incomplete source coverage, duplicated evidence, noisy telemetry, constituency-prior error, temporal misalignment, and manipulation detection.

Canonical systems interpretation:

```text
P(E,t)                  theoretical latent state — FROZEN
EvidencePacket(E,t)     sensor boundary — FROZEN v1
P-hat(E,t)              state estimator — ACCEPTED for Phase II-B controlled use
real-world collectors   future major uncertainty
```

---

## 5. Research decision

```text
P semantic contract            CLOSED / FROZEN
Evidence Packet v1             FROZEN
P estimator v1                 ACCEPTED FOR PHASE II-B
Fresh validation               PASS — 12/12
SALIENT recall                 6/6
NOT_SALIENT recall             6/6
Insufficient evidence          0
Technical failures             0
Repeated semantic failure      NONE
Further synthetic P tuning     STOP
```

Do not create additional synthetic P sets merely to increase confidence or report a larger score. Revisit P implementation only if integrated validation or real-world dogfooding exposes a repeated attributable failure mode.

---

## 6. Next pointer

The no-cognitive-change AWARE gate is already frozen as:

$$
\boxed{AWARE \iff S \land (D \lor P)}
$$

and the production scheduler already contains the equivalent oracle-awareness wiring through `AwarenessSignals`.

Next work:

```text
D semantics  CLOSED; estimator v3 residuals known / not certified
S            CLOSED; estimator v1 accepted
P            CLOSED; estimator v1 accepted
        ↓
INTEGRATED no-Delta AWARE VALIDATION
        ↓
component attribution + final AWARE/DROP outcome
```
