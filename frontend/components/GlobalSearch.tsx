"use client";

import Link from "next/link";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api } from "@/lib/api";
import { attentionLabel } from "@/lib/attentionPresentation";

type Source = {
  id: string;
  title?: string | null;
  canonical_url?: string | null;
  content_text?: string | null;
  publisher?: string | null;
  ingestion_method?: string | null;
  raw_metadata?: Record<string, any>;
};
type Plan = { candidate_type?: string | null; candidate_id: string; disposition: string; created_at?: string | null };

function sourceOrigin(source: Source) {
  if (source.raw_metadata?.paper_profile) return `arXiv${source.raw_metadata?.primary_category ? ` · ${String(source.raw_metadata.primary_category).replace(/^.*\(([^)]+)\).*$/, "$1")}` : ""}`;
  if ((source.ingestion_method === "WEIBO_PUBLIC" || source.ingestion_method === "X_PUBLIC") && source.publisher) return source.publisher;
  try { if (source.canonical_url) return new URL(source.canonical_url).hostname.replace(/^www\./, ""); } catch {}
  return source.publisher || source.ingestion_method || "Source";
}
function title(source: Source) {
  const raw = source.raw_metadata?.paper_title || source.title || "Untitled source";
  return String(raw).replace(/\s*\|\s*[^|]+$/, "").trim();
}

function excerpt(source: Source) {
  const text = String(source.raw_metadata?.abstract || source.content_text || "").replace(/\s+/g, " ").trim();
  return text.length > 180 ? `${text.slice(0, 180).trim()}…` : text;
}

function buildReaderHref(sourceId: string, query: string) {
  const returnParams = new URLSearchParams();
  returnParams.set("q", query);
  const returnTo = `/inbox?${returnParams.toString()}`;
  const params = new URLSearchParams({ source: sourceId, returnTo, returnLabel: "Search results" });
  return `/attention?${params.toString()}`;
}

export default function GlobalSearch() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Source[]>([]);
  const [plans, setPlans] = useState<Record<string, Plan>>({});
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      } else if (event.key === "Escape") {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!open) return;
    requestAnimationFrame(() => inputRef.current?.focus());
    api<Plan[]>("/kernel/attention").then((items) => {
      const next: Record<string, Plan> = {};
      for (const plan of items) if (!next[plan.candidate_id]) next[plan.candidate_id] = plan;
      setPlans(next);
    }).catch(() => undefined);
  }, [open]);
  useEffect(() => {
    if (!open || !query.trim()) { setResults([]); setLoading(false); return; }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {
        const items = await api<Source[]>(`/sources/search?q=${encodeURIComponent(query.trim())}&limit=12`);
        if (!cancelled) setResults(items);
      } catch {
        if (!cancelled) setResults([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 160);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [open, query]);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previous; };
  }, [open]);

  const modal = open ? createPortal(
    <div className="global-search-backdrop" onMouseDown={(event) => { if (event.currentTarget === event.target) setOpen(false); }}>
      <section className="global-search-panel" role="dialog" aria-modal="true" aria-label="Search RAOS">
        <header><span className="global-search-icon">⌕</span><input ref={inputRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search everything RAOS has observed…" /><kbd>Esc</kbd></header>
        <div className="global-search-body">
          {!query.trim() && <div className="global-search-empty"><strong>Find something RAOS has already seen.</strong><span>Search titles, article text, publishers, and URLs. This is retrieval, not a new attention judgment.</span></div>}
          {query.trim() && loading && <div className="global-search-empty"><span>Searching your observed world…</span></div>}
          {query.trim() && !loading && results.length === 0 && <div className="global-search-empty"><strong>No matching source.</strong><span>Try a title fragment, topic, publisher, or phrase from the article.</span></div>}
          {results.length > 0 && <div className="global-search-results">{results.map((source) => {
            const plan = plans[source.id];
            const state = plan?.disposition || "UNANALYZED";
            return <Link key={source.id} className="global-search-result" href={buildReaderHref(source.id, query.trim())} onClick={() => setOpen(false)}>
              <div className="global-search-result-meta"><span className={`source-cognition-chip ${state}`}>{state === "UNANALYZED" ? "Not analyzed" : attentionLabel(state)}</span><span>{sourceOrigin(source)}</span></div>
              <strong>{title(source)}</strong>
              {excerpt(source) && <p>{excerpt(source)}</p>}
            </Link>;
          })}</div>}
        </div>
        <footer><span>Searches the full preserved article text.</span>{query.trim() && <Link href={`/inbox?q=${encodeURIComponent(query.trim())}`} onClick={() => setOpen(false)}>Open in Source library →</Link>}</footer>
      </section>
    </div>, document.body
  ) : null;

  return <>
    <button className="global-search-entry" onClick={() => setOpen(true)} aria-label="Search RAOS">
      <span>⌕</span><span className="global-search-entry-copy"><strong>Search RAOS</strong><small>Find anything already observed</small></span><kbd>⌘K</kbd>
    </button>
    {modal}
  </>;
}
