"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { API, api } from "@/lib/api";
import { formatBeijingTime, formatRelativeTime, timestampMs } from "@/lib/time";

type Mode = "URL" | "TEXT" | "PDF" | "MANUAL_OBSERVATION";
type Disposition = "DROP" | "AWARE" | "WATCH" | "ENGAGE";
type StateFilter = "ALL" | Disposition | "UNANALYZED";
type Source = {
  id: string; title?: string | null; canonical_url?: string | null; content_text?: string | null;
  ingestion_method?: string | null; ingested_at?: string | null; published_at?: string | null; publisher?: string | null;
  raw_metadata?: Record<string, any>;
};
type AttentionPlan = {
  id: string; candidate_type?: string | null; candidate_id: string; disposition: Disposition; created_at?: string | null;
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
function excerpt(source: Source, length = 210) {
  const text = (source.content_text || "").replace(/\s+/g, " ").trim();
  if (!text) return "Ready in RAOS.";
  return text.length > length ? `${text.slice(0, length).trim()}…` : text;
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
function editorialVariant(index: number) {
  if (index === 0) return "lead";
  if (index === 1 || index === 2) return "side";
  const pattern = ["wide", "standard", "standard", "compact", "standard", "wide", "compact"];
  return pattern[(index - 3) % pattern.length];
}
function stateLabel(state: StateFilter) {
  if (state === "UNANALYZED") return "Not analyzed";
  return state;
}

const MODES: Array<[Mode, string, string]> = [
  ["URL", "URL", "Article or public page"],
  ["TEXT", "Text", "Paste notes or content"],
  ["PDF", "PDF", "Paper or document"],
  ["MANUAL_OBSERVATION", "Observation", "Something you directly observed"],
];
const STATE_FILTERS: StateFilter[] = ["ALL", "ENGAGE", "WATCH", "AWARE", "DROP", "UNANALYZED"];

export default function InboxPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("URL");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<Source[]>([]);
  const [attentionBySource, setAttentionBySource] = useState<Record<string, AttentionPlan>>({});
  const [libraryQuery, setLibraryQuery] = useState("");
  const [originFilter, setOriginFilter] = useState("ALL");
  const [stateFilter, setStateFilter] = useState<StateFilter>("ALL");
  const [visibleCount, setVisibleCount] = useState(18);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [items, plans] = await Promise.all([
          api<Source[]>("/sources"),
          api<AttentionPlan[]>("/kernel/attention").catch(() => []),
        ]);
        if (cancelled) return;
        setRecent([...items].filter((item) => !isSystemFixture(item)).sort((a,b) => timestampMs(sourceTimeValue(b)) - timestampMs(sourceTimeValue(a))));
        const latest: Record<string, AttentionPlan> = {};
        for (const plan of plans) {
          if (plan.candidate_type && plan.candidate_type !== "SOURCE") continue;
          const prior = latest[plan.candidate_id];
          if (!prior || timestampMs(plan.created_at) >= timestampMs(prior.created_at)) latest[plan.candidate_id] = plan;
        }
        setAttentionBySource(latest);
      } catch { /* Keep Inbox readable even if a secondary status call fails. */ }
    })();
    return () => { cancelled = true; };
  }, []);

  const sourceOrigins = useMemo(() => {
    const counts = new Map<string, number>();
    for (const source of recent) counts.set(origin(source), (counts.get(origin(source)) || 0) + 1);
    return [...counts.entries()].sort((a,b) => b[1] - a[1]);
  }, [recent]);
  const stateCounts = useMemo(() => {
    const counts: Record<StateFilter, number> = { ALL: recent.length, ENGAGE: 0, WATCH: 0, AWARE: 0, DROP: 0, UNANALYZED: 0 };
    for (const source of recent) {
      const state = attentionBySource[source.id]?.disposition || "UNANALYZED";
      counts[state] += 1;
    }
    return counts;
  }, [recent, attentionBySource]);
  const filteredRecent = useMemo(() => recent.filter((source) => {
    if (originFilter !== "ALL" && origin(source) !== originFilter) return false;
    const state = attentionBySource[source.id]?.disposition || "UNANALYZED";
    if (stateFilter !== "ALL" && state !== stateFilter) return false;
    if (!libraryQuery.trim()) return true;
    const haystack = `${displayTitle(source)} ${excerpt(source)} ${origin(source)} ${state}`.toLowerCase();
    return haystack.includes(libraryQuery.trim().toLowerCase());
  }), [recent, originFilter, stateFilter, libraryQuery, attentionBySource]);

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
        <div><div className="eyebrow">Inbox</div><h1 className="page-title">Give RAOS something to think about.</h1><p className="page-subtitle">What RAOS has observed. New arrivals can be understood automatically; opening a source is just reading.</p></div>
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

      <section className="section source-library-section">
        <div className="section-heading inbox-library-heading"><div><h2>Source library</h2><p>{recent.length} sources observed. The layout follows arrival rhythm; cognition state stays visible without becoming the content.</p></div></div>
        <div className="inbox-library-toolbar">
          <input value={libraryQuery} onChange={(e) => { setLibraryQuery(e.target.value); setVisibleCount(18); }} placeholder="Search sources, topics, or RAOS state…" />
          <div className="source-state-filter-row" aria-label="Cognition state filters">
            {STATE_FILTERS.map((state) => <button key={state} className={stateFilter === state ? `source-state-filter active ${state}` : `source-state-filter ${state}`} onClick={() => { setStateFilter(state); setVisibleCount(18); }}><span>{state === "ALL" ? "All states" : stateLabel(state)}</span><strong>{stateCounts[state]}</strong></button>)}
          </div>
          <div className="source-filter-row" aria-label="Source filters">
            <button className={originFilter === "ALL" ? "source-filter active" : "source-filter"} onClick={() => { setOriginFilter("ALL"); setVisibleCount(18); }}>All sources · {recent.length}</button>
            {sourceOrigins.slice(0, 10).map(([name, count]) => <button key={name} className={originFilter === name ? "source-filter active" : "source-filter"} onClick={() => { setOriginFilter(name); setVisibleCount(18); }}>{name} · {count}</button>)}
          </div>
        </div>

        <div className="source-editorial-grid">
          {filteredRecent.slice(0, visibleCount).map((source, index) => {
            const when = sourceTimeValue(source);
            const image = heroImage(source);
            const fallback = Boolean(source.raw_metadata?.feed_fallback);
            const plan = attentionBySource[source.id];
            const state: StateFilter = plan?.disposition || "UNANALYZED";
            const variant = editorialVariant(index);
            return (
              <Link className={`source-editorial-card ${variant} state-${state} ${image ? "has-visual" : "text-only"}`} href={`/attention?source=${source.id}`} key={source.id}>
                {image && <div className="source-card-visual"><img src={image} alt="" loading="lazy" /></div>}
                <div className="source-card-content">
                  <div className="source-card-meta">
                    <span className={`source-cognition-chip ${state}`}>{stateLabel(state)}</span>
                    <span className="source-origin">{origin(source)}</span>
                    {fallback && <span className="feed-summary-chip">Feed summary</span>}
                    {when && <><span className="meta-separator">·</span><span title={formatBeijingTime(when)}>{formatRelativeTime(when)}</span></>}
                  </div>
                  <h3>{displayTitle(source)}</h3>
                  <p>{excerpt(source, variant === "lead" || variant === "wide" ? 260 : 155)}</p>
                  <div className="source-card-footer">
                    <span>{plan ? "RAOS cognition available" : "Readable · cognition pending or baseline"}</span>
                    <span className="text-link">Read →</span>
                  </div>
                </div>
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
