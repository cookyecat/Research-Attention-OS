"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

type Home = {
  decision_items: number;
  engage_items: number;
  watch_topics: number;
  discarded: number;
  estimated_attention_minutes: number;
  proposed_patches: number;
  sources: number;
};

type SourceSummary = { id: string; title?: string | null; canonical_url?: string | null; ingestion_method?: string | null };

const RANK: Record<string, number> = { ENGAGE: 0, WATCH: 1, AWARE: 2, DROP: 3 };

function actionCopy(disposition: string) {
  if (disposition === "ENGAGE") return "Needs focused attention now.";
  if (disposition === "WATCH") return "RAOS is carrying the next check for you.";
  if (disposition === "AWARE") return "Worth knowing; no follow-up is required.";
  return "No attention needed right now.";
}

export default function Page() {
  const [home, setHome] = useState<Home | null>(null);
  const [plans, setPlans] = useState<any[]>([]);
  const [sources, setSources] = useState<Record<string, SourceSummary>>({});
  const [watches, setWatches] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api<Home>("/meta/home"), api<any[]>("/kernel/attention"), api<SourceSummary[]>("/sources"), api<any[]>("/watches")])
      .then(([nextHome, nextPlans, nextSources, nextWatches]) => {
        setHome(nextHome);
        setPlans(nextPlans);
        setSources(Object.fromEntries(nextSources.map((s) => [s.id, s])));
        setWatches(nextWatches);
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
    return Array.from(latest.values()).sort((a, b) => (RANK[a.disposition] ?? 9) - (RANK[b.disposition] ?? 9));
  }, [plans]);

  const engageCount = current.filter((p) => p.disposition === "ENGAGE").length;
  const needsYou = current.filter((p) => p.disposition === "ENGAGE").slice(0, 3);
  const awareness = current.filter((p) => p.disposition === "AWARE").length;
  const discarded = current.filter((p) => p.disposition === "DROP").length;
  const currentBudget = current.reduce((minutes, p) => minutes + Number(p.cognitive_budget_minutes || 0), 0);
  const activeWatchResponsibilities = new Set(
    watches.filter((w) => w.status === "ACTIVE").map((w) => `${w.target_type}:${w.target_ref}`),
  ).size;

  return (
    <>
      <header className="page-header">
        <div>
          <div className="eyebrow">Today</div>
          <h1 className="page-title">Your attention, already filtered.</h1>
          <p className="page-subtitle">RAOS watches the information flow so you can spend time only where your cognition or decisions actually need it.</p>
        </div>
        <Link className="button-link ghost" href="/inbox">Add source</Link>
      </header>

      {error && <p className="error">{error}</p>}

      <section className="hero-panel">
        <div className="eyebrow">What needs you now</div>
        <h2>{engageCount > 0 ? `${engageCount} item${engageCount === 1 ? "" : "s"} deserve focused attention` : "Nothing requires focused attention right now"}</h2>
        <p>{engageCount > 0 ? "Start with the highest-value cognitive work. Everything else can wait." : "RAOS is absorbing the background noise. You can keep working."}</p>
      </section>

      {needsYou.length > 0 && (
        <section className="section">
          <div className="section-heading"><div><h2>Engage now</h2><p>Items most likely to change active cognition or decisions.</p></div></div>
          <div className="stack">
            {needsYou.map((p) => {
              const source = sources[p.candidate_id];
              return (
                <Link className={`card attention-card disposition-${p.disposition}`} href={`/attention?source=${p.candidate_id}`} key={p.id}>
                  <div className="row"><span className={`badge ${p.disposition}`}>{p.disposition}</span><span className="meta">{source?.ingestion_method || "source"}</span></div>
                  <h3>{source?.title || "Untitled source"}</h3>
                  <p className="attention-summary">{actionCopy(p.disposition)}</p>
                  <span className="text-link">Open →</span>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      <section className="section">
        <div className="section-heading"><div><h2>System state</h2><p>A compact view of work RAOS has already absorbed for you.</p></div></div>
        <div className="stats">
          <div className="stat"><b>{activeWatchResponsibilities}</b><span>monitoring responsibilities delegated to RAOS</span></div>
          <div className="stat"><b>{awareness}</b><span>items worth knowing without deeper work</span></div>
          <div className="stat"><b>{discarded}</b><span>current items filtered out — attention saved</span></div>
          <div className="stat"><b>{home?.proposed_patches ?? "—"}</b><span>Kernel changes waiting for your authorization</span></div>
        </div>
      </section>

      <section className="section grid2">
        <div className="card">
          <div className="eyebrow">Delegated attention</div>
          <h3>RAOS is watching {activeWatchResponsibilities} responsibilities for you</h3>
          <p className="muted">You do not need to remember to revisit them. RAOS owns the next check.</p>
          <div className="actions"><Link className="button-link ghost" href="/watch">Open Watch</Link></div>
        </div>
        <div className="card">
          <div className="eyebrow">Attention budget</div>
          <h3>{currentBudget} min across current source states</h3>
          <p className="muted">This is not a to-do debt. It is the current policy budget before you choose what to open.</p>
          <div className="actions"><Link className="button-link ghost" href="/attention">Review Attention</Link></div>
        </div>
      </section>
    </>
  );
}
