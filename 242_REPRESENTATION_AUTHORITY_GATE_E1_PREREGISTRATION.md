# RAOS Topology Commitment Gate E1 — Preregistration (historical file name retained)

Status: **PREREGISTERED / SHADOW SIMULATION IMPLEMENTED / NO REPRESENTATION MUTATION / E2 NOT AUTHORIZED**  
Date: 2026-09-19

## 1. Purpose

E1 converts an already persisted RepresentationAuditRun into a deterministic **topology-commitment simulation** without invoking another model.

This phase exists to separate:

```text
epistemic hypothesis
from
topology-changing side effect
```

A grounded SAME_EVENT judgment may be admitted into probabilistic epistemic World Representation with uncertainty. That does not mean RAOS should merge Event topology, suppress duplicate evidence, or replace Event membership.

E1 is therefore not a world-truth certification gate. It is a high-precision commitment gate for operations with asymmetric downstream cost.

## 2. Frozen principle

The Topology Commitment Gate is not another semantic reasoner.

```text
RepresentationAuditRun
+
Frozen deterministic evidence predicates
+
Versioned policy
+
Phase13 execution identity
→ deterministic gate outcome
```

Forbidden:

```text
LLM confidence
LLM rationale interpretation
embedding threshold
title similarity threshold
hidden re-query of mutable graph state
→ authority
```

## 3. E1 is simulation only

Allowed outputs:

```text
WOULD_AUTHORIZE
CANDIDATE_ONLY
REJECTED
UNRESOLVED
```

E1 must not:

```text
insert EventMembershipAssertion
insert EventLineage
mutate Event.status
merge/split Events
promote SourceEdge
change graph_digest
change decision_representation_digest
authorize Coverage→P
change Attention
```

## 4. Frozen predicate snapshot

Future RepresentationAuditRuns must freeze a compact predicate snapshot inside the existing evidence_bundle_refs JSON.

No new table/entity is introduced.

Minimum predicate contract:

```text
representation-authority-predicates-v0.1

source_identity
  same_source_id
  same_external_item_id
  same_canonical_url
  same_content_hash

frame_authority
  frame_a_semantic_audited
  frame_b_semantic_audited
  both_semantic_audited
  frame_a_routable
  frame_b_routable

event_semantic_exactness
  event_semantic_fingerprint_a
  event_semantic_fingerprint_b
  exact_event_semantic_fingerprint

provenance
  explicit_graph_facts with direction / relationship / detected_by

audit_grounding
  support ids
  conflict ids

execution
  origin purpose
  origin attestation status
  origin profile hash
```

The snapshot itself has a deterministic digest.

An audit lacking a frozen predicate snapshot is not E1-authority-eligible.

No retroactive mutation of historical RepresentationAuditRuns is allowed merely to make them eligible.

## 5. Event semantic fingerprint

V0.1 uses only exact, normalized, audited structured semantics.

It may include:

```text
actors: normalized exact name + role
actions: normalized exact description + temporal status
affected systems/populations: normalized exact description + scope
```

Support ids, Source ids, event ids, summaries, rationale and model prose are excluded.

The fingerprint exists only as a high-precision deterministic anchor.

It is deliberately not fuzzy.

```text
exact fingerprint mismatch
≠ DIFFERENT_EVENT
```

It only means this exact authority predicate is unavailable.

## 6. SAME_EVENT policy V0.1

Permanent risk asymmetry:

```text
False Merge cost ≫ Missed Merge cost
```

Therefore cross-publication SAME_EVENT is not authorized merely because the Auditor judged SAME_EVENT.

Minimum general requirements:

```text
audit.event_identity = SAME_EVENT
both frames semantic-audited
FRAME_A and FRAME_B cited as support
no cited conflicting evidence
origin audit execution = canonical + attested
```

Then at least one V0.1 strong deterministic anchor must exist.

Initial strong anchor:

```text
same ExternalInformationItem
+
same canonical URL
+
exact event semantic fingerprint
```

or equivalently an even stronger exact identity case.

Different content hashes are expected for distinct immutable Source versions of the same ExternalInformationItem. Content-hash equality is therefore corroborating evidence, not a required cross-version predicate.

This is intentionally narrow.

Cases such as:

```text
different URLs
different publications
same actors/action according to LLM
same-event Auditor judgment
```

remain:

```text
CANDIDATE_ONLY
```

until a later policy version introduces calibrated deterministic multi-axis corroboration.

## 7. Same canonical URL is not enough

A URL may:

```text
change over time
contain multiple events
be re-rendered
be appended
```

Therefore:

```text
same canonical URL
→ strong Source identity/versioning evidence
≠ automatic SAME_EVENT
```

## 8. DIFFERENT_EVENT policy V0.1

A DIFFERENT_EVENT audit is useful evidence, but E1 V0.1 does not create a new authoritative negative-pair ontology.

Therefore:

```text
DIFFERENT_EVENT + grounded audited frames
→ WOULD_ACCEPT_NEGATIVE_JUDGMENT diagnostically
→ no representation mutation
```

For the public E1 outcome vocabulary it remains:

```text
CANDIDATE_ONLY
```

with reason code:

```text
NEGATIVE_RELATION_NO_AUTHORITY_PROJECTION_V01
```

This avoids adding a sixth persistence entity merely to encode negative pair facts.

## 9. Provenance policy V0.1

### REPOST / DERIVED_FROM

E1 may only consider WOULD_AUTHORIZE when the audit judgment is corroborated by an already frozen explicit directed graph fact with a trusted non-LLM detector:

```text
PARSER
METADATA
USER
```

and the relationship/direction matches the audit.

An AI-only existing SourceEdge is not sufficient to bootstrap its own authority.

### INDEPENDENT

Requires frozen positive independence evidence.

No such predicate currently exists in the D3 bundle.

Therefore current expected behavior:

```text
INDEPENDENT
→ CANDIDATE_ONLY or UNRESOLVED
```

Never:

```text
absence of DERIVED_FROM
→ INDEPENDENT
```

### UNKNOWN

```text
UNKNOWN
→ UNRESOLVED
```

## 10. relation_context policy V0.1

RELATED / UNRELATED remain semantic/navigation judgments in E1.

They do not mutate canonical representation.

```text
RELATED / UNRELATED
→ CANDIDATE_ONLY
```

The dimension remains available for future exploration and presentation policies.

## 11. Phase13 execution requirements

A WOULD_AUTHORIZE simulation requires the originating audit to have frozen:

```text
purpose = CANONICAL
attestation = ATTESTED
profile identity present
```

The actual future mutation path will additionally require current side-effect authority at commit time.

E1 simulation does not mutate, so it may be replayed for research/forensics, but its result must expose whether the original audit was authority-eligible.

## 12. Fail-closed conditions

At minimum:

```text
missing frozen predicate snapshot
predicate snapshot digest mismatch
audit input/frame identity mismatch
unsupported auditor contract
legacy/unaudited frame
unknown relation label
conflicting evidence on a would-authorize path
origin execution not canonical/attested
→ never WOULD_AUTHORIZE
```

## 13. Replay invariant

For the same:

```text
RepresentationAuditRun
predicate snapshot
policy version
```

the E1 result must be identical without calling an LLM or reading mutable semantic state.

## 14. Calibration plan

Run E1 shadow simulation over:

1. the 9-case D4 seed corpus;
2. the 12-case real-flow probe;
3. all persisted v0.6+ shadow audits once enough accumulate.

Expected initial behavior is conservative:

```text
many CANDIDATE_ONLY
many UNRESOLVED
possibly zero WOULD_AUTHORIZE
```

Zero WOULD_AUTHORIZE is acceptable.

The research goal is not authority yield. It is high precision and legible rejection reasons.

## 15. Promotion gate

E1 may not progress from simulation to actual authority mutation until all are true:

```text
deterministic replay verified
no graph/digest mutation in simulation
high-precision positive fixtures exist
hard negatives stay blocked
Phase13 commit-time authority path designed
non-destructive Event membership/revision behavior reviewed
dogfood calibration reviewed
```

Only after that should E2 discuss authoritative EventMembershipAssertion writes.
