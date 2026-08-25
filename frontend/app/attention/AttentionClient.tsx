"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

export default function AttentionPage() {
  const params = useSearchParams();
  const sourceId = params.get("source");
  const [plans, setPlans] = useState<any[]>([]);
  const [analysis, setAnalysis] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<any[]>("/kernel/attention")
      .then(setPlans)
      .catch((e) => setError(String(e.message || e)));
  }, []);

  useEffect(() => {
    if (!sourceId) return;
    api("/analysis/extract", { method: "POST", body: JSON.stringify({ source_id: sourceId }) })
      .then(setAnalysis)
      .catch((e) => setError(String(e.message || e)));
  }, [sourceId]);

  const shown = useMemo(() => plans.filter((p) => p.attention_state !== "DROP" || sourceId), [plans, sourceId]);

  async function act(patchId: string, action: "accept" | "reject") {
    await api(`/kernel/patches/${patchId}/${action}`, { method: "POST" });
    if (sourceId) {
      setAnalysis(await api("/analysis/extract", { method: "POST", body: JSON.stringify({ source_id: sourceId }) }));
    }
  }

  return (
    <>
      <h2>Attention</h2>
      <p className="lede">Extracted objects, Kernel match, AttentionPlan, Model Delta, and proposed KernelPatch. AI cannot commit Beliefs.</p>
      {error && <p className="error">{error}</p>}
      {analysis && (
        <>
          <div className="card">
            <h3>AttentionPlan</h3>
            <div className="row">
              <span className={`badge ${analysis.attention_plan.attention_state}`}>{analysis.attention_plan.attention_state}</span>
              <span className={`badge ${analysis.attention_plan.urgency}`}>{analysis.attention_plan.urgency}</span>
              {(analysis.attention_plan.processing_modes || []).map((m: string) => (
                <span className="badge" key={m}>{m}</span>
              ))}
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
              <p key={m.node_id}><span className="badge">{m.node_type}</span> {m.title} ({m.score})</p>
            ))}
          </div>
          <div className="card">
            <h3>What could this change?</h3>
            <p>{analysis.model_delta.summary}</p>
            <ul>
              {analysis.model_delta.distinctions.map((d: string) => (
                <li key={d}>{d}</li>
              ))}
              {analysis.model_delta.questions.map((d: string) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          </div>
          <div className="card">
            <h3>KernelPatch (human commit required)</h3>
            {analysis.kernel_patches.length === 0 && <p>No KernelPatch proposed — the source persists, but the Kernel is unchanged until a justified patch is accepted.</p>}
            {analysis.kernel_patches.map((p: any) => (
              <div key={p.id} className="card">
                <div className="row">
                  <span className="badge">{p.status}</span>
                  <span className="badge">{p.change_type}</span>
                  <span className="badge">{p.target_object_type}</span>
                </div>
                <p>{p.reasoning}</p>
                {p.status === "PROPOSED" && (
                  <div className="actions">
                    <button onClick={() => act(p.id, "accept")}>Accept</button>
                    <button className="danger" onClick={() => act(p.id, "reject")}>Reject</button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
      <h3>Recent plans</h3>
      {shown.map((p) => (
        <div className="card" key={p.id}>
          <div className="row">
            <span className={`badge ${p.attention_state}`}>{p.attention_state}</span>
            {(p.processing_modes || []).map((m: string) => (
              <span className="badge" key={m}>{m}</span>
            ))}
          </div>
          <p>{p.reason}</p>
        </div>
      ))}
    </>
  );
}
