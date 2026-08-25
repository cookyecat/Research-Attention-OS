"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function WatchPage() {
  const [watches, setWatches] = useState<any[]>([]);

  async function load() {
    setWatches(await api("/watches"));
  }

  useEffect(() => {
    load();
  }, []);

  async function fire(watch: any) {
    const trigger = watch.triggers?.[0];
    if (!trigger) return;
    await api(`/watches/${watch.id}/triggers/${trigger.id}/fire`, { method: "POST" });
    await load();
  }

  return (
    <>
      <h2>Watch</h2>
      <p className="lede">WATCH is not a bookmark. Future attention responsibility is transferred to the system. When a trigger fires, the scheduler is re-run and WATCH may promote to ENGAGE.</p>
      {watches.map((w) => (
        <div className="card" key={w.id}>
          <div className="row">
            <span className="badge">{w.status}</span>
            <span className="badge">{w.target_type}</span>
          </div>
          <h3>{w.target_ref}</h3>
          <p>{w.created_reason}</p>
          <div className="row">
            {(w.triggers || []).map((t: any) => (
              <span className="badge" key={t.id}>{t.trigger_type}</span>
            ))}
          </div>
          {w.status === "ACTIVE" && (
            <div className="actions">
              <button className="ghost" onClick={() => fire(w)}>Simulate trigger</button>
            </div>
          )}
        </div>
      ))}
    </>
  );
}
