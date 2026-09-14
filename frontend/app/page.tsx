"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { formatRelativeTime, timestampMs } from "@/lib/time";

type Home = { proposed_patches: number };
type SourceSummary = {
  id: string;
  title?: string | null;
  canonical_url?: string | null;
  content_text?: string | null;
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
  return source?.raw_metadata?.published || source?.ingested_at || fallback || null;
}
function heroImage(source?: SourceSummary) {
  return source?.raw_metadata?.hero_image_cached_url || source?.raw_metadata?.hero_image_url || null;
}
function heroImageAlt(source?: SourceSummary) {
  return source?.raw_metadata?.hero_image_alt || displayTitle(source);
}
function excerpt(source?: SourceSummary, length = 260) {
  const text = (source?.content_text || "").replace(/\s+/g, " ").trim();
  if (!text) return "RAOS has classified this source and kept only the attention state you need.";
  const title = displayTitle(source).toLowerCase();
  const cleaned = text.toLowerCase().startsWith(title) ? text.slice(displayTitle(source).length).trim() : text;
  return cleaned.length > length ? `${cleaned.slice(0, length).trim()}…` : cleaned;
}
function isSystemFixture(source?: SourceSummary) {
  if (!source || source.raw_metadata?.acquisition) return false;
  const title = (source.title || "").toLowerCase();
  return /(^|\b)(smoke test|live smoke|rollout smoke|dogfood smoke)(\b|$)/i.test(title);
}

function actionCopy(disposition: string) {
  if (disposition === "ENGAGE") return "Needs focused attention";
  if (disposition === "AWARE") return "Worth knowing";
  if (disposition === "WATCH") return "RAOS is watching";
  return "Filtered out";
}

export default function Page() {
  const [home, setHome] = useState<Home | null>(null);
  const [plans, setPlans] = useState<any[]>([]);
  const [sources, setSources] = useState<Record<string, SourceSummary>>({});
  const [watches, setWatches] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

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
      if (!latest.has(key)) latest.set(key, plan);
    }
    return Array.from(latest.values());
  }, [plans]);

  const editorial = useMemo(() => current
    .filter((plan) => plan.disposition !== "DROP" && plan.candidate_type === "SOURCE" && !isSystemFixture(sources[plan.candidate_id]))
    .sort((a, b) => timestampMs(timeValue(sources[b.candidate_id], b.created_at)) - timestampMs(timeValue(sources[a.candidate_id], a.created_at))), [current, sources]);

  const engage = current.filter((plan) => plan.disposition === "ENGAGE");
  const lead = editorial[0];
  const brief = editorial.slice(1, 4);
  const awareCount = current.filter((plan) => plan.disposition === "AWARE").length;
  const dropCount = current.filter((plan) => plan.disposition === "DROP").length;
  const currentBudget = current.reduce((sum, plan) => sum + Number(plan.cognitive_budget_minutes || 0), 0);
  const activeWatchResponsibilities = new Set(watches.filter((watch) => watch.status === "ACTIVE").map((watch) => `${watch.target_type}:${watch.target_ref}`));
  const delegated = Array.from(activeWatchResponsibilities).slice(0, 4).map((key) => key.split(":").slice(1).join(":"));

  return (
    <>
      <header className="page-header today-header">
        <div>
          <div className="eyebrow">Today</div>
          <h1 className="page-title">What deserves your attention.</h1>
          <p className="page-subtitle">A living brief of what changed, what matters, and what RAOS is already carrying for you.</p>
        </div>
        <Link className="button-link ghost" href="/inbox">Add source</Link>
      </header>
      {error && <p className="error">{error}</p>}

      {engage.length > 0 && (
        <Link className="focus-alert" href={`/attention?source=${engage[0].candidate_id}`}>
          <span className="focus-alert-dot" />
          <div><strong>{engage.length} item{engage.length === 1 ? "" : "s"} still need your judgment</strong><span>{displayTitle(sources[engage[0].candidate_id])}</span></div>
          <span className="focus-alert-action">Review →</span>
        </Link>
      )}

      {lead ? (
        <section className="today-editorial">
          <Link className={`lead-story disposition-${lead.disposition}`} href={`/attention?source=${lead.candidate_id}`}>
            {heroImage(sources[lead.candidate_id]) && <img className="lead-story-image" src={heroImage(sources[lead.candidate_id])} alt={heroImageAlt(sources[lead.candidate_id])} loading="eager" />}
            <div className="story-kicker"><span className={`badge ${lead.disposition}`}>{lead.disposition}</span><span>{origin(sources[lead.candidate_id])}</span><span>·</span><span>{formatRelativeTime(timeValue(sources[lead.candidate_id], lead.created_at))}</span></div>
            <h2>{displayTitle(sources[lead.candidate_id])}</h2>
            <p>{excerpt(sources[lead.candidate_id], 330)}</p>
            <div className="story-footer"><strong>{actionCopy(lead.disposition)}</strong><span>Read story →</span></div>
          </Link>

          <aside className="brief-rail">
            <div className="brief-heading"><span>Brief</span><Link href="/attention">View all →</Link></div>
            {brief.map((plan) => {
              const source = sources[plan.candidate_id];
              return (
                <Link className="brief-story" href={`/attention?source=${plan.candidate_id}`} key={plan.id}>
                  <div className="story-kicker"><span className={`status-dot-small ${plan.disposition}`} />{origin(source)} · {formatRelativeTime(timeValue(source, plan.created_at))}</div>
                  <h3>{displayTitle(source)}</h3>
                  <p>{excerpt(source, 135)}</p>
                </Link>
              );
            })}
            {brief.length === 0 && <div className="brief-empty">No other current items. RAOS has already filtered the rest.</div>}
          </aside>
        </section>
      ) : (
        <section className="hero-panel"><div className="eyebrow">Quiet is a feature</div><h2>Nothing new needs you right now.</h2><p>RAOS is still monitoring in the background. Keep working.</p></section>
      )}

      <section className="section today-lower-grid">
        <div>
          <div className="section-heading"><div><h2>RAOS is carrying these</h2><p>You do not need to keep them in working memory.</p></div><Link className="text-link" href="/watch">Open Watch →</Link></div>
          <div className="delegated-list">
            {delegated.map((item, index) => <div className="delegated-item" key={`${item}-${index}`}><span className="delegated-index">{String(index + 1).padStart(2, "0")}</span><strong>{item}</strong><span>Monitoring</span></div>)}
            {delegated.length === 0 && <div className="empty-state">Nothing is delegated right now.</div>}
          </div>
        </div>
        <aside className="attention-pulse">
          <div className="eyebrow">Attention pulse</div>
          <div className="pulse-number"><strong>{currentBudget}</strong><span>min</span></div>
          <p>Current policy budget across all source states — not a to-do debt.</p>
          <div className="pulse-stats"><span><b>{awareCount}</b> know</span><span><b>{dropCount}</b> filtered</span><span><b>{activeWatchResponsibilities.size}</b> delegated</span><span><b>{home?.proposed_patches ?? 0}</b> context changes</span></div>
        </aside>
      </section>
    </>
  );
}
