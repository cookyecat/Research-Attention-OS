"use client";

import Link from "next/link";
import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, apiOrNull, cachedApi, invalidateApiCache } from "@/lib/api";
import { formatBeijingTime, formatRelativeTime, timestampMs } from "@/lib/time";
import { attentionLabel } from "@/lib/attentionPresentation";
import KernelPatchCard from "@/components/KernelPatchCard";
import AttentionFeedbackPanel from "@/components/AttentionFeedbackPanel";
import BionicText from "@/components/BionicText";

type SourceSummary = {
  id: string;
  source_type?: string | null;
  title?: string | null;
  canonical_url?: string | null;
  content_text?: string | null;
  published_at?: string | null;
  publisher?: string | null;
  ingested_at?: string | null;
  ingestion_method?: string | null;
  raw_metadata?: Record<string, any>;
};

const RANK: Record<string, number> = { ENGAGE: 0, WATCH: 1, AWARE: 2, DROP: 3 };
const FILTERS = ["CURRENT", "ENGAGE", "WATCH", "AWARE", "DROP"] as const;

function paperCategoryCode(source?: SourceSummary) {
  const value = String(source?.raw_metadata?.primary_category || "");
  const match = value.match(/\(([^)]+)\)/);
  return match?.[1] || value || null;
}

function isPaperSource(source?: SourceSummary) {
  if (!source) return false;
  if (source.source_type === "PAPER" || source.raw_metadata?.paper_profile) return true;
  try { return Boolean(source.canonical_url && new URL(source.canonical_url).hostname.replace(/^www\./, "") === "arxiv.org"); } catch {}
  return false;
}

function sourceOrigin(source?: SourceSummary) {
  if (!source) return "Unknown source";
  if (isPaperSource(source)) {
    const category = paperCategoryCode(source);
    return category ? `arXiv · ${category}` : "arXiv";
  }
  try { if (source.canonical_url) return new URL(source.canonical_url).hostname.replace(/^www\./, ""); } catch {}
  return source.ingestion_method || "Manual source";
}

function sourceTimeValue(source?: SourceSummary, fallback?: string | null) {
  const raw = source?.raw_metadata || {};
  return source?.published_at || raw.published || source?.ingested_at || fallback || null;
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
  return source?.raw_metadata?.author || source?.raw_metadata?.social_author || null;
}
function heroImage(source?: SourceSummary) {
  if (isPaperSource(source)) return source?.raw_metadata?.paper_lead_figure_url || null;
  return source?.raw_metadata?.hero_image_cached_url || source?.raw_metadata?.hero_image_url || null;
}
function paperAuthors(source?: SourceSummary) {
  const values = source?.raw_metadata?.authors;
  return Array.isArray(values) ? values.filter(Boolean) : [];
}
function paperAffiliations(source?: SourceSummary) {
  const values = source?.raw_metadata?.affiliations;
  return Array.isArray(values) ? values.filter(Boolean) : [];
}
function paperSections(source?: SourceSummary) {
  const values = source?.raw_metadata?.paper_sections;
  return Array.isArray(values) ? values.filter((item) => item?.id && item?.title) : [];
}
function heroImageAlt(source?: SourceSummary) {
  return source?.raw_metadata?.hero_image_alt || displayTitle(source);
}
function articleImages(source?: SourceSummary) {
  const images = source?.raw_metadata?.article_images;
  return Array.isArray(images) ? images.filter((image) => image?.url) : [];
}
function articleBlocks(source?: SourceSummary) {
  const blocks = source?.raw_metadata?.article_blocks;
  return Array.isArray(blocks) ? blocks.filter((block) => block?.type) : [];
}
function mediaAssets(source?: SourceSummary) {
  const assets = source?.raw_metadata?.media_assets;
  if (Array.isArray(assets)) return assets.filter((asset) => asset?.type && (asset?.url || asset?.embed_url));
  return articleImages(source).map((image) => ({ type: "IMAGE", ...image }));
}
function mediaUrl(asset: any) {
  return asset?.cached_url || asset?.url || null;
}
function isSocialSource(source?: SourceSummary) {
  return Boolean(source?.raw_metadata?.social_platform);
}
function socialMediaAssets(source?: SourceSummary) {
  const assets = mediaAssets(source);
  if (assets.length) return assets;
  const raw = source?.raw_metadata || {};
  const fallback = raw.hero_image_cached_url || raw.hero_image_url;
  return fallback ? [{ type: "IMAGE", cached_url: raw.hero_image_cached_url, url: raw.hero_image_url, media_id: "hero" }] : [];
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

function SocialMediaGallery({ assets }: { assets: any[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);
  const visible = assets.filter((asset) => mediaUrl(asset));
  if (!visible.length) return null;
  return <section className={`social-media-gallery count-${Math.min(visible.length, 9)}`} aria-label="Source media">
    {visible.map((asset, index) => {
      const kind = String(asset?.type || "IMAGE").toUpperCase();
      const src = mediaUrl(asset);
      const poster = asset?.poster_cached_url || asset?.poster_url || undefined;
      const isExpanded = expanded === index;
      const label = asset?.media_kind === "LIVEPHOTO" ? "LIVE" : kind === "VIDEO" ? "VIDEO" : null;
      if (kind === "VIDEO" && isExpanded) {
        return <div className="social-media-item expanded video" key={`${asset.media_id || index}-${src}`}>
          <video controls autoPlay preload="metadata" playsInline poster={poster}>
            <source src={src} type={asset?.mime_type || undefined} />
          </video>
          <button type="button" className="social-media-collapse" onClick={() => setExpanded(null)}>收起</button>
        </div>;
      }
      return <button
        type="button"
        className={`social-media-item ${isExpanded ? "expanded" : ""}`}
        key={`${asset.media_id || index}-${src}`}
        onClick={() => setExpanded(isExpanded ? null : index)}
        aria-label={isExpanded ? "收起媒体" : "展开媒体"}
      >
        {kind === "VIDEO" ? <video muted preload="metadata" playsInline poster={poster}><source src={src} type={asset?.mime_type || undefined} /></video> : <img src={src} alt={asset?.alt || asset?.caption || "微博图片"} loading="lazy" />}
        {label && <span className="social-media-kind">{label}</span>}
      </button>;
    })}
  </section>;
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

function structuredMediaPlacements(blocks: any[], assets: any[]) {
  const placements = new Map<number, any[]>();
  const contentIndexes = blocks
    .map((block, index) => (["paragraph", "heading", "list", "quote"].includes(String(block?.type || "").toLowerCase()) ? index : -1))
    .filter((index) => index >= 0);

  const blockText = (block: any) => {
    const type = String(block?.type || "").toLowerCase();
    if (type === "list") return (Array.isArray(block?.items) ? block.items : []).map((item: any) => typeof item === "string" ? item : item?.text || "").join(" ");
    return String(block?.text || "");
  };
  const add = (index: number, asset: any) => placements.set(index, [...(placements.get(index) || []), asset]);

  assets.forEach((asset, assetIndex) => {
    const context = normalizedLine(String(asset?.context_text || ""));
    let target = -1;
    if (context) {
      target = blocks.findIndex((block) => {
        const text = normalizedLine(blockText(block));
        return Boolean(text) && (text === context || (context.length >= 24 && (text.includes(context) || context.includes(text))));
      });
    }
    if (target < 0 && contentIndexes.length) {
      const slot = Math.min(contentIndexes.length - 1, Math.max(0, Math.round(((assetIndex + 1) / (assets.length + 1)) * (contentIndexes.length - 1))));
      target = contentIndexes[slot];
    }
    if (target >= 0) add(target, asset);
  });
  return placements;
}

function StructuredArticleBody({ blocks, media, anchors, selectedClaimId, onSelect }: { blocks: any[]; media: any[]; anchors: EvidenceAnchor[]; selectedClaimId: string | null; onSelect: (claim: any) => void }) {
  let paragraphIndex = 0;
  const mediaPlacements = structuredMediaPlacements(blocks, media);

  return <div className="reader-body structured-reader-body">
    {blocks.map((block, blockIndex) => {
      const type = String(block?.type || "").toLowerCase();
      let content: React.ReactNode = null;
      if (type === "heading") {
        const level = Number(block.level || 2);
        const text = String(block.text || "");
        if (level >= 4) content = <h4 className="reader-section-heading level-4"><BionicText text={text} /></h4>;
        else if (level === 3) content = <h3 className="reader-section-heading level-3"><BionicText text={text} /></h3>;
        else content = <h2 className="reader-section-heading level-2"><BionicText text={text} /></h2>;
      } else if (type === "paragraph") {
        const index = paragraphIndex++;
        content = <ReaderParagraph text={String(block.text || "")} index={index} anchors={anchors} selectedClaimId={selectedClaimId} onSelect={onSelect} />;
      } else if (type === "list") {
        const Tag = block.ordered ? "ol" : "ul";
        const items = Array.isArray(block.items) ? block.items : [];
        content = <Tag className="reader-structured-list">{items.map((item: any, itemIndex: number) => {
          const text = typeof item === "string" ? item : String(item?.text || "");
          const lead = typeof item === "object" ? String(item?.lead || "").trim() : "";
          const tail = lead && text.startsWith(lead) ? text.slice(lead.length).trimStart() : text;
          return <li key={`${blockIndex}-${itemIndex}`}>{lead && <strong className="reader-list-lead"><BionicText text={lead} /></strong>}{lead && tail ? " " : null}<BionicText text={tail} /></li>;
        })}</Tag>;
      } else if (type === "quote") {
        content = <blockquote className="reader-structured-quote"><BionicText text={String(block.text || "")} /></blockquote>;
      } else if (type === "table") {
        const headers = Array.isArray(block.headers) ? block.headers : [];
        const rows = Array.isArray(block.rows) ? block.rows : [];
        const width = Math.max(headers.length, ...rows.map((row: any[]) => Array.isArray(row) ? row.length : 0), 1);
        content = <div className="reader-table-scroll" role="region" aria-label="Article table" tabIndex={0}>
          <table className="reader-structured-table">
            {headers.length > 0 && <thead><tr>{Array.from({ length: width }).map((_, cellIndex) => <th key={`h-${cellIndex}`}><BionicText text={String(headers[cellIndex] || "")} /></th>)}</tr></thead>}
            <tbody>{rows.map((row: any[], rowIndex: number) => <tr key={`r-${rowIndex}`}>{Array.from({ length: width }).map((_, cellIndex) => <td key={`c-${rowIndex}-${cellIndex}`}><BionicText text={String((Array.isArray(row) ? row[cellIndex] : "") || "")} /></td>)}</tr>)}</tbody>
          </table>
        </div>;
      } else if (type === "image") {
        content = <ReaderMedia asset={{ type: "IMAGE", ...block }} />;
      }
      const placedMedia = mediaPlacements.get(blockIndex) || [];
      if (!content && !placedMedia.length) return null;
      return <React.Fragment key={`block-${blockIndex}`}>
        {content}
        {placedMedia.map((asset: any, mediaIndex: number) => <ReaderMedia asset={asset} key={`structured-media-${blockIndex}-${asset.embed_url || asset.cached_url || asset.url || mediaIndex}`} />)}
      </React.Fragment>;
    })}
  </div>;
}

function displayTitle(source?: SourceSummary) {
  const paperTitle = source?.raw_metadata?.paper_title;
  if (paperTitle) return String(paperTitle).trim();
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

type DspCompletion = { D: string; S: string; P: string; outcome: "AWARE" | "DROP" };

function dspGateOutcome(d: string, s: string, p: string): "AWARE" | "DROP" {
  return s === "MATERIAL" && (d === "IN" || p === "SALIENT") ? "AWARE" : "DROP";
}

function dspChoices(value: unknown, positive: string, negative: string) {
  return value == null ? [positive, negative] : [String(value)];
}

function dspComposition(event: any, awareness: any) {
  if (!event) return null;
  const states = event.component_states || {};
  const d = states.D ?? null;
  const s = states.S ?? null;
  const p = states.P ?? null;
  const rows: DspCompletion[] = [];
  for (const dc of dspChoices(d, "IN", "OUT")) {
    for (const sc of dspChoices(s, "MATERIAL", "NOT_MATERIAL")) {
      for (const pc of dspChoices(p, "SALIENT", "NOT_SALIENT")) {
        rows.push({ D: dc, S: sc, P: pc, outcome: dspGateOutcome(dc, sc, pc) });
      }
    }
  }
  const outcomes = Array.from(new Set(rows.map((row) => row.outcome)));
  const determined = outcomes.length === 1 ? outcomes[0] : null;
  const unknown = [d == null ? "D" : null, s == null ? "S" : null, p == null ? "P" : null].filter(Boolean) as string[];
  let explanation = "All three signals are known, so the gate can be evaluated directly.";
  if (s === "NOT_MATERIAL") {
    explanation = "S is decisive here. Because the event is not materially consequential, the AWARE gate is false regardless of D or P. Missing collective-attention evidence cannot change this decision.";
  } else if (s === "MATERIAL" && d === "IN") {
    explanation = "D and S already satisfy the gate. The event is inside your standing world and materially consequential, so P is not needed to determine AWARE.";
  } else if (s === "MATERIAL" && d === "OUT" && p == null) {
    explanation = "P is decision-critical here. With D outside your standing world, collective attention would decide whether this material event becomes AWARE or remains DROP.";
  } else if (determined && unknown.length) {
    explanation = `The missing ${unknown.join(" / ")} evidence is not decision-critical here: every valid completion leads to ${determined}.`;
  } else if (!determined && unknown.length) {
    explanation = `The missing ${unknown.join(" / ")} evidence can change the outcome, so the no-Delta gate is not logically determined yet.`;
  }
  let examples = rows;
  if (rows.length > 4) {
    if (determined) examples = [rows[0], rows[rows.length - 1]];
    else {
      const aware = rows.find((row) => row.outcome === "AWARE");
      const drop = rows.find((row) => row.outcome === "DROP");
      examples = [aware, drop].filter(Boolean) as DspCompletion[];
    }
  }
  return {
    formula: "AWARE iff S AND (D OR P)",
    explanation,
    rows,
    examples,
    determined,
    unknown,
    actual: event.disposition || awareness?.disposition || null,
  };
}

function normalizedLine(value: string) {
  return value.toLowerCase().replace(/[\s\p{P}\p{S}]+/gu, " ").trim();
}

function readerContentText(source?: SourceSummary) {
  const corrected = source?.raw_metadata?.display_content_text;
  return typeof corrected === "string" && corrected.trim() ? corrected : (source?.content_text || "");
}

function readerParagraphs(source?: SourceSummary) {
  const structured = articleBlocks(source);
  if (structured.length > 0) {
    return structured
      .filter((block) => block?.type === "paragraph")
      .map((block) => String(block.text || "").trim())
      .filter(Boolean);
  }
  const content = readerContentText(source);
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
  const paperWords = Number(source?.raw_metadata?.paper_word_count || 0);
  if (paperWords > 0) return Math.max(1, Math.round(paperWords / 230));
  const content = readerContentText(source);
  if (!content.trim()) return null;
  const cjk = (content.match(/[\u3400-\u9fff]/g) || []).length;
  const words = content.replace(/[\u3400-\u9fff]/g, " ").trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / 230 + cjk / 450));
}

function sourceExcerpt(source?: SourceSummary, length = 190) {
  const preferred = isPaperSource(source) ? source?.raw_metadata?.abstract : null;
  const text = String(preferred || source?.content_text || "").replace(/\s+/g, " ").trim();
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

function representativeSourceId(plan: any) {
  return plan?.representative_source_id || (plan?.candidate_type === "SOURCE" ? plan?.candidate_id : null);
}

function sourceForPlan(plan: any, sources: Record<string, SourceSummary>) {
  const id = representativeSourceId(plan);
  return id ? sources[id] : undefined;
}

function titleForPlan(plan: any, source?: SourceSummary) {
  if (plan?.candidate_type === "EVENT" && plan?.event?.title) return String(plan.event.title);
  return source ? displayTitle(source) : `${plan?.candidate_type || "Candidate"} ${plan?.candidate_id || ""}`;
}

function sourceFromAttentionCard(card: any): SourceSummary {
  return {
    id: card.id,
    source_type: card.source_type,
    title: card.title,
    canonical_url: card.canonical_url,
    content_text: card.excerpt,
    published_at: card.published_at,
    publisher: card.publisher,
    ingested_at: card.ingested_at,
    ingestion_method: card.ingestion_method,
    raw_metadata: {
      ...(card.presentation_metadata || {}),
      hero_image_url: card.hero_image_url,
      hero_image_cached_url: card.hero_image_url,
      hero_image_alt: card.hero_image_alt,
    },
  };
}

function planFromAttentionCard(card: any) {
  return {
    id: card.attention_plan_id,
    candidate_type: "EVENT",
    candidate_id: card.event_id,
    representative_source_id: card.id,
    disposition: card.disposition,
    created_at: card.attention_created_at,
    reason: card.reason,
    urgency: card.urgency,
    cognitive_budget_minutes: card.cognitive_budget_minutes,
  };
}

export default function AttentionPage() {
  const params = useSearchParams();
  const sourceId = params.get("source");
  const viewParam = params.get("view");
  const returnToRaw = params.get("returnTo");
  const returnTo = returnToRaw && returnToRaw.startsWith("/") && !returnToRaw.startsWith("//") ? returnToRaw : "/attention";
  const returnLabel = params.get("returnLabel") || (returnTo.startsWith("/inbox") ? "Inbox" : "Attention");
  const [plans, setPlans] = useState<any[]>([]);
  const [sources, setSources] = useState<Record<string, SourceSummary>>({});
  const [analysis, setAnalysis] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeAnalysisJob, setActiveAnalysisJob] = useState<any>(null);
  const [analysisStatusChecking, setAnalysisStatusChecking] = useState(false);
  const [jobSubmitting, setJobSubmitting] = useState(false);
  const busy = analysisStatusChecking || jobSubmitting || Boolean(
    activeAnalysisJob && ["QUEUED", "RUNNING"].includes(String(activeAnalysisJob.status || ""))
  );
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("CURRENT");
  const [query, setQuery] = useState("");
  const [detailView, setDetailView] = useState<"reader" | "inspector">("reader");
  const [activeParagraph, setActiveParagraph] = useState(0);
  const [readingProgress, setReadingProgress] = useState(0);
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const [selectedSourceDetail, setSelectedSourceDetail] = useState<SourceSummary | null>(null);
  const [sourceDetailLoading, setSourceDetailLoading] = useState(false);
  const [landscape, setLandscape] = useState<any>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [attentionCounts, setAttentionCounts] = useState<Record<string, number>>({});
  const [loadingMore, setLoadingMore] = useState(false);

  async function loadPlans(_force = false, append = false) {
    const params = new URLSearchParams({ limit: "30", disposition: filter });
    if (query.trim()) params.set("q", query.trim());
    if (append && nextCursor) params.set("cursor", nextCursor);
    const payload = await api<any>(`/user-space/attention?${params.toString()}`);
    const nextPlans = payload.items.map(planFromAttentionCard);
    const nextSources = payload.items.map(sourceFromAttentionCard);
    setPlans((current) => append ? [...current, ...nextPlans] : nextPlans);
    setSources((current) => {
      const incoming = Object.fromEntries(nextSources.map((source: SourceSummary) => [source.id, source]));
      return append ? { ...current, ...incoming } : incoming;
    });
    setAttentionCounts(payload.counts || {});
    setNextCursor(payload.next_cursor || null);
  }

  async function loadMoreAttention() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      await loadPlans(false, true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingMore(false);
    }
  }

  async function loadAnalysis(mode: "read" | "analyze" | "reprocess" = "read") {
    if (!sourceId) return;
    const targetSourceId = sourceId;
    if (mode === "read") {
      setAnalysis(await apiOrNull<any>(`/analysis/by-source/${targetSourceId}`));
      return;
    }
    if (activeAnalysisJob && ["QUEUED", "RUNNING"].includes(String(activeAnalysisJob.status || ""))) return;

    setError(null);
    setJobSubmitting(true);
    try {
      const job = await api<any>(`/analysis/jobs?reprocess=${mode === "reprocess" ? "true" : "false"}`, {
        method: "POST", body: JSON.stringify({ source_id: targetSourceId }),
      });
      setActiveAnalysisJob(job);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setJobSubmitting(false);
    }
  }


  useEffect(() => {
    if (sourceId) return;
    let cancelled = false;
    const timer = window.setTimeout(() => {
      loadPlans(false, false).catch((e) => { if (!cancelled) setError(String(e.message || e)); });
    }, query.trim() ? 140 : 0);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [sourceId, filter, query]);
  useEffect(() => {
    let cancelled = false;
    setSelectedSourceDetail(null);
    setLandscape(null);
    if (!sourceId) return () => { cancelled = true; };
    setSourceDetailLoading(true);
    Promise.all([
      api<SourceSummary>(`/sources/${sourceId}`),
      apiOrNull<any>(`/sources/${sourceId}/landscape`),
    ])
      .then(([source, world]) => {
        if (cancelled) return;
        setSelectedSourceDetail(source);
        setLandscape(world);
      })
      .catch(() => undefined)
      .finally(() => { if (!cancelled) setSourceDetailLoading(false); });
    return () => { cancelled = true; };
  }, [sourceId]);
  useEffect(() => {
    let cancelled = false;
    setAnalysis(null);
    setActiveAnalysisJob(null);
    setDetailView(viewParam === "system" ? "inspector" : "reader");
    if (!sourceId) return () => { cancelled = true; };

    setAnalysisStatusChecking(true);
    Promise.all([
      apiOrNull<any>(`/analysis/by-source/${sourceId}`),
      api<any>(`/analysis/jobs/source/${sourceId}/active`),
    ]).then(([existing, active]) => {
      if (cancelled) return;
      setAnalysis(existing);
      setActiveAnalysisJob(active?.active ? active.job : null);
    }).catch((e: unknown) => {
      if (!cancelled) setError(e instanceof Error ? e.message : String(e));
    }).finally(() => {
      if (!cancelled) setAnalysisStatusChecking(false);
    });
    return () => { cancelled = true; };
  }, [sourceId, viewParam]);

  useEffect(() => {
    const jobId = activeAnalysisJob?.id;
    if (!jobId || !sourceId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const poll = async () => {
      try {
        const job = await api<any>(`/analysis/jobs/${jobId}`);
        if (cancelled) return;
        setActiveAnalysisJob(job);
        if (job.status === "COMPLETED") {
          const completed = await apiOrNull<any>(`/analysis/by-source/${sourceId}`);
          if (cancelled) return;
          if (completed) setAnalysis(completed);
          setActiveAnalysisJob(null);
          const refreshedLandscape = await apiOrNull<any>(`/sources/${sourceId}/landscape`);
          if (!cancelled) setLandscape(refreshedLandscape);
          await loadPlans(true);
          return;
        }
        if (job.status === "FAILED") {
          setError(job.error || "RAOS analysis failed.");
          setActiveAnalysisJob(null);
          return;
        }
        timer = setTimeout(poll, 1200);
      } catch (e: unknown) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
        timer = setTimeout(poll, 2500);
      }
    };

    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [activeAnalysisJob?.id, sourceId]);

  const currentPlans = useMemo(() => {
    const latest = new Map<string, any>();
    for (const plan of plans) {
      const key = `${plan.candidate_type}:${plan.candidate_id}`;
      if (!latest.has(key)) latest.set(key, plan);
    }
    return Array.from(latest.values()).sort((a, b) => (RANK[a.disposition] ?? 9) - (RANK[b.disposition] ?? 9));
  }, [plans]);

  const shown = useMemo(() => currentPlans.filter((p) => {
    const source = sourceForPlan(p, sources);
    if (!source) return false;
    if (isSystemFixture(source)) return false;
    if (filter === "CURRENT" && p.disposition === "DROP") return false;
    if (filter !== "CURRENT" && p.disposition !== filter) return false;
    if (!query.trim()) return true;
    const title = titleForPlan(p, source);
    return `${title} ${p.reason || ""}`.toLowerCase().includes(query.toLowerCase());
  }), [currentPlans, filter, query, sources]);

  const counts = attentionCounts;
  const editorialShown = useMemo(() => [...shown].sort((a, b) =>
    timestampMs(sourceTimeValue(sourceForPlan(b, sources), b.created_at)) - timestampMs(sourceTimeValue(sourceForPlan(a, sources), a.created_at))
  ), [shown, sources]);
  const selectedSource = sourceId ? (selectedSourceDetail || sources[sourceId]) : undefined;

  useEffect(() => {
    if (!sourceId || detailView !== "reader") return;
    const update = () => {
      const paperBody = document.querySelector<HTMLElement>(".paper-body");
      const body = paperBody || document.querySelector<HTMLElement>(".reader-body");
      const items = paperBody
        ? Array.from(paperBody.querySelectorAll<HTMLElement>(":scope > section.ltx_section"))
        : Array.from(document.querySelectorAll<HTMLElement>(".reader-paragraph"));
      if (!body || items.length === 0) return;
      const focusY = window.innerHeight * 0.38;
      let bestIndex = 0; let bestDistance = Number.POSITIVE_INFINITY;
      items.forEach((item, index) => {
        const distance = Math.abs(item.getBoundingClientRect().top - focusY);
        if (distance < bestDistance) { bestDistance = distance; bestIndex = paperBody ? index : Number(item.dataset.readerIndex || 0); }
      });
      setActiveParagraph(bestIndex);
      const rect = body.getBoundingClientRect();
      const consumed = Math.max(0, Math.min(rect.height, focusY - rect.top));
      setReadingProgress(rect.height > 0 ? consumed / rect.height : 0);
    };
    update(); window.addEventListener("scroll", update, { passive: true }); window.addEventListener("resize", update);
    return () => { window.removeEventListener("scroll", update); window.removeEventListener("resize", update); };
  }, [sourceId, detailView, analysis, selectedSourceDetail]);

  async function afterCommit() {
    await loadPlans(true);
    if (sourceId) {
      const existing = await apiOrNull<any>(`/analysis/by-source/${sourceId}`);
      if (existing) setAnalysis(existing);
    }
  }

  function scrollToPaperSection(sectionId: string) {
    const node = document.getElementById(sectionId);
    if (!node) return;
    node.scrollIntoView({ behavior: "smooth", block: "start" });
    try { history.replaceState(null, "", `#${sectionId}`); } catch {}
  }

  if (sourceId) {
    const plan = analysis ? (analysis.latest_attention_plan || analysis.attention_plan) : null;
    const awareness = analysis?.no_delta_awareness;
    const awarenessEvent = awareness?.events?.find((event: any) => event?.event_id === awareness?.witness_event_id) || awareness?.events?.[0];
    const composition = awareness?.applicable ? dspComposition(awarenessEvent, awareness) : null;
    const operation = analysis?.update?.operation || plan?.update?.operation || null;
    const paperMode = isPaperSource(selectedSource) && Boolean(selectedSource?.raw_metadata?.paper_profile);
    const paperMeta = selectedSource?.raw_metadata || {};
    const paperAuthorList = paperAuthors(selectedSource);
    const paperAffiliationList = paperAffiliations(selectedSource);
    const paperSectionList = paperSections(selectedSource);
    const paragraphs = readerParagraphs(selectedSource);
    const minutes = readingMinutes(selectedSource);
    const topMatch = analysis?.kernel_matches?.[0];
    const claims = analysis?.claims || [];
    const structuredBlocks = articleBlocks(selectedSource);
    const structuredMedia = structuredBlocks.length > 0 ? mediaAssets(selectedSource).filter((asset) => String(asset?.type || "").toUpperCase() !== "IMAGE") : [];
    const socialMode = isSocialSource(selectedSource);
    const socialMedia = socialMode ? socialMediaAssets(selectedSource) : [];
    const readerEvidenceAnchors = paperMode ? [] : selectReaderEvidenceAnchors(paragraphs, claims);
    const inlineMedia = paperMode || socialMode || structuredBlocks.length > 0 ? [] : mediaAssets(selectedSource);
    const activeAnchor = paperMode ? null : readerEvidenceAnchors.find((anchor) => anchor.paragraphIndex === activeParagraph);
    const activeClaim = paperMode ? null : (claims.find((claim: any) => claim.id === selectedClaimId) || activeAnchor?.claim || null);
    const progressPercent = Math.max(0, Math.min(100, Math.round(readingProgress * 100)));
    const progressUnits = paperMode ? paperSectionList.length : paragraphs.length;
    const referenceSources = landscape?.references?.sources || [];
    const resolvedReferenceSources = referenceSources.filter((item: any) => !item.stub);
    const literalReferenceStubs = referenceSources.filter((item: any) => item.stub);

    return (
      <>
        <div className="detail-toolbar">
          <Link className="back-link" href={returnTo}>← Back to {returnLabel}</Link>
          <div className="view-switch" role="tablist" aria-label="Detail view">
            <button className={detailView === "reader" ? "active" : ""} onClick={() => setDetailView("reader")}>Reader</button>
            <button className={detailView === "inspector" ? "active" : ""} onClick={() => setDetailView("inspector")}>RAOS Inspector</button>
          </div>
        </div>

        {error && <p className="error">{error}</p>}
        {!selectedSource && !error && <div className="empty-state">Loading source…</div>}

        {selectedSource && detailView === "reader" && (
          <div className="reader-layout">
            <article className="reader-article">
              <header className="reader-header">
                <div className="reader-source-line">
                  {paperMode && <span className="paper-type-mark">PAPER</span>}
                  <span>{sourceOrigin(selectedSource)}</span>
                  {!paperMode && sourceAuthor(selectedSource) && <><span>·</span><span>{sourceAuthor(selectedSource)}</span></>}
                  {sourceTime(selectedSource) && <><span>·</span><span>{sourceTime(selectedSource)}</span></>}
                  {minutes && <><span>·</span><span>{minutes} min read</span></>}
                </div>
                <h1>{displayTitle(selectedSource)}</h1>
                {paperMode && paperAuthorList.length > 0 && <div className="paper-authors">{paperAuthorList.join(", ")}</div>}
                {paperMode && paperAffiliationList.length > 0 && <details className="paper-affiliations"><summary>{paperAuthorList.length} authors · {paperAffiliationList.length} affiliations</summary><div>{paperAffiliationList.map((item: string) => <span key={item}>{item}</span>)}</div></details>}
                <div className="reader-header-decision-row">
                  {plan ? <div className={`reader-status reader-header-status ${plan.disposition}`}>
                    <span className={`human-state ${plan.disposition}`} title={`RAOS state: ${plan.disposition}`}>{attentionLabel(plan.disposition)}</span>
                    <strong>{actionCopy(plan.disposition)}</strong>
                  </div> : <div className="reader-status reader-header-status UNANALYZED">
                    <span className="badge">UNANALYZED</span>
                    <strong>{busy ? "RAOS is analyzing in the background. You can keep reading." : "Available to read. RAOS has not analyzed this source yet."}</strong>
                    <button className="ghost" disabled={busy} onClick={() => loadAnalysis("analyze")}>{busy ? "Analyzing…" : "Analyze with RAOS"}</button>
                  </div>}
                  {paperMode ? <div className="paper-primary-actions">
                    {paperMeta.pdf_url && <a className="button-link paper-action-primary" href={paperMeta.pdf_url} target="_blank" rel="noreferrer">PDF ↗</a>}
                    {paperMeta.abs_url && <a className="button-link ghost" href={paperMeta.abs_url} target="_blank" rel="noreferrer">arXiv ↗</a>}
                    {paperMeta.html_url && <a className="button-link ghost" href={paperMeta.html_url} target="_blank" rel="noreferrer">HTML ↗</a>}
                  </div> : selectedSource?.canonical_url && <a className="button-link ghost reader-original-link" href={selectedSource.canonical_url} target="_blank" rel="noreferrer">Open original ↗</a>}
                </div>
              </header>

              {!paperMode && !socialMode && heroImage(selectedSource) && (
                <figure className="reader-hero-media">
                  <img src={heroImage(selectedSource)} alt={heroImageAlt(selectedSource)} loading="eager" />
                  {selectedSource?.raw_metadata?.hero_image_alt && <figcaption>{selectedSource.raw_metadata.hero_image_alt}</figcaption>}
                </figure>
              )}

              {selectedSource?.raw_metadata?.feed_fallback && <div className="reader-status feed-fallback-status">
                <span className="badge AWARE">FEED SUMMARY</span>
                <strong>The publisher page was unavailable to the crawler, so RAOS preserved the publisher-provided RSS summary instead.</strong>
                {selectedSource.canonical_url && <a href={selectedSource.canonical_url} target="_blank" rel="noreferrer">Open original ↗</a>}
              </div>}

              {selectedSource?.raw_metadata?.publisher_dynamic_media_status && selectedSource.raw_metadata.publisher_dynamic_media_status !== "captured" && <div className="reader-status media-integrity-status">
                <span className="badge">MEDIA PARTIAL</span>
                <strong>Some publisher media may not be included in this saved view.</strong>
                {selectedSource.canonical_url && <a href={selectedSource.canonical_url} target="_blank" rel="noreferrer">Open original ↗</a>}
              </div>}

              {paperMode ? <>
                {paperMeta.abstract && <section className="paper-abstract">
                  <div className="eyebrow">Abstract</div>
                  <p><BionicText text={String(paperMeta.abstract)} /></p>
                </section>}
                {paperMeta.paper_body_html && paperSectionList.length > 0 && <nav className="paper-toc" aria-label="Paper contents">
                  <div className="paper-toc-label"><span className="eyebrow">On this paper</span><span>{paperSectionList.length} sections</span></div>
                  <div className="paper-toc-items">{paperSectionList.map((section: any, sectionIndex: number) => <button type="button" className={activeParagraph === sectionIndex ? "active" : ""} onClick={() => scrollToPaperSection(section.id)} key={section.id}>{section.title}</button>)}</div>
                </nav>}
                {paperMeta.paper_body_html ? <div className="paper-body" dangerouslySetInnerHTML={{__html: String(paperMeta.paper_body_html)}} /> : sourceDetailLoading ? <div className="paper-loading"><span className="eyebrow">Loading paper</span><p>Fetching the full arXiv HTML reading view…</p></div> : <div className="reader-empty paper-abstract-only">
                  <div className="eyebrow">Abstract-only source</div>
                  <h3>arXiv does not provide a full HTML reading view for this version.</h3>
                  <p>The abstract and scholarly metadata are preserved here. Use PDF or arXiv for the complete paper.</p>
                </div>}
              </> : structuredBlocks.length > 0 ? (
                <StructuredArticleBody
                  blocks={structuredBlocks}
                  media={structuredMedia}
                  anchors={readerEvidenceAnchors}
                  selectedClaimId={selectedClaimId}
                  onSelect={(claim) => setSelectedClaimId(claim.id)}
                />
              ) : paragraphs.length > 0 ? (
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

              {!paperMode && socialMode && socialMedia.length > 0 && <SocialMediaGallery assets={socialMedia} />}

              {landscape && ((landscape.references?.count || 0) > 0 || (landscape.coverage?.other_source_count || 0) > 0 || (landscape.related?.count || 0) > 0) && (
                <section className="reader-landscape" aria-label="Source world context">
                  <div className="reader-landscape-head">
                    <div>
                      <div className="eyebrow">World context</div>
                      <h3>{landscape.event?.title || "How this source sits in the information landscape"}</h3>
                    </div>
                    {landscape.coverage?.source_count > 1 && <span className="landscape-count">{landscape.coverage.source_count} sources</span>}
                  </div>

                  {resolvedReferenceSources.length > 0 && <div className="landscape-group">
                    <div className="landscape-group-title">
                      <strong>Referenced sources · {resolvedReferenceSources.length}</strong>
                      <span>Known RAOS Sources explicitly linked from this article. CITES does not by itself prove original source, derivation, independence, or same-event identity.</span>
                    </div>
                    <div className="landscape-source-list">
                      {resolvedReferenceSources.map((item: any) => (
                        item.canonical_url ? (
                          <a className="landscape-source-row" key={item.source_id} href={item.canonical_url} target="_blank" rel="noreferrer">
                            <span>
                              <strong>{item.title || item.publisher || item.canonical_url || "Referenced source"}</strong>
                              <small>{item.publisher || item.source_type || "Source"} · explicit link</small>
                            </span>
                            <span aria-hidden="true">↗</span>
                          </a>
                        ) : (
                          <Link
                            className="landscape-source-row"
                            key={item.source_id}
                            href={`/attention?source=${item.source_id}&returnTo=${encodeURIComponent(returnTo)}&returnLabel=${encodeURIComponent(returnLabel)}`}
                          >
                            <span>
                              <strong>{item.title || item.publisher || "Referenced source"}</strong>
                              <small>{item.publisher || item.source_type || "Source"} · explicit link</small>
                            </span>
                            <span aria-hidden="true">→</span>
                          </Link>
                        )
                      ))}
                    </div>
                  </div>}

                  {literalReferenceStubs.length > 0 && <details className="landscape-related">
                    <summary>Other explicit links · {literalReferenceStubs.length}</summary>
                    <p>Literal links preserved for provenance. This may include navigation, policy, commerce, author, or unresolved external links; they are not promoted to world context until resolved.</p>
                    <div className="landscape-source-list">
                      {literalReferenceStubs.map((item: any) => (
                        item.canonical_url ? (
                          <a className="landscape-source-row" key={item.source_id} href={item.canonical_url} target="_blank" rel="noreferrer">
                            <span>
                              <strong>{item.title || item.publisher || item.canonical_url || "Explicit link"}</strong>
                              <small>{item.publisher || item.source_type || "URL"} · literal link</small>
                            </span>
                            <span aria-hidden="true">↗</span>
                          </a>
                        ) : null
                      ))}
                    </div>
                  </details>}

                  {(landscape.references?.count || 0) > 0 && <div className="landscape-audit-line">
                    Provenance authority: {landscape.references.count} literal explicit-link relations preserved; only resolved Sources are promoted above.
                  </div>}

                  {(landscape.coverage?.other_source_count || 0) > 0 && <div className="landscape-group">
                    <div className="landscape-group-title">
                      <strong>Coverage · {landscape.coverage.source_count} sources</strong>
                      <span>Same world event. Shown for provenance and cross-source context, not as extra events.</span>
                    </div>
                    <div className="landscape-source-list">
                      {landscape.coverage.sources.map((item: any) => (
                        <Link
                          className="landscape-source-row"
                          key={item.source_id}
                          href={`/attention?source=${item.source_id}&returnTo=${encodeURIComponent(returnTo)}&returnLabel=${encodeURIComponent(returnLabel)}`}
                        >
                          <span>
                            <strong>{item.title || item.publisher || "Source"}</strong>
                            <small>{item.publisher || "Unknown publisher"} · {String(item.relationship || "REPORTS_SAME_EVENT").replaceAll("_", " ").toLowerCase()}</small>
                          </span>
                          <span aria-hidden="true">→</span>
                        </Link>
                      ))}
                    </div>
                    {landscape.coverage?.independence && <div className="landscape-audit-line">
                      Graph view: {landscape.coverage.independence.independent_sources} independent · {landscape.coverage.independence.secondary_reports} secondary
                    </div>}
                  </div>}

                  {(landscape.related?.count || 0) > 0 && <details className="landscape-related">
                    <summary>Related reading · {landscape.related.count}</summary>
                    <p>Different event or claim context. Kept folded so RAOS does not turn reading into an endless recommendation loop.</p>
                    <div className="landscape-source-list">
                      {landscape.related.sources.map((item: any) => (
                        <Link
                          className="landscape-source-row"
                          key={item.source_id}
                          href={`/attention?source=${item.source_id}&returnTo=${encodeURIComponent(returnTo)}&returnLabel=${encodeURIComponent(returnLabel)}`}
                        >
                          <span>
                            <strong>{item.title || item.publisher || "Source"}</strong>
                            <small>{item.publisher || "Unknown publisher"} · {String(item.relationship || "RELATED").replaceAll("_", " ").toLowerCase()}</small>
                          </span>
                          <span aria-hidden="true">→</span>
                        </Link>
                      ))}
                    </div>
                  </details>}
                </section>
              )}
            </article>

            <aside className={`reader-rail ${readingProgress > 0.02 ? "is-reading" : ""}`}>
              {plan ? <>
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
              </> : <section className="reader-note primary-context unanalyzed-note">
                <div className="eyebrow">Not analyzed yet</div>
                <p>This source is in your library, but RAOS has not run cognition on it. Reading is free; analyze only when you want a relevance judgment.</p>
                <button disabled={busy} onClick={() => loadAnalysis("analyze")}>{busy ? "Analyzing…" : "Analyze with RAOS"}</button>
              </section>}

              {readingProgress > 0.01 && <section className="reader-progress-card">
                <div className="eyebrow">Reading</div>
                <div className="reader-progress-track"><span style={{width: `${progressPercent}%`}} /></div>
                <div className="reader-progress-meta"><span>{progressPercent}% through {paperMode ? "paper" : "article"}</span><span>{paperMode ? "Section" : "¶"} {Math.min(activeParagraph + 1, Math.max(1, progressUnits))} / {Math.max(1, progressUnits)}</span></div>
                {paperMode && paperSectionList[activeParagraph]?.title && <strong className="paper-current-section">{paperSectionList[activeParagraph].title}</strong>}
              </section>}

              {readingProgress > 0.01 && activeClaim && <section className="reader-evidence-card">
                <div className="eyebrow">RAOS evidence near here</div>
                <h4>{activeClaim.claim_type || "Claim"}</h4>
                <p><BionicText text={claimDisplayText(activeClaim)} /></p>
                <button onClick={() => setDetailView("inspector")}>Open in Inspector →</button>
              </section>}

              {analysis && plan && <button className="inspector-entry" onClick={() => setDetailView("inspector")}>
                <span>Inspect RAOS decision</span>
                <small>See cognition, evidence, D/S/P, Kernel mapping, and pipeline trace</small>
              </button>}
            </aside>
          </div>
        )}


        {selectedSource && !analysis && detailView === "inspector" && (
          <div className="empty-state inspector-unanalysed">
            <div className="eyebrow">Operating system view</div>
            <h2>No AnalysisRun exists for this source.</h2>
            <p>RAOS has preserved the Source but has intentionally not spent cognition budget on it yet.</p>
            <button disabled={busy} onClick={() => loadAnalysis("analyze")}>{busy ? "Analyzing…" : "Analyze with RAOS"}</button>
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
                    {composition && <div className={`dsp-composition ${composition.determined ? composition.determined.toLowerCase() : "unresolved"}`}>
                      <div className="dsp-composition-head">
                        <div><span>Decision composition</span><strong>Why these signals become {composition.actual || plan.disposition}</strong></div>
                        <code>{composition.formula}</code>
                      </div>
                      <p>{composition.explanation}</p>
                      <div className="dsp-completion-grid">
                        {composition.examples.map((row: DspCompletion, index: number) => <div className="dsp-completion-row" key={`${row.D}-${row.S}-${row.P}-${index}`}>
                          <span>D = <b>{row.D}</b></span>
                          <span>S = <b>{row.S}</b></span>
                          <span>P = <b>{row.P}</b></span>
                          <span className="dsp-arrow">→</span>
                          <strong className={`dsp-outcome ${row.outcome}`}>{row.outcome}</strong>
                        </div>)}
                      </div>
                      {composition.rows.length > composition.examples.length && <small>RAOS checked {composition.rows.length} valid completions of the unknown signals. {composition.determined ? `All lead to ${composition.determined}.` : "At least two lead to different outcomes."}</small>}
                    </div>}
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

                {awareness && awareness.applicable === false && (
                  <section className="section card">
                    <div className="eyebrow">No-Delta awareness path</div>
                    <h3>D / S / P was not applicable to this source</h3>
                    <p className="muted">RAOS found no canonical cognitive effect, but it also could not legally route this source into an audited event for the D / S / P branch.</p>
                    <div className="reason-grid">
                      <div className="signal-card"><strong>D · Standing world</strong><span>Not evaluated: no routable audited event.</span><span className="signal-state">NOT EVALUATED</span></div>
                      <div className="signal-card"><strong>S · Material consequence</strong><span>Not evaluated: no routable audited event.</span><span className="signal-state">NOT EVALUATED</span></div>
                      <div className="signal-card"><strong>P · Collective attention</strong><span>Not evaluated: no routable audited event.</span><span className="signal-state">NOT EVALUATED</span></div>
                    </div>
                    <div className="technical-body no-delta-not-applicable">
                      <p><strong>Why:</strong> {awareness.reason || "The audited event projection was not eligible for D / S / P evaluation."}</p>
                      <p><strong>Decision consequence:</strong> No canonical cognitive effect existed, and the no-Delta branch had no legal event to promote into situational awareness.</p>
                    </div>
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
                        <div className="trace-block">
                          <h4>AnalysisRun</h4>
                          <p>provider {analysis.analysis_run?.provider_type} · {analysis.analysis_run?.status}</p>
                          <p>strategy {plan.score_debug?.decision_strategy?.strategy_id || "unknown"}<br/>version {plan.score_debug?.decision_strategy?.version || "unknown"}</p>
                          <p>authority {analysis.execution_authority?.purpose || analysis.execution_snapshot?.execution_context?.purpose || "unknown"} · {analysis.execution_authority?.attestation?.status || analysis.execution_snapshot?.execution_context?.attestation?.status || "unknown"}</p>
                          <p>pipeline {analysis.analysis_run?.pipeline_version}<br/>extractor {analysis.analysis_run?.extractor_version}<br/>matcher {analysis.analysis_run?.matcher_version}<br/>prompt {analysis.analysis_run?.prompt_version}</p>
                        </div>
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
        <div><div className="eyebrow">Attention</div><h1 className="page-title">Your filtered world.</h1><p className="page-subtitle">One world event, one current attention state. Read the representative source; RAOS keeps the evidence bundle behind it.</p></div>
        <Link className="button-link ghost" href="/inbox">Add source</Link>
      </header>
      {error && <p className="error">{error}</p>}

      <div className="section-heading">
        <div className="filter-bar">
          {FILTERS.map((value) => <button className={filter === value ? "filter-chip active" : "filter-chip"} key={value} onClick={() => setFilter(value)}>{value === "CURRENT" ? "Current" : attentionLabel(value)} · {counts[value] || 0}</button>)}
        </div>
        <input className="search-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search current attention…" />
      </div>

      {shown.length === 0 && <div className="empty-state">No current attention items match this view.</div>}
      {shown.length > 0 && (
        <div className={filter === "CURRENT" && !query.trim() ? "attention-newsroom" : "attention-card-grid"}>
          {editorialShown.map((p, index) => {
            const source = sourceForPlan(p, sources);
            const title = titleForPlan(p, source);
            const when = sourceTimeValue(source, p.created_at);
            const newsroom = filter === "CURRENT" && !query.trim();
            const readingSourceId = representativeSourceId(p);
            if (!source || !readingSourceId) return null;
            return (
              <Link className={`${newsroom && index === 0 ? "attention-lead" : "attention-story-card"} disposition-${p.disposition}`} href={`/attention?source=${readingSourceId}`} key={p.id}>
                {heroImage(source) && <img className="story-visual" src={heroImage(source)} alt={heroImageAlt(source)} loading="lazy" />}
                <div className="story-kicker"><span className={`human-state ${p.disposition}`} title={`RAOS state: ${p.disposition}`}>{attentionLabel(p.disposition)}</span><span>{sourceOrigin(source)}</span>{when && <><span>·</span><span title={formatBeijingTime(when)}>{formatRelativeTime(when)}</span></>}</div>
                <h2>{title}</h2>
                <p>{sourceExcerpt(source, newsroom && index === 0 ? 300 : 165)}</p>
                <div className="story-footer"><strong>{actionCopy(p.disposition)}</strong><span>Read →</span></div>
              </Link>
            );
          })}
        </div>
      )}
      {nextCursor && <div className="library-more"><button className="ghost" disabled={loadingMore} onClick={loadMoreAttention}>{loadingMore ? "Loading…" : "Show 30 more"}</button></div>}
    </>
  );
}
