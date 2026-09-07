# Integrated no-Delta AWARE — Pre-Measurement Plumbing Failure

Status: **ATTRIBUTED / NOT A SCORED RUN**  
Date: 2026-09-07  
Scope: attempted first integrated IA1-IA12 measurement

## 1. Observed symptom

The attempted integrated runner returned in approximately 0.1 seconds with:

```text
D n_scored = 0
S n_scored = 0
P n_scored = 0
final n_scored = 0
n_component_failures = 12
actual_models.D = []
actual_models.S = []
actual_models.P = []
```

No D/S/P model call completed. Therefore this artifact is not valid estimator evidence and must not be interpreted as a failed semantic/system measurement.

## 2. Root cause

Import-order plumbing bug:

```text
integrated runner imports no_delta_awareness_integration_v1
    -> integration imports production Scheduler
    -> Scheduler imports matching
    -> matching imports KernelNode
    -> KernelNode imports app.db
    -> app.db imports app.config.settings
    -> Settings() is instantiated
```

At that time `load_repo_env()` had not yet executed in the runner.

Therefore `settings.llm_api_key` was instantiated from the pre-bootstrap environment and remained `None` even though the repository `.env` was loaded later.

The component estimators consequently failed immediately before a real provider call.

This is:

```text
measurement / instrumentation plumbing failure
!= D failure
!= S failure
!= P failure
!= Boolean gate failure
```

## 3. Fix

Bootstrap fix:

```text
b83801d11826b87b507e50027f8aad0a4afa660b
```

The integrated eval harness now loads repository environment configuration before importing production Scheduler/model modules that can instantiate `app.config.settings`.

Runner hardening:

```text
6bf7bec813e80b15f41114fd152f1ea540c1b5fb
```

The runner now:

- performs a runtime API-key preflight before measurement;
- refuses to start a canonical first run if required provider configuration is absent;
- preserves individually scorable D/S/P component results even if another component fails;
- records component error details for attribution.

Regression tests:

```text
e1b198dfc6c4cfeae60cd05fabfa478057ef4208
```

They protect:

- `.env` bootstrap before Scheduler import;
- missing-key fail-fast behavior;
- preservation of surviving component measurements when another component fails.

## 4. Provenance decision

The locally generated artifact named:

```text
eval/live/results/no_delta_awareness_integration_v1_fresh_first_run.json
```

from the pre-fix attempt must **not** retain the canonical `first_run` name, because no actual first measurement occurred.

Preserve it, if desired, under an explicit diagnostic name such as:

```text
eval/live/results/no_delta_awareness_integration_v1_pre_measurement_plumbing_failure.json
```

Then the canonical `no_delta_awareness_integration_v1_fresh_first_run.json` path remains reserved for the first post-fix run that actually invokes the frozen D/S/P estimators.

This is not post-hoc rerunning for a better score. It is correction of a pre-measurement instrumentation failure before any prediction was observed.
