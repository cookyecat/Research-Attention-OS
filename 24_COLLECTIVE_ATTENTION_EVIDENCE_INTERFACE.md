# Collective Attention Salience (P) — Observable Evidence Interface

Status: **ACTIVE INTERFACE DESIGN — CANDIDATE v0.2**  
Date: 2026-09-07  
Semantic baseline: `22_COLLECTIVE_ATTENTION_SALIENCE.md`  
Estimator modeling baseline: `23_COLLECTIVE_ATTENTION_ESTIMATOR_MODELING.md`

> Purpose: define the smallest reproducible evidence object that a P estimator may consume. This interface is a sensor/evidence boundary, not a second P classifier. It must preserve provenance, time, scope, coverage, and uncertainty without redefining the frozen P semantics.

---

## 1. Design principle

The frozen estimand is:

$$
P(E,t)=LatentSalience(R_E(\le t))
$$

with:

$$
R_E(t)=\frac{1}{|\mathcal G_E|}\sum_{i\in\mathcal G_E}a_i(E,t)
$$

RAOS cannot directly observe the theoretical numerator or denominator today.

Therefore the interface must expose **observations about the latent state**, not pretend that observations are the latent state itself.

Canonical separation:

```text
world / platforms / communities
        ↓
observable evidence
        ↓
P Evidence Packet
        ↓
P estimator v1
        ↓
SALIENT / NOT_SALIENT
```

Critical invariant:

$$
\boxed{Observation\neq P}
$$

A search spike, 1M views, 50 media articles, or 30% decline is evidence. None is P by itself.

---

## 2. Evidence Packet v0.2

Candidate top-level shape:

```json
{
  "event": {
    "event_id": "...",
    "as_of": "2026-09-07T00:00:00Z",
    "semantic_summary": "..."
  },
  "constituency_prior": {
    "description": "...",
    "scope": "domain | geographic | product | organization | broad_public | other",
    "reference_scale": "10^1 | 10^2 | 10^3 | 10^4 | 10^5 | 10^6 | 10^7+ | unknown",
    "reference_size_hint": "40 | 200-400 | unknown",
    "basis": "lookup | llm_prior | explicit_event_scope | external_source | unknown",
    "provenance": "..."
  },
  "collection_context": {
    "channels_checked": ["..."],
    "channels_unavailable": ["..."],
    "notes": "..."
  },
  "current_attention_evidence": [
    {
      "kind": "...",
      "window": "...",
      "observation": "...",
      "source": "...",
      "observed_at": "...",
      "independence_group": "...",
      "quality": "direct | structural | weak | contaminated",
      "contamination": ["paid", "bot", "forced_exposure", "duplicate", "unknown"]
    }
  ],
  "recent_attention_history": [
    {
      "window": "...",
      "observation": "...",
      "source": "..."
    }
  ]
}
```

This is a research interface candidate, not yet a frozen production schema.

---

## 3. Event block

Required:

```text
event_id
as_of
semantic_summary
```

### `event_id`

Stable identifier for the event cluster being judged.

P is defined over an event, not over an arbitrary individual post/article.

### `as_of`

The exact evaluation time.

This field is mandatory because:

$$
P=P(E,t)
$$

Two evaluations of the same event at different times may legitimately produce different P values.

### `semantic_summary`

A concise factual description of the underlying event.

It should contain enough semantic information to infer the objective constituency, but must not contain a pre-computed P judgment.

Forbidden examples:

```text
"a viral event"
"a highly salient AI topic"
"an event everyone is discussing"
```

unless those phrases are themselves grounded observations supplied in the attention-evidence section.

---

## 4. Constituency prior

The constituency prior describes the denominator-side approximation:

$$
\hat{\mathcal G}_E
$$

It is **context for estimation**, not a required hard gate.

Candidate fields:

### `description`

Natural-language reference community, e.g.:

```text
active AI-safety research and industry community
relevant commuters in Singapore
active players of game X
employees using company Y's internal finance system
broad national public
```

### `scope`

A coarse diagnostic only:

```text
domain
geographic
product
organization
broad_public
other
```

This is not a constituency ontology and must not become one.

### `reference_scale`

Prefer order-of-magnitude over false precision:

```text
10^1
10^2
10^3
10^4
10^5
10^6
10^7+
unknown
```

The `10^1` bucket is required because a legitimately small semantic constituency can still be the correct denominator, as in an organization-internal event.

### `reference_size_hint`

Optional grounded hint when the event or an external source explicitly provides a useful population size or range.

Examples:

```text
40
200-400
about 5,000
unknown
```

This field must not contain invented precision. Use it only when the size is explicitly stated or independently grounded.

The estimator should use the coarse reference scale when exact size is unavailable.

### `basis`

How the prior was obtained:

```text
lookup
llm_prior
explicit_event_scope
external_source
unknown
```

### `provenance`

Enough information to reproduce or audit the prior.

Important invariant:

> The constituency prior must be chosen from event semantics before using current attention observations to optimize the denominator.

---

## 5. Collection context

The interface must distinguish:

```text
not observed
```

from:

```text
observed and approximately zero / no meaningful signal
```

Therefore the packet carries lightweight collection coverage.

### `channels_checked`

Evidence channels that were actually queried or supplied.

Examples:

```text
search_trends
news_clusters
reddit
field_media
platform_engagement
manual_structural_evidence
```

### `channels_unavailable`

Relevant channels known to be unavailable to this measurement.

Examples:

```text
x_internal_telemetry
weibo_unique_viewers
tiktok_dwell_time
```

### `notes`

Optional collector limitations or coverage details.

This block does **not** tell the estimator what P should be. It only makes evidence absence interpretable.

Canonical invariant:

$$
\boxed{Unavailable\neq Zero}
$$

---

## 6. Current attention evidence

`current_attention_evidence` is the core numerator-side observation surface.

The interface deliberately permits both quantitative and structural evidence.

### 6.1 Candidate `kind` values

These are evidence forms, not required exhaustive enum values:

```text
active_search
meaningful_view_or_read
engagement
human_discussion
institutional_followup
domain_media_coverage
general_media_coverage
cross_source_spread
cross_platform_spread
community_channel_share
trend_or_rank
paid_exposure
autoplay_or_forced_exposure
bot_or_duplicate_activity
other
```

Do not turn this list into a fixed ontology unless implementation requires it.

### 6.2 `window`

Every dynamic observation must declare its time window.

Examples:

```text
last 20m
last 3h
2026-09-06T18:00Z/2026-09-07T00:00Z
past 7d
```

Without a window, attention counts/trends are not reproducible.

### 6.3 `observation`

The observed fact or source-grounded summary.

Good examples:

```text
"search index increased ~8x relative to the prior 7-day hourly baseline"
"11 of 14 major labs in the field issued public responses within 24h"
"2M autoplay starts, median watch time <3s, negligible search lift"
"discussion volume remains ~4x normal after a 30% decline from yesterday's peak"
```

Bad examples:

```text
"attention is high"
"P should be SALIENT"
"the event is important"
```

The evidence interface should carry facts, not conclusions.

### 6.4 `source`

The collector or external evidence source.

Examples:

```text
Google Trends
news cluster collector
Reddit collector
GitHub discussion collector
manual research annotation
synthetic controlled-eval statement
```

### 6.5 `observed_at`

Timestamp at which the observation was obtained.

This is distinct from the observation window.

### 6.6 `independence_group`

A lightweight way to prevent obvious double counting.

Example:

```text
newswire_reuters_story_123
same_platform_reposts_cluster_7
independent_search_signal
```

Many outlets copying one wire story should not automatically masquerade as many independent attention sources.

This field is diagnostic; it is not a mandatory estimator gate.

### 6.7 `quality`

Coarse evidence quality:

```text
direct       actual human-attention behavior or strong measurement
structural   indirect but strong penetration evidence
weak         ambiguous / low-information evidence
contaminated evidence known to include manipulation or forced exposure
```

The final estimator remains responsible for joint semantic judgment.

### 6.8 `contamination`

Explicit flags:

```text
paid
bot
forced_exposure
duplicate
unknown
```

Presence of contamination does not mechanically discard the observation; it tells the estimator not to equate raw volume with genuine attention.

---

## 7. Recent attention history

P has temporal inertia, therefore recent history is a first-class input when available.

Candidate minimal entry:

```json
{
  "window": "previous 24h",
  "observation": "domain discussion was very high; major institutions were still actively responding",
  "source": "..."
}
```

Important discipline:

> Prefer history of observations over history of previous model labels.

A previous `P=SALIENT` prediction may be included later as auxiliary state, but it must not become self-reinforcing truth.

Otherwise estimator error can persist merely because the previous estimator said so.

For v1 controlled evaluation, observation history is preferred.

---

## 8. Information explicitly excluded from the P evidence interface

Do not include these as P evidence fields:

```text
user_interest
standing_radar_match
D
material_consequence
S
event_importance
editorial_worthiness
sentiment
stance
positive_or_negative_valence
recommended_attention_action
predicted_P
```

Reason:

- `D` belongs to the personal-attention field;
- `S` belongs to shared-world consequence;
- sentiment/stance are orthogonal opinion variables;
- AttentionAction is downstream policy;
- `predicted_P` would make the interface circular.

This exclusion is essential to preserve D/S/P orthogonality.

---

## 9. Missing evidence and unknown values

The interface must represent absence of observation honestly.

Rules:

1. missing evidence is `unknown`, not zero;
2. no search-trend source available does not mean search volume is low;
3. no social-platform collector does not mean social discussion is absent;
4. unknown constituency size does not imply broad-public normalization;
5. an explicit observation such as "search index showed no meaningful lift" is different from a missing search channel;
6. the estimator must be allowed to return `insufficient_evidence` as measurement status without inventing a third semantic P label.

Canonical distinction:

```text
semantic target:
SALIENT / NOT_SALIENT

measurement status:
scorable / insufficient_evidence / technical_failure
```

---

## 10. Reproducibility requirement

A scored P evaluation must be reproducible from a frozen Evidence Packet.

Therefore fresh controlled cases should freeze:

```text
event semantic summary
as_of time
constituency prior or explicit unknown
collection coverage
current evidence observations
recent history observations
human P label
```

The model must not browse or retrieve additional live evidence during the controlled first-run unless that retrieval protocol itself is pre-registered and frozen.

Otherwise two runs at different times may receive different world evidence and cease to be comparable.

---

## 11. Minimal-v1 principle

Do not require platform-scale telemetry for P estimator v1.

The smallest useful packet can be:

```json
{
  "event": {...},
  "constituency_prior": {...},
  "collection_context": {...},
  "current_attention_evidence": [...],
  "recent_attention_history": [...]
}
```

All blocks may contain coarse natural-language observations.

For controlled semantic validation this is preferable to introducing fake numeric precision.

The research question is:

> Can a frozen estimator map a reproducible evidence packet to the Human P judgment implied by the frozen semantic contract?

not:

> Can RAOS already reconstruct the hidden telemetry of X, Weibo, TikTok, or Toutiao?

---

## 12. Calibration coverage check — PC1–PC24

The interface was checked against all development cases after v0.1 was drafted.

This is a representational check only. It does not re-score or reuse the Human labels as fresh validation evidence.

### Stable / current salience

```text
PC1, PC10
```

Representable through current evidence plus recent history without requiring positive velocity.

### Emerging attention

```text
PC2, PC4, PC6, PC12
```

Representable through search growth, independent uptake, cross-source/platform spread, and short current windows.

### Single-source but genuine human attention

```text
PC3
```

Representable through meaningful-view / engagement observations without imposing a mandatory multi-source gate.

### Paid / synthetic / passive exposure

```text
PC5, PC11, PC21
```

Representable through contamination flags plus explicit low genuine-attention observations.

### Constituency-scale normalization

```text
PC7, PC8, PC13, PC14, PC15, PC16, PC23, PC24
```

Representable through constituency description, coarse reference scale, optional grounded size hint, and structural/current attention evidence.

The v0.1 scale list was insufficient for PC15's legitimate ~40-person constituency. v0.2 adds `10^1` plus optional `reference_size_hint`.

### Inertia / decay / failed reactivation

```text
PC9, PC17, PC18, PC19, PC20
```

Representable through recent observation history plus current evidence. No previous model label is required.

### Lower-volume but stronger genuine attention

```text
PC22
```

Representable through meaningful engagement, active search, voluntary propagation, and ongoing discussion.

Coverage result:

```text
PC1-PC24 representable: 24/24
P-label leakage required: 0/24
D/S fields required: 0/24
Exact hidden platform telemetry required: 0/24
```

No remaining development case currently requires a new semantic P concept.

---

## 13. Example packets

### 13.1 Specialist-domain salience

```json
{
  "event": {
    "event_id": "ex-ai-safety-1",
    "as_of": "2026-09-07T00:00:00Z",
    "semantic_summary": "A new specialist AI-safety technique was released."
  },
  "constituency_prior": {
    "description": "active AI-safety research and industry community",
    "scope": "domain",
    "reference_scale": "10^4",
    "reference_size_hint": "unknown",
    "basis": "llm_prior",
    "provenance": "frozen controlled-eval prior"
  },
  "collection_context": {
    "channels_checked": ["manual_structural_evidence"],
    "channels_unavailable": [],
    "notes": "controlled evaluation packet"
  },
  "current_attention_evidence": [
    {
      "kind": "institutional_followup",
      "window": "last 24h",
      "observation": "most major labs in the field have publicly responded",
      "source": "synthetic controlled-eval statement",
      "observed_at": "2026-09-07T00:00:00Z",
      "independence_group": "field_labs",
      "quality": "structural",
      "contamination": []
    },
    {
      "kind": "domain_media_coverage",
      "window": "last 24h",
      "observation": "major specialist outlets are all covering the release",
      "source": "synthetic controlled-eval statement",
      "observed_at": "2026-09-07T00:00:00Z",
      "independence_group": "domain_media",
      "quality": "structural",
      "contamination": []
    }
  ],
  "recent_attention_history": []
}
```

### 13.2 High exposure, weak genuine attention

```json
{
  "event": {
    "event_id": "ex-autoplay-1",
    "as_of": "2026-09-07T00:00:00Z",
    "semantic_summary": "A video was heavily promoted by a recommendation surface."
  },
  "constituency_prior": {
    "description": "broad platform video audience",
    "scope": "broad_public",
    "reference_scale": "10^7+",
    "reference_size_hint": "unknown",
    "basis": "explicit_event_scope",
    "provenance": "frozen controlled-eval prior"
  },
  "collection_context": {
    "channels_checked": ["platform_engagement", "search_trends"],
    "channels_unavailable": [],
    "notes": "controlled evaluation packet"
  },
  "current_attention_evidence": [
    {
      "kind": "autoplay_or_forced_exposure",
      "window": "last 24h",
      "observation": "20M autoplay starts; median watch time under 3 seconds",
      "source": "synthetic controlled-eval statement",
      "observed_at": "2026-09-07T00:00:00Z",
      "independence_group": "platform_autoplay",
      "quality": "contaminated",
      "contamination": ["forced_exposure"]
    },
    {
      "kind": "active_search",
      "window": "last 24h",
      "observation": "no meaningful increase from baseline",
      "source": "synthetic controlled-eval statement",
      "observed_at": "2026-09-07T00:00:00Z",
      "independence_group": "search",
      "quality": "direct",
      "contamination": []
    }
  ],
  "recent_attention_history": []
}
```

### 13.3 Established salience with short-term decline

```json
{
  "event": {
    "event_id": "ex-inertia-1",
    "as_of": "2026-09-07T00:00:00Z",
    "semantic_summary": "An industry event became a dominant topic yesterday."
  },
  "constituency_prior": {
    "description": "relevant industry professional community",
    "scope": "domain",
    "reference_scale": "10^5",
    "reference_size_hint": "unknown",
    "basis": "llm_prior",
    "provenance": "frozen controlled-eval prior"
  },
  "collection_context": {
    "channels_checked": ["manual_structural_evidence"],
    "channels_unavailable": [],
    "notes": "controlled evaluation packet"
  },
  "current_attention_evidence": [
    {
      "kind": "human_discussion",
      "window": "last 6h",
      "observation": "discussion is down ~30% from yesterday but remains far above normal",
      "source": "synthetic controlled-eval statement",
      "observed_at": "2026-09-07T00:00:00Z",
      "independence_group": "domain_discussion",
      "quality": "direct",
      "contamination": []
    }
  ],
  "recent_attention_history": [
    {
      "window": "previous 24h",
      "observation": "the event was one of the industry's dominant discussion topics and most major institutions were actively responding",
      "source": "synthetic controlled-eval statement"
    }
  ]
}
```

---

## 14. Candidate freeze criteria for the interface

Freeze Evidence Packet v1 when:

1. it can represent all PC1–PC24 calibration evidence without adding P-specific conclusions;
2. it preserves event time and evidence windows;
3. it can express constituency scale without requiring exact population counts;
4. it can preserve a grounded small denominator when one is explicitly known;
5. it distinguishes genuine attention evidence from exposure/manipulation evidence;
6. it can express enough history to support inertia judgments;
7. missing/unavailable sources remain unknown rather than being silently treated as zero;
8. D, S, sentiment, and downstream AttentionAction remain absent;
9. two researchers given the same frozen packet can reproduce the estimator input exactly.

Current development coverage satisfies these representational criteria. The interface remains candidate until explicitly frozen for estimator v1.

---

## 15. Current research decision

```text
P semantics                         FROZEN
P estimator architecture           ACTIVE
P Evidence Packet v0.2             CANDIDATE — 24/24 DEV COVERAGE
Exact numeric penetration field    NOT REQUIRED
Current evidence provenance        REQUIRED
As-of time                         REQUIRED
Collection coverage                REQUIRED FOR REAL-WORLD PACKETS
History support                    REQUIRED WHEN AVAILABLE
Unknown != zero                    REQUIRED
D/S/policy fields                  EXCLUDED
Live browsing during controlled eval NOT ALLOWED unless pre-registered
```

---

## 16. Next step

The evidence interface is now representationally sufficient for all PC1–PC24 development cases.

The next research decision is whether to freeze this shape as Evidence Packet v1 and implement a minimal P estimator against it.

Do not modify the frozen P semantic contract to make the estimator easier.
