"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, apiOrNull } from "@/lib/api";
import KernelPatchCard from "@/components/KernelPatchCard";

export default function AttentionPage() {
  const params = useSearchParams();
  const sourceId = params.get("source");
  const [plans, setPlans] = useState<any[]>([]);
  const [analysis, setAnalysis] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadPlans() {
    setPlans(await api<any[]>("/kernel/attention"));
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

  const shown = useMemo(() => plans.filter((p) => p.disposition !== "DROP" || sourceId), [plans, sourceId]);

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
              <span className={`badge ${analysis.disposition || analysis.attention_plan.disposition}`}>{analysis.disposition || analysis.attention_plan.disposition}</span>
              {analysis.update?.operation && (
                <span className="badge">{analysis.update.operation}{analysis.update.target_node_id ? ` → ${analysis.update.target_node_id}` : ""}</span>
              )}
              <span className={`badge ${analysis.attention_plan.urgency}`}>{analysis.attention_plan.urgency}</span>
            </div>
            <p>{analysis.attention_plan.reason}</p>
          </div>
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
      <h3>Recent plans</h3>
      {shown.map((p) => (
        <div className="card" key={p.id}>
          <div className="row">
            <span className={`badge ${p.disposition}`}>{p.disposition}</span>
            {p.update?.operation && (
              <span className="badge">{p.update.operation}</span>
            )}
          </div>
          <p>{p.reason}</p>
        </div>
      ))}
    </>
  );
}
