# RAOS Content-Identity Authority Quarantine — Result

Status: **FIXED / DOGFOOD VALIDATED**  
Date: 2026-09-19

## 1. Trigger

E1 provenance-authority study inspected persisted SourceGraph edges and found that many historical `REPOSTS / METADATA` relations joined obviously unrelated Bilibili videos.

Examples included unrelated Agent tutorials, interviews and information feeds being placed into the same repost chain.

## 2. Root cause

The affected Sources were acquisition records with:

```text
content_scope = METADATA_ONLY
content_text = "-"
defer_cognition = true
```

or other repeated metadata-only teaser text.

The ingestion layer correctly computed a literal `content_hash` for the observed text, but the SourceGraph layer incorrectly interpreted any equal content hash as semantic duplicate evidence:

```text
same content_hash
→ REPOSTS / METADATA
```

For metadata-only placeholders this implication is invalid.

The bug was therefore not in hashing. It was an authority-boundary bug:

```text
literal content identity
≠ semantic duplicate authority
```

## 3. Why this was serious

`REPOSTS` participates in current decision-relevant relational context and can affect:

```text
independence_report
relational_context_digest
is_duplicate
secondary_report_count
Coverage
WATCH duplicate suppression
future provenance authority
```

A wrong REPOST edge can therefore silently suppress evidence multiplicity and distort cognition.

## 4. Unified invariant

A single current-authority predicate was introduced:

```text
source_content_identity_eligible(Source)
```

Content-hash equality may carry duplicate/repost semantics only when the Source contains substantive semantic content.

Current fail-closed exclusions include:

```text
content_scope = METADATA_ONLY
REFERENCE_STUB / stub
empty content
known placeholder-only content
deleted Source
missing content_hash
```

A second predicate:

```text
source_edge_authority_eligible(db, edge)
```

provides the current authority view over persisted SourceEdge history.

Historical rows are not deleted.

## 5. Affected paths

The invariant is shared by:

```text
link_near_duplicates()
freeze_analysis_relational_context()
independence_report()
Information Landscape Coverage
Continuous Attention relevance / duplicate suppression
legacy attach_or_create_event() content-hash fallback
RepresentationEvidenceBundle graph facts
E1 deterministic provenance predicate
```

This avoids six independent ad-hoc fixes.

## 6. Non-destructive history

Existing incorrect REPOST rows remain in SQLite for forensic history.

They are now interpreted as:

```text
persisted historical edge
+
authority_eligible = false
→ excluded from current representation authority
```

No destructive cleanup migration is required.

## 7. Dogfood impact

Before the fix:

```text
REPOSTS total = 142
current eligible under old semantics = 142
```

After the authority filter:

```text
REPOSTS total = 142
authority eligible = 5
quarantined = 137
distinct Sources touched by quarantine = 66
```

Most quarantined edges are metadata-only Bilibili records.

Across 1113 current non-deleted Sources:

```text
Sources with outgoing decision-relevant secondary facts:
old = 48
new = 4

Sources whose relational facts change:
44
```

## 8. Regression semantics

Metadata-only placeholder Sources with identical hashes must now satisfy:

```text
no new REPOSTS edge
independence remains independent
no Landscape Coverage expansion
WATCH does not classify duplicate
legacy Event fallback does not attach by hash
E1 does not treat quarantined graph fact as provenance authority
```

Substantive Sources with genuinely identical content retain the original duplicate semantics.

## 9. Contract versioning

Because frozen Representation evidence now records SourceGraph authority eligibility, contracts were bumped:

```text
RepresentationEvidenceBundle:
  representation-evidence-bundle-v0.3

Representation Auditor:
  representation-auditor-frame-pair-v0.7

Authority predicates:
  representation-authority-predicates-v0.2

E1 shadow policy:
  representation-authority-shadow-v0.2
```

Pre-fix audits remain immutable historical records and are not silently upgraded.

## 10. Architectural conclusion

The correct invariant is:

> A hash is an identity sensor over observed bytes/text, not an authority proof about semantic provenance.

Authority must explicitly decide whether the observed content is semantically eligible to support duplicate/repost conclusions.

This preserves the Occam architecture: one content hash, one SourceGraph, one authority filter — no new duplicate ontology or cleanup entity.
