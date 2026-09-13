"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
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

function sourceOrigin(source?: SourceSummary) {
  if (!source) return "Unknown source";
  try {
    if (source.canonical_url) return new URL(source.canonical_url).hostname.replace(/^www\./, "");
  } catch {}
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

export default function AttentionPage() {
  const params = useSearchParams();
  const sourceId = params.get("source");
  const [plans, setPlans] = useState<any[]>([]);
  const [sources, setSources] = useState<Record<string, SourceSummary>>({});
  const [showDrop, setShowDrop] = useState(false);
  const [analysis, setAnalysis] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadPlans() {
    const [nextPlans, nextSources] = await Promise.all([
      api<any[]>("/kernel/attention"),
      api<SourceSummary[]>("/sources"),
    ]);
    setPlans(nextPlans);
    setSources(Object.fromEntries(nextSources.map((source) => [source.id, source])));
  }

  async function loadAnalysis(mode: "read" | "extract" | "reprocess" = "read") {
    if (!sourceId) return;
    setBusy(true);
    setError(null);
    try {
      if (mode === "reprocess") {
        setAnalysis(await api("/analysis/reprocess", { method: "POST", body: JSON.stringify({ source_id: sourceId }) }));
        return;
      }
      if (mode === "extract") {
        setAnalysis(await api("/analysis/extract", { method: "POST", body: JSON.stringify({ source_id: sourceId }) }));
        return;
      }
      const existing = await apiOrNull<any>(`/analysis/by-source/${sourceId}`);
      if (existing) setAnalysis(existing);
      else {
        setAnalysis(await api("/analysis/extract", { method: "POST", body: JSON.stringify({ source_id: sourceId }) }));
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadPlans().catch((e) => setError(String(e.message || e)));
  }, []);

  useEffect(() => {
    loadAnalysis("read");
  }, [sourceId]);

  const currentPlans = useMemo(() => {
    const latest = new Map<string, any>();
    for (const plan of plans) {
      const key = `${plan.candidate_type}:${plan.candidate_id}`;
      if (!latest.has(key)) latest.set(key, plan);
    }
    return Array.from(latest.values());
  }, [plans]);

  const shown = useMemo(
    () => currentPlans.filter((p) => showDrop || p.disposition !== "DROP"),
    [currentPlans, showDrop],
  );

  const selectedSource = sourceId ? sources[sourceId] : undefined;

  async function afterCommit() {
    await loadPlans();
    if (sourceId) {
      const existing = await apiOrNull<any>(`/analysis/by-source/${sourceId}`);
      if (existing) setAnalysis(existing);
    }
  }

  return (
    <>
      <h2>Attention</h2>
      <p className="lede">Extracted objects, Kernel match, AttentionPlan, Model Delta, and proposed KernelPatch. AI cannot commit Beliefs. Refresh reads the existing AnalysisRun; it does not re-run the pipeline.</p>
      {error && <p className="error">{error}</p>}
      {sourceId && (
        <div className="actions">
          <button className="ghost" disabled={busy} onClick={() => loadAnalysis("reprocess")}>Reprocess</button>
        </div>
      )}
      {analysis && (
        <>
          {selectedSource && (
            <div className="card source-header">
              <div className="row">
                <span className="badge">{sourceOrigin(selectedSource)}</span>
                {sourceTime(selectedSource) && <span className="meta">{sourceTime(selectedSource)}</span>}
              </div>
              <h3>{selectedSource.title || "Untitled source"}</h3>
              {selectedSource.canonical_url && (
                <a className="text-link" href={selectedSource.canonical_url} target="_blank" rel="noreferrer">
                  Open original ↗
                </a>
              )}
            </div>
          )}
          {analysis.analysis_run && (
            <div className="card">
              <h3>AnalysisRun</h3>
              <div className="row">
                <span className="badge">{analysis.analysis_run.provider_type}</span>
                <span className="badge">{analysis.analysis_run.status}</span>
                {analysis.analysis_run.fallback_used && <span className="badge">fallback</span>}
              </div>
              <p className="lede">
                pipeline {analysis.analysis_run.pipeline_version} · extractor {analysis.analysis_run.extractor_version} ·
                matcher {analysis.analysis_run.matcher_version} · prompt {analysis.analysis_run.prompt_version}
              </p>
            </div>
          )}
          <div className="card">
            <h3>AttentionPlan</h3>
            <div className="row">
              <span className={`badge ${(analysis.latest_attention_plan || analysis.attention_plan).disposition}`}>
                {(analysis.latest_attention_plan || analysis.attention_plan).disposition}
              </span>
              {analysis.update?.operation && (
                <span className="badge">{analysis.update.operation}{analysis.update.target_node_id ? ` → ${analysis.update.target_node_id}` : ""}</span>
              )}
              <span className={`badge ${(analysis.latest_attention_plan || analysis.attention_plan).urgency}`}>
                {(analysis.latest_attention_plan || analysis.attention_plan).urgency}
              </span>
            </div>
            <p>{(analysis.latest_attention_plan || analysis.attention_plan).reason}</p>
            {analysis.original_attention_plan?.id &&
              analysis.latest_attention_plan?.id &&
              analysis.original_attention_plan.id !== analysis.latest_attention_plan.id && (
                <p className="lede">Original plan retained as provenance only.</p>
              )}
          </div>
          {(analysis.latest_attention_plan || analysis.attention_plan)?.id && (
            <AttentionFeedbackPanel
              planId={(analysis.latest_attention_plan || analysis.attention_plan).id}
              analysis={analysis}
              onSubmitted={async () => {
                if (!sourceId) return;
                const existing = await apiOrNull<any>(`/analysis/by-source/${sourceId}`);
                if (existing) setAnalysis(existing);
              }}
            />
          )}
          <div className="grid2">
            <div className="card">
              <h3>Claims</h3>
              {analysis.claims.map((c: any) => (
                <p key={c.id}><span className="badge">{c.claim_type}</span> {c.text}</p>
              ))}
            </div>
            <div className="card">
              <h3>Observations</h3>
              {analysis.observations.length === 0 && <p>None — interpretations are not stored here.</p>}
              {analysis.observations.map((c: any) => (
                <p key={c.id}><span className="badge">{c.observation_type}</span> {c.text}</p>
              ))}
            </div>
          </div>
          <div className="card">
            <h3>Inferences</h3>
            {analysis.inferences.map((c: any) => (
              <p key={c.id}>{c.text}</p>
            ))}
          </div>
          <div className="card">
            <h3>Kernel match</h3>
            {analysis.kernel_matches.map((m: any) => (
              <p key={m.node_id}><span className="badge">{m.relevance_type || m.node_type}</span> {m.title} ({m.score})</p>
            ))}
          </div>
          <div className="card">
            <h3>Cognitive delta</h3>
            <p>{analysis.delta_content || analysis.model_delta.summary}</p>
            <ul>
              {(analysis.model_delta.distinctions || []).map((d: string) => (
                <li key={d}>{d}</li>
              ))}
              {(analysis.model_delta.questions || []).map((d: string) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          </div>
          <div className="card">
            <h3>KernelPatch (human commit required)</h3>
            {analysis.kernel_patches.length === 0 && <p>No KernelPatch proposed — the source persists, but the Kernel is unchanged until a justified patch is accepted.</p>}
            {analysis.kernel_patches.map((p: any) => (
              <KernelPatchCard key={p.id} patch={p} onCommitted={afterCommit} />
            ))}
          </div>
        </>
      )}
      <div className="section-heading">
        <div>
          <h3>Attention feed</h3>
          <p className="lede compact">One source, one current attention state. Older plans are retained as provenance but not repeated here.</p>
        </div>
        <button className="ghost" onClick={() => setShowDrop((value) => !value)}>
          {showDrop ? "Hide DROP" : "Show DROP"}
        </button>
      </div>
      {shown.length === 0 && <p className="lede">No current attention items.</p>}
      {shown.map((p) => {
        const source = sources[p.candidate_id];
        const title = source?.title || `${p.candidate_type} ${p.candidate_id}`;
        const href = p.candidate_type === "SOURCE" ? `/attention?source=${p.candidate_id}` : undefined;
        const content = (
          <>
            <div className="row">
              <span className={`badge ${p.disposition}`}>{p.disposition}</span>
              {p.update?.operation && <span className="badge">{p.update.operation}</span>}
              <span className="meta">{sourceOrigin(source)}</span>
              {sourceTime(source, p.created_at) && <span className="meta">{sourceTime(source, p.created_at)}</span>}
            </div>
            <h3>{title}</h3>
            <p className="attention-reason">{p.reason}</p>
            {href && <span className="text-link">View analysis →</span>}
          </>
        );
        return href ? (
          <Link className="card attention-card" href={href} key={p.id}>
            {content}
          </Link>
        ) : (
          <div className="card" key={p.id}>{content}</div>
        );
      })}
    </>
  );
}
