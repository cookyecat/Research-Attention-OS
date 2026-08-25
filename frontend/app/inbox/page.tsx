"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { API, api } from "@/lib/api";

export default function InboxPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"TEXT" | "URL" | "MANUAL_OBSERVATION" | "PDF">("TEXT");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      let source: { id: string };
      if (mode === "PDF") {
        const fileInput = document.getElementById("pdf") as HTMLInputElement;
        const file = fileInput?.files?.[0];
        if (!file) throw new Error("Choose a PDF");
        const fd = new FormData();
        fd.append("file", file);
        if (title) fd.append("title", title);
        const res = await fetch(`${API}/sources/pdf`, { method: "POST", body: fd });
        if (!res.ok) throw new Error(await res.text());
        source = await res.json();
      } else {
        source = await api("/sources", {
          method: "POST",
          body: JSON.stringify({
            source_type: mode,
            title: title || null,
            content_text: mode === "URL" ? null : body,
            url: mode === "URL" ? body : null,
          }),
        });
      }
      const analysis = await api<{ source_id: string }>("/analysis/run", {
        method: "POST",
        body: JSON.stringify({ source_id: source.id, persist_suggested_watches: true }),
      });
      router.push(`/attention?source=${analysis.source_id}`);
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h2>Add Source</h2>
      <p className="lede">Paste text, a public URL, a PDF, or a first-class field observation. Ingestion does not schedule attention.</p>
      <label>Input type</label>
      <select value={mode} onChange={(e) => setMode(e.target.value as typeof mode)}>
        <option value="TEXT">Pasted text</option>
        <option value="URL">URL</option>
        <option value="PDF">PDF / paper</option>
        <option value="MANUAL_OBSERVATION">Manual observation</option>
      </select>
      <label>Title (optional)</label>
      <input value={title} onChange={(e) => setTitle(e.target.value)} />
      {mode === "PDF" ? (
        <>
          <label>PDF file</label>
          <input id="pdf" type="file" accept="application/pdf" />
        </>
      ) : (
        <>
          <label>{mode === "URL" ? "Public URL" : mode === "MANUAL_OBSERVATION" ? "What you observed" : "Text"}</label>
          <textarea value={body} onChange={(e) => setBody(e.target.value)} />
        </>
      )}
      {error && <p className="error">{error}</p>}
      <div className="actions">
        <button disabled={busy} onClick={submit}>
          {busy ? "Ingesting…" : "Ingest and analyze"}
        </button>
      </div>
    </>
  );
}
