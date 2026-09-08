# Phase 8B — Continuous Source Arrival Result

Status: **CLOSED / SUFFICIENT**
Date: 2026-09-09
Measurement SHA: `e9d6b7c107c9e94b9ee42e68c4ce216a62d316dc`

## 1. Question

Phase 8B asked whether continuous source arrival can distinguish a new article from genuinely new evidence before spending additional WATCH/LLM attention.

Core invariant:

> **New Article != New Evidence.**

More precisely:

```text
New Source != New Relevant Evidence != New Independent Evidence
```
## 2. Controlled arrival sequence

The canonical development sequence was:

```text
A = original evidence -> WATCH
B = exact repost of A
C = secondary REPORTS_ON A
X = unrelated source
D = independent evidence attached to the same Event
```

The experiment used a deterministic rule provider so the measurement isolated SourceGraph/evidence-independence behavior rather than LLM variance.
## 3. Canonical result

All preregistered conditions passed:

```text
B repost      -> DUPLICATE_SUPPRESSED -> no re-analysis
C secondary   -> RECHECK -> independent=1, secondary=1 -> KEEP_ACTIVE
X unrelated   -> ordinary analysis, not injected into WATCH
D independent -> RECHECK -> independent=2, secondary=1 -> PROMOTED
```

Watch history remained singular and auditable:

```text
DUPLICATE_SUPPRESSED -> KEEP_ACTIVE -> PROMOTED
```
## 4. Research memory

> **The system's input unit is an article, but its cognitive unit is not an article.**

> **Article count is not evidence count.**

RAOS does not care how many documents entered the system. It cares what genuinely new, decision-relevant change entered the represented world state.

Secondary reports may still matter as observations of attention or propagation, but they must not silently inflate independent evidence maturity.
## 5. Decision

Phase 8B is sufficient. Do not expand synthetic arrival cases merely to accumulate a larger benchmark.

The next step is **Phase 8C — Narrow Real Dogfood Loop**: expose the same continuous-arrival semantics to a small, auditable real source inbox/feed before attempting broad crawling or open-world semantic event clustering.
