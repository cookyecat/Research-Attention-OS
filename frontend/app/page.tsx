"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, cachedApi } from "@/lib/api";
import { formatRelativeTime, timestampMs } from "@/lib/time";
import { formatVisitClock, readVisitContinuity, VISIT_CONTINUITY_EVENT } from "@/lib/visitContinuity";
import {
  attentionAction,
  attentionLabel,
  briefWhy,
  closestContext,
  decisionWhy,
  watchTriggerLabel,
} from "@/lib/attentionPresentation";

type Home = { proposed_patches: number };
type SourceSummary = {
  id: string;
  source_id?: string;
  title?: string | null;
  canonical_url?: string | null;
  excerpt?: string | null;
  published_at?: string | null;
  ingested_at?: string | null;
  ingestion_method?: string | null;
  origin_label?: string | null;
  hero_image_url?: string | null;
  hero_image_alt?: string | null;
  reading_minutes?: number | null;
  presentation_metadata?: Record<string, any>;
};
type TodayPayload = {
  lead?: any | null;
  briefs?: any[];
  counts: Record<string, number>;
  current_attention_count: number;
  continuity?: { observed: number; surfaced: number } | null;
};

function displayTitle(source?: SourceSummary) {
  const title = source?.presentation_metadata?.paper_title || source?.title || "Untitled source";
  return String(title).replace(/\s*\|\s*[^|]+$/, "").trim() || String(title);
}
function origin(source?: SourceSummary) {
  if (source?.origin_label) return source.origin_label;
  try { if (source?.canonical_url) return new URL(source.canonical_url).hostname.replace(/^www\./, ""); } catch {}
  return source?.ingestion_method || "source";
}
function timeValue(source?: SourceSummary, fallback?: string | null) {
  return source?.published_at || source?.presentation_metadata?.published || source?.ingested_at || fallback || null;
}
function heroImage(source?: SourceSummary) {
  return source?.hero_image_url || null;
}
function heroImageAlt(source?: SourceSummary) {
  return source?.hero_image_alt || displayTitle(source);
}
function heroVisualMode(source?: SourceSummary): "none" | "editorial" | "evidence" {
  if (!heroImage(source)) return "none";
  const meta = source?.presentation_metadata || {};
  const social = Boolean(meta.social_platform) || source?.ingestion_method === "WEIBO_PUBLIC" || source?.ingestion_method === "X_PUBLIC";
  if (social) return "evidence";
  if (meta.paper_profile && !source?.hero_image_url) return "none";
  return "editorial";
}
function excerpt(source?: SourceSummary, length = 260) {
  const text = (source?.excerpt || "").replace(/\s+/g, " ").trim();
  if (!text) return "RAOS has already judged this source and kept only the part that deserves your awareness.";
  return text.length > length ? `${text.slice(0, length).trim()}…` : text;
}
function readingMinutes(source?: SourceSummary) {
  return source?.reading_minutes ?? null;
}
function isSystemFixture(_source?: SourceSummary) {
  return false;
}
function planSourceId(plan?: any) {
  return plan?.representative_source_id || (plan?.candidate_type === "SOURCE" ? plan?.candidate_id : null);
}

export default function Page() {
  const [home, setHome] = useState<Home | null>(null);
  const [plans, setPlans] = useState<any[]>([]);
  const [sources, setSources] = useState<Record<string, SourceSummary>>({});
  const [watches, setWatches] = useState<any[]>([]);
  const [lastVisit, setLastVisit] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [attentionAvailable, setAttentionAvailable] = useState<boolean | null>(null);
  const [attentionCounts, setAttentionCounts] = useState<Record<string, number>>({});
  const [continuity, setContinuity] = useState<{ observed: number; surfaced: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const sync = () => setLastVisit(readVisitContinuity().previousVisitAt);
    sync();
    window.addEventListener(VISIT_CONTINUITY_EVENT, sync as EventListener);
    return () => window.removeEventListener(VISIT_CONTINUITY_EVENT, sync as EventListener);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const since = lastVisit ? `?since_ms=${lastVisit}` : "";
      const results = await Promise.allSettled([
        api<any[]>("/kernel/patches").then((patches) => ({
          proposed_patches: patches.filter((patch) => patch?.status === "PROPOSED").length,
        })),
        api<TodayPayload>(`/user-space/today${since}`),
        api<any[]>("/watches"),
      ]);
      if (cancelled) return;

      const [homeResult, todayResult, watchesResult] = results;
      if (homeResult.status === "fulfilled") setHome(homeResult.value);
      if (todayResult.status === "fulfilled") {
        const payload = todayResult.value;
        const cards = [payload.lead, ...(payload.briefs || [])].filter(Boolean) as any[];
        const nextPlans = cards.map((card) => ({
          id: card.attention_plan_id,
          candidate_type: "EVENT",
          candidate_id: card.event_id,
          representative_source_id: card.id,
          disposition: card.disposition,
          created_at: card.attention_created_at,
          reason: card.reason,
          urgency: card.urgency,
          cognitive_budget_minutes: card.cognitive_budget_minutes,
        }));
        setPlans(nextPlans);
        setSources(Object.fromEntries(cards.map((card) => [card.id, card as SourceSummary])));
        setAttentionCounts(payload.counts || {});
        setContinuity(payload.continuity || null);
        setAttentionAvailable(true);
      } else {
        setAttentionAvailable(false);
      }
      if (watchesResult.status === "fulfilled") setWatches(watchesResult.value);

      const labels = ["home", "attention", "watches"];
      const failedLabels = results
        .map((result, index) => ({ result, index }))
        .filter(({ result }) => result.status === "rejected")
        .map(({ index }) => labels[index]);
      setError(failedLabels.length > 0
        ? "Some live RAOS data is temporarily unavailable: " + failedLabels.join(", ") + "."
        : null);
      setLoading(false);
    })();

    api("/kernel/seed", { method: "POST" }).catch(() => undefined);
    return () => { cancelled = true; };
  }, [lastVisit]);

  const current = useMemo(() => {
    const latest = new Map<string, any>();
    for (const plan of plans) {
      const key = `${plan.candidate_type}:${plan.candidate_id}`;
      const prior = latest.get(key);
      if (!prior || timestampMs(plan.created_at) >= timestampMs(prior.created_at)) latest.set(key, plan);
    }
    return Array.from(latest.values());
  }, [plans]);

  const visibleSourcePlans = useMemo(() => current.filter((plan) => {
    const sourceId = planSourceId(plan);
    return Boolean(sourceId && sources[sourceId] && !isSystemFixture(sources[sourceId]));
  }), [current, sources]);

  const editorial = useMemo(() => visibleSourcePlans
    .filter((plan) => plan.disposition === "ENGAGE" || plan.disposition === "AWARE")
    .sort((a, b) => {
      const rank = (a.disposition === "ENGAGE" ? 0 : 1) - (b.disposition === "ENGAGE" ? 0 : 1);
      if (rank) return rank;
      const sourceA = planSourceId(a);
      const sourceB = planSourceId(b);
      return timestampMs(timeValue(sourceB ? sources[sourceB] : undefined, b.created_at))
        - timestampMs(timeValue(sourceA ? sources[sourceA] : undefined, a.created_at));
    }), [visibleSourcePlans, sources]);

  const engage = visibleSourcePlans.filter((plan) => plan.disposition === "ENGAGE");
  const engageCount = attentionCounts.ENGAGE ?? engage.length;
  const awareCount = attentionCounts.AWARE ?? visibleSourcePlans.filter((plan) => plan.disposition === "AWARE").length;
  const dropCount = attentionCounts.DROP ?? 0;
  const watchCount = attentionCounts.WATCH ?? 0;
  const judgedCount = attentionCounts.ALL ?? visibleSourcePlans.length;
  const lead = editorial[0];
  const leadSourceId = lead ? planSourceId(lead) : null;
  const leadSource = leadSourceId ? sources[leadSourceId] : undefined;
  const leadVisual = heroVisualMode(leadSource);
  const brief = editorial.slice(1, 4);

  const activeWatchGroups = useMemo(() => {
    const grouped = new Map<string, any[]>();
    for (const watch of watches.filter((item) => item.status === "ACTIVE")) {
      const key = `${watch.target_type}:${watch.target_ref}`;
      grouped.set(key, [...(grouped.get(key) || []), watch]);
    }
    return Array.from(grouped.values()).map((group) => {
      const primary = group[0];
      const triggers = Array.from(new Set(group.flatMap((watch) => (watch.triggers || []).map((trigger: any) => String(trigger.trigger_type)))));
      return { primary, triggers };
    });
  }, [watches]);

  const newObserved = lastVisit ? (continuity?.observed ?? 0) : null;
  const newSurfaced = lastVisit ? (continuity?.surfaced ?? 0) : null;
  const lastVisitClock = formatVisitClock(lastVisit);

  const statusTitle = loading
    ? "Loading current attention…"
    : attentionAvailable === false
      ? "Current attention is temporarily unavailable."
      : engageCount > 0
        ? `${engageCount} item${engageCount === 1 ? "" : "s"} need${engageCount === 1 ? "s" : ""} you now.`
        : "You're caught up.";
  const attentionUnknown = loading || attentionAvailable === false;
  const statusCopy = loading
    ? "RAOS is rebuilding the current view from its persisted state."
    : attentionAvailable === false
      ? "The underlying observations are still preserved; this view could not load the current Attention projection."
      : engageCount > 0
        ? "Everything else has already been filtered, compressed, or delegated to RAOS."
        : "Nothing urgent is waiting. RAOS is still observing and carrying delegated checks in the background.";

  return (
    <>
      <header className="page-header today-header">
        <div>
          <div className="eyebrow">Today</div>
          <h1 className="page-title">What deserves your attention.</h1>
          <p className="page-subtitle">RAOS has already scanned the incoming world. Start with what needs you, understand why, then get back to your work.</p>
        </div>
        <Link className="button-link ghost" href="/inbox">Add source</Link>
      </header>
      {error && <p className="error">{error}</p>}

      <section className={`today-trust-summary ${engageCount > 0 ? "needs-you" : "caught-up"}`}>
        <div className="today-trust-status">
          <span className="trust-status-dot" />
          <div><strong>{statusTitle}</strong><span>{statusCopy}</span></div>
        </div>
        <div className="today-trust-meta">
          {attentionUnknown ? <><span>Current state</span><strong>Loading…</strong></> : lastVisit ? <><span>Since your last visit{lastVisitClock ? ` · ${lastVisitClock}` : ""}</span><strong>{newObserved ?? 0} observed · {newSurfaced ?? 0} surfaced</strong></> : <><span>Current state</span><strong>{dropCount} filtered · {activeWatchGroups.length} active monitors</strong></>}
        </div>
      </section>

      <section className="quiet-proof-strip" aria-label="RAOS work behind the quiet">
        <div className="quiet-proof-intro">
          <span>Behind the quiet</span>
          <strong>RAOS is carrying the scan load.</strong>
        </div>
        <div className="quiet-proof-stats">
          <span><b>{attentionUnknown ? "—" : judgedCount}</b><small>judged</small></span>
          <span><b>{attentionUnknown ? "—" : dropCount}</b><small>filtered</small></span>
          <span><b>{attentionUnknown ? "—" : awareCount}</b><small>worth knowing</small></span>
          <span><b>{attentionUnknown ? "—" : watchCount}</b><small>left to watch</small></span>
          <span><b>{loading ? "—" : activeWatchGroups.length}</b><small>active monitors</small></span>
        </div>
        {(home?.proposed_patches ?? 0) > 0 && <Link className="quiet-proof-action" href="/kernel">{home?.proposed_patches} context change awaits you →</Link>}
      </section>

      {loading ? (
        <section className="hero-panel quiet-hero"><div className="eyebrow">Loading</div><h2>Building the current attention view.</h2><p>RAOS is reading its persisted projections. Observations remain available while this view catches up.</p></section>
      ) : attentionAvailable === false ? (
        <section className="hero-panel quiet-hero"><div className="eyebrow">Attention unavailable</div><h2>The current Attention projection could not be loaded.</h2><p>The underlying observations are preserved. Retry this page when the projection service is available.</p></section>
      ) : lead && leadSourceId ? (
        <section className="today-editorial">
          <Link className={`lead-story disposition-${lead.disposition} visual-${leadVisual}`} href={`/attention?source=${leadSourceId}`}>
            {leadVisual !== "none" && heroImage(leadSource) && (
              <div className={`lead-story-visual ${leadVisual}`}>
                <img src={heroImage(leadSource) || ""} alt={heroImageAlt(leadSource)} loading="eager" />
                {leadVisual === "evidence" && <span>Source visual · preserved as evidence, not decoration</span>}
              </div>
            )}
            <div className="story-kicker">
              <span className={`human-state ${lead.disposition}`} title={`RAOS state: ${lead.disposition}`}>{attentionLabel(lead.disposition)}</span>
              <span>{origin(leadSource)}</span><span>·</span><span>{formatRelativeTime(timeValue(leadSource, lead.created_at))}</span>
            </div>
            <h2>{displayTitle(leadSource)}</h2>
            <p>{excerpt(leadSource, 300)}</p>
            <div className="trust-why-block">
              <span>Why this is here</span>
              <p>{decisionWhy(lead)}</p>
              {closestContext(lead) && <small>Closest current context · {closestContext(lead)}</small>}
            </div>
            <div className="story-footer"><strong>{attentionAction(lead.disposition)}</strong><span>{readingMinutes(leadSource) ? `${readingMinutes(leadSource)} min read` : "Read"} →</span></div>
          </Link>

          <aside className="brief-rail">
            <div className="brief-heading"><span>Brief</span><Link href="/attention">View all →</Link></div>
            {brief.map((plan) => {
              const sourceId = planSourceId(plan);
              const source = sourceId ? sources[sourceId] : undefined;
              if (!sourceId || !source) return null;
              return (
                <Link className="brief-story" href={`/attention?source=${sourceId}`} key={plan.id}>
                  <div className="story-kicker"><span className={`status-dot-small ${plan.disposition}`} />{origin(source)} · {formatRelativeTime(timeValue(source, plan.created_at))}</div>
                  <h3>{displayTitle(source)}</h3>
                  <p className="brief-why">↳ {briefWhy(plan)}</p>
                  <span className="brief-action">{attentionLabel(plan.disposition)}</span>
                </Link>
              );
            })}
            {brief.length === 0 && <div className="brief-empty">No other items deserve awareness right now. RAOS has already filtered the rest.</div>}
          </aside>
        </section>
      ) : (
        <section className="hero-panel quiet-hero"><div className="eyebrow">Quiet is a feature</div><h2>Nothing new needs you right now.</h2><p>RAOS is still observing, filtering, and carrying delegated checks. You can keep working.</p></section>
      )}

      <section className="section today-lower-grid">
        <div>
          <div className="section-heading"><div><h2>RAOS is carrying these</h2><p>You do not need to keep them in working memory.</p></div><Link className="text-link" href="/watch">Open Watch →</Link></div>
          <div className="delegated-list">
            {activeWatchGroups.slice(0, 4).map(({ primary, triggers }, index) => (
              <div className="delegated-item" key={`${primary.target_type}:${primary.target_ref}`}>
                <span className="delegated-index">{String(index + 1).padStart(2, "0")}</span>
                <div className="delegated-copy"><strong>{primary.target_ref}</strong>{triggers.length > 0 && <small>Waiting for {triggers.slice(0, 3).map(watchTriggerLabel).join(" · ")}</small>}</div>
                <span className="monitoring-state">Monitoring</span>
              </div>
            ))}
            {activeWatchGroups.length === 0 && <div className="empty-state">Nothing is delegated right now.</div>}
          </div>
        </div>
      </section>
    </>
  );
}
