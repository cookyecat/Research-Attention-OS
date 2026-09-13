"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

type Watch = any;

function humanReason(watch: Watch) {
  if (watch.target_type === "KERNEL") return "RAOS is monitoring for new evidence that could change or strengthen this part of your Kernel.";
  if (watch.target_type === "METHOD") return "RAOS is waiting for stronger evidence or a concrete release so you do not have to remember to check again.";
  return "RAOS has accepted responsibility for the next meaningful update.";
}

export default function WatchPage() {
  const [watches, setWatches] = useState<Watch[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try { setWatches(await api("/watches")); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : String(e)); }
  }
  useEffect(() => { load(); }, []);

  const grouped = useMemo(() => {
    const map = new Map<string, Watch[]>();
    for (const watch of watches) {
      const key = `${watch.target_type}:${watch.target_ref}`;
      map.set(key, [...(map.get(key) || []), watch]);
    }
    return Array.from(map.values()).sort((a, b) => (a[0].status === "ACTIVE" ? 0 : 1) - (b[0].status === "ACTIVE" ? 0 : 1));
  }, [watches]);

  async function fire(watch: Watch) {
    const trigger = watch.triggers?.[0];
    if (!trigger) return;
    await api(`/watches/${watch.id}/triggers/${trigger.id}/fire`, { method: "POST" });
    await load();
  }

  return (
    <>
      <header className="page-header">
        <div><div className="eyebrow">Watch</div><h1 className="page-title">RAOS is remembering for you.</h1><p className="page-subtitle">WATCH is delegated future attention, not a bookmark. You can forget these for now; RAOS owns the next check.</p></div>
      </header>
      {error && <p className="error">{error}</p>}

      <div className="stats" style={{marginBottom: 30}}>
        <div className="stat"><b>{grouped.length}</b><span>distinct monitoring responsibilities</span></div>
        <div className="stat"><b>{grouped.filter((g) => g.some((w) => w.status === "ACTIVE")).length}</b><span>currently active</span></div>
        <div className="stat"><b>{watches.reduce((n, w) => n + (w.checks?.length || 0), 0)}</b><span>checks already performed</span></div>
        <div className="stat"><b>{watches.filter((w) => w.triggers?.some((t: any) => t.last_triggered_at)).length}</b><span>watch records triggered before</span></div>
      </div>

      <div className="stack">
        {grouped.map((group) => {
          const primary = group[0];
          const activeCount = group.filter((w) => w.status === "ACTIVE").length;
          const triggers = Array.from(new Set(group.flatMap((w) => (w.triggers || []).map((t: any) => t.trigger_type))));
          const lastTriggered = group.flatMap((w) => (w.triggers || []).map((t: any) => t.last_triggered_at).filter(Boolean)).sort().at(-1);
          return (
            <article className="card watch-card" key={`${primary.target_type}:${primary.target_ref}`}>
              <div>
                <div className="row"><span className="badge WATCH">WATCH</span><span className="badge">{primary.target_type}</span>{group.length > 1 && <span className="meta">{group.length} records grouped</span>}</div>
                <h3>{primary.target_ref}</h3>
                <p className="attention-summary">{humanReason(primary)}</p>
                <div className="row">{triggers.map((trigger) => <span className="badge" key={String(trigger)}>{String(trigger).replaceAll("_", " ")}</span>)}</div>
                <details className="technical-details">
                  <summary>Technical / developer controls</summary>
                  <div className="technical-body">
                    {group.map((w) => <div className="claim-item" key={w.id}><p><strong>{w.status}</strong> · {w.created_reason}</p>{w.status === "ACTIVE" && w.triggers?.[0] && <div className="actions"><button className="ghost" onClick={() => fire(w)}>Simulate trigger</button></div>}</div>)}
                  </div>
                </details>
              </div>
              <div className="watch-state"><strong>{activeCount > 0 ? "Monitoring" : primary.status}</strong><small>{lastTriggered ? `Last trigger ${new Date(lastTriggered).toLocaleString()}` : "Waiting for new evidence"}</small></div>
            </article>
          );
        })}
      </div>
      {grouped.length === 0 && <div className="empty-state">No active monitoring responsibilities.</div>}
    </>
  );
}
