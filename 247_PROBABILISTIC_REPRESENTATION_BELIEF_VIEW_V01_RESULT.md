# RAOS Probabilistic Representation Belief View V0.1 — Result

Status: ENGINEERING V0.1 / READ-ONLY DOGFOOD VALIDATED  
Date: 2026-09-19

## 1. Implemented scope

Implemented a minimal engineering approximation of Probabilistic World Representation without adding a database entity.

New service:

backend/app/services/representation_belief.py

New read-only API:

GET /sources/{source_id}/representation-beliefs

The implementation derives probability-bearing views from existing immutable RepresentationAuditRun history.

It does not mutate Event, EventSource, SourceEdge, EventMembershipAssertion, EventLineage, graph_digest, decision_representation_digest or Attention.

## 2. Frozen stochastic epoch

Audit realizations are grouped only when all of the following are equal:

same unordered FramePair  
same input_evidence_digest  
same Auditor contract  
same provider  
same model.

A group is one frozen stochastic epoch.

Different evidence digests create different epochs rather than rewriting the earlier distribution.

Different contracts/models are never mixed into one spectrum.

## 3. Response spectrum

For one epoch the view exposes:

SAME_EVENT count  
DIFFERENT_EVENT count  
UNCERTAIN count  
empirical categorical response distribution  
response entropy in bits  
decisive fraction  
sample count.

The response spectrum is explicitly labelled as an Auditor behavior distribution, not calibrated world truth.

## 4. Operational epistemic opinion

With prior ignorance weight W=2 and base rate a=0.5:

b = n_same / (N+W)  
d = n_different / (N+W)  
u = (n_uncertain+W) / (N+W).

Projected operational proxy:

p_op = b + a*u.

The API exposes:

belief_same_mass  
disbelief_same_mass  
uncertainty_mass  
projected_same_probability_proxy  
calibrated_world_truth_probability = false.

UNCERTAIN increases uncommitted mass instead of becoming negative evidence.

## 5. Sampling caveat

The API explicitly exposes:

iid_sampling_certified = false  
effective_sample_count_estimated = false.

Repeated LLM realizations are treated as empirical response samples, not asserted to be statistically independent IID evidence.

## 6. Distributional epoch comparison

For compatible contract/provider/model streams, later evidence-digest epochs expose Jensen-Shannon divergence from the previous compatible response spectrum.

A label flip is therefore not automatically interpreted as a regime shift; the distributional object is observable directly.

## 7. Correctness protection

A potentially silent API bug was prevented before rollout:

The user-facing limit parameter must limit returned hypothesis pairs, not truncate RepresentationAuditRun realizations before aggregation.

Truncating raw audit rows would produce plausible but false probability counts.

V0.1 therefore aggregates all available realizations for each returned pair, then applies the pair limit.

## 8. Synthetic validation

Core tests cover:

single SAME_EVENT realization retains high uncertainty  
UNCERTAIN adds uncommitted mass rather than negative evidence  
evidence digest change creates a new epoch  
JSD detects a complete response-spectrum shift  
FramePair orientation does not change SAME_EVENT belief  
pair-result limiting never truncates realizations.

Focused belief/API tests:

6 passed.

## 9. Existing real repeated epochs

Before adding new samples, current v0.7 history already contained seven frozen epochs with two realizations each.

All seven were internally 2/2 consistent.

Examples:

Jev release pairs: 2/2 SAME_EVENT  
Steam Frame vs Deck 2: 2/2 DIFFERENT_EVENT  
Paper2Agent vs OpenAI Ads: 2/2 DIFFERENT_EVENT.

At N=2, even unanimous output retains uncertainty mass 0.5.

Therefore:

2/2 SAME_EVENT -> projected proxy 0.75, not 1.0  
2/2 DIFFERENT_EVENT -> projected proxy 0.25, not 0.0.

## 10. Fixed N=8 real spectrum experiment

Three frozen real FramePairs were sampled to N=8 and then stopped.

Case A — Jev SAME_EVENT:

8 SAME_EVENT  
0 DIFFERENT_EVENT  
0 UNCERTAIN  
response entropy = 0  
belief_same_mass = 0.8  
uncertainty_mass = 0.2  
projected_same_probability_proxy = 0.9.

Case B — Steam Frame related but different event:

0 SAME_EVENT  
8 DIFFERENT_EVENT  
0 UNCERTAIN  
response entropy = 0  
disbelief_same_mass = 0.8  
uncertainty_mass = 0.2  
projected_same_probability_proxy = 0.1.

Case C — PHP webserver vs AI-jobs survey:

0 SAME_EVENT  
8 DIFFERENT_EVENT  
0 UNCERTAIN  
response entropy = 0  
disbelief_same_mass = 0.8  
uncertainty_mass = 0.2  
projected_same_probability_proxy = 0.1.

These are concentrated Auditor response spectra for these three bundles.

They do not establish that objective SAME_EVENT truth probabilities are 0.9/0.1.

## 11. Interpretation

The experiment supports the engineering usefulness of a distributional view even when the sampled distribution is degenerate.

A stable 8/8 response means:

the inference system repeatedly produces the same judgment under the frozen bundle/configuration.

It does not mean:

the world hypothesis has been proven with 100 percent certainty.

The prior ignorance mass prevents a small repeated sample from masquerading as absolute certainty, while preserving the distinction between stable inference behavior and calibrated world belief.

## 12. Snapshot boundary

V0.1 deliberately does not add belief state to world-representation-v0.1 graph_digest or decision-representation-v0.1.

Reason:

repeated research sampling would otherwise churn canonical graph identity before any downstream component consumes the belief distribution.

Current separation:

materialized graph -> graph_digest  
derived epistemic belief -> representation-belief-view-v0.1  
decision-bearing state -> decision_representation_digest.

This boundary should change only when probability-bearing hypotheses become an actual input to cognition/Attention or topology commitment.

## 13. Architectural result

No new domain entity was required.

Existing immutable RepresentationAuditRun history is sufficient to materialize the first probability-bearing Representation view.

The resulting architecture is:

Evidence  
-> grounded stochastic Auditor realizations  
-> response spectrum  
-> operational epistemic opinion  
-> optional future calibrated world-belief estimator  
-> risk-based topology commitment.

Execution Authority remains orthogonal and deterministic.


## 14. Source-version continuity and live validation

The first live smoke exposed an important observation-history boundary: ordinary Source APIs resolve historical acquisition-backed Source ids to the current immutable Source version, but probabilistic representation must preserve the full epistemic trajectory across versions of the same ExternalInformationItem.

A small `source_version_ids()` helper now lets the belief view aggregate EventEvidenceFrames and RepresentationAuditRuns across the immutable Source-version family while leaving ordinary Reader/Search current-version semantics unchanged.

A regression test verifies that an audit attached to an old Source version remains visible when the belief API is requested through the current version.

Final live dogfood smoke for the Jev ExternalInformationItem:

- current Source id: a7601f5e-49f5-4e48-966b-f5f70a00ff52
- immutable Source versions: 2
- belief contract: representation-belief-view-v0.1
- hypothesis pairs visible: 4
- one frozen epoch with N=8
- counts: 8 SAME_EVENT / 0 DIFFERENT_EVENT / 0 UNCERTAIN
- operational masses: belief 0.8 / disbelief 0.0 / uncertainty 0.2
- projected same-event probability proxy: 0.9
- calibrated world-truth probability: false
- IID sampling certified: false
- topology commitment authority: NONE

Runtime after rollout remained CANONICAL / ATTESTED / READY.

Final backend regression after source-version continuity fix:

888 passed / 63 skipped / 1 known Case-K failure.

The known residual remains PREEMPT expected vs PRIORITY actual and is unrelated to Probabilistic Representation.


## 15. Controlled evolution saturation finding

Phase14B-Controlled compared four immutable evidence epochs under fixed N=4 sampling:

```text
E0 weak          -> 4/4 UNCERTAIN
E1 named         -> 4/4 SAME_EVENT
E2 corroborated  -> 4/4 SAME_EVENT
E3 conflict      -> 4/4 DIFFERENT_EVENT
```

This validates bounded directional evidence sensitivity, but also exposes a deliberate limitation of `representation-belief-view-v0.1`.

E1 and E2 contain materially different corroborating detail yet have the same categorical response spectrum and therefore the same operational opinion/proxy. The view cannot measure evidence-strength improvement after the Auditor response has saturated.

Therefore:

```text
representation-belief-view-v0.1
= stochastic Auditor response view + explicit ignorance
!= calibrated evidence-sensitive world-belief posterior
```

Evidence epoch digest/provenance must remain first-class even when the operational proxy is unchanged. Do not interpret proxy delta as the complete amount of epistemic update.
