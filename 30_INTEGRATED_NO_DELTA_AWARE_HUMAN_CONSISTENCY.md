# Integrated no-Delta AWARE — Human Consistency Check

Status: **RECORDED BOUNDARY RESIDUALS / DO NOT RETUNE YET**  
Date: 2026-09-07  
Fresh Human Gold commit: `964ef46e9ee54caa7d1957160053f6560cd5476b`  
Frozen gate: `AWARE iff S AND (D OR P)`

## 1. Purpose

Before any integrated estimator run, compare the independently elicited Human component labels `(D,S,P)` with the independently elicited Human final `AWARE/DROP` judgment.

This is not an estimator measurement. It is a pure Human-policy consistency diagnostic.

## 2. Result

Across IA1-IA12:

```text
Human final judgments                12
Frozen-gate agreement                10
Frozen-gate disagreement              2
Agreement rate                    10/12 = 0.8333333333
```

Human final class balance:

```text
AWARE   5
DROP    7
```

Frozen-gate predictions from Human D/S/P:

```text
AWARE   5
DROP    7
```

The aggregate class balance is identical, but two individual cases swap sides.

## 3. Boundary residuals

### IA4 — Human AWARE, frozen gate DROP

```text
D = IN
S = NOT_MATERIAL
P = SALIENT
Human Final = AWARE
Frozen gate = DROP
```

The event is a highly salient cosmetic game skin. It is inside the user's standing game radar and has genuine collective attention, but it is not materially consequential under the frozen S definition.

This residual challenges the necessity of `S=1` for every no-Delta AWARE judgment. It does not by itself justify changing the gate because the Human annotator reported some uncertainty on the integrated cases.

### IA12 — Human DROP, frozen gate AWARE

```text
D = OUT
S = MATERIAL
P = SALIENT
Human Final = DROP
Frozen gate = AWARE
```

The event is a materially consequential and highly salient commercial-space regulatory change, while commercial space is explicitly outside the current standing radar.

This residual challenges whether `P=1` should independently substitute for `D=1` in every out-of-radar case. Again, one boundary judgment is insufficient to reopen the frozen gate.

## 4. Important interpretation

The two residuals point in opposite directions:

```text
IA4  suggests S may sometimes be too strict as a mandatory gate.
IA12 suggests P may sometimes be too permissive as a substitute for D.
```

Therefore there is no simple one-sided patch justified by the current evidence.

Do not respond by adding weights, exceptions, or a larger ontology.

## 5. Separate component-semantic note

IA10 was labeled:

```text
D = OUT
```

even though the frozen Standing Radar profile contains a direct-family affiliation clause for institutions. Because the case explicitly states a stable direct-family affiliation, this is a tension between the fresh Human label and the frozen D semantic contract.

Preserve the label as Human Gold. Attribute any D disagreement explicitly rather than silently rewriting either side.

## 6. Research decision

```text
Human Gold                         FROZEN AS SUPPLIED
Frozen AWARE gate                  UNCHANGED
Human-gate consistency             10/12
Boundary residuals                 IA4, IA12
Potential D semantic-policy tension IA10
Estimator run                      STILL UNSEEN
```

The first integrated run remains an attribution run, not a certification gate. Proceed without retuning D/S/P, the gate, or the Human Gold.

After real end-to-end predictions exist, classify each residual as:

```text
component estimator error
masked component error
causal final error
cross-component policy residual
Human policy boundary / noisy Gold
```

Only repeated real-world or fresh-integrated evidence should reopen the frozen gate.
