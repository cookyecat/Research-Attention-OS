"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { formatBeijingTime } from "@/lib/time";

type Watch = any;

function humanReason(watch: Watch) {
  if (watch.target_type === "KERNEL") return "RAOS is monitoring for new evidence that could change or strengthen this part of your current context.";
  if (watch.target_type === "METHOD") return "RAOS is waiting for stronger evidence or a concrete release so you do not have to remember to check again.";
  return "RAOS has accepted responsibility for the next meaningful update.";
}

function triggerLabel(trigger: string) {
  const labels: Record<string, string> = {
    NEW_EVIDENCE: "new evidence",
    PAPER_RELEASE: "a paper release",
    CODE_RELEASE: "a code release",
    INDEPENDENT_REPLICATION: "independent replication",
  };
  return labels[trigger] || trigger.toLowerCase().replaceAll("_", " ");
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

  const activeResponsibilities = grouped.filter((group) => group.some((watch) => watch.status === "ACTIVE")).length;
  const updatedResponsibilities = grouped.filter((group) => group.some((watch) => watch.triggers?.some((trigger: any) => trigger.last_triggered_at))).length;

  async function fire(watch: Watch) {
    const trigger = watch.triggers?.[0];
    if (!trigger) return;
    await api(`/watches/${watch.id}/triggers/${trigger.id}/fire`, { method: "POST" });
    await load();
  }

  return (
    <>
      <header className="page-header">
        <div><div className="eyebrow">Watch</div><h1 className="page-title">RAOS is remembering for you.</h1><p className="page-subtitle">These are things you no longer need to keep in your head. RAOS owns the next check and will bring them back only when something meaningful changes.</p></div>
      </header>
      {error && <p className="error">{error}</p>}

      <div className="stats" style={{marginBottom: 30}}>
        <div className="stat"><b>{grouped.length}</b><span>things RAOS is responsible for remembering</span></div>
        <div className="stat"><b>{activeResponsibilities}</b><span>currently being monitored</span></div>
        <div className="stat"><b>{updatedResponsibilities}</b><span>have produced a prior update</span></div>
        <div className="stat"><b>{Math.max(0, grouped.length - activeResponsibilities)}</b><span>no longer actively monitored</span></div>
      </div>

      <div className="stack">
        {grouped.map((group) => {
          const primary = group[0];
          const active = group.some((watch) => watch.status === "ACTIVE");
          const triggers = Array.from(new Set(group.flatMap((watch) => (watch.triggers || []).map((trigger: any) => trigger.trigger_type))));
          const lastTriggered = group.flatMap((watch) => (watch.triggers || []).map((trigger: any) => trigger.last_triggered_at).filter(Boolean)).sort().at(-1);
          const waitingFor = triggers.map((trigger) => triggerLabel(String(trigger))).join(", ");
          return (
            <article className="card watch-card" key={`${primary.target_type}:${primary.target_ref}`}>
              <div>
                <div className="row"><span className="badge WATCH">WATCH</span></div>
                <h3>{primary.target_ref}</h3>
                <p className="attention-summary">{humanReason(primary)}</p>
                {waitingFor && <p className="watch-waiting"><span>Waiting for</span> {waitingFor}</p>}
                <details className="technical-details">
                  <summary>RAOS Inspector</summary>
                  <div className="technical-body">
                    <p className="meta">Target type · {primary.target_type} · {group.length} persisted record{group.length === 1 ? "" : "s"}</p>
                    {group.map((watch) => <div className="claim-item" key={watch.id}><p><strong>{watch.status}</strong> · {watch.created_reason}</p>{watch.status === "ACTIVE" && watch.triggers?.[0] && <div className="actions"><button className="ghost" onClick={() => fire(watch)}>Simulate trigger</button></div>}</div>)}
                  </div>
                </details>
              </div>
              <div className="watch-state"><strong>{active ? "Monitoring" : "Inactive"}</strong><small>{lastTriggered ? `Last update ${formatBeijingTime(lastTriggered)}` : "Nothing new yet"}</small></div>
            </article>
          );
        })}
      </div>
      {grouped.length === 0 && <div className="empty-state">Nothing is delegated to RAOS right now.</div>}
    </>
  );
}
