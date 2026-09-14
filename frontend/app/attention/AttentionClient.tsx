"use client";

import Link from "next/link";
import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, apiOrNull } from "@/lib/api";
import { formatBeijingTime, formatRelativeTime, timestampMs } from "@/lib/time";
import KernelPatchCard from "@/components/KernelPatchCard";
import AttentionFeedbackPanel from "@/components/AttentionFeedbackPanel";
import BionicText from "@/components/BionicText";

type SourceSummary = {
  id: string;
  source_type?: string | null;
  title?: string | null;
  canonical_url?: string | null;
  content_text?: string | null;
  ingested_at?: string | null;
  ingestion_method?: string | null;
  raw_metadata?: Record<string, any>;
};

const RANK: Record<string, number> = { ENGAGE: 0, WATCH: 1, AWARE: 2, DROP: 3 };
const FILTERS = ["CURRENT", "ENGAGE", "WATCH", "AWARE", "DROP"] as const;

function sourceOrigin(source?: SourceSummary) {
  if (!source) return "Unknown source";
  try { if (source.canonical_url) return new URL(source.canonical_url).hostname.replace(/^www\./, ""); } catch {}
  return source.ingestion_method || "Manual source";
}

function sourceTimeValue(source?: SourceSummary, fallback?: string | null) {
  const raw = source?.raw_metadata || {};
  return raw.published || source?.ingested_at || fallback || null;
}

function sourceTime(source?: SourceSummary, fallback?: string | null) {
  const value = sourceTimeValue(source, fallback);
  return value ? formatBeijingTime(value) : null;
}

function isSystemFixture(source?: SourceSummary) {
  if (!source || source.raw_metadata?.acquisition) return false;
  const title = (source.title || "").toLowerCase();
  return /(^|\b)(smoke test|live smoke|rollout smoke|dogfood smoke)(\b|$)/i.test(title);
}

function sourceAuthor(source?: SourceSummary) {
  return source?.raw_metadata?.author || null;
}
function heroImage(source?: SourceSummary) {
  return source?.raw_metadata?.hero_image_cached_url || source?.raw_metadata?.hero_image_url || null;
}
function heroImageAlt(source?: SourceSummary) {
  return source?.raw_metadata?.hero_image_alt || displayTitle(source);
}
function articleImages(source?: SourceSummary) {
  const images = source?.raw_metadata?.article_images;
  return Array.isArray(images) ? images.filter((image) => image?.url) : [];
}
function mediaAssets(source?: SourceSummary) {
  const assets = source?.raw_metadata?.media_assets;
  if (Array.isArray(assets)) return assets.filter((asset) => asset?.type && (asset?.url || asset?.embed_url));
  return articleImages(source).map((image) => ({ type: "IMAGE", ...image }));
}
function mediaUrl(asset: any) {
  return asset?.cached_url || asset?.url || null;
}

function claimDisplayText(claim: any) {
  const text = String(claim?.text || "");
  const marker = "substantive_basis=";
  const index = text.indexOf(marker);
  return index >= 0 ? text.slice(index + marker.length).trim() : text;
}

function evidenceSentences(claims: any[]) {
  const out: Array<{ text: string; claim: any }> = [];
  for (const claim of claims || []) {
    const span = String(claim?.source_span_text || "");
    if (!span.trim()) continue;
    const sentences = span.match(/[^.!?。！？]+[.!?。！？]+|[^.!?。！？]+$/g) || [];
    for (const raw of sentences) {
      const text = raw.trim();
      if (text.length >= 24) out.push({ text, claim });
    }
  }
  return out;
}

type EvidenceAnchor = { paragraphIndex: number; start: number; end: number; claim: any; text: string };

function evidenceCandidates(paragraphs: string[], claims: any[]) {
  const candidates: EvidenceAnchor[] = [];
  const sentences = evidenceSentences(claims);
  paragraphs.forEach((paragraph, paragraphIndex) => {
    const matches = sentences
      .map((item) => {
        const start = paragraph.indexOf(item.text);
        return start >= 0 ? { paragraphIndex, start, end: start + item.text.length, claim: item.claim, text: item.text } : null;
      })
      .filter(Boolean) as EvidenceAnchor[];
    if (!matches.length) return;
    matches.sort((a, b) => {
      const score = (anchor: EvidenceAnchor) => anchor.text.length >= 60 && anchor.text.length <= 220 ? 0 : Math.abs(anchor.text.length - 140);
      return score(a) - score(b) || a.start - b.start;
    });
    candidates.push(matches[0]);
  });
  return candidates;
}

function selectReaderEvidenceAnchors(paragraphs: string[], claims: any[]) {
  const candidates = evidenceCandidates(paragraphs, claims);
  if (candidates.length <= 1) return candidates;
  const maxAnchors = Math.min(5, Math.max(1, Math.ceil(paragraphs.length / 4)));
  if (candidates.length <= maxAnchors) return candidates;
  const selected: EvidenceAnchor[] = [];
  const remaining = [...candidates];
  for (let slot = 0; slot < maxAnchors && remaining.length; slot++) {
    const target = ((slot + 0.5) / maxAnchors) * Math.max(0, paragraphs.length - 1);
    remaining.sort((a, b) => Math.abs(a.paragraphIndex - target) - Math.abs(b.paragraphIndex - target) || a.paragraphIndex - b.paragraphIndex);
    selected.push(remaining.shift()!);
  }
  return selected.sort((a, b) => a.paragraphIndex - b.paragraphIndex);
}

function inlineMediaForParagraph(assets: any[], paragraph: string, index: number, total: number) {
  return assets.filter((asset, assetIndex) => {
    const context = String(asset?.context_text || "").trim();
    if (context && (paragraph.includes(context) || context.includes(paragraph))) return true;
    if (!context && total > 5) {
      const target = Math.min(total - 1, Math.max(1, Math.round(((assetIndex + 1) / (assets.length + 1)) * total)));
      return index === target;
    }
    return false;
  });
}

function ReaderMedia({ asset }: { asset: any }) {
  const kind = String(asset?.type || "").toUpperCase();
  const caption = asset?.caption || asset?.alt || asset?.title || null;
  if (kind === "IMAGE") {
    const src = mediaUrl(asset);
    if (!src) return null;
    return <figure className="reader-inline-media reader-media-image">
      <img src={src} alt={asset?.alt || asset?.caption || "Article visual"} loading="lazy" />
      {caption && <figcaption>{caption}</figcaption>}
    </figure>;
  }
  if (kind === "VIDEO") {
    const src = mediaUrl(asset);
    if (!src) return null;
    const poster = asset?.poster_cached_url || asset?.poster_url || undefined;
    return <figure className="reader-inline-media reader-media-video">
      <video controls preload="metadata" playsInline poster={poster}>
        <source src={src} type={asset?.mime_type || undefined} />
        Your browser does not support embedded video.
      </video>
      {caption && <figcaption>{caption}</figcaption>}
      {asset?.url && <a className="reader-media-source" href={asset.url} target="_blank" rel="noreferrer">Open video source ↗</a>}
    </figure>;
  }
  if (kind === "EMBED" && asset?.embed_url) {
    return <figure className="reader-inline-media reader-media-embed">
      <div className="reader-embed-frame">
        <iframe
          src={asset.embed_url}
          title={asset?.title || `${asset?.provider || "Embedded"} video`}
          loading="lazy"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
          referrerPolicy="strict-origin-when-cross-origin"
          sandbox="allow-scripts allow-same-origin allow-presentation allow-popups"
        />
      </div>
      {caption && <figcaption>{caption}</figcaption>}
    </figure>;
  }
  return null;
}

function ReaderParagraph({ text, index, anchors, selectedClaimId, onSelect }: { text: string; index: number; anchors: EvidenceAnchor[]; selectedClaimId: string | null; onSelect: (claim: any) => void }) {
  const ranges = anchors.filter((anchor) => anchor.paragraphIndex === index);
  if (ranges.length === 0) return <p className="reader-paragraph" data-reader-index={index}><BionicText text={text} /></p>;
  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  ranges.forEach((range, rangeIndex) => {
    if (range.start > cursor) nodes.push(<BionicText key={`plain-${rangeIndex}`} text={text.slice(cursor, range.start)} />);
    const highlighted = text.slice(range.start, range.end);
    nodes.push(<span key={`evidence-${rangeIndex}`} className={`evidence-highlight ${selectedClaimId === range.claim.id ? "active" : ""}`} role="button" tabIndex={0} title="RAOS evidence anchor" onClick={() => onSelect(range.claim)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") onSelect(range.claim); }}><BionicText text={highlighted} /></span>);
    cursor = Math.max(cursor, range.end);
  });
  if (cursor < text.length) nodes.push(<BionicText key="plain-tail" text={text.slice(cursor)} />);
  return <p className="reader-paragraph" data-reader-index={index}>{nodes}</p>;
}

function displayTitle(source?: SourceSummary) {
  const title = source?.title || "Untitled source";
  return title.replace(/\s*\|\s*[^|]+$/, "").trim() || title;
}

function actionCopy(disposition: string) {
  if (disposition === "ENGAGE") return "This deserves focused attention now.";
  if (disposition === "WATCH") return "RAOS is keeping responsibility for the next update. You do not need to monitor this manually.";
  if (disposition === "AWARE") return "Worth knowing once. No cognitive commitment or follow-up is required.";
  return "No attention needed right now.";
}

function operationCopy(operation?: string | null) {
  if (operation === "CHALLENGE") return "This challenges something already in your Kernel.";
  if (operation === "REINFORCE") return "This strengthens or adds support to existing cognition.";
  if (operation === "OPEN_NEW") return "This may justify opening a new cognitive branch.";
  return "No material cognitive change to your current Kernel.";
}

function displayP(value: unknown) {
  if (value == null) return "UNKNOWN";
  return String(value);
}

function normalizedLine(value: string) {
  return value.toLowerCase().replace(/[\s\p{P}\p{S}]+/gu, " ").trim();
}

function readerParagraphs(source?: SourceSummary) {
  const content = source?.content_text || "";
  if (!content.trim()) return [];
  const fullTitle = source?.title || "";
  const shortTitle = fullTitle.replace(/\s*\|\s*[^|]+$/, "").trim();
  const titleForms = new Set([normalizedLine(fullTitle), normalizedLine(shortTitle)].filter(Boolean));
  return content
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !titleForms.has(normalizedLine(line)));
}

function readingMinutes(source?: SourceSummary) {
  const content = source?.content_text || "";
  if (!content.trim()) return null;
  const cjk = (content.match(/[\u3400-\u9fff]/g) || []).length;
  const words = content.replace(/[\u3400-\u9fff]/g, " ").trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / 230 + cjk / 450));
}

function sourceExcerpt(source?: SourceSummary, length = 190) {
  const text = (source?.content_text || "").replace(/\s+/g, " ").trim();
  if (!text) return "RAOS has a current attention state for this source.";
  const shortTitle = displayTitle(source);
  const cleaned = text.toLowerCase().startsWith(shortTitle.toLowerCase()) ? text.slice(shortTitle.length).trim() : text;
  return cleaned.length > length ? `${cleaned.slice(0, length).trim()}…` : cleaned;
}

function readerWhy(plan: any, analysis: any) {
  const operation = analysis?.update?.operation || plan?.update?.operation || null;
  if (analysis?.no_delta_awareness?.applicable) {
    return "This sits inside an area you asked RAOS to monitor and the event had material consequences, but it does not change your current working model.";
  }
  if (plan?.disposition === "WATCH") {
    return "The evidence matters to your current work, but the next useful step depends on future evidence. RAOS will keep watching for you.";
  }
  if (plan?.disposition === "ENGAGE") {
    if (operation === "CHALLENGE") return "This may overturn or revise something you currently rely on, so it deserves direct attention.";
    if (operation === "REINFORCE") return "This provides meaningful new support for an active question, bottleneck, or model in your work.";
    if (operation === "OPEN_NEW") return "This may open a genuinely new line of inquiry that is important enough to inspect now.";
    return "RAOS believes this can materially affect active cognition or a current decision.";
  }
  if (plan?.disposition === "AWARE") return "This is useful context to know, but RAOS found no reason for deeper work or follow-up.";
  return "RAOS found no current reason to spend your attention here.";
}

function nextMove(disposition: string) {
  if (disposition === "ENGAGE") return "Read this carefully, then decide whether your current view or work should change.";
  if (disposition === "WATCH") return "Read only if useful now. You can safely leave future monitoring to RAOS.";
  if (disposition === "AWARE") return "Read it once, absorb the context, and move on.";
  return "You can skip this unless you are personally curious.";
}

export default function AttentionPage() {
  const params = useSearchParams();
  const sourceId = params.get("source");
  const viewParam = params.get("view");
  const [plans, setPlans] = useState<any[]>([]);
  const [sources, setSources] = useState<Record<string, SourceSummary>>({});
  const [analysis, setAnalysis] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("CURRENT");
  const [query, setQuery] = useState("");
  const [detailView, setDetailView] = useState<"reader" | "inspector">("reader");
  const [activeParagraph, setActiveParagraph] = useState(0);
  const [readingProgress, setReadingProgress] = useState(0);
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);

  async function loadPlans() {
    const [nextPlans, nextSources] = await Promise.all([api<any[]>("/kernel/attention"), api<SourceSummary[]>("/sources")]);
    setPlans(nextPlans);
    setSources(Object.fromEntries(nextSources.map((source) => [source.id, source])));
  }

  async function loadAnalysis(mode: "read" | "reprocess" = "read") {
    if (!sourceId) return;
    setBusy(true); setError(null);
    try {
      if (mode === "reprocess") {
        setAnalysis(await api("/analysis/reprocess", { method: "POST", body: JSON.stringify({ source_id: sourceId }) }));
      } else {
        const existing = await apiOrNull<any>(`/analysis/by-source/${sourceId}`);
        setAnalysis(existing || await api("/analysis/extract", { method: "POST", body: JSON.stringify({ source_id: sourceId }) }));
      }
    } catch (e: unknown) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }

  useEffect(() => { loadPlans().catch((e) => setError(String(e.message || e))); }, []);
  useEffect(() => { setAnalysis(null); setDetailView(viewParam === "system" ? "inspector" : "reader"); loadAnalysis("read"); }, [sourceId, viewParam]);

  const currentPlans = useMemo(() => {
    const latest = new Map<string, any>();
    for (const plan of plans) {
      const key = `${plan.candidate_type}:${plan.candidate_id}`;
      if (!latest.has(key)) latest.set(key, plan);
    }
    return Array.from(latest.values()).sort((a, b) => (RANK[a.disposition] ?? 9) - (RANK[b.disposition] ?? 9));
  }, [plans]);

  const shown = useMemo(() => currentPlans.filter((p) => {
    if (isSystemFixture(sources[p.candidate_id])) return false;
    if (filter === "CURRENT" && p.disposition === "DROP") return false;
    if (filter !== "CURRENT" && p.disposition !== filter) return false;
    if (!query.trim()) return true;
    const title = sources[p.candidate_id]?.title || "";
    return `${title} ${p.reason || ""}`.toLowerCase().includes(query.toLowerCase());
  }), [currentPlans, filter, query, sources]);

  const counts = useMemo(() => {
    const visible = currentPlans.filter((p) => !isSystemFixture(sources[p.candidate_id]));
    return Object.fromEntries(FILTERS.map((f) => [f, f === "CURRENT" ? visible.filter((p) => p.disposition !== "DROP").length : visible.filter((p) => p.disposition === f).length]));
  }, [currentPlans, sources]);
  const editorialShown = useMemo(() => [...shown].sort((a, b) =>
    timestampMs(sourceTimeValue(sources[b.candidate_id], b.created_at)) - timestampMs(sourceTimeValue(sources[a.candidate_id], a.created_at))
  ), [shown, sources]);
  const selectedSource = sourceId ? sources[sourceId] : undefined;

  useEffect(() => {
    if (!sourceId || detailView !== "reader" || !analysis) return;
    const update = () => {
      const body = document.querySelector<HTMLElement>(".reader-body");
      const items = Array.from(document.querySelectorAll<HTMLElement>(".reader-paragraph"));
      if (!body || items.length === 0) return;
      const focusY = window.innerHeight * 0.38;
      let bestIndex = 0; let bestDistance = Number.POSITIVE_INFINITY;
      for (const item of items) {
        const distance = Math.abs(item.getBoundingClientRect().top - focusY);
        if (distance < bestDistance) { bestDistance = distance; bestIndex = Number(item.dataset.readerIndex || 0); }
      }
      setActiveParagraph(bestIndex);
      const rect = body.getBoundingClientRect();
      const consumed = Math.max(0, Math.min(rect.height, focusY - rect.top));
      setReadingProgress(rect.height > 0 ? consumed / rect.height : 0);
    };
    update(); window.addEventListener("scroll", update, { passive: true }); window.addEventListener("resize", update);
    return () => { window.removeEventListener("scroll", update); window.removeEventListener("resize", update); };
  }, [sourceId, detailView, analysis]);

  async function afterCommit() {
    await loadPlans();
    if (sourceId) {
      const existing = await apiOrNull<any>(`/analysis/by-source/${sourceId}`);
      if (existing) setAnalysis(existing);
    }
  }

  if (sourceId) {
    const plan = analysis ? (analysis.latest_attention_plan || analysis.attention_plan) : null;
    const awareness = analysis?.no_delta_awareness;
    const awarenessEvent = awareness?.events?.[0];
    const operation = analysis?.update?.operation || plan?.update?.operation || null;
    const paragraphs = readerParagraphs(selectedSource);
    const minutes = readingMinutes(selectedSource);
    const topMatch = analysis?.kernel_matches?.[0];
    const claims = analysis?.claims || [];
    const readerEvidenceAnchors = selectReaderEvidenceAnchors(paragraphs, claims);
    const inlineMedia = mediaAssets(selectedSource);
    const activeAnchor = readerEvidenceAnchors.find((anchor) => anchor.paragraphIndex === activeParagraph);
    const activeClaim = claims.find((claim: any) => claim.id === selectedClaimId) || activeAnchor?.claim || null;
    const progressPercent = Math.max(0, Math.min(100, Math.round(readingProgress * 100)));

    return (
      <>
        <div className="detail-toolbar">
          <Link className="back-link" href="/attention">← Back to Attention</Link>
          <div className="view-switch" role="tablist" aria-label="Detail view">
            <button className={detailView === "reader" ? "active" : ""} onClick={() => setDetailView("reader")}>Reader</button>
            <button className={detailView === "inspector" ? "active" : ""} onClick={() => setDetailView("inspector")}>RAOS Inspector</button>
          </div>
        </div>

        {error && <p className="error">{error}</p>}
        {!analysis && !error && <div className="empty-state">Loading source…</div>}

        {analysis && plan && detailView === "reader" && (
          <div className="reader-layout">
            <article className="reader-article">
              <header className="reader-header">
                <div className="reader-source-line">
                  <span>{sourceOrigin(selectedSource)}</span>
                  {sourceAuthor(selectedSource) && <><span>·</span><span>{sourceAuthor(selectedSource)}</span></>}
                  {sourceTime(selectedSource) && <><span>·</span><span>{sourceTime(selectedSource)}</span></>}
                  {minutes && <><span>·</span><span>{minutes} min read</span></>}
                </div>
                <h1>{displayTitle(selectedSource)}</h1>
                <div className="reader-actions">
                  {selectedSource?.canonical_url && <a className="button-link ghost" href={selectedSource.canonical_url} target="_blank" rel="noreferrer">Open original ↗</a>}
                </div>
              </header>

              {heroImage(selectedSource) && (
                <figure className="reader-hero-media">
                  <img src={heroImage(selectedSource)} alt={heroImageAlt(selectedSource)} loading="eager" />
                  {selectedSource?.raw_metadata?.hero_image_alt && <figcaption>{selectedSource.raw_metadata.hero_image_alt}</figcaption>}
                </figure>
              )}

              <div className={`reader-status ${plan.disposition}`}>
                <span className={`badge ${plan.disposition}`}>{plan.disposition}</span>
                <strong>{actionCopy(plan.disposition)}</strong>
              </div>

              {paragraphs.length > 0 ? (
                <div className="reader-body">
                  {paragraphs.map((paragraph, index) => (
                    <React.Fragment key={`${index}-${paragraph.slice(0, 24)}`}>
                      <ReaderParagraph text={paragraph} index={index} anchors={readerEvidenceAnchors} selectedClaimId={selectedClaimId} onSelect={(claim) => setSelectedClaimId(claim.id)} />
                      {inlineMediaForParagraph(inlineMedia, paragraph, index, paragraphs.length).map((asset: any, mediaIndex: number) => (
                        <ReaderMedia asset={asset} key={`${asset.type}-${asset.embed_url || asset.cached_url || asset.url || mediaIndex}`} />
                      ))}
                    </React.Fragment>
                  ))}
                </div>
              ) : (
                <div className="reader-empty">
                  <h3>No local readable text is available for this source.</h3>
                  <p>RAOS has the analysis record, but this source does not contain a preserved text body.</p>
                  {selectedSource?.canonical_url && <a className="button-link" href={selectedSource.canonical_url} target="_blank" rel="noreferrer">Read at source ↗</a>}
                </div>
              )}
            </article>

            <aside className={`reader-rail ${readingProgress > 0.02 ? "is-reading" : ""}`}>
              <section className="reader-note primary-context">
                <div className="eyebrow">Why it matters to you</div>
                <p><BionicText text={readerWhy(plan, analysis)} /></p>
                {topMatch && <div className="reader-context"><span>Closest current context</span><strong>{topMatch.title}</strong></div>}
              </section>

              {readingProgress <= 0.02 && <section className="reader-note primary-context">
                <div className="eyebrow">What to do</div>
                <p><BionicText text={nextMove(plan.disposition)} /></p>
                {plan.cognitive_budget_minutes != null && <div className="reader-budget">RAOS budget · {plan.cognitive_budget_minutes} min</div>}
              </section>}

              {readingProgress > 0.01 && <section className="reader-progress-card">
                <div className="eyebrow">Reading</div>
                <div className="reader-progress-track"><span style={{width: `${progressPercent}%`}} /></div>
                <div className="reader-progress-meta"><span>{progressPercent}% through article</span><span>¶ {Math.min(activeParagraph + 1, paragraphs.length)} / {paragraphs.length}</span></div>
              </section>}

              {readingProgress > 0.01 && activeClaim && <section className="reader-evidence-card">
                <div className="eyebrow">RAOS evidence near here</div>
                <h4>{activeClaim.claim_type || "Claim"}</h4>
                <p><BionicText text={claimDisplayText(activeClaim)} /></p>
                <button onClick={() => setDetailView("inspector")}>Open in Inspector →</button>
              </section>}

              <button className="inspector-entry" onClick={() => setDetailView("inspector")}>
                <span>Inspect RAOS decision</span>
                <small>See cognition, evidence, D/S/P, Kernel mapping, and pipeline trace</small>
              </button>
            </aside>
          </div>
        )}

        {analysis && plan && detailView === "inspector" && (
          <>
            <header className="page-header inspector-header">
              <div>
                <div className="eyebrow">Operating system view</div>
                <h1 className="page-title">RAOS Inspector</h1>
                <p className="page-subtitle">Inspect why the operating system made this attention decision. This is not the normal reading surface.</p>
                <div className="source-meta" style={{marginTop: 10}}><span>{selectedSource?.title || "Source"}</span></div>
              </div>
              <button className="ghost" disabled={busy} onClick={() => loadAnalysis("reprocess")}>{busy ? "Reprocessing…" : "Reprocess"}</button>
            </header>

            <div className="detail-grid">
              <div>
                <section className={`decision-hero ${plan.disposition}`}>
                  <div className="row"><span className={`badge ${plan.disposition}`}>{plan.disposition}</span>{operation && <span className="badge">{operation}</span>}</div>
                  <div className="decision-label">{plan.disposition}</div>
                  <p className="decision-copy">{actionCopy(plan.disposition)}</p>
                  <div className="metric-line" style={{marginTop: 14}}>
                    <span><strong>{plan.cognitive_budget_minutes ?? 0} min</strong> attention budget</span>
                    <span><strong>{plan.urgency || "NORMAL"}</strong> urgency</span>
                    <span><strong>{operation || "NONE"}</strong> cognitive effect</span>
                  </div>
                </section>

                {awareness?.applicable && (
                  <section className="section card">
                    <div className="eyebrow">No-Delta awareness path</div>
                    <h3>Situational relevance without cognitive change</h3>
                    <p className="muted">This branch is separate from cognitive change and uses standing-world fit, material consequence, and collective-attention evidence.</p>
                    <div className="reason-grid">
                      <div className="signal-card"><strong>D · Standing world</strong><span>Inside the user&apos;s monitoring jurisdiction?</span><span className="signal-state">{displayP(awarenessEvent?.component_states?.D)}</span></div>
                      <div className="signal-card"><strong>S · Material consequence</strong><span>Material disturbance to a consequential shared system?</span><span className="signal-state">{displayP(awarenessEvent?.component_states?.S)}</span></div>
                      <div className="signal-card"><strong>P · Collective attention</strong><span>Observed salience among the relevant constituency?</span><span className="signal-state">{displayP(awarenessEvent?.component_states?.P)}</span></div>
                    </div>
                    <details className="technical-details">
                      <summary>Estimator reasoning</summary>
                      <div className="technical-body">
                        {awarenessEvent?.D?.reason && <p><strong>D:</strong> {awarenessEvent.D.reason}</p>}
                        {awarenessEvent?.S?.reason && <p><strong>S:</strong> {awarenessEvent.S.reason}</p>}
                        {awarenessEvent?.P?.reason && <p><strong>P:</strong> {awarenessEvent.P.reason}</p>}
                      </div>
                    </details>
                  </section>
                )}

                <section className="section card">
                  <div className="eyebrow">Cognitive impact</div>
                  <h3>{operationCopy(operation)}</h3>
                  <p className="muted">{analysis.delta_content || analysis.model_delta?.summary || "No cognitive delta summary available."}</p>
                  {(analysis.model_delta?.distinctions?.length > 0 || analysis.model_delta?.questions?.length > 0) && (
                    <ul>{[...(analysis.model_delta.distinctions || []), ...(analysis.model_delta.questions || [])].map((item: string) => <li key={item}>{item}</li>)}</ul>
                  )}
                </section>

                {analysis.kernel_matches?.length > 0 && (
                  <section className="section card">
                    <div className="eyebrow">Kernel mapping</div>
                    <h3>Where the source touches current cognitive state</h3>
                    {analysis.kernel_matches.slice(0, 6).map((m: any) => (
                      <div className="kernel-match" key={m.node_id}>
                        <div className="row"><span className="badge">{m.node_type}</span><span className="meta">{m.relevance_type || "match"}</span>{m.score != null && <span className="meta">score {m.score}</span>}</div>
                        <h4>{m.title}</h4>
                        {m.reason && <p>{m.reason}</p>}
                      </div>
                    ))}
                  </section>
                )}

                <section className="section">
                  <details className="technical-details">
                    <summary>Evidence & pipeline trace</summary>
                    <div className="technical-body">
                      <div className="trace-grid">
                        <div className="trace-block"><h4>AnalysisRun</h4><p>provider {analysis.analysis_run?.provider_type} · {analysis.analysis_run?.status}</p><p>pipeline {analysis.analysis_run?.pipeline_version}<br/>extractor {analysis.analysis_run?.extractor_version}<br/>matcher {analysis.analysis_run?.matcher_version}<br/>prompt {analysis.analysis_run?.prompt_version}</p></div>
                        <div className="trace-block"><h4>Decision trace</h4><p>{plan.reason}</p><p>Strategy details and provenance remain frozen in the AnalysisRun.</p></div>
                      </div>
                      <h3 style={{marginTop: 22}}>Extracted evidence</h3>
                      <div className="claim-list">
                        {(analysis.claims || []).map((c: any) => <div className="claim-item" key={c.id}><span className="badge">{c.claim_type}</span><p>{c.text}</p></div>)}
                        {(analysis.observations || []).map((c: any) => <div className="claim-item" key={c.id}><span className="badge">observation</span><p>{c.text}</p></div>)}
                        {(analysis.inferences || []).map((c: any) => <div className="claim-item" key={c.id}><span className="badge">inference</span><p>{c.text}</p></div>)}
                      </div>
                    </div>
                  </details>
                </section>
              </div>

              <aside className="detail-side">
                {plan?.id && <AttentionFeedbackPanel planId={plan.id} analysis={analysis} onSubmitted={afterCommit} />}
                {analysis.kernel_patches?.length > 0 && (
                  <section className="section">
                    <div className="eyebrow">Human authorization required</div>
                    <h3>Proposed Kernel change</h3>
                    <p className="muted">RAOS can propose a cognitive update, but only you can commit it.</p>
                    {analysis.kernel_patches.map((p: any) => <KernelPatchCard key={p.id} patch={p} onCommitted={afterCommit} />)}
                  </section>
                )}
              </aside>
            </div>
          </>
        )}
      </>
    );
  }

  return (
    <>
      <header className="page-header">
        <div><div className="eyebrow">Attention</div><h1 className="page-title">Your filtered world.</h1><p className="page-subtitle">One source, one current attention state. Start with what needs you; everything else has already been compressed.</p></div>
        <Link className="button-link ghost" href="/inbox">Add source</Link>
      </header>
      {error && <p className="error">{error}</p>}

      <div className="section-heading">
        <div className="filter-bar">
          {FILTERS.map((value) => <button className={filter === value ? "filter-chip active" : "filter-chip"} key={value} onClick={() => setFilter(value)}>{value === "CURRENT" ? "Current" : value} · {counts[value] || 0}</button>)}
        </div>
        <input className="search-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search current attention…" />
      </div>

      {shown.length === 0 && <div className="empty-state">No current attention items match this view.</div>}
      {shown.length > 0 && (
        <div className={filter === "CURRENT" && !query.trim() ? "attention-newsroom" : "attention-card-grid"}>
          {editorialShown.map((p, index) => {
            const source = sources[p.candidate_id];
            const title = source ? displayTitle(source) : `${p.candidate_type} ${p.candidate_id}`;
            const when = sourceTimeValue(source, p.created_at);
            const newsroom = filter === "CURRENT" && !query.trim();
            return (
              <Link className={`${newsroom && index === 0 ? "attention-lead" : "attention-story-card"} disposition-${p.disposition}`} href={`/attention?source=${p.candidate_id}`} key={p.id}>
                {heroImage(source) && <img className="story-visual" src={heroImage(source)} alt={heroImageAlt(source)} loading="lazy" />}
                <div className="story-kicker"><span className={`badge ${p.disposition}`}>{p.disposition}</span><span>{sourceOrigin(source)}</span>{when && <><span>·</span><span title={formatBeijingTime(when)}>{formatRelativeTime(when)}</span></>}</div>
                <h2>{title}</h2>
                <p>{sourceExcerpt(source, newsroom && index === 0 ? 300 : 165)}</p>
                <div className="story-footer"><strong>{actionCopy(p.disposition)}</strong><span>Read →</span></div>
              </Link>
            );
          })}
        </div>
      )}
    </>
  );
}
