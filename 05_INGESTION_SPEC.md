# Research Attention OS — INGESTION_SPEC.md

Version: RAOS v1.1

## 1. Purpose

The ingestion layer is external I/O.

```text
discover / receive
      ↓
fetch
      ↓
parse
      ↓
normalize
      ↓
fingerprint
      ↓
persist Source
```

It does not make final cognitive scheduling decisions.

## 2. SourceConnector interface

```python
class SourceConnector(Protocol):
    def discover(self, query_or_config) -> list[DiscoveredItem]: ...
    def fetch(self, item: DiscoveredItem) -> RawSource: ...
    def parse(self, raw: RawSource) -> ParsedSource: ...
    def normalize(self, parsed: ParsedSource) -> NormalizedSource: ...
    def fingerprint(self, normalized: NormalizedSource) -> str: ...
```

Manual connectors do not need active discovery.

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

## 5. Phase-2 connectors

### arXivConnector
- query/direct ID/URL;
- metadata;
- abstract;
- optional PDF;
- reference resolution.

### RSSConnector
- poll configured feeds;
- create Source candidates;
- deduplicate.

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
Handled by EventCluster later.

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
7. user observation enters without pretending to be a web source.
