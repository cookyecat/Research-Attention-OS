# RAOS Acquisition Source Diversity Expansion Result

Status: **DOGFOOD ACTIVE / RSS DIVERSITY EXPANDED**
Date: 2026-09-14

## 1. Dogfood residual

After Reader UX V3/V3.1 became usable, the dominant product residual moved upstream: Inbox, Today, and Attention repeatedly showed the same small set of articles.

Runtime inspection confirmed that Acquisition was healthy but the registry contained only three active definitions:

- The Verge RSS;
- Google DeepMind Blog;
- NVIDIA Blog.

The worker was still polling on schedule. The scarcity was primarily a source-diversity problem, not a crawler liveness failure.

## 2. Registry expansion

Eight additional RSS/Atom definitions were registered for dogfood:

- OpenAI News;
- Google AI;
- Google Research;
- Hugging Face Blog;
- Microsoft Research;
- Meta Engineering;
- arXiv cs.AI;
- arXiv cs.RO.
The current registry therefore has 11 definitions. Ten are enabled. Hugging Face is temporarily disabled because its DNS exposes a public IPv4 plus a non-global IPv6 address; the conservative SSRF validator correctly refuses to weaken its safety rule merely to admit one feed.

New definitions were baselined without cognition so historical backlog did not masquerade as newly arrived information. Successful baseline delivery expanded persisted Sources from 27 to 62.

## 3. Acquisition robustness fixes

Source diversity exposed a second residual: one broken article inside an RSS feed could previously abort the whole Source poll.

`poll_source()` now isolates delivery at the individual discovered-item boundary. A failed item is rolled back independently, recorded in `item_errors`, and sibling items continue.

This preserves the stronger invariant:

```text
one bad Source must not stop other Sources
AND
one bad item must not stop sibling items in the same Source
```

Focused acquisition regression now includes explicit sibling-item isolation coverage.

## 4. Feed-content fallback

OpenAI's RSS endpoint is publicly readable, but current article pages return HTTP 403 to the RAOS URL fetcher. RAOS does not bypass that restriction.

RSS/Atom parsing now preserves publisher-supplied summary/content when present. If normal URL delivery fails and publisher feed content exists, Acquisition persists a clearly marked `RSS_FALLBACK` Source with the original canonical URL, publication time, title, and feed provenance.

The five current OpenAI feed items were successfully baselined through this fallback with zero item failures.
## 5. Immediate cognition sample

To make the richer registry visible in Attention immediately without analyzing the whole historical baseline, one representative Source from each successful new feed was explicitly analyzed.

Observed outcomes included:

- Google AI running/search article → DROP;
- Google Research ToolGrad → AWARE;
- Microsoft Research GigaPath-Flash → AWARE;
- arXiv Harness Effect → DROP;
- OpenAI Perplexity/Astra RSS fallback → DROP.

This is a useful dogfood result: source expansion did not simply inflate Attention. RAOS continued to compress low-relevance material while surfacing some research context.

Two cognition-side long-tail residuals were also exposed independently of Acquisition: one Meta article produced malformed model JSON, and one robotics paper hit `UNKNOWN_SUPPORT:R003`. They are not treated as source-acquisition failures.

## 6. DeepSeek cost observation

Recorded successful expansion analyses consumed 27,270 input tokens and 2,385 output tokens. At the current DeepSeek V4 Flash off-peak cache-miss rates, this is approximately RMB 0.052 for the recorded successful calls.

Using the observed historical average of roughly 6k total tokens per analyzed Source, RMB 5 is sufficient for roughly several hundred additional text Sources; the practical bottleneck is currently source quality and product behavior, not model budget.

## 7. Social-source next boundary

This RSS-diversity checkpoint originally identified social acquisition as the next boundary. Follow-on dogfood immediately established a stricter split recorded in `195_RAOS_PUBLIC_SOCIAL_ACQUISITION_AND_SOURCE_LIBRARY_RESULT.md`: public social acquisition can be supported without account credentials when a platform exposes a stable public transport, while authenticated Following/home timelines remain a separate future authority boundary.

No private/authenticated social data was accessed in this checkpoint.

## 8. Authority boundary

This work changes information supply and delivery robustness only.

It does **not** change:

- Sensor/Auditor semantics;
- D/S/P definitions or estimators;
- Delta/cognitive-effect law;
- Attention policy;
- Watch responsibility semantics;
- Kernel authority or human authorization.

The next useful product evaluation is to dogfood the now larger information stream before adding more speculative UI features.
