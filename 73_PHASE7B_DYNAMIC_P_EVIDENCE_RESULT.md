# Phase 7B — Dynamic P Evidence Result

Status: **CLOSED / SUFFICIENT FOR PHASE 7**
Date: 2026-09-08
Measurement SHA: `eea6e96b0a077fdb09f3ab8ede7f4fa8f4bf32ca`

## 1. Question

Phase 7B did not retune frozen P semantics or create another synthetic accuracy benchmark.
It asked a different state-estimation question:

> **Can the same event move through a plausible time-varying collective-attention trajectory, and can that estimated P(t) drive the frozen no-Delta Attention Policy correctly?**

All evidence in this experiment is simulated development evidence, not a claim about current real-world salience.
## 2. Controlled wiring

The dynamic P estimator consumed only frozen Evidence Packet v1 fields:

```text
current observations
+ recent observation history
+ collection coverage
+ fixed constituency prior
```

Previous P labels were not fed back as self-validating state.
For the final no-Delta gate, controls were fixed as:

```text
D = OUT
S = MATERIAL
Delta = NONE
P = dynamic estimator output
```

Therefore `P=SALIENT -> AWARE` and `P=NOT_SALIENT -> DROP` were exercised through the production Scheduler.
## 3. Results

Three repeated runs on the exact same measurement SHA used `deepseek-v4-flash`.
Across 10 preregistered time points per run:

```text
30 / 30 P judgments matched expected dynamic state
30 / 30 final DROP/AWARE actions matched
0 insufficient-evidence outputs
0 technical failures
```

Specialist-attention cycle:

```text
quiet -> NOT_SALIENT -> DROP
forming -> SALIENT -> AWARE
established -> SALIENT -> AWARE
short decline -> SALIENT -> AWARE
sustained decay -> NOT_SALIENT -> DROP
organic rebound -> SALIENT -> AWARE
```
Manipulated-exposure cycle:

```text
paid exposure -> NOT_SALIENT -> DROP
bot/duplicate trend -> NOT_SALIENT -> DROP
organic formation -> SALIENT -> AWARE
organic sustained attention -> SALIENT -> AWARE
```

This supports the frozen principles:

> **Short-term negative velocity is not attention loss.**

> **Exposure is not attention.**

> **P is a latent time-dependent state estimated from evidence history, not a copy of one current count.**
## 4. Decision

Phase 7B is sufficient for the Phase 7 objective. Do not keep expanding synthetic P cases merely to accumulate a larger score.

Remaining open-world uncertainty belongs mainly to future acquisition and state-estimation quality:

```text
event clustering
constituency prior quality
coverage / missing channels
noisy or manipulated telemetry
temporal alignment
live collection reliability
```

Those are better learned during narrow Phase 8 dogfooding than by endlessly extending controlled fixtures.

Next: **Phase 7C — Minimal Trusted Brain World Model.**
