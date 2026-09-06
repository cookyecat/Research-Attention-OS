# Collective Attention Salience (P) — Observable Evidence Interface

Status: **ACTIVE INTERFACE DESIGN — CANDIDATE v0.1**  
Date: 2026-09-07  
Semantic baseline: `22_COLLECTIVE_ATTENTION_SALIENCE.md`  
Estimator modeling baseline: `23_COLLECTIVE_ATTENTION_ESTIMATOR_MODELING.md`

> Purpose: define the smallest reproducible evidence object that a P estimator may consume. This interface is a sensor/evidence boundary, not a second P classifier. It must preserve provenance, time, scope, and uncertainty without redefining the frozen P semantics.

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

## 2. Evidence Packet v0.1

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
    "reference_scale": "10^2 | 10^3 | 10^4 | 10^5 | 10^6 | 10^7+ | unknown",
    "basis": "lookup | llm_prior | explicit_event_scope | external_source | unknown",
    "provenance": "..."
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
10^2
10^3
10^4
10^5
10^6
10^7+
unknown
```

A range may be used later if evidence shows that single buckets are too coarse.

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

## 5. Current attention evidence

`current_attention_evidence` is the core numerator-side observation surface.

The interface deliberately permits both quantitative and structural evidence.

### 5.1 Candidate `kind` values

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

### 5.2 `window`

Every dynamic observation must declare its time window.

Examples:

```text
last 20m
last 3h
2026-09-06T18:00Z/2026-09-07T00:00Z
past 7d
```

Without a window, attention counts/trends are not reproducible.

### 5.3 `observation`

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

### 5.4 `source`

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

### 5.5 `observed_at`

Timestamp at which the observation was obtained.

This is distinct from the observation window.

### 5.6 `independence_group`

A lightweight way to prevent obvious double counting.

Example:

```text
newswire_reuters_story_123
same_platform_reposts_cluster_7
independent_search_signal
```

Many outlets copying one wire story should not automatically masquerade as many independent attention sources.

This field is diagnostic; it is not a mandatory estimator gate.

### 5.7 `quality`

Coarse evidence quality:

```text
direct       actual human-attention behavior or strong measurement
structural   indirect but strong penetration evidence
weak         ambiguous / low-information evidence
contaminated evidence known to include manipulation or forced exposure
```

The final estimator remains responsible for joint semantic judgment.

### 5.8 `contamination`

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

## 6. Recent attention history

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

## 7. Information explicitly excluded from the P evidence interface

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

## 8. Missing evidence and unknown values

The interface must represent absence of observation honestly.

Rules:

1. missing evidence is `unknown`, not zero;
2. no search-trend source available does not mean search volume is low;
3. no social-platform collector does not mean social discussion is absent;
4. unknown constituency size does not imply broad-public normalization;
5. the estimator must be allowed to return `insufficient_evidence` as measurement status without inventing a third semantic P label.

Canonical distinction:

```text
semantic target:
SALIENT / NOT_SALIENT

measurement status:
scorable / insufficient_evidence / technical_failure
```

---

## 9. Reproducibility requirement

A scored P evaluation must be reproducible from a frozen Evidence Packet.

Therefore fresh controlled cases should freeze:

```text
event semantic summary
as_of time
constituency prior or explicit unknown
current evidence observations
recent history observations
human P label
```

The model must not browse or retrieve additional live evidence during the controlled first-run unless that retrieval protocol itself is pre-registered and frozen.

Otherwise two runs at different times may receive different world evidence and cease to be comparable.

---

## 10. Minimal-v1 principle

Do not require platform-scale telemetry for P estimator v1.

The smallest useful packet can be:

```json
{
  "event": {...},
  "constituency_prior": {...},
  "current_attention_evidence": [...],
  "recent_attention_history": [...]
}
```

All four blocks may contain coarse natural-language observations.

For controlled semantic validation this is preferable to introducing fake numeric precision.

The research question is:

> Can a frozen estimator map a reproducible evidence packet to the Human P judgment implied by the frozen semantic contract?

not:

> Can RAOS already reconstruct the hidden telemetry of X, Weibo, TikTok, or Toutiao?

---

## 11. Example packets

### 11.1 Specialist-domain salience

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
    "basis": "llm_prior",
    "provenance": "frozen controlled-eval prior"
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

### 11.2 High exposure, weak genuine attention

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
    "basis": "explicit_event_scope",
    "provenance": "frozen controlled-eval prior"
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

### 11.3 Established salience with short-term decline

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
    "basis": "llm_prior",
    "provenance": "frozen controlled-eval prior"
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

## 12. Candidate freeze criteria for the interface

Freeze Evidence Packet v1 when:

1. it can represent all PC1–PC24 calibration evidence without adding P-specific conclusions;
2. it preserves event time and evidence windows;
3. it can express constituency scale without requiring exact population counts;
4. it distinguishes genuine attention evidence from exposure/manipulation evidence;
5. it can express enough history to support inertia judgments;
6. missing sources remain unknown rather than being silently treated as zero;
7. D, S, sentiment, and downstream AttentionAction remain absent;
8. two researchers given the same frozen packet can reproduce the estimator input exactly.

---

## 13. Current research decision

```text
P semantics                         FROZEN
P estimator architecture           ACTIVE
P Evidence Packet v0.1             CANDIDATE
Exact numeric penetration field    NOT REQUIRED
Current evidence provenance        REQUIRED
As-of time                         REQUIRED
History support                    REQUIRED WHEN AVAILABLE
Unknown != zero                    REQUIRED
D/S/policy fields                  EXCLUDED
Live browsing during controlled eval NOT ALLOWED unless pre-registered
```

---

## 14. Next step

Before writing the estimator prompt, validate this interface against the already-discussed PC1–PC24 development cases.

The goal is not to re-label those cases. Their Human labels are already development evidence.

The goal is to ask:

> **Can every relevant fact that drove the Human P judgment be represented in this packet without smuggling the answer itself into the evidence?**

If yes, freeze Evidence Packet v1 and only then implement P estimator v1 against that interface.
