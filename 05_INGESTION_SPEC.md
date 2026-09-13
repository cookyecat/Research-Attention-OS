# Research Attention OS — INGESTION_SPEC.md

Version: RAOS v1.1
Status: **ACTIVE INGESTION BOUNDARY; external discovery now belongs to Acquisition Plane**

## 1. Purpose

Current HEAD separates **Acquisition** from **Ingestion**:

```text
Acquisition Plane
  discover / observe / identify external item / snapshot
      ↓
Ingestion boundary
  fetch → parse → normalize → fingerprint → persist RAOS Source
      ↓
Sensor / Auditor / cognition
```

Acquisition answers “what became observable?” Ingestion turns a selected object into a normalized RAOS `Source`. Neither layer makes cognitive relevance or Attention decisions.

## 2. Acquisition Adapter vs Ingestion Connector

Acquisition adapter (current v0.1 RSS/Atom transport):

```python
class AcquisitionAdapter(Protocol):
    def discover(self, source_definition) -> list[DiscoveredExternalItem]: ...
```

The Acquisition service owns external identity, Observation, Snapshot, baseline, and polling semantics.

Ingestion connectors/services own content retrieval and normalization:

```python
fetch → parse → normalize → fingerprint → persist Source
```

Do not merge discovery scheduling into the cognitive pipeline.

## 3. Canonical NormalizedSource

```yaml
NormalizedSource:
  source_type:
  title:
  canonical_url:
  content_text:
  published_at:
  author_entities:
  publisher:
  language:
  external_ids:
  raw_metadata:
  binary_object_ref:
```

## 4. MVP connectors

### ManualTextConnector
Input: pasted text.

Must:
- preserve original text;
- allow optional title;
- create content hash;
- mark ingestion_method MANUAL_TEXT.

### URLConnector
Input: public URL.

Must:
1. fetch;
2. resolve redirects;
3. retain canonical URL where available;
4. extract readable main content;
5. extract title/author/time where available;
6. preserve raw metadata;
7. create fingerprint.

Graceful degradation is required.

### PDFConnector
Input: uploaded PDF.

Must:
- store binary;
- extract text;
- preserve page boundaries where practical;
- extract title/authors/DOI/arXiv when possible;
- detect references section;
- emit reference candidates.

If confidence is high that it is a paper, use source_type PAPER.

### ManualObservationConnector
Input: user field observation.

Example:
> At WRC I saw repeated move-pause-move during folding.

Creates:
- Source type MANUAL_OBSERVATION;
- Observation candidate with observer_type USER.

This is a first-class path.

## 5. Additional / future connectors

### arXivConnector
- query/direct ID/URL;
- metadata;
- abstract;
- optional PDF;
- reference resolution.

### RSS / Atom Acquisition Adapter — ACTIVE v0.1
- poll configured `SourceDefinition` rows;
- create/resolve External Information Objects and Observations;
- create immutable Snapshots linked to normalized RAOS Sources;
- establish a present-time baseline for newly registered feeds before cognitive analysis;
- isolate one Source failure from unrelated Sources.

RSS discovery does not decide which feed items matter cognitively.

### GitHubConnector
- repository metadata;
- README;
- releases;
- optional release monitoring.

### MediaConnector
- site-specific parsers where appropriate;
- fallback to URLConnector.

### WeChatSharedURLConnector
- accept user-shared public article URL;
- parse when accessible;
- otherwise retain URL plus user-pasted content.

Do not make MVP depend on bulk historical WeChat crawling.

## 6. Future connectors

Possible:
- Scholar alerts;
- Semantic Scholar;
- Hugging Face;
- X;
- company blogs;
- YouTube transcripts;
- benchmark leaderboards.

## 7. Deduplication

Acquisition distinguishes **external item identity** from semantic same-event identity. Safe acquisition-level dedup includes stable external IDs, canonical URL identity, and exact content snapshots.

### Exact duplicate
Use:
- DOI;
- arXiv ID;
- canonical URL;
- content hash.

### Near duplicate
Use:
- normalized title;
- publisher;
- publication time;
- text similarity.

### Same-event duplicate
Handled by EventCluster / Source Graph downstream. Acquisition must not collapse semantically similar reports merely because they describe the same event.

Never delete provenance silently; preserve relation metadata.

## 8. Fingerprint priority

```text
DOI
else arXiv ID
else canonical URL
else normalized(title + publisher + published_at)
else content hash
```

Persist fingerprint version.

## 9. Parsing boundaries

Ingestion may extract:
- title;
- author;
- publication time;
- abstract;
- references;
- sections.

It must not decide:
- whether a founder claim is true;
- whether a claim changes a Belief;
- whether the user should ENGAGE.

## 10. Paper references

Emit:

```yaml
ReferenceCandidate:
  raw_text:
  title:
  authors:
  year:
  venue:
  doi:
  arxiv_id:
  url:
  confidence:
```

Pass to Source Graph resolution.

## 11. Ingestion state machine

```text
PENDING
  ↓
FETCHING
  ↓
PARSING
  ↓
NORMALIZING
  ↓
DEDUPLICATING
  ↓
PERSISTED
```

Errors:
```text
FETCH_FAILED
PARSE_FAILED
NORMALIZE_FAILED
```

Retries are bounded.

## 12. Security

Required:
- never execute downloaded code;
- sanitize HTML;
- file-size limits;
- MIME validation;
- SSRF protection;
- block internal/private URL ranges;
- separate untrusted binaries.

## 13. Legal/product constraint

Prefer:
- public URLs;
- user-provided material;
- official APIs;
- RSS;
- explicitly shared content.

Do not assume unrestricted scraping rights.

## 14. Provenance

Every Source retains:
- origin;
- fetch method;
- parser version;
- ingestion timestamp;
- original URL/file ref;
- external IDs.

## 15. Acceptance criteria

A connector passes if:
1. valid input ingests;
2. provenance persists;
3. duplicates do not explode;
4. parsing failure is visible;
5. downstream extraction can read normalized text;
6. paper references emit unresolved candidates;
7. user observation enters without pretending to be a web source;
8. newly registered unattended Sources baseline current history without triggering cognition;
9. one failing Acquisition Source does not terminate independent polling;
10. the worker loads the same explicit runtime environment/semantic contract as the HTTP backend.
