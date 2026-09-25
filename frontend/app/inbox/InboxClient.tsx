"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { API, api, cachedApi, invalidateApiCache } from "@/lib/api";
import { formatBeijingTime, formatRelativeTime, timestampMs } from "@/lib/time";
import { attentionLabel } from "@/lib/attentionPresentation";

type Mode = "URL" | "TEXT" | "PDF" | "MANUAL_OBSERVATION";
type Disposition = "DROP" | "AWARE" | "WATCH" | "ENGAGE";
type StateFilter = "ALL" | Disposition | "UNANALYZED";
type Source = {
  id: string; title?: string | null; canonical_url?: string | null; content_text?: string | null;
  ingestion_method?: string | null; ingested_at?: string | null; published_at?: string | null; publisher?: string | null;
  raw_metadata?: Record<string, any>;
};
type AttentionPlan = {
  id: string;
  candidate_type?: string | null;
  candidate_id: string;
  representative_source_id?: string | null;
  source_ids?: string[];
  disposition: Disposition;
  created_at?: string | null;
};
type InboxPayload = {
  items: any[];
  next_cursor?: string | null;
  summary: {
    source_count: number;
    state_counts: Record<StateFilter, number>;
    origins: Array<{ name: string; count: number }>;
  };
};

function isPaperSource(source: Source) {
  if (source.raw_metadata?.paper_profile) return true;
  try { return Boolean(source.canonical_url && new URL(source.canonical_url).hostname.replace(/^www\./, "") === "arxiv.org"); } catch {}
  return false;
}
function paperCategoryCode(source: Source) {
  const value = String(source.raw_metadata?.primary_category || "");
  const match = value.match(/\(([^)]+)\)/);
  return match?.[1] || value || null;
}
function displayTitle(source: Source) {
  if (source.raw_metadata?.paper_title) return String(source.raw_metadata.paper_title).trim();
  const title = source.title || "Untitled source";
  return title.replace(/\s*\|\s*[^|]+$/, "").trim() || title;
}
function origin(source: Source) {
  if (isPaperSource(source)) {
    const category = paperCategoryCode(source);
    return category ? `arXiv · ${category}` : "arXiv";
  }
  if ((source.ingestion_method === "WEIBO_PUBLIC" || source.ingestion_method === "X_PUBLIC") && source.publisher) return source.publisher;
  try { if (source.canonical_url) return new URL(source.canonical_url).hostname.replace(/^www\./, ""); } catch {}
  return source.publisher || source.ingestion_method || "source";
}
function excerpt(source: Source, length = 210) {
  const preferred = isPaperSource(source) ? source.raw_metadata?.abstract : null;
  const text = String(preferred || source.content_text || "").replace(/\s+/g, " ").trim();
  if (!text) return "Ready in RAOS.";
  return text.length > length ? `${text.slice(0, length).trim()}…` : text;
}
function sourceTimeValue(source: Source) {
  return source.published_at || source.raw_metadata?.published || source.ingested_at || null;
}
function heroImage(source: Source) {
  if (isPaperSource(source)) return source.raw_metadata?.paper_lead_figure_url || null;
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
  if (state === "ALL") return "All states";
  if (state === "UNANALYZED") return "Not analyzed";
  return attentionLabel(state);
}

const MODES: Array<[Mode, string, string]> = [
  ["URL", "URL", "Article or public page"],
  ["TEXT", "Text", "Paste notes or content"],
  ["PDF", "PDF", "Paper or document"],
  ["MANUAL_OBSERVATION", "Observation", "Something you directly observed"],
];
const STATE_FILTERS: StateFilter[] = ["ALL", "ENGAGE", "WATCH", "AWARE", "DROP", "UNANALYZED"];

function initialStateFilter(value: string | null): StateFilter {
  return STATE_FILTERS.includes(value as StateFilter) ? value as StateFilter : "ALL";
}

function sourceFromSurface(card: any): Source {
  return {
    id: card.id,
    title: card.title,
    canonical_url: card.canonical_url,
    content_text: card.excerpt,
    ingestion_method: card.ingestion_method,
    ingested_at: card.ingested_at,
    published_at: card.published_at,
    publisher: card.publisher,
    raw_metadata: {
      ...(card.presentation_metadata || {}),
      hero_image_url: card.hero_image_url,
      hero_image_cached_url: card.hero_image_url,
      hero_image_alt: card.hero_image_alt,
    },
  };
}

function attentionFromSurface(card: any): AttentionPlan | null {
  if (!card.disposition || !card.attention_plan_id) return null;
  return {
    id: card.attention_plan_id,
    candidate_type: "EVENT",
    candidate_id: card.event_id || card.id,
    representative_source_id: card.id,
    disposition: card.disposition,
  };
}

async function apiWithRetry<T>(path: string, attempts = 4): Promise<T> {
  let lastError: unknown;
  const ttlMs = path.startsWith("/sources?compact=true")
    ? 30_000
    : path.startsWith("/kernel/attention?compact=true")
      ? 5_000
      : 0;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      return ttlMs > 0
        ? await cachedApi<T>(path, ttlMs)
        : await api<T>(path);
    } catch (error) {
      lastError = error;
      if (attempt + 1 < attempts) {
        await new Promise((resolve) => window.setTimeout(resolve, 250 * (2 ** attempt)));
      }
    }
  }
  throw lastError;
}

export default function InboxPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const restoredScroll = useRef(false);
  const [mode, setMode] = useState<Mode>("URL");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [libraryLoading, setLibraryLoading] = useState(true);
  const [recent, setRecent] = useState<Source[]>([]);
  const [attentionBySource, setAttentionBySource] = useState<Record<string, AttentionPlan>>({});
  const [libraryQuery, setLibraryQuery] = useState(() => searchParams.get("q") || "");
  const [originFilter, setOriginFilter] = useState(() => searchParams.get("origin") || "ALL");
  const [stateFilter, setStateFilter] = useState<StateFilter>(() => initialStateFilter(searchParams.get("state")));
  const [visibleCount, setVisibleCount] = useState(() => Math.max(18, Number(searchParams.get("n") || 18) || 18));
  const [libraryMatchIds, setLibraryMatchIds] = useState<Set<string> | null>(null);
  const [librarySummary, setLibrarySummary] = useState<InboxPayload["summary"]>({
    source_count: 0,
    state_counts: { ALL: 0, ENGAGE: 0, WATCH: 0, AWARE: 0, DROP: 0, UNANALYZED: 0 },
    origins: [],
  });
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setLibraryLoading(true);
      try {
        const params = new URLSearchParams({ limit: "30", state: stateFilter });
        if (originFilter !== "ALL") params.set("origin", originFilter);
        if (libraryQuery.trim()) params.set("q", libraryQuery.trim());
        const payload = await apiWithRetry<InboxPayload>(`/user-space/inbox?${params.toString()}`);
        if (cancelled) return;
        const nextSources = payload.items.map(sourceFromSurface).filter((item) => !isSystemFixture(item));
        const nextAttention: Record<string, AttentionPlan> = {};
        for (const card of payload.items) {
          const plan = attentionFromSurface(card);
          if (plan) nextAttention[card.id] = plan;
        }
        setRecent(nextSources);
        setAttentionBySource(nextAttention);
        setLibrarySummary(payload.summary);
        setNextCursor(payload.next_cursor || null);
        setLibraryMatchIds(null);
        setError(null);
      } catch (e) {
        if (!cancelled) setError(`Failed to load Source library: ${String((e as Error).message || e)}`);
      } finally {
        if (!cancelled) setLibraryLoading(false);
      }
    }, libraryQuery.trim() ? 140 : 0);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [stateFilter, originFilter, libraryQuery]);

  const currentInboxHref = useMemo(() => {
    const params = new URLSearchParams();
    if (libraryQuery.trim()) params.set("q", libraryQuery.trim());
    if (stateFilter !== "ALL") params.set("state", stateFilter);
    if (originFilter !== "ALL") params.set("origin", originFilter);
    if (visibleCount > 18) params.set("n", String(visibleCount));
    const query = params.toString();
    return `/inbox${query ? `?${query}` : ""}`;
  }, [libraryQuery, stateFilter, originFilter, visibleCount]);

  useEffect(() => {
    router.replace(currentInboxHref, { scroll: false });
  }, [currentInboxHref, router]);

  useEffect(() => {
    if (restoredScroll.current || recent.length === 0) return;
    restoredScroll.current = true;
    const raw = sessionStorage.getItem(`raos-inbox-scroll:${currentInboxHref}`);
    const y = Number(raw || 0);
    if (y > 0) requestAnimationFrame(() => window.scrollTo({ top: y, behavior: "auto" }));
  }, [recent.length, currentInboxHref]);

  function rememberInboxPosition() {
    sessionStorage.setItem(`raos-inbox-scroll:${currentInboxHref}`, String(window.scrollY));
  }

  function readerHref(sourceId: string) {
    const params = new URLSearchParams({ source: sourceId, returnTo: currentInboxHref, returnLabel: "Inbox" });
    return `/attention?${params.toString()}`;
  }

  const sourceOrigins = useMemo(
    () => librarySummary.origins.map((item) => [item.name, item.count] as [string, number]),
    [librarySummary]
  );
  const stateCounts = librarySummary.state_counts;
  const filteredRecent = recent;

  async function loadMore() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const params = new URLSearchParams({ limit: "30", state: stateFilter, cursor: nextCursor });
      if (originFilter !== "ALL") params.set("origin", originFilter);
      if (libraryQuery.trim()) params.set("q", libraryQuery.trim());
      const payload = await api<InboxPayload>(`/user-space/inbox?${params.toString()}`);
      const moreSources = payload.items.map(sourceFromSurface).filter((item) => !isSystemFixture(item));
      const moreAttention: Record<string, AttentionPlan> = {};
      for (const card of payload.items) {
        const plan = attentionFromSurface(card);
        if (plan) moreAttention[card.id] = plan;
      }
      setRecent((current) => [...current, ...moreSources]);
      setAttentionBySource((current) => ({ ...current, ...moreAttention }));
      setLibrarySummary(payload.summary);
      setNextCursor(payload.next_cursor || null);
    } catch (e) {
      setError(`Failed to load more Sources: ${String((e as Error).message || e)}`);
    } finally {
      setLoadingMore(false);
    }
  }

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
      invalidateApiCache("/sources?compact=true");
      invalidateApiCache("/kernel/attention?compact=true");
      router.push(`/attention?${new URLSearchParams({ source: analysis.source_id, returnTo: currentInboxHref, returnLabel: "Inbox" }).toString()}`);
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
        <div className="section-heading inbox-library-heading"><div><h2>Source library</h2><p>{libraryLoading ? "Loading current Source library…" : `${librarySummary.source_count} sources observed. The layout follows arrival rhythm; cognition state stays visible without becoming the content.`}</p></div></div>
        <div className="inbox-library-toolbar">
          <input value={libraryQuery} onChange={(e) => { setLibraryQuery(e.target.value); setVisibleCount(18); }} placeholder="Search sources, topics, or RAOS state…" />
          <div className="source-state-filter-row" aria-label="Cognition state filters">
            {STATE_FILTERS.map((state) => <button key={state} className={stateFilter === state ? `source-state-filter active ${state}` : `source-state-filter ${state}`} onClick={() => { setStateFilter(state); setVisibleCount(18); }}><span>{state === "ALL" ? "All states" : stateLabel(state)}</span><strong>{libraryLoading ? "…" : stateCounts[state]}</strong></button>)}
          </div>
          <div className="source-filter-row" aria-label="Source filters">
            <button className={originFilter === "ALL" ? "source-filter active" : "source-filter"} onClick={() => { setOriginFilter("ALL"); setVisibleCount(18); }}>All sources · {libraryLoading ? "…" : librarySummary.source_count}</button>
            {sourceOrigins.slice(0, 10).map(([name, count]) => <button key={name} className={originFilter === name ? "source-filter active" : "source-filter"} onClick={() => { setOriginFilter(name); setVisibleCount(18); }}>{name} · {count}</button>)}
          </div>
        </div>

        <div className="source-editorial-grid">
          {filteredRecent.map((source, index) => {
            const when = sourceTimeValue(source);
            const image = heroImage(source);
            const fallback = Boolean(source.raw_metadata?.feed_fallback);
            const plan = attentionBySource[source.id];
            const state: StateFilter = plan?.disposition || "UNANALYZED";
            const variant = editorialVariant(index);
            return (
              <Link className={`source-editorial-card ${variant} state-${state} ${image ? "has-visual" : "text-only"}`} href={readerHref(source.id)} onClick={rememberInboxPosition} key={source.id}>
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
        {nextCursor && <div className="library-more"><button className="ghost" disabled={loadingMore} onClick={loadMore}>{loadingMore ? "Loading…" : "Show 30 more"}</button></div>}
        {!libraryLoading && filteredRecent.length === 0 && <div className="empty-state">No acquired sources match this filter.</div>}
      </section>
    </>
  );
}
