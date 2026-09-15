"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

type DeliveryEnvelope = {
  id: string;
  disposition: string;
  urgency: string;
  delivery_class: string;
  payload: {
    title?: string | null;
    reason?: string | null;
    source_id?: string | null;
    canonical_url?: string | null;
  };
};

function websocketUrl(): string {
  const configured = process.env.NEXT_PUBLIC_DELIVERY_WS_URL;
  if (configured) return configured;
  if (typeof window === "undefined") return "";
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.hostname || "127.0.0.1";
  return `${protocol}//${host}:8000/deliveries/ws`;
}

export default function DeliveryListener() {
  const [queue, setQueue] = useState<DeliveryEnvelope[]>([]);
  const current = queue[0] ?? null;
  const wsUrl = useMemo(() => websocketUrl(), []);

  useEffect(() => {
    if (!wsUrl) return;
    let socket: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let closed = false;

    const connect = () => {
      if (closed) return;
      socket = new WebSocket(wsUrl);
      socket.onmessage = (event) => {
        try {
          const item = JSON.parse(event.data) as DeliveryEnvelope;
          if (item.delivery_class !== "INTERRUPT" || item.disposition !== "ENGAGE") return;
          setQueue((prior) => prior.some((row) => row.id === item.id) ? prior : [...prior, item]);
        } catch {
          // Transport payload errors never become Attention decisions.
        }
      };
      socket.onclose = () => {
        if (!closed) timer = setTimeout(connect, 2000);
      };
      socket.onerror = () => socket?.close();
    };

    connect();
    return () => {
      closed = true;
      if (timer) clearTimeout(timer);
      socket?.close();
    };
  }, [wsUrl]);

  const resolve = async (outcome: "acknowledge" | "dismiss") => {
    if (!current) return;
    try {
      await api(`/deliveries/${current.id}/${outcome}`, { method: "POST" });
    } finally {
      setQueue((prior) => prior.filter((row) => row.id !== current.id));
    }
  };

  if (!current) return null;

  return (
    <aside className="delivery-toast" aria-live="assertive" aria-label="RAOS attention delivery">
      <div className="delivery-toast-kicker">
        RAOS · {current.urgency === "PREEMPT" ? "Interrupt now" : "Needs your attention"}
      </div>
      <h2>{current.payload.title || "Attention item"}</h2>
      {current.payload.reason ? <p>{current.payload.reason}</p> : null}
      <div className="delivery-toast-actions">
        {current.payload.source_id ? (
          <a href={`/attention?source=${encodeURIComponent(current.payload.source_id)}`}>Open in RAOS</a>
        ) : current.payload.canonical_url ? (
          <a href={current.payload.canonical_url} target="_blank" rel="noreferrer">Open source</a>
        ) : null}
        <button type="button" onClick={() => void resolve("acknowledge")}>Acknowledge</button>
        <button type="button" className="quiet" onClick={() => void resolve("dismiss")}>Dismiss</button>
      </div>
      {queue.length > 1 ? <div className="delivery-toast-count">{queue.length - 1} more waiting</div> : null}
    </aside>
  );
}
