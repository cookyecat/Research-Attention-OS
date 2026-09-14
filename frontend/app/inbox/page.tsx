"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { API, api } from "@/lib/api";
import { formatBeijingTime, formatRelativeTime, timestampMs } from "@/lib/time";

type Mode = "URL" | "TEXT" | "PDF" | "MANUAL_OBSERVATION";
type Source = {
  id: string; title?: string | null; canonical_url?: string | null; content_text?: string | null;
  ingestion_method?: string | null; ingested_at?: string | null; published_at?: string | null; publisher?: string | null;
  raw_metadata?: Record<string, any>;
};

function displayTitle(source: Source) {
  const title = source.title || "Untitled source";
  return title.replace(/\s*\|\s*[^|]+$/, "").trim() || title;
}
function origin(source: Source) {
  if ((source.ingestion_method === "WEIBO_PUBLIC" || source.ingestion_method === "X_PUBLIC") && source.publisher) return source.publisher;
  try { if (source.canonical_url) return new URL(source.canonical_url).hostname.replace(/^www\./, ""); } catch {}
  return source.publisher || source.ingestion_method || "source";
}
function excerpt(source: Source) {
  const text = (source.content_text || "").replace(/\s+/g, " ").trim();
  if (!text) return "Ready in RAOS.";
  return text.length > 150 ? `${text.slice(0, 150).trim()}…` : text;
}
function sourceTimeValue(source: Source) {
  return source.published_at || source.raw_metadata?.published || source.ingested_at || null;
}
function heroImage(source: Source) {
  return source.raw_metadata?.hero_image_cached_url || source.raw_metadata?.hero_image_url || null;
}
function isSystemFixture(source: Source) {
  const title = (source.title || "").toLowerCase();
  return title.includes("smoke test") || title.includes("live smoke") || title.includes("rollout smoke");
}

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
  const [libraryQuery, setLibraryQuery] = useState("");
  const [originFilter, setOriginFilter] = useState("ALL");
  const [visibleCount, setVisibleCount] = useState(18);

  useEffect(() => {
    api<Source[]>("/sources").then((items) => setRecent(
      [...items]
        .filter((item) => !isSystemFixture(item))
        .sort((a,b) => timestampMs(sourceTimeValue(b)) - timestampMs(sourceTimeValue(a)))
    )).catch(() => undefined);
  }, []);

  const sourceOrigins = useMemo(() => {
    const counts = new Map<string, number>();
    for (const source of recent) counts.set(origin(source), (counts.get(origin(source)) || 0) + 1);
    return [...counts.entries()].sort((a,b) => b[1] - a[1]);
  }, [recent]);
  const filteredRecent = useMemo(() => recent.filter((source) => {
    if (originFilter !== "ALL" && origin(source) !== originFilter) return false;
    if (!libraryQuery.trim()) return true;
    const haystack = `${displayTitle(source)} ${excerpt(source)} ${origin(source)}`.toLowerCase();
    return haystack.includes(libraryQuery.trim().toLowerCase());
  }), [recent, originFilter, libraryQuery]);

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
        <div className="section-heading inbox-library-heading"><div><h2>Source library</h2><p>{recent.length} sources acquired so far. Read first; analysis is optional.</p></div></div>
        <div className="inbox-library-toolbar">
          <input value={libraryQuery} onChange={(e) => { setLibraryQuery(e.target.value); setVisibleCount(18); }} placeholder="Search acquired sources…" />
          <div className="source-filter-row">
            <button className={originFilter === "ALL" ? "source-filter active" : "source-filter"} onClick={() => { setOriginFilter("ALL"); setVisibleCount(18); }}>All · {recent.length}</button>
            {sourceOrigins.slice(0, 10).map(([name, count]) => <button key={name} className={originFilter === name ? "source-filter active" : "source-filter"} onClick={() => { setOriginFilter(name); setVisibleCount(18); }}>{name} · {count}</button>)}
          </div>
        </div>
        <div className="recent-source-grid">
          {filteredRecent.slice(0, visibleCount).map((source, index) => {
            const when = sourceTimeValue(source);
            const image = heroImage(source);
            const fallback = Boolean(source.raw_metadata?.feed_fallback);
            return (
              <Link className={index === 0 ? "recent-source-card featured" : "recent-source-card"} href={`/attention?source=${source.id}`} key={source.id}>
                {image && <div className="recent-source-visual"><img src={image} alt="" loading="lazy" /></div>}
                <div className="story-kicker"><span>{origin(source)}</span>{fallback && <span className="feed-summary-chip">Feed summary</span>}{when && <><span>·</span><span title={formatBeijingTime(when)}>{formatRelativeTime(when)}</span></>}</div>
                <h3>{displayTitle(source)}</h3>
                <p>{excerpt(source)}</p>
                <span className="text-link">Read in RAOS →</span>
              </Link>
            );
          })}
        </div>
        {filteredRecent.length > visibleCount && <div className="library-more"><button className="ghost" onClick={() => setVisibleCount((n) => n + 18)}>Show 18 more · {filteredRecent.length - visibleCount} remaining</button></div>}
        {filteredRecent.length === 0 && <div className="empty-state">No acquired sources match this filter.</div>}
      </section>
    </>
  );
}
