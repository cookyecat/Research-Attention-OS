"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import KernelPatchCard from "@/components/KernelPatchCard";

const ORDER = ["GOAL", "PROJECT", "BOTTLENECK", "QUESTION", "BELIEF", "HYPOTHESIS", "MODEL", "DECISION", "EXPERIMENT"];
const LABELS: Record<string, string> = {
  GOAL: "Goals",
  PROJECT: "Projects",
  BOTTLENECK: "Bottlenecks",
  QUESTION: "Open questions",
  BELIEF: "Working beliefs",
  HYPOTHESIS: "Hypotheses",
  MODEL: "Models",
  DECISION: "Decisions",
  EXPERIMENT: "Experiments",
};

function nodeSummary(n: any) {
  return n.payload?.proposition || n.payload?.description || n.payload?.text || n.title;
}

export default function KernelPage() {
  const [kernel, setKernel] = useState<Record<string, any[]>>({});
  const [patches, setPatches] = useState<any[]>([]);
  const [query, setQuery] = useState("");

  async function load() {
    const [k, p] = await Promise.all([api<Record<string, any[]>>("/kernel"), api<any[]>("/kernel/patches")]);
    setKernel(k); setPatches(p);
  }

  useEffect(() => { api("/kernel/seed", { method: "POST" }).finally(load); }, []);

  const counts = useMemo(() => {
    const total = Object.values(kernel).reduce((n, items) => n + (items?.length || 0), 0);
    return {
      total,
      questions: kernel.QUESTION?.length || 0,
      bottlenecks: kernel.BOTTLENECK?.length || 0,
      projects: kernel.PROJECT?.length || 0,
    };
  }, [kernel]);

  const proposed = patches.filter((p) => p.status === "PROPOSED");

  return (
    <>
      <header className="page-header">
        <div>
          <div className="eyebrow">Your context</div>
          <h1 className="page-title">What RAOS knows about your work.</h1>
          <p className="page-subtitle">This is the durable context RAOS uses to decide what matters to you. You stay in control: suggested changes never become part of your context until you authorize them.</p>
        </div>
      </header>

      <div className="kernel-overview">
        <div className="stat"><b>{counts.projects}</b><span>active projects</span></div>
        <div className="stat"><b>{counts.questions}</b><span>open questions</span></div>
        <div className="stat"><b>{counts.bottlenecks}</b><span>known bottlenecks</span></div>
        <div className="stat"><b>{proposed.length}</b><span>suggested changes waiting for you</span></div>
      </div>

      {proposed.length > 0 && (
        <section className="section">
          <div className="section-heading"><div><div className="eyebrow">Your decision</div><h2>Suggested context changes</h2><p>RAOS can suggest. Only you can change the durable context it reasons from.</p></div></div>
          {proposed.map((patch) => <KernelPatchCard key={patch.id} patch={patch} onCommitted={load} />)}
        </section>
      )}

      <section className="section">
        <div className="section-heading">
          <div><h2>Your working context</h2><p>Projects, questions, beliefs, and constraints that shape what RAOS pays attention to.</p></div>
          <input className="search-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search your context…" />
        </div>

        {ORDER.filter((type) => kernel[type]?.length).map((type) => {
          const items = kernel[type].filter((node) => `${node.title} ${nodeSummary(node)}`.toLowerCase().includes(query.toLowerCase()));
          if (items.length === 0) return null;
          return (
            <div className="kernel-group" key={type}>
              <div className="kernel-group-header"><h3>{LABELS[type] || type}</h3><span className="meta">{items.length}</span></div>
              <div className="grid2">
                {items.map((node) => (
                  <article className="card kernel-card" key={node.id}>
                    <h4>{node.title}</h4>
                    {nodeSummary(node) !== node.title && <p className="muted">{nodeSummary(node)}</p>}
                    {node.payload?.scope && <p className="context-scope">Scope · {node.payload.scope}</p>}
                    <details className="technical-details context-inspector">
                      <summary>RAOS Inspector</summary>
                      <div className="technical-body">
                        <p><strong>Kernel type:</strong> {type}</p>
                        <p><strong>Status:</strong> {node.status || "—"}</p>
                        <p><strong>Version:</strong> {node.current_version ?? "—"}</p>
                        {node.payload?.confidence != null && <p><strong>Confidence:</strong> {node.payload.confidence}</p>}
                        <p className="meta mono">{node.id}</p>
                      </div>
                    </details>
                  </article>
                ))}
              </div>
            </div>
          );
        })}
      </section>
    </>
  );
}
