# RAOS Public Social Acquisition + Source Library Result

Status: **DOGFOOD READY**
Date: 2026-09-14

## 1. Residual

After RSS diversity expansion, real use exposed two coupled problems:

- Inbox still rendered only the six most recent Sources, hiding most of the expanded acquisition pool;
- baseline Sources without an AnalysisRun could not be read and remained stuck on `Loading source…` because opening Reader implicitly triggered cognition.

This made Acquisition appear sparse even when persisted information had already expanded substantially.

## 2. Source Library

Inbox is now a Source Library rather than a six-item recent list.

It renders 18 Sources initially, supports incremental expansion, source/domain filters, and text search. Publisher hero visuals are reused when available. Internal smoke fixtures remain excluded from User Space.

Source publication time is now exposed through `SourceOut` and preferred over ingestion time, so baseline imports preserve the source's real chronology rather than appearing to have all been published at bootstrap time.

## 3. Read before cognition

Reader no longer requires an AnalysisRun. A persisted Source is immediately readable from Inbox even if cognition has never been executed.

The unanalysed state is explicit:

```text
Source exists
→ Reader available immediately
→ NOT ANALYZED YET
→ Analyze with RAOS only on explicit user action
```

This separates information acquisition from LLM spending and removes the previous indefinite `Loading source…` state for baseline material.

`RSS_FALLBACK` Sources also disclose that only publisher feed text was preserved when the canonical page could not be fetched. A short feed summary is therefore presented as provenance-aware fallback content rather than pretending to be a full article.

## 4. Public social Adapter boundary

Acquisition now dispatches through a transport Adapter boundary rather than assuming every unattended Source is RSS:

```text
SourceDefinition
      ↓
Adapter
├─ RSS
├─ WEIBO_PUBLIC
└─ X_PUBLIC
      ↓
ExternalInformationItem → Observation → Snapshot → RAOS Source
```

All transports reuse the existing identity, observation, snapshot, baseline, and optional-cognition pipeline. No social transport has authority to judge relevance.

`WEIBO_PUBLIC` uses Sina Weibo's anonymous visitor-session flow (`genvisitor2` → public mobile API) and requires no logged-in account or private Cookie. UID `1912085257` (`斌叔OKmath`) was validated live and registered as an enabled 10-minute dogfood Source.

`X_PUBLIC` is implemented as a separate optional Adapter using X's public syndication timeline through the locally configured `proxychains4` transport. It requires no X login or API key.

The current Karpathy syndication payload was parseable but stale relative to the present date, so `X · Karpathy` is registered but disabled. This preserves the plug-in boundary without letting an unreliable freshness source contaminate the active world model.

Authenticated social access remains a separate future layer:

```text
PUBLIC adapter ≠ authenticated Following timeline
```

If account-authorized X/Weibo sources are added later, they must carry explicit authorization and provenance rather than reusing browser cookies invisibly.

## 5. Live dogfood state

The running dogfood database reached 68 persisted Sources after RSS expansion plus the first Weibo baseline. Five latest public Weibo posts were captured with zero delivery failures and without baseline cognition.

The active registry contains 13 definitions: RSS/Atom sources, one enabled `WEIBO_PUBLIC` source, one disabled `X_PUBLIC` source, and Hugging Face retained disabled under the conservative SSRF policy.

## 6. Product invariant

The Source Library and public-social work freezes a stronger product invariant:

```text
Acquisition volume may grow independently of cognition volume.
```

A large observable information pool is allowed. Analysis is an optional cognitive act, not a prerequisite for reading or preserving a Source.

This is important for both cost control and RAOS semantics: external information can become observable without immediately demanding user attention or LLM reasoning.

## 7. Authority boundary

This work changes transport diversity, delivery robustness, Source presentation, and the read-before-cognition interaction contract only.

It does not change Sensor/Auditor semantics, Delta law, D/S/P, Attention policy, Watch responsibility, Kernel authority, or human authorization.

Public social adapters consume only anonymously observable material. No private account data, private timeline, or logged-in following graph was accessed during this implementation.
