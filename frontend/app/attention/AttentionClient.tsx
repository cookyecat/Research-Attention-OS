"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, apiOrNull } from "@/lib/api";
import KernelPatchCard from "@/components/KernelPatchCard";
import AttentionFeedbackPanel from "@/components/AttentionFeedbackPanel";

type SourceSummary = {
  id: string;
  title?: string | null;
  canonical_url?: string | null;
  ingested_at?: string | null;
  ingestion_method?: string | null;
  raw_metadata?: Record<string, any>;
};

const RANK: Record<string, number> = { ENGAGE: 0, WATCH: 1, AWARE: 2, DROP: 3 };
const FILTERS = ["ALL", "ENGAGE", "WATCH", "AWARE", "DROP"] as const;

function sourceOrigin(source?: SourceSummary) {
  if (!source) return "Unknown source";
  try { if (source.canonical_url) return new URL(source.canonical_url).hostname.replace(/^www\./, ""); } catch {}
  return source.ingestion_method || "Manual source";
}

function sourceTime(source?: SourceSummary, fallback?: string | null) {
  const raw = source?.raw_metadata || {};
  const value = raw.published || source?.ingested_at || fallback;
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
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

export default function AttentionPage() {
  const params = useSearchParams();
  const sourceId = params.get("source");
  const [plans, setPlans] = useState<any[]>([]);
  const [sources, setSources] = useState<Record<string, SourceSummary>>({});
  const [analysis, setAnalysis] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("ALL");
  const [query, setQuery] = useState("");

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
  useEffect(() => { setAnalysis(null); loadAnalysis("read"); }, [sourceId]);

  const currentPlans = useMemo(() => {
    const latest = new Map<string, any>();
    for (const plan of plans) {
      const key = `${plan.candidate_type}:${plan.candidate_id}`;
      if (!latest.has(key)) latest.set(key, plan);
    }
    return Array.from(latest.values()).sort((a, b) => (RANK[a.disposition] ?? 9) - (RANK[b.disposition] ?? 9));
  }, [plans]);

  const shown = useMemo(() => currentPlans.filter((p) => {
    if (filter !== "ALL" && p.disposition !== filter) return false;
    if (!query.trim()) return true;
    const title = sources[p.candidate_id]?.title || "";
    return `${title} ${p.reason || ""}`.toLowerCase().includes(query.toLowerCase());
  }), [currentPlans, filter, query, sources]);

  const counts = useMemo(() => Object.fromEntries(FILTERS.map((f) => [f, f === "ALL" ? currentPlans.length : currentPlans.filter((p) => p.disposition === f).length])), [currentPlans]);
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

    return (
      <>
        <Link className="back-link" href="/attention">← Back to Attention</Link>
        <header className="page-header">
          <div>
            <div className="eyebrow">Attention detail</div>
            <h1 className="page-title source-title">{selectedSource?.title || "Source analysis"}</h1>
            <div className="source-meta" style={{marginTop: 10}}>
              <span>{sourceOrigin(selectedSource)}</span>
              {sourceTime(selectedSource) && <span>· {sourceTime(selectedSource)}</span>}
              {selectedSource?.canonical_url && <><span>·</span><a className="text-link" href={selectedSource.canonical_url} target="_blank" rel="noreferrer">Open original ↗</a></>}
            </div>
          </div>
          <button className="ghost" disabled={busy} onClick={() => loadAnalysis("reprocess")}>{busy ? "Reprocessing…" : "Reprocess"}</button>
        </header>

        {error && <p className="error">{error}</p>}
        {!analysis && !error && <div className="empty-state">Loading analysis…</div>}

        {analysis && plan && (
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
                  <div className="eyebrow">Why RAOS surfaced this</div>
                  <h3>No cognitive change, but the event still matters situationally.</h3>
                  <p className="muted">The no-Delta awareness path is separate from cognitive change. This decision is based on the event itself, your standing monitoring scope, and available attention evidence.</p>
                  <div className="reason-grid">
                    <div className="signal-card"><strong>D · Your standing world</strong><span>Does this belong to a world you asked RAOS to monitor?</span><span className="signal-state">{displayP(awarenessEvent?.component_states?.D)}</span></div>
                    <div className="signal-card"><strong>S · Material consequence</strong><span>Did the event materially disturb a consequential shared system?</span><span className="signal-state">{displayP(awarenessEvent?.component_states?.S)}</span></div>
                    <div className="signal-card"><strong>P · Collective attention</strong><span>Are the relevant people genuinely paying attention right now?</span><span className="signal-state">{displayP(awarenessEvent?.component_states?.P)}</span></div>
                  </div>
                  <details className="technical-details">
                    <summary>See D / S / P reasoning</summary>
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
                  <div className="eyebrow">Relevant to your Kernel</div>
                  <h3>Where this information touches your current cognitive state</h3>
                  {analysis.kernel_matches.slice(0, 4).map((m: any) => (
                    <div className="kernel-match" key={m.node_id}>
                      <div className="row"><span className="badge">{m.node_type}</span><span className="meta">{m.relevance_type || "match"}</span></div>
                      <h4>{m.title}</h4>
                      {m.reason && <p>{m.reason}</p>}
                    </div>
                  ))}
                </section>
              )}

              <section className="section">
                <details className="technical-details">
                  <summary>Evidence & technical trace</summary>
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
                  <div className="eyebrow">Your authorization required</div>
                  <h3>Proposed Kernel change</h3>
                  <p className="muted">RAOS can propose a cognitive update, but only you can commit it.</p>
                  {analysis.kernel_patches.map((p: any) => <KernelPatchCard key={p.id} patch={p} onCommitted={afterCommit} />)}
                </section>
              )}
            </aside>
          </div>
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
          {FILTERS.map((value) => <button className={filter === value ? "filter-chip active" : "filter-chip"} key={value} onClick={() => setFilter(value)}>{value === "ALL" ? "All" : value} · {counts[value] || 0}</button>)}
        </div>
        <input className="search-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search current attention…" />
      </div>

      {shown.length === 0 && <div className="empty-state">No current attention items match this view.</div>}
      <div className="stack">
        {shown.map((p) => {
          const source = sources[p.candidate_id];
          const title = source?.title || `${p.candidate_type} ${p.candidate_id}`;
          const operation = p.update?.operation;
          return (
            <Link className={`card attention-card disposition-${p.disposition}`} href={`/attention?source=${p.candidate_id}`} key={p.id}>
              <div className="row"><span className={`badge ${p.disposition}`}>{p.disposition}</span>{operation && <span className="badge">{operation}</span>}<span className="meta">{sourceOrigin(source)}</span>{sourceTime(source, p.created_at) && <span className="meta">· {sourceTime(source, p.created_at)}</span>}</div>
              <h3>{title}</h3>
              <p className="attention-summary">{actionCopy(p.disposition)} {operation ? operationCopy(operation) : ""}</p>
              <div className="attention-footer"><span className="text-link">Open →</span>{p.cognitive_budget_minutes != null && <span className="meta">{p.cognitive_budget_minutes} min attention</span>}</div>
            </Link>
          );
        })}
      </div>
    </>
  );
}
