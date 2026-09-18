"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
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
  title?: string | null;
  canonical_url?: string | null;
  content_text?: string | null;
  published_at?: string | null;
  ingested_at?: string | null;
  ingestion_method?: string | null;
  raw_metadata?: Record<string, any>;
};

function displayTitle(source?: SourceSummary) {
  const title = source?.title || "Untitled source";
  return title.replace(/\s*\|\s*[^|]+$/, "").trim() || title;
}
function origin(source?: SourceSummary) {
  try { if (source?.canonical_url) return new URL(source.canonical_url).hostname.replace(/^www\./, ""); } catch {}
  return source?.ingestion_method || "source";
}
function timeValue(source?: SourceSummary, fallback?: string | null) {
  return source?.published_at || source?.raw_metadata?.published || source?.ingested_at || fallback || null;
}
function heroImage(source?: SourceSummary) {
  return source?.raw_metadata?.paper_lead_figure_url || source?.raw_metadata?.hero_image_cached_url || source?.raw_metadata?.hero_image_url || null;
}
function heroImageAlt(source?: SourceSummary) {
  return source?.raw_metadata?.hero_image_alt || displayTitle(source);
}
function heroVisualMode(source?: SourceSummary): "none" | "editorial" | "evidence" {
  if (!heroImage(source)) return "none";
  const raw = source?.raw_metadata || {};
  const social = Boolean(raw.social_platform) || source?.ingestion_method === "WEIBO_PUBLIC" || source?.ingestion_method === "X_PUBLIC";
  if (social) return "evidence";
  if (raw.paper_profile && !raw.paper_lead_figure_url) return "none";
  return "editorial";
}
function excerpt(source?: SourceSummary, length = 260) {
  const text = (source?.content_text || "").replace(/\s+/g, " ").trim();
  if (!text) return "RAOS has already judged this source and kept only the part that deserves your awareness.";
  const title = displayTitle(source);
  const cleaned = text.toLowerCase().startsWith(title.toLowerCase()) ? text.slice(title.length).trim() : text;
  return cleaned.length > length ? `${cleaned.slice(0, length).trim()}…` : cleaned;
}
function readingMinutes(source?: SourceSummary) {
  const content = source?.content_text || "";
  if (!content.trim()) return null;
  const cjk = (content.match(/[\u3400-\u9fff]/g) || []).length;
  const words = content.replace(/[\u3400-\u9fff]/g, " ").trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / 230 + cjk / 450));
}
function isSystemFixture(source?: SourceSummary) {
  if (!source || source.raw_metadata?.acquisition) return false;
  const title = (source.title || "").toLowerCase();
  return /(^|\b)(smoke test|live smoke|rollout smoke|dogfood smoke)(\b|$)/i.test(title);
}

export default function Page() {
  const [home, setHome] = useState<Home | null>(null);
  const [plans, setPlans] = useState<any[]>([]);
  const [sources, setSources] = useState<Record<string, SourceSummary>>({});
  const [watches, setWatches] = useState<any[]>([]);
  const [lastVisit, setLastVisit] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const sync = () => setLastVisit(readVisitContinuity().previousVisitAt);
    sync();
    window.addEventListener(VISIT_CONTINUITY_EVENT, sync as EventListener);
    return () => window.removeEventListener(VISIT_CONTINUITY_EVENT, sync as EventListener);
  }, []);

  useEffect(() => {
    Promise.all([api<Home>("/meta/home"), api<any[]>("/kernel/attention"), api<SourceSummary[]>("/sources?compact=true"), api<any[]>("/watches")])
      .then(([nextHome, nextPlans, nextSources, nextWatches]) => {
        setHome(nextHome); setPlans(nextPlans); setWatches(nextWatches);
        setSources(Object.fromEntries(nextSources.map((source) => [source.id, source])));
      })
      .catch((e) => setError(String(e.message || e)));
    api("/kernel/seed", { method: "POST" }).catch(() => undefined);
  }, []);

  const current = useMemo(() => {
    const latest = new Map<string, any>();
    for (const plan of plans) {
      const key = `${plan.candidate_type}:${plan.candidate_id}`;
      const prior = latest.get(key);
      if (!prior || timestampMs(plan.created_at) >= timestampMs(prior.created_at)) latest.set(key, plan);
    }
    return Array.from(latest.values());
  }, [plans]);

  const visibleSourcePlans = useMemo(() => current.filter((plan) =>
    plan.candidate_type === "SOURCE" && sources[plan.candidate_id] && !isSystemFixture(sources[plan.candidate_id])
  ), [current, sources]);

  const editorial = useMemo(() => visibleSourcePlans
    .filter((plan) => plan.disposition === "ENGAGE" || plan.disposition === "AWARE")
    .sort((a, b) => {
      const rank = (a.disposition === "ENGAGE" ? 0 : 1) - (b.disposition === "ENGAGE" ? 0 : 1);
      if (rank) return rank;
      return timestampMs(timeValue(sources[b.candidate_id], b.created_at)) - timestampMs(timeValue(sources[a.candidate_id], a.created_at));
    }), [visibleSourcePlans, sources]);

  const engage = visibleSourcePlans.filter((plan) => plan.disposition === "ENGAGE");
  const awareCount = visibleSourcePlans.filter((plan) => plan.disposition === "AWARE").length;
  const dropCount = visibleSourcePlans.filter((plan) => plan.disposition === "DROP").length;
  const watchCount = visibleSourcePlans.filter((plan) => plan.disposition === "WATCH").length;
  const lead = editorial[0];
  const leadSource = lead ? sources[lead.candidate_id] : undefined;
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

  const newObserved = lastVisit ? Object.values(sources).filter((source) => timestampMs(source.ingested_at) > lastVisit).length : null;
  const newSurfaced = lastVisit ? visibleSourcePlans.filter((plan) =>
    timestampMs(plan.created_at) > lastVisit && (plan.disposition === "ENGAGE" || plan.disposition === "AWARE")
  ).length : null;
  const lastVisitClock = formatVisitClock(lastVisit);

  const statusTitle = engage.length > 0
    ? `${engage.length} item${engage.length === 1 ? "" : "s"} need${engage.length === 1 ? "s" : ""} you now.`
    : "You're caught up.";
  const statusCopy = engage.length > 0
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

      <section className={`today-trust-summary ${engage.length > 0 ? "needs-you" : "caught-up"}`}>
        <div className="today-trust-status">
          <span className="trust-status-dot" />
          <div><strong>{statusTitle}</strong><span>{statusCopy}</span></div>
        </div>
        <div className="today-trust-meta">
          {lastVisit ? <><span>Since your last visit{lastVisitClock ? ` · ${lastVisitClock}` : ""}</span><strong>{newObserved ?? 0} observed · {newSurfaced ?? 0} surfaced</strong></> : <><span>Current state</span><strong>{dropCount} filtered · {activeWatchGroups.length} active monitors</strong></>}
        </div>
      </section>

      <section className="quiet-proof-strip" aria-label="RAOS work behind the quiet">
        <div className="quiet-proof-intro">
          <span>Behind the quiet</span>
          <strong>RAOS is carrying the scan load.</strong>
        </div>
        <div className="quiet-proof-stats">
          <span><b>{visibleSourcePlans.length}</b><small>judged</small></span>
          <span><b>{dropCount}</b><small>filtered</small></span>
          <span><b>{awareCount}</b><small>worth knowing</small></span>
          <span><b>{watchCount}</b><small>left to watch</small></span>
          <span><b>{activeWatchGroups.length}</b><small>active monitors</small></span>
        </div>
        {(home?.proposed_patches ?? 0) > 0 && <Link className="quiet-proof-action" href="/kernel">{home?.proposed_patches} context change awaits you →</Link>}
      </section>

      {lead ? (
        <section className="today-editorial">
          <Link className={`lead-story disposition-${lead.disposition} visual-${leadVisual}`} href={`/attention?source=${lead.candidate_id}`}>
            {leadVisual !== "none" && heroImage(leadSource) && (
              <div className={`lead-story-visual ${leadVisual}`}>
                <img src={heroImage(leadSource) || ""} alt={heroImageAlt(leadSource)} loading="eager" />
                {leadVisual === "evidence" && <span>Source visual · preserved as evidence, not decoration</span>}
              </div>
            )}
            <div className="story-kicker">
              <span className={`human-state ${lead.disposition}`} title={`RAOS state: ${lead.disposition}`}>{attentionLabel(lead.disposition)}</span>
              <span>{origin(sources[lead.candidate_id])}</span><span>·</span><span>{formatRelativeTime(timeValue(sources[lead.candidate_id], lead.created_at))}</span>
            </div>
            <h2>{displayTitle(sources[lead.candidate_id])}</h2>
            <p>{excerpt(sources[lead.candidate_id], 300)}</p>
            <div className="trust-why-block">
              <span>Why this is here</span>
              <p>{decisionWhy(lead)}</p>
              {closestContext(lead) && <small>Closest current context · {closestContext(lead)}</small>}
            </div>
            <div className="story-footer"><strong>{attentionAction(lead.disposition)}</strong><span>{readingMinutes(sources[lead.candidate_id]) ? `${readingMinutes(sources[lead.candidate_id])} min read` : "Read"} →</span></div>
          </Link>

          <aside className="brief-rail">
            <div className="brief-heading"><span>Brief</span><Link href="/attention">View all →</Link></div>
            {brief.map((plan) => {
              const source = sources[plan.candidate_id];
              return (
                <Link className="brief-story" href={`/attention?source=${plan.candidate_id}`} key={plan.id}>
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
