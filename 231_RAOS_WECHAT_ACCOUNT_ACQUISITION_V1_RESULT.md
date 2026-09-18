# RAOS WeChat Account Acquisition V1 — Result

Status: **DOGFOOD READY**  
Date: 2026-09-18

## 1. Scope

V1 adds first-class acquisition for three public WeChat Official Accounts:

- 机器之心
- 新智元
- 量子位

The goal is continuous public-article observation without authenticated personal WeChat state, while preserving publisher identity, article structure, images, and provenance.

## 2. Architecture

The acquisition contract is intentionally split into discovery and article transport:

```text
public feed/index
→ discover a candidate WeChat article
→ verify configured __biz
→ stable identity = biz + mid + idx
→ try publisher-direct mp.weixin.qq.com
→ if readable: use publisher-direct body
→ if WeChat challenge blocks the page: use the same feed item's full-HTML snapshot
→ normalize into one canonical Information Object
```

The canonical URL remains the original `mp.weixin.qq.com` URL in both cases.

## 3. Trust and provenance invariants

A Wechat2RSS path is a **transport fallback**, not a second independent report.

```text
wechat_mirror_role = transport-fallback
wechat_mirror_is_independent_evidence = false
```

Permanent rule:

> **Discovery transport is not evidence multiplicity.**

A mirror, cache, rendered fallback, or feed snapshot carrying the same publisher object must never inflate collective-attention or corroboration evidence.

Article identity is stable across tracking/query churn:

```text
wechat:{biz}:{mid}:{idx}
```

Parameters such as `sn`, `chksm`, ordering differences, or other transport query parameters do not create a second information object.

The configured `__biz` is verified before a discovered item is admitted. A mismatched account is rejected.

## 4. Reader fidelity

V1 preserves:

- canonical article title and publisher;
- paragraph / heading / list structure;
- substantive body images;
- original WeChat CDN media identity;
- WeChat `mpvideo` iframe embeds when publisher-direct HTML exposes them.

Wechat2RSS image-proxy URLs are restored to original `mmbiz.qpic.cn` identities before deduplication and caching. The proxy URL is retained only as transport provenance.

WeChat-rich-text span boundaries receive publisher-specific text normalization so formatting spans do not invent spaces inside words or numbers.

Examples fixed during dogfood:

```text
E gocentric  → Egocentric
Harne ss     → Harness
1 5 0        → 150
```

Images embedded inside H1–H4 publisher heading templates are treated as heading decoration rather than standalone figures.

## 5. Discovery sources

Current dogfood discovery uses public, anonymous feeds that expose the original WeChat article URL and full article HTML snapshots.

机器之心 and 新智元 each have two configured discovery feeds for redundancy. 量子位 currently has one validated feed.

Official-site feeds/APIs remain available as future discovery corroboration/fallback, but V1 does not ingest them as duplicate independent information objects.

## 6. Dogfood baseline

Three `WECHAT_ACCOUNT` SourceDefinitions are active with a 30-minute polling interval.

A controlled baseline captured the latest 3 articles per account:

```text
3 accounts × 3 articles = 9 baseline Sources
```

Baseline semantics:

```text
cognition_deferred = true
cognition_defer_reason = baseline
cognition_reconcile_eligible = false
```

No baseline article was pushed through cognition. Future genuinely new arrivals are handled by normal acquisition/cognition flow.

The nine baseline articles were later corrected append-only for span-boundary canonical-text normalization. Historical Sources were preserved.

## 7. Validation

Real browser/API validation confirmed:

```text
机器之心  9 headings / 9 figures
新智元    1 heading  / 11 figures
量子位    5 headings / 13 figures
```

Reader counts matched the final structured metadata exactly for the sampled current Snapshots.

Focused WeChat + URL presentation regression:

```text
20 passed
```

Final full backend regression:

```text
835 passed
63 skipped
1 failed
```

The only failure remains the pre-existing Case-K `PREEMPT` vs `PRIORITY` urgency residual. No new acquisition, cognition, or Phase 13 regression was introduced.

Final live runtime:

```text
overall      READY
purpose      CANONICAL
attestation  ATTESTED
mismatches   []

Observation  READY
Cognition    READY
Attention    READY
Delivery     READY
```

## 8. Frozen V1 principles

1. **Discover broadly, but verify publisher identity before admission.**
2. **Transport fallback is not independent evidence.**
3. **Canonical identity must survive URL/query churn.**
4. **Publisher-direct is preferred; a verified full-body mirror may carry the same information object when direct access is blocked.**
5. **Presentation repair must not silently rewrite already-cognized canonical content.**
6. **Publisher-specific adapters are justified only by repeated dogfood evidence, not one-off URL patches.**
