"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, apiOrNull } from "@/lib/api";
import { formatBeijingTime, formatRelativeTime, timestampMs } from "@/lib/time";
import KernelPatchCard from "@/components/KernelPatchCard";
import AttentionFeedbackPanel from "@/components/AttentionFeedbackPanel";

type SourceSummary = {
  id: string;
  source_type?: string | null;
  title?: string | null;
  canonical_url?: string | null;
  content_text?: string | null;
  ingested_at?: string | null;
  ingestion_method?: string | null;
  raw_metadata?: Record<string, any>;
};

const RANK: Record<string, number> = { ENGAGE: 0, WATCH: 1, AWARE: 2, DROP: 3 };
const FILTERS = ["CURRENT", "ENGAGE", "WATCH", "AWARE", "DROP"] as const;

function sourceOrigin(source?: SourceSummary) {
  if (!source) return "Unknown source";
  try { if (source.canonical_url) return new URL(source.canonical_url).hostname.replace(/^www\./, ""); } catch {}
  return source.ingestion_method || "Manual source";
}

function sourceTimeValue(source?: SourceSummary, fallback?: string | null) {
  const raw = source?.raw_metadata || {};
  return raw.published || source?.ingested_at || fallback || null;
}

function sourceTime(source?: SourceSummary, fallback?: string | null) {
  const value = sourceTimeValue(source, fallback);
  return value ? formatBeijingTime(value) : null;
}

function isSystemFixture(source?: SourceSummary) {
  if (!source || source.raw_metadata?.acquisition) return false;
  const title = (source.title || "").toLowerCase();
  return /(^|\b)(smoke test|live smoke|rollout smoke|dogfood smoke)(\b|$)/i.test(title);
}

function sourceAuthor(source?: SourceSummary) {
  return source?.raw_metadata?.author || null;
}
function heroImage(source?: SourceSummary) {
  return source?.raw_metadata?.hero_image_url || null;
}
function heroImageAlt(source?: SourceSummary) {
  return source?.raw_metadata?.hero_image_alt || displayTitle(source);
}

function displayTitle(source?: SourceSummary) {
  const title = source?.title || "Untitled source";
  return title.replace(/\s*\|\s*[^|]+$/, "").trim() || title;
}

function actionCopy(disposition: string) {
  if (disposition === "ENGAGE") return "This deserves focused attention now.";
  if (disposition === "WATCH") return "RAOS is keeping responsibility for the next update. You do not need to monitor this manually.";
  if (disposition === "AWARE") return "Worth knowing once. No cognitive commitment or follow-up is required.";
  return "No attention needed right now.";
}

function operationCopy(operation?: string | null) {
  if (operation === "CHALLENGE") return "This challenges something already in your Kernel.";
  if (operation === "REINFORCE") return "This strengthens or adds support to existing cognition.";
  if (operation === "OPEN_NEW") return "This may justify opening a new cognitive branch.";
  return "No material cognitive change to your current Kernel.";
}

function displayP(value: unknown) {
  if (value == null) return "UNKNOWN";
  return String(value);
}

function normalizedLine(value: string) {
  return value.toLowerCase().replace(/[\s\p{P}\p{S}]+/gu, " ").trim();
}

function readerParagraphs(source?: SourceSummary) {
  const content = source?.content_text || "";
  if (!content.trim()) return [];
  const fullTitle = source?.title || "";
  const shortTitle = fullTitle.replace(/\s*\|\s*[^|]+$/, "").trim();
  const titleForms = new Set([normalizedLine(fullTitle), normalizedLine(shortTitle)].filter(Boolean));
  return content
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !titleForms.has(normalizedLine(line)));
}

function readingMinutes(source?: SourceSummary) {
  const content = source?.content_text || "";
  if (!content.trim()) return null;
  const cjk = (content.match(/[\u3400-\u9fff]/g) || []).length;
  const words = content.replace(/[\u3400-\u9fff]/g, " ").trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / 230 + cjk / 450));
}

function sourceExcerpt(source?: SourceSummary, length = 190) {
  const text = (source?.content_text || "").replace(/\s+/g, " ").trim();
  if (!text) return "RAOS has a current attention state for this source.";
  const shortTitle = displayTitle(source);
  const cleaned = text.toLowerCase().startsWith(shortTitle.toLowerCase()) ? text.slice(shortTitle.length).trim() : text;
  return cleaned.length > length ? `${cleaned.slice(0, length).trim()}…` : cleaned;
}

function readerWhy(plan: any, analysis: any) {
  const operation = analysis?.update?.operation || plan?.update?.operation || null;
  if (analysis?.no_delta_awareness?.applicable) {
    return "This sits inside an area you asked RAOS to monitor and the event had material consequences, but it does not change your current working model.";
  }
  if (plan?.disposition === "WATCH") {
    return "The evidence matters to your current work, but the next useful step depends on future evidence. RAOS will keep watching for you.";
  }
  if (plan?.disposition === "ENGAGE") {
    if (operation === "CHALLENGE") return "This may overturn or revise something you currently rely on, so it deserves direct attention.";
    if (operation === "REINFORCE") return "This provides meaningful new support for an active question, bottleneck, or model in your work.";
    if (operation === "OPEN_NEW") return "This may open a genuinely new line of inquiry that is important enough to inspect now.";
    return "RAOS believes this can materially affect active cognition or a current decision.";
  }
  if (plan?.disposition === "AWARE") return "This is useful context to know, but RAOS found no reason for deeper work or follow-up.";
  return "RAOS found no current reason to spend your attention here.";
}

function nextMove(disposition: string) {
  if (disposition === "ENGAGE") return "Read this carefully, then decide whether your current view or work should change.";
  if (disposition === "WATCH") return "Read only if useful now. You can safely leave future monitoring to RAOS.";
  if (disposition === "AWARE") return "Read it once, absorb the context, and move on.";
  return "You can skip this unless you are personally curious.";
}

export default function AttentionPage() {
  const params = useSearchParams();
  const sourceId = params.get("source");
  const viewParam = params.get("view");
  const [plans, setPlans] = useState<any[]>([]);
  const [sources, setSources] = useState<Record<string, SourceSummary>>({});
  const [analysis, setAnalysis] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("CURRENT");
  const [query, setQuery] = useState("");
  const [detailView, setDetailView] = useState<"reader" | "inspector">("reader");

  async function loadPlans() {
    const [nextPlans, nextSources] = await Promise.all([api<any[]>("/kernel/attention"), api<SourceSummary[]>("/sources")]);
    setPlans(nextPlans);
    setSources(Object.fromEntries(nextSources.map((source) => [source.id, source])));
  }

  async function loadAnalysis(mode: "read" | "reprocess" = "read") {
    if (!sourceId) return;
    setBusy(true); setError(null);
    try {
      if (mode === "reprocess") {
        setAnalysis(await api("/analysis/reprocess", { method: "POST", body: JSON.stringify({ source_id: sourceId }) }));
      } else {
        const existing = await apiOrNull<any>(`/analysis/by-source/${sourceId}`);
        setAnalysis(existing || await api("/analysis/extract", { method: "POST", body: JSON.stringify({ source_id: sourceId }) }));
      }
    } catch (e: unknown) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }

  useEffect(() => { loadPlans().catch((e) => setError(String(e.message || e))); }, []);
  useEffect(() => { setAnalysis(null); setDetailView(viewParam === "system" ? "inspector" : "reader"); loadAnalysis("read"); }, [sourceId, viewParam]);

  const currentPlans = useMemo(() => {
    const latest = new Map<string, any>();
    for (const plan of plans) {
      const key = `${plan.candidate_type}:${plan.candidate_id}`;
      if (!latest.has(key)) latest.set(key, plan);
    }
    return Array.from(latest.values()).sort((a, b) => (RANK[a.disposition] ?? 9) - (RANK[b.disposition] ?? 9));
  }, [plans]);

  const shown = useMemo(() => currentPlans.filter((p) => {
    if (isSystemFixture(sources[p.candidate_id])) return false;
    if (filter === "CURRENT" && p.disposition === "DROP") return false;
    if (filter !== "CURRENT" && p.disposition !== filter) return false;
    if (!query.trim()) return true;
    const title = sources[p.candidate_id]?.title || "";
    return `${title} ${p.reason || ""}`.toLowerCase().includes(query.toLowerCase());
  }), [currentPlans, filter, query, sources]);

  const counts = useMemo(() => {
    const visible = currentPlans.filter((p) => !isSystemFixture(sources[p.candidate_id]));
    return Object.fromEntries(FILTERS.map((f) => [f, f === "CURRENT" ? visible.filter((p) => p.disposition !== "DROP").length : visible.filter((p) => p.disposition === f).length]));
  }, [currentPlans, sources]);
  const editorialShown = useMemo(() => [...shown].sort((a, b) =>
    timestampMs(sourceTimeValue(sources[b.candidate_id], b.created_at)) - timestampMs(sourceTimeValue(sources[a.candidate_id], a.created_at))
  ), [shown, sources]);
  const selectedSource = sourceId ? sources[sourceId] : undefined;

  async function afterCommit() {
    await loadPlans();
    if (sourceId) {
      const existing = await apiOrNull<any>(`/analysis/by-source/${sourceId}`);
      if (existing) setAnalysis(existing);
    }
  }

  if (sourceId) {
    const plan = analysis ? (analysis.latest_attention_plan || analysis.attention_plan) : null;
    const awareness = analysis?.no_delta_awareness;
    const awarenessEvent = awareness?.events?.[0];
    const operation = analysis?.update?.operation || plan?.update?.operation || null;
    const paragraphs = readerParagraphs(selectedSource);
    const minutes = readingMinutes(selectedSource);
    const topMatch = analysis?.kernel_matches?.[0];

    return (
      <>
        <div className="detail-toolbar">
          <Link className="back-link" href="/attention">← Back to Attention</Link>
          <div className="view-switch" role="tablist" aria-label="Detail view">
            <button className={detailView === "reader" ? "active" : ""} onClick={() => setDetailView("reader")}>Reader</button>
            <button className={detailView === "inspector" ? "active" : ""} onClick={() => setDetailView("inspector")}>RAOS Inspector</button>
          </div>
        </div>

        {error && <p className="error">{error}</p>}
        {!analysis && !error && <div className="empty-state">Loading source…</div>}

        {analysis && plan && detailView === "reader" && (
          <div className="reader-layout">
            <article className="reader-article">
              <header className="reader-header">
                <div className="reader-source-line">
                  <span>{sourceOrigin(selectedSource)}</span>
                  {sourceAuthor(selectedSource) && <><span>·</span><span>{sourceAuthor(selectedSource)}</span></>}
                  {sourceTime(selectedSource) && <><span>·</span><span>{sourceTime(selectedSource)}</span></>}
                  {minutes && <><span>·</span><span>{minutes} min read</span></>}
                </div>
                <h1>{displayTitle(selectedSource)}</h1>
                <div className="reader-actions">
                  {selectedSource?.canonical_url && <a className="button-link ghost" href={selectedSource.canonical_url} target="_blank" rel="noreferrer">Open original ↗</a>}
                </div>
              </header>

              {heroImage(selectedSource) && (
                <figure className="reader-hero-media">
                  <img src={heroImage(selectedSource)} alt={heroImageAlt(selectedSource)} loading="eager" />
                  {selectedSource?.raw_metadata?.hero_image_alt && <figcaption>{selectedSource.raw_metadata.hero_image_alt}</figcaption>}
                </figure>
              )}

              <div className={`reader-status ${plan.disposition}`}>
                <span className={`badge ${plan.disposition}`}>{plan.disposition}</span>
                <strong>{actionCopy(plan.disposition)}</strong>
              </div>

              {paragraphs.length > 0 ? (
                <div className="reader-body">
                  {paragraphs.map((paragraph, index) => <p key={`${index}-${paragraph.slice(0, 24)}`}>{paragraph}</p>)}
                </div>
              ) : (
                <div className="reader-empty">
                  <h3>No local readable text is available for this source.</h3>
                  <p>RAOS has the analysis record, but this source does not contain a preserved text body.</p>
                  {selectedSource?.canonical_url && <a className="button-link" href={selectedSource.canonical_url} target="_blank" rel="noreferrer">Read at source ↗</a>}
                </div>
              )}
            </article>

            <aside className="reader-rail">
              <section className="reader-note">
                <div className="eyebrow">Why it matters to you</div>
                <p>{readerWhy(plan, analysis)}</p>
                {topMatch && (
                  <div className="reader-context">
                    <span>Closest current context</span>
                    <strong>{topMatch.title}</strong>
                  </div>
                )}
              </section>

              <section className="reader-note">
                <div className="eyebrow">What to do</div>
                <p>{nextMove(plan.disposition)}</p>
                {plan.cognitive_budget_minutes != null && <div className="reader-budget">RAOS budget · {plan.cognitive_budget_minutes} min</div>}
              </section>

              <button className="inspector-entry" onClick={() => setDetailView("inspector")}>
                <span>Inspect RAOS decision</span>
                <small>See cognition, evidence, D/S/P, Kernel mapping, and pipeline trace</small>
              </button>
            </aside>
          </div>
        )}

        {analysis && plan && detailView === "inspector" && (
          <>
            <header className="page-header inspector-header">
              <div>
                <div className="eyebrow">Operating system view</div>
                <h1 className="page-title">RAOS Inspector</h1>
                <p className="page-subtitle">Inspect why the operating system made this attention decision. This is not the normal reading surface.</p>
                <div className="source-meta" style={{marginTop: 10}}><span>{selectedSource?.title || "Source"}</span></div>
              </div>
              <button className="ghost" disabled={busy} onClick={() => loadAnalysis("reprocess")}>{busy ? "Reprocessing…" : "Reprocess"}</button>
            </header>

            <div className="detail-grid">
              <div>
                <section className={`decision-hero ${plan.disposition}`}>
                  <div className="row"><span className={`badge ${plan.disposition}`}>{plan.disposition}</span>{operation && <span className="badge">{operation}</span>}</div>
                  <div className="decision-label">{plan.disposition}</div>
                  <p className="decision-copy">{actionCopy(plan.disposition)}</p>
                  <div className="metric-line" style={{marginTop: 14}}>
                    <span><strong>{plan.cognitive_budget_minutes ?? 0} min</strong> attention budget</span>
                    <span><strong>{plan.urgency || "NORMAL"}</strong> urgency</span>
                    <span><strong>{operation || "NONE"}</strong> cognitive effect</span>
                  </div>
                </section>

                {awareness?.applicable && (
                  <section className="section card">
                    <div className="eyebrow">No-Delta awareness path</div>
                    <h3>Situational relevance without cognitive change</h3>
                    <p className="muted">This branch is separate from cognitive change and uses standing-world fit, material consequence, and collective-attention evidence.</p>
                    <div className="reason-grid">
                      <div className="signal-card"><strong>D · Standing world</strong><span>Inside the user&apos;s monitoring jurisdiction?</span><span className="signal-state">{displayP(awarenessEvent?.component_states?.D)}</span></div>
                      <div className="signal-card"><strong>S · Material consequence</strong><span>Material disturbance to a consequential shared system?</span><span className="signal-state">{displayP(awarenessEvent?.component_states?.S)}</span></div>
                      <div className="signal-card"><strong>P · Collective attention</strong><span>Observed salience among the relevant constituency?</span><span className="signal-state">{displayP(awarenessEvent?.component_states?.P)}</span></div>
                    </div>
                    <details className="technical-details">
                      <summary>Estimator reasoning</summary>
                      <div className="technical-body">
                        {awarenessEvent?.D?.reason && <p><strong>D:</strong> {awarenessEvent.D.reason}</p>}
                        {awarenessEvent?.S?.reason && <p><strong>S:</strong> {awarenessEvent.S.reason}</p>}
                        {awarenessEvent?.P?.reason && <p><strong>P:</strong> {awarenessEvent.P.reason}</p>}
                      </div>
                    </details>
                  </section>
                )}

                <section className="section card">
                  <div className="eyebrow">Cognitive impact</div>
                  <h3>{operationCopy(operation)}</h3>
                  <p className="muted">{analysis.delta_content || analysis.model_delta?.summary || "No cognitive delta summary available."}</p>
                  {(analysis.model_delta?.distinctions?.length > 0 || analysis.model_delta?.questions?.length > 0) && (
                    <ul>{[...(analysis.model_delta.distinctions || []), ...(analysis.model_delta.questions || [])].map((item: string) => <li key={item}>{item}</li>)}</ul>
                  )}
                </section>

                {analysis.kernel_matches?.length > 0 && (
                  <section className="section card">
                    <div className="eyebrow">Kernel mapping</div>
                    <h3>Where the source touches current cognitive state</h3>
                    {analysis.kernel_matches.slice(0, 6).map((m: any) => (
                      <div className="kernel-match" key={m.node_id}>
                        <div className="row"><span className="badge">{m.node_type}</span><span className="meta">{m.relevance_type || "match"}</span>{m.score != null && <span className="meta">score {m.score}</span>}</div>
                        <h4>{m.title}</h4>
                        {m.reason && <p>{m.reason}</p>}
                      </div>
                    ))}
                  </section>
                )}

                <section className="section">
                  <details className="technical-details">
                    <summary>Evidence & pipeline trace</summary>
                    <div className="technical-body">
                      <div className="trace-grid">
                        <div className="trace-block"><h4>AnalysisRun</h4><p>provider {analysis.analysis_run?.provider_type} · {analysis.analysis_run?.status}</p><p>pipeline {analysis.analysis_run?.pipeline_version}<br/>extractor {analysis.analysis_run?.extractor_version}<br/>matcher {analysis.analysis_run?.matcher_version}<br/>prompt {analysis.analysis_run?.prompt_version}</p></div>
                        <div className="trace-block"><h4>Decision trace</h4><p>{plan.reason}</p><p>Strategy details and provenance remain frozen in the AnalysisRun.</p></div>
                      </div>
                      <h3 style={{marginTop: 22}}>Extracted evidence</h3>
                      <div className="claim-list">
                        {(analysis.claims || []).map((c: any) => <div className="claim-item" key={c.id}><span className="badge">{c.claim_type}</span><p>{c.text}</p></div>)}
                        {(analysis.observations || []).map((c: any) => <div className="claim-item" key={c.id}><span className="badge">observation</span><p>{c.text}</p></div>)}
                        {(analysis.inferences || []).map((c: any) => <div className="claim-item" key={c.id}><span className="badge">inference</span><p>{c.text}</p></div>)}
                      </div>
                    </div>
                  </details>
                </section>
              </div>

              <aside className="detail-side">
                {plan?.id && <AttentionFeedbackPanel planId={plan.id} analysis={analysis} onSubmitted={afterCommit} />}
                {analysis.kernel_patches?.length > 0 && (
                  <section className="section">
                    <div className="eyebrow">Human authorization required</div>
                    <h3>Proposed Kernel change</h3>
                    <p className="muted">RAOS can propose a cognitive update, but only you can commit it.</p>
                    {analysis.kernel_patches.map((p: any) => <KernelPatchCard key={p.id} patch={p} onCommitted={afterCommit} />)}
                  </section>
                )}
              </aside>
            </div>
          </>
        )}
      </>
    );
  }

  return (
    <>
      <header className="page-header">
        <div><div className="eyebrow">Attention</div><h1 className="page-title">Your filtered world.</h1><p className="page-subtitle">One source, one current attention state. Start with what needs you; everything else has already been compressed.</p></div>
        <Link className="button-link ghost" href="/inbox">Add source</Link>
      </header>
      {error && <p className="error">{error}</p>}

      <div className="section-heading">
        <div className="filter-bar">
          {FILTERS.map((value) => <button className={filter === value ? "filter-chip active" : "filter-chip"} key={value} onClick={() => setFilter(value)}>{value === "CURRENT" ? "Current" : value} · {counts[value] || 0}</button>)}
        </div>
        <input className="search-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search current attention…" />
      </div>

      {shown.length === 0 && <div className="empty-state">No current attention items match this view.</div>}
      {shown.length > 0 && (
        <div className={filter === "CURRENT" && !query.trim() ? "attention-newsroom" : "attention-card-grid"}>
          {editorialShown.map((p, index) => {
            const source = sources[p.candidate_id];
            const title = source ? displayTitle(source) : `${p.candidate_type} ${p.candidate_id}`;
            const when = sourceTimeValue(source, p.created_at);
            const newsroom = filter === "CURRENT" && !query.trim();
            return (
              <Link className={`${newsroom && index === 0 ? "attention-lead" : "attention-story-card"} disposition-${p.disposition}`} href={`/attention?source=${p.candidate_id}`} key={p.id}>
                {heroImage(source) && <img className="story-visual" src={heroImage(source)} alt={heroImageAlt(source)} loading="lazy" />}
                <div className="story-kicker"><span className={`badge ${p.disposition}`}>{p.disposition}</span><span>{sourceOrigin(source)}</span>{when && <><span>·</span><span title={formatBeijingTime(when)}>{formatRelativeTime(when)}</span></>}</div>
                <h2>{title}</h2>
                <p>{sourceExcerpt(source, newsroom && index === 0 ? 300 : 165)}</p>
                <div className="story-footer"><strong>{actionCopy(p.disposition)}</strong><span>Read →</span></div>
              </Link>
            );
          })}
        </div>
      )}
    </>
  );
}
