# Research Attention OS — SOURCE_GRAPH_SPEC.md

Version: RAOS v1.1

## 1. Purpose

Source Graph answers:
- Where did this claim originate?
- Are ten reports independent or copied from one announcement?
- What paper does this article cite?
- Which references are foundational?
- Which later works extend or contradict this source?

## 2. Core graph

```text
Source A
  ├── CITES → Source B
  ├── REPORTS_ON → Source C
  ├── REPOSTS → Source D
  ├── DISCUSSES → Source E
  ├── EXTENDS → Source F
  ├── CONTRADICTS → Source G
  └── DERIVED_FROM → Source H
```

## 3. Edge semantics

### CITES
A explicitly references B.

### REPORTS_ON
A media/report source reports on B.

### REPOSTS
A substantially republishes B.

### DISCUSSES
A commentary/analysis centers on B.

### EXTENDS
A technical work explicitly extends B.

### CONTRADICTS
A explicitly reaches conflicting source-level conclusions.

### DERIVED_FROM
A is adapted, translated, summarized, or generated from B.

Do not infer EXTENDS/CONTRADICTS casually.

## 4. SourceEdge

```yaml
SourceEdge:
  id:
  source_id:
  target_id:
  relationship:
    CITES
    REPORTS_ON
    REPOSTS
    DISCUSSES
    EXTENDS
    CONTRADICTS
    DERIVED_FROM
  confidence:
  detected_by:
    PARSER
    AI
    USER
    METADATA
  evidence:
  created_at:
```

## 5. Paper-reference pipeline

```text
Paper A
  ↓
Reference Extraction
  ↓
ReferenceCandidate
  ↓
Resolution
  ↓
Existing Source?
   /       yes      no
 ↓         ↓
reuse    create stub
   \      /
    CITES edge
```

## 6. Resolution priority

1. DOI exact match;
2. arXiv ID exact match;
3. canonical URL exact match;
4. title + first author + year;
5. high-confidence fuzzy title;
6. unresolved reference stub.

Never silently merge low-confidence candidates.

## 7. Stub Source

References may exist before full retrieval:

```yaml
Source:
  source_type: PAPER
  title: known
  content_text: null
  ingestion_method: REFERENCE_STUB
```

Later hydration may fill metadata/PDF.

## 8. Citation-depth control

Do not recursively crawl literature by default.

### Depth 0
Current paper.

### Depth 1
Direct references.

### Depth 2+
Only when triggered by:
- Kernel relevance;
- citation centrality;
- explicit user request;
- evidence verification;
- foundational-source detection.

This is itself a compute/attention scheduling problem.

## 9. Primary-source preference

During VERIFY, climb toward primary technical sources where possible.

Example:

```text
Media Article
   REPORTS_ON
Company Blog
   CITES
Technical Paper
```

Keep all provenance; prefer paper for technical verification.

## 10. Independence estimation

Ten reports deriving from one press release do not equal ten independent confirmations.

Future heuristic may use:
- REPOSTS;
- DERIVED_FROM;
- shared primary source;
- near-duplicate text;
- same quotations;
- publication timing.

MVP may show:
```text
Independent sources: 1
Secondary reports: 7
```

## 11. Source Graph vs Evidence Graph

Source Graph:
```text
Paper A CITES Paper B
```

Evidence Graph:
```text
Observation O12 SUPPORTS Belief B3
```

Never merge these concepts.

## 12. APIs

Suggested:

```text
GET /sources/{id}/graph
GET /sources/{id}/references
POST /sources/{id}/resolve-references
POST /source-edges
```

Optional later:
```text
POST /sources/{id}/hydrate-references
```

## 13. MVP UI

A compact panel is enough:

```text
Primary source: Technical paper
Referenced by: 3 media articles
Direct references: 42
Resolved: 31
Relevant to your Kernel: 5
```

Do not prioritize decorative graph visualization.

## 14. Scheduler integration

Examples:

```text
Repeated by many REPOSTS
→ credibility does not multiply
```

```text
Claim traced to primary technical paper
→ VERIFY primary source
```

```text
Reference strongly matches active Bottleneck
→ ENGAGE / DEEP_DIVE
```

## 15. Reference-first research workflow

```text
Paper
  ↓
Extract references
  ↓
Resolve Source Graph
  ↓
Rank by Kernel relevance
  ↓
Select only high-value references
  ↓
LEARN / VERIFY / WATCH
```

## 16. Acceptance criteria

1. Paper creates CITES edges.
2. Unresolved references can be stubs.
3. High-confidence duplicates resolve to one Source.
4. Media reports can link to primary sources.
5. Repost count is not independent evidence count.
6. Scheduler can use graph metadata.
7. Traversal is bounded by depth and Kernel relevance.
