"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import KernelPatchCard from "@/components/KernelPatchCard";

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

  return (
    <>
      <h2>Cognitive Kernel</h2>
      <p className="lede">Active researcher state. Small and high-density. History is append-only; AI proposals stay PROPOSED until you Accept, Modify, or Reject.</p>
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
              {n.payload?.proposition && n.payload.proposition !== n.title && <p>{n.payload.proposition}</p>}
              {n.payload?.scope && <p className="lede">Scope: {n.payload.scope}</p>}
              {n.payload?.confidence != null && <p>Confidence: {n.payload.confidence}</p>}
              {n.payload?.description && n.payload.description !== n.title && <p>{n.payload.description}</p>}
              {n.payload?.text && n.payload.text !== n.title && <p>{n.payload.text}</p>}
            </div>
          ))}
        </div>
      ))}
      <h3>Proposed patches</h3>
      {patches.filter((p) => p.status === "PROPOSED").map((p) => (
        <KernelPatchCard key={p.id} patch={p} onCommitted={load} />
      ))}
    </>
  );
}
