"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import KernelPatchCard from "@/components/KernelPatchCard";

const ORDER = ["GOAL", "PROJECT", "BOTTLENECK", "QUESTION", "BELIEF", "HYPOTHESIS", "MODEL", "DECISION", "EXPERIMENT"];

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
      beliefs: (kernel.BELIEF?.length || 0) + (kernel.MODEL?.length || 0),
    };
  }, [kernel]);

  const proposed = patches.filter((p) => p.status === "PROPOSED");

  return (
    <>
      <header className="page-header">
        <div><div className="eyebrow">Cognitive Kernel</div><h1 className="page-title">Your current cognitive state.</h1><p className="page-subtitle">The Kernel is the durable, reviewable model RAOS reasons against. AI may propose changes; only you can commit them.</p></div>
      </header>

      <div className="kernel-overview">
        <div className="stat"><b>{counts.total}</b><span>active cognitive objects</span></div>
        <div className="stat"><b>{counts.questions}</b><span>open questions</span></div>
        <div className="stat"><b>{counts.bottlenecks}</b><span>active bottlenecks</span></div>
        <div className="stat"><b>{proposed.length}</b><span>changes waiting for your authorization</span></div>
      </div>

      {proposed.length > 0 && (
        <section className="section">
          <div className="section-heading"><div><div className="eyebrow">Your authorization required</div><h2>Proposed changes</h2><p>These are suggestions, not committed cognition.</p></div></div>
          {proposed.map((p) => <KernelPatchCard key={p.id} patch={p} onCommitted={load} />)}
        </section>
      )}

      <section className="section">
        <div className="section-heading">
          <div><h2>Kernel workspace</h2><p>Browse the ideas, projects, questions, and constraints RAOS currently treats as durable context.</p></div>
          <input className="search-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search your Kernel…" />
        </div>

        {ORDER.filter((type) => kernel[type]?.length).map((type) => {
          const items = kernel[type].filter((n) => `${n.title} ${nodeSummary(n)}`.toLowerCase().includes(query.toLowerCase()));
          if (items.length === 0) return null;
          return (
            <div className="kernel-group" key={type}>
              <div className="kernel-group-header"><h3>{type}</h3><span className="meta">{items.length}</span></div>
              <div className="grid2">
                {items.map((n) => (
                  <article className="card kernel-card" key={n.id}>
                    <div className="row"><span className="badge">{n.status}</span><span className="meta">v{n.current_version}</span>{n.payload?.confidence != null && <span className="meta">confidence {n.payload.confidence}</span>}</div>
                    <h4>{n.title}</h4>
                    {nodeSummary(n) !== n.title && <p className="muted">{nodeSummary(n)}</p>}
                    {n.payload?.scope && <p className="meta">Scope · {n.payload.scope}</p>}
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
