# RAOS Frontend Design Principles

Status: **LIVING DESIGN CONTRACT**
Scope: User Space, Reader, Attention presentation, and explicit RAOS Inspector/System surfaces.

## 1. Core product principle

RAOS is an attention operating system, not a visualization of its own internals.

```text
Show the user their world.
Show the operating system only when they ask to inspect it.
```

Therefore:

```math
User\ Space \neq Operating\ System\ View
```

Normal UI optimizes for comprehension, attention allocation, reading comfort, and action. Scheduler state, cognition traces, D/S/P internals, raw claims, model provenance, and execution diagnostics belong in explicit Inspector/System surfaces.

### 1.1 User-space hierarchy mirrors the operating doctrine

The frontend must preserve the distinction between what RAOS sees, what RAOS judges, and what the human must consciously handle:

```text
Inbox      = what RAOS observed / preserved
Attention  = what RAOS judged into a current attention state
Today      = what deserves conscious human attention now
```

The desired scaling behavior is asymmetric:

```text
more observed information
→ more automatic machine cognition
→ less human-visible residue
```

A busy Acquisition layer and busy cognition layer should therefore be compatible with a calm Today surface. User Space must not reward itself for showing everything the system knows.

## 2. Reader is attentional recomposition

The RAOS Reader is **not a mirror of the source webpage**. It is a reading space that re-composes the source's attentional structure.

```math
\boxed{RAOS\ Reader = Attentional\ Recomposition(Source)}
```

The source publisher optimizes for publishing, brand, engagement, advertising, navigation, and social distribution. RAOS optimizes for:

```math
\boxed{Comprehension + Attention + Cognitive\ Relevance}
```

## 3. Source fidelity is not layout fidelity

RAOS must preserve source truth and provenance without copying source layout.

Preserve faithfully:

- original text and quotations;
- title, author, publisher, URL, publication time;
- publisher-declared hero image, useful article visuals, captions, and alt text;
- provenance and links back to the original source.

Do not reproduce by default:

- publisher navigation and branding chrome;
- advertisements and sponsor modules;
- related-story widgets, comments, social/share controls;
- engagement mechanics and arbitrary DOM/layout structure.

```math
\boxed{Source\ Fidelity \neq Layout\ Fidelity}
```

Presentation metadata must remain presentation-only unless a separate research decision explicitly promotes it into cognition.

## 4. Visual structure is part of cognition ergonomics

A visual does not need to add new propositional facts to be valuable. Images, whitespace, typography, hierarchy, and rhythm can reduce visual fatigue and give the eye stable anchors.

A useful working model is:

```math
\boxed{Visual\ Value = Semantic\ Information + Attentional\ Structure + Reading\ Rhythm}
```

Implications:

- use publisher-declared hero visuals when available;
- preserve semantic article figures and diagrams conservatively;
- do not inject unrelated decorative images that could imply false source semantics;
- allow text-native sources to remain text-native rather than forcing fake covers;
- use hierarchy, spacing, and asymmetry to make importance visually legible.

Substantive source media is a first-class part of the reading experience. Preserve the media meaning, not the publisher machinery: trusted embeds may be re-embedded; direct article images/video should be locally cached when technically reasonable; large media may fall back to the original URL; autoplay stays off; ads, avatars, related-story thumbnails, tracking media, and generic fallback posters stay out of Reader.

A page itself is an attention-allocation problem. Title, image, RAOS guidance, evidence anchors, body text, and side rail all compete for visual priority and must be deliberately scheduled.

### 4.1 Inbox is a living intake landscape

Inbox represents what RAOS has observed. It should therefore feel alive without becoming another engagement feed. Uniform card matrices create rapid visual habituation and hide information state. Use controlled editorial rhythm instead: one visual anchor, secondary cards, then recurring wide/standard/compact forms with predictable spacing.

```math
\boxed{Inbox = Scanability + Visual\ Rhythm + State\ Visibility}
```

Every Source card should reveal its current cognition state when one exists (`DROP / AWARE / WATCH / ENGAGE`). An unanalyzed Source must remain readable and visibly distinct without implying a judgment RAOS has not made. Layout hierarchy is presentation only: it must not fabricate cognitive importance or reorder Source chronology by hidden recommendation logic.

## 5. Human action first, internals last

Default presentation order:

```text
information / source
→ why it matters
→ what to do
→ evidence and reading support
→ technical trace only on request
```

This is the frontend analogue of RAOS's core mission: reduce the amount of cognitive work returned to the human.

For a Reader detail page, the current RAOS disposition is part of the entry contract, not a body annotation. It should appear immediately after the title and before the hero media/body so the user knows why the Source is in front of them before beginning the reading journey. `Open original` remains available but visually subordinate to the RAOS judgment.

```math
\boxed{Source\ identity \rightarrow RAOS\ judgment \rightarrow Reading}
```

## 6. Evidence should return to the source text

When RAOS has already extracted and audited claims, the Reader should map those results back to the original source where possible.

Evidence anchors must obey:

```text
frozen cognition result
→ presentation-only source-span alignment
→ subtle original-text anchor
```

Do not create new claims merely to make the UI richer. Underlines/highlights should be traceable to existing evidence spans. Clicking an anchor may reveal a concise human-readable explanation; raw claim schema remains in Inspector.

Evidence emphasis is itself a scarce attention resource. If everything is emphasized, nothing is emphasized. Reader anchors therefore remain sparse, deterministic, and spatially distributed: at most one anchor per selected paragraph and only a small bounded set across an article.

## 7. The reading companion should be context-sensitive

The side rail should not permanently occupy attention with static cards.

Before reading, it may answer:

- Why does this matter to me?
- What should I do?

During reading, it should shift toward:

- reading progress;
- evidence near the current paragraph;
- locally relevant RAOS guidance.

The interface should adapt to the reader's current task rather than repeat the same system message throughout the article.

## 8. Reading aids are presentation, not cognition

Text-size controls, theme, line-height, and optional half-bold/bionic reading are ergonomic transforms only.

They must not mutate:

- Source text;
- copied/searchable text;
- semantic extraction inputs;
- claims, Auditor results, Attention decisions, or Kernel state.

Defaults should remain conservative and optional. Accessibility and user preference outrank novelty.

## 9. Authority and provenance remain visible at the right depth

User Space may simplify language, but it must never fabricate provenance or imply that RAOS authored source content. Original-source links and attribution remain available. Human-committed cognition must remain visually distinct from AI judgment or proposed changes.

## 10. Dogfood rule

Frontend evolution should be residual-driven:

```text
real use
→ observe reading/interaction friction
→ identify earliest presentation cause
→ minimal correction
→ production-browser validation
```

Avoid speculative feature accumulation. Every added visual or interaction should reduce attention cost, improve comprehension, or make authority/provenance clearer.

## 11. Scholarly Sources deserve a scholarly profile

A paper is not an ordinary publisher webpage. When a structured scholarly representation is available, Reader should preserve the research object rather than the host site's chrome.

```math
\boxed{Paper\ fidelity = scholarly\ structure\ fidelity \neq page\ fidelity}
```

For papers, prioritize title, authors, affiliations, abstract, section hierarchy, figures, equations, tables, references, version history, and canonical PDF/HTML links. Site logos, recommendation widgets, citation-tool placeholders, labs chrome, and generic webpage furniture are not paper content.

Section navigation must be functional and grounded in the actual preserved body. Never display an interactive-looking table of contents when the corresponding body is unavailable. Paper reading progress should follow sections, not arbitrary paragraph counts.

List/index payloads may remain compact, but detail reading must fetch the full Source separately; compact list state must never overwrite a full Reader detail object.
## 12. Structured publisher articles use cleaned semantic structure

For ordinary publisher webpages, Reader should reconstruct article semantics rather than mirror publisher DOM or flatten everything into plain text.

```text
canonical content_text → cognition
clean article_blocks   → presentation
```

Preferred presentation structure includes headings, paragraphs, semantic lists, quotations, substantive figures, captions, and meaningful inline media. Newsletter modules, follow/share controls, bylines/author avatars, related-story recirculation, comments, navigation, advertising and publisher furniture are not Reader body content.

When multiple extraction views disagree, choose the representation that best preserves the article's semantic hierarchy while excluding publisher chrome. A cleaned main-content extractor may define the editorial boundary; DOM may conservatively recover captions, emphasis and missing body media.

Historical presentation hydration must fail closed when current canonical text differs from the frozen Source text. Improving how an old Source is rendered must never silently rewrite the information that historical cognition actually saw.

> **Preserve the information object, not the publisher machinery.**
