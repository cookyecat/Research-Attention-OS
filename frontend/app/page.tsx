"use client";

import { useEffect, useState } from "react";
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

export default function Page() {
  const [home, setHome] = useState<Home | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Home>("/meta/home")
      .then(setHome)
      .catch((e) => setError(String(e.message || e)));
    api("/kernel/seed", { method: "POST" }).catch(() => undefined);
  }, []);

  return (
    <>
      <h2>Scheduled cognitive work</h2>
      <p className="lede">
        Home is not an unread count. It is the current AttentionPlan against your Cognitive Kernel.
      </p>
      {error && <p className="error">{error}</p>}
      {home && (
        <div className="stats">
          <div className="stat">
            <b>{home.decision_items}</b>
            <span>may affect a current decision</span>
          </div>
          <div className="stat">
            <b>{home.engage_items}</b>
            <span>deserve attention</span>
          </div>
          <div className="stat">
            <b>{home.watch_topics}</b>
            <span>topics being watched</span>
          </div>
          <div className="stat">
            <b>{home.discarded}</b>
            <span>discarded (a positive outcome)</span>
          </div>
        </div>
      )}
      <p className="lede">
        Estimated attention required: {home?.estimated_attention_minutes ?? "—"} minutes. Proposed KernelPatches
        waiting for human commit: {home?.proposed_patches ?? "—"}.
      </p>
    </>
  );
}
