"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, apiOrNull } from "@/lib/api";

type Source = { id: string; title?: string | null; ingested_at?: string | null };

export default function SystemPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [watches, setWatches] = useState<any[]>([]);
  const [kernel, setKernel] = useState<Record<string, any[]>>({});
  const [latestAnalysis, setLatestAnalysis] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [nextSources, nextPlans, nextWatches, nextKernel] = await Promise.all([
          api<Source[]>("/sources?compact=true"),
          api<any[]>("/kernel/attention"),
          api<any[]>("/watches"),
          api<Record<string, any[]>>("/kernel"),
        ]);
        setSources(nextSources); setPlans(nextPlans); setWatches(nextWatches); setKernel(nextKernel);
        for (const source of nextSources.slice(0, 12)) {
          const analysis = await apiOrNull<any>(`/analysis/by-source/${source.id}`);
          if (analysis?.analysis_run) { setLatestAnalysis(analysis); break; }
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : String(e));
      }
    }
    load();
  }, []);

  const currentStates = useMemo(() => {
    const seen = new Set<string>();
    for (const plan of plans) seen.add(`${plan.candidate_type}:${plan.candidate_id}`);
    return seen.size;
  }, [plans]);
  const watchResponsibilities = useMemo(() => new Set(watches.map((watch) => `${watch.target_type}:${watch.target_ref}`)).size, [watches]);
  const kernelObjects = useMemo(() => Object.values(kernel).reduce((count, items) => count + (items?.length || 0), 0), [kernel]);
  const run = latestAnalysis?.analysis_run;
  const latestSource = sources.find((source) => source.id === latestAnalysis?.source_id);
  const contract = run?.stage_provenance?.impact?.contract || run?.stage_provenance?.matching?.contract || "—";

  return (
    <>
      <header className="page-header system-page-header">
        <div>
          <div className="eyebrow">Operating system view</div>
          <h1 className="page-title">RAOS System</h1>
          <p className="page-subtitle">Internal state for diagnosis and development. Normal reading and attention work belongs in User Space.</p>
        </div>
        <span className="system-warning">Inspector mode</span>
      </header>
      {error && <p className="error">{error}</p>}

      <section className="system-banner">
        <strong>This is the operating system, not the user interface.</strong>
        <span>Raw counts, execution identity, and pipeline state are intentionally concentrated here instead of leaking into normal reading surfaces.</span>
      </section>

      <div className="stats system-stats">
        <div className="stat"><b>{sources.length}</b><span>Sources persisted</span></div>
        <div className="stat"><b>{currentStates}</b><span>current source attention states</span></div>
        <div className="stat"><b>{watches.length}</b><span>raw Watch records · {watchResponsibilities} responsibilities</span></div>
        <div className="stat"><b>{kernelObjects}</b><span>Kernel objects</span></div>
      </div>

      <section className="section grid2">
        <div className="card system-card">
          <div className="eyebrow">Execution identity</div>
          <h3>{contract}</h3>
          {run ? (
            <div className="system-kv">
              <span>Pipeline</span><strong>{run.pipeline_version || "—"}</strong>
              <span>Provider</span><strong>{run.provider_type || "—"}</strong>
              <span>Model</span><strong>{run.model_name || "—"}</strong>
              <span>Fallback</span><strong>{String(Boolean(run.fallback_used))}</strong>
            </div>
          ) : <p className="muted">No completed AnalysisRun found in the recent Source window.</p>}
        </div>

        <div className="card system-card">
          <div className="eyebrow">Latest inspected run</div>
          {run ? (
            <>
              <h3>{latestSource?.title || "Recent AnalysisRun"}</h3>
              <p className="meta mono">{latestAnalysis?.source_id}</p>
              <div className="system-kv">
                <span>Status</span><strong>{run.status || "—"}</strong>
                <span>Latency</span><strong>{run.latency_ms != null ? `${run.latency_ms} ms` : "—"}</strong>
                <span>Prompt tokens</span><strong>{run.prompt_tokens ?? "—"}</strong>
                <span>Completion tokens</span><strong>{run.completion_tokens ?? "—"}</strong>
              </div>
              {latestAnalysis?.source_id && <div className="actions"><Link className="button-link ghost" href={`/attention?source=${latestAnalysis.source_id}&view=system`}>Inspect this run →</Link></div>}
            </>
          ) : <p className="muted">Waiting for run provenance.</p>}
        </div>
      </section>

      <section className="section card system-card">
        <div className="eyebrow">Raw subsystem inventory</div>
        <h3>Current persisted objects</h3>
        <div className="system-inventory">
          <div><span>AttentionPlan ledger</span><strong>{plans.length}</strong></div>
          <div><span>Watch ledger</span><strong>{watches.length}</strong></div>
          {Object.entries(kernel).filter(([, items]) => items?.length).map(([type, items]) => (
            <div key={type}><span>Kernel · {type}</span><strong>{items.length}</strong></div>
          ))}
        </div>
      </section>

      <section className="section card system-card">
        <div className="eyebrow">Boundary rule</div>
        <h3>User Space ≠ Operating System View</h3>
        <p className="muted">User Space shows information, meaning, and actions. RAOS System shows scheduling, cognition, provenance, execution, and raw internal representations.</p>
      </section>
    </>
  );
}
