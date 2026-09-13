"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API, api } from "@/lib/api";

type Mode = "URL" | "TEXT" | "PDF" | "MANUAL_OBSERVATION";
type Source = { id: string; title?: string | null; ingestion_method?: string | null; ingested_at?: string | null };

const MODES: Array<[Mode, string, string]> = [
  ["URL", "URL", "Article or public page"],
  ["TEXT", "Text", "Paste notes or content"],
  ["PDF", "PDF", "Paper or document"],
  ["MANUAL_OBSERVATION", "Observation", "Something you directly observed"],
];

export default function InboxPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("URL");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<Source[]>([]);

  useEffect(() => {
    api<Source[]>("/sources").then((items) => setRecent(items.slice(0, 6))).catch(() => undefined);
  }, []);

  async function submit() {
    setBusy(true); setError(null);
    try {
      let source: { id: string };
      if (mode === "PDF") {
        const file = (document.getElementById("pdf") as HTMLInputElement)?.files?.[0];
        if (!file) throw new Error("Choose a PDF first.");
        const fd = new FormData(); fd.append("file", file); if (title) fd.append("title", title);
        const res = await fetch(`${API}/sources/pdf`, { method: "POST", body: fd });
        if (!res.ok) throw new Error(await res.text());
        source = await res.json();
      } else {
        if (!body.trim()) throw new Error(mode === "URL" ? "Paste a URL first." : "Add some content first.");
        source = await api("/sources", { method: "POST", body: JSON.stringify({ source_type: mode, title: title || null, content_text: mode === "URL" ? null : body, url: mode === "URL" ? body : null }) });
      }
      const analysis = await api<{ source_id: string }>("/analysis/run", { method: "POST", body: JSON.stringify({ source_id: source.id }) });
      router.push(`/attention?source=${analysis.source_id}`);
    } catch (e) { setError(String((e as Error).message || e)); }
    finally { setBusy(false); }
  }

  return (
    <>
      <header className="page-header">
        <div><div className="eyebrow">Inbox</div><h1 className="page-title">Give RAOS something to think about.</h1><p className="page-subtitle">Add information here. RAOS will decide whether it deserves your attention — ingestion itself does not.</p></div>
      </header>

      <div className="ingest-tabs">
        {MODES.map(([value, label, description]) => <button key={value} className={mode === value ? "ingest-tab active" : "ingest-tab"} onClick={() => { setMode(value); setError(null); }}><strong>{label}</strong><span style={{display:"block",fontSize:11,fontWeight:500,opacity:.7,marginTop:2}}>{description}</span></button>)}
      </div>

      <section className="card ingest-panel">
        {mode === "URL" && <><label>Public URL</label><input autoFocus value={body} onChange={(e) => setBody(e.target.value)} placeholder="https://…" /></>}
        {mode === "TEXT" && <><label>Text</label><textarea autoFocus value={body} onChange={(e) => setBody(e.target.value)} placeholder="Paste article text, notes, or a passage…" /></>}
        {mode === "MANUAL_OBSERVATION" && <><label>What did you observe?</label><textarea autoFocus value={body} onChange={(e) => setBody(e.target.value)} placeholder="Describe the observation as directly as possible…" /></>}
        {mode === "PDF" && <div className="drop-zone"><div className="eyebrow">PDF / paper</div><p>Choose a PDF. RAOS will preserve it as a source and run the same cognitive pipeline.</p><input id="pdf" type="file" accept="application/pdf" /></div>}
        <label>Title <span className="muted">· optional</span></label>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="RAOS will usually infer this from the source" />
        {error && <p className="error">{error}</p>}
        <div className="actions"><button disabled={busy} onClick={submit}>{busy ? "Analyzing…" : "Analyze with RAOS"}</button></div>
      </section>

      <section className="section">
        <div className="section-heading"><div><h2>Recent sources</h2><p>Jump back into something you recently added or acquired.</p></div></div>
        <div className="stack">
          {recent.map((source) => <Link className="card" href={`/attention?source=${source.id}`} key={source.id}><div className="row"><span className="badge">{source.ingestion_method || "source"}</span>{source.ingested_at && <span className="meta">{new Date(source.ingested_at).toLocaleString()}</span>}</div><h3>{source.title || "Untitled source"}</h3><span className="text-link">Open analysis →</span></Link>)}
        </div>
      </section>
    </>
  );
}
