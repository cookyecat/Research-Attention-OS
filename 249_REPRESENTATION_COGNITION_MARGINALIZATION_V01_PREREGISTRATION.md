# RAOS Representation–Cognition Marginalization V0.1 — Preregistration

Status: **PREREGISTERED / SHADOW MATH ONLY / NO PRODUCTION ATTENTION CHANGE**  
Date: 2026-09-19

## 1. Goal

Connect the two probability structures without modifying the validated Phase10 conditional cognition kernel.

Representation uncertainty:

```math
P(R | E_{<=t})
```

Cognitive stochasticity:

```math
P(T,A | R,K,Theta)
```

Target composition:

```math
P(A | E_{<=t},K,Theta)
=
\int P(A | R,K,Theta) dP(R | E_{<=t})
```

## 2. Preserve the old Phase10 kernel

Existing Phase10 code remains the conditional kernel:

```text
R fixed
→ repeated cognition realizations
→ P(T,A | R,K,Theta)
```

V0.1 must not rewrite Phase10A/B/C metrics or reinterpret their historical results.

Composition belongs outside that kernel.

## 3. No global graph enumeration

V0.1 must not enumerate every possible global Event graph.

Future experiments may vary one local irreducible representation hypothesis at a time and construct in-memory counterfactual representation variants.

No counterfactual topology is persisted.

No new database entity is introduced.

## 4. Pure categorical marginalization

For a finite set of representation scenarios R_i with normalized weights w_i and conditional Attention distributions q_i(a):

```math
q(a)
=
\sum_i w_i q_i(a)
```

This is the marginal Attention distribution.

## 5. Uncertainty decomposition

For categorical Attention A:

```math
H(A | E)
=
E_R[H(A | R)]
+
I(A;R | E)
```

Interpretation:

```text
E_R[H(A | R)]
= expected cognitive stochasticity conditional on representation

I(A;R | E)
= additional Attention uncertainty attributable to representation uncertainty
```

This decomposition is a central V0.1 diagnostic.

It distinguishes:

```text
"the world model is uncertain"
from
"cognition is stochastic even when the world model is fixed"
```

## 6. Weight semantics

The pure algebra accepts normalized scenario weights.

Two semantics must be distinguished:

### CALIBRATED_POSTERIOR

Weights may be interpreted as an approximation to:

```math
P(R_i | E)
```

### OPERATIONAL_PROXY

Weights come from an uncalibrated engineering proxy such as `representation-belief-view-v0.1`.

Results are diagnostic mixtures only.

They must not be labelled Bayesian posterior Attention probabilities and must not drive production Attention.

Current RAOS is in:

```text
OPERATIONAL_PROXY
```

mode.

## 7. V0.1 implementation boundary

Allowed:

- pure distribution normalization;
- weighted categorical mixture;
- entropy;
- expected conditional entropy;
- representation-induced mutual information;
- numerical decomposition checks;
- synthetic/unit validation.

Not allowed:

- production Attention changes;
- graph mutation;
- Event merge;
- new persistence table;
- using `projected_same_probability_proxy` as commitment authority;
- constructing large counterfactual graph spaces;
- modifying Phase10 historical results.

## 8. Promotion condition

A real RAOS shadow experiment requires both:

1. at least two explicit in-memory representation variants for the same evidence epoch;
2. the existing Phase10 conditional cognition kernel evaluated independently under each variant.

Until that adapter exists, V0.1 stops at pure composition algebra.

Do not fake a real marginalization experiment by mixing unrelated historical epochs.

## 9. Success criteria

The algebra layer is ready when:

- mixture probabilities normalize exactly within tolerance;
- identical conditional distributions yield zero representation-induced information;
- deterministic but different conditional distributions yield positive representation-induced information;
- entropy decomposition residual is numerically near zero;
- weight semantics are explicit in every result.

## 10. Non-claims

V0.1 does not claim:

- current belief proxy is calibrated;
- representation scenarios are globally exhaustive;
- local hypotheses are independent;
- Phase10 samples are exact IID;
- Attention should yet consume probabilistic representation in production.
