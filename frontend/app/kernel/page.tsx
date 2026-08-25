"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const ORDER = ["GOAL", "PROJECT", "BOTTLENECK", "QUESTION", "BELIEF", "HYPOTHESIS", "MODEL", "DECISION", "EXPERIMENT"];

export default function KernelPage() {
  const [kernel, setKernel] = useState<Record<string, any[]>>({});
  const [patches, setPatches] = useState<any[]>([]);

  async function load() {
    const [k, p] = await Promise.all([api<Record<string, any[]>>("/kernel"), api<any[]>("/kernel/patches")]);
    setKernel(k);
    setPatches(p);
  }

  useEffect(() => {
    api("/kernel/seed", { method: "POST" }).finally(load);
  }, []);

  async function act(id: string, action: "accept" | "reject") {
    await api(`/kernel/patches/${id}/${action}`, { method: "POST" });
    await load();
  }

  return (
    <>
      <h2>Cognitive Kernel</h2>
      <p className="lede">Active researcher state. Small and high-density. History is append-only; AI proposals stay PROPOSED until you commit.</p>
      {ORDER.filter((t) => kernel[t]?.length).map((t) => (
        <div key={t}>
          <h3>{t}</h3>
          {kernel[t].map((n) => (
            <div className="card" key={n.id}>
              <div className="row">
                <span className="badge">{n.status}</span>
                <span className="badge">v{n.current_version}</span>
              </div>
              <h3>{n.title}</h3>
              {n.payload?.proposition && <p>{n.payload.proposition}</p>}
              {n.payload?.scope && <p className="lede">Scope: {n.payload.scope}</p>}
              {n.payload?.confidence != null && <p>Confidence: {n.payload.confidence}</p>}
              {n.payload?.description && <p>{n.payload.description}</p>}
            </div>
          ))}
        </div>
      ))}
      <h3>Proposed patches</h3>
      {patches.filter((p) => p.status === "PROPOSED").map((p) => (
        <div className="card" key={p.id}>
          <div className="row">
            <span className="badge">{p.change_type}</span>
            <span className="badge">{p.target_object_type}</span>
          </div>
          <p>{p.reasoning}</p>
          <div className="actions">
            <button onClick={() => act(p.id, "accept")}>Accept</button>
            <button className="ghost" onClick={() => act(p.id, "reject")}>Reject</button>
          </div>
        </div>
      ))}
    </>
  );
}
