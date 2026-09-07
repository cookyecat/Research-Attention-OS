"""Semantic Evidence Packet v0.1 — bounded explicit dossier for the Auditor.

Purpose:
Improve what is explicitly presented to Semantic Evidence Auditor v0.1.1 without expanding
Auditor authority.

Packet policy:
- keep the Sensor's existing primary excerpts;
- optionally add the full already-cited paragraph/page container;
- add deterministic source metadata;
- never retrieve adjacent paragraphs/pages;
- never search for replacement evidence;
- never rewrite or repair semantic objects.

This is evidence packaging, not semantic repair.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Literal

from eval.live.semantic_source_loader_v0_1 import LoadedSemanticSource

PACKET_VERSION = "semantic-evidence-packet-v0.1"

EvidenceKind = Literal["PRIMARY_EXCERPT", "CITATION_CONTEXT", "SOURCE_METADATA"]


@dataclass(frozen=True)
class EvidencePacketItemV0_1:
    evidence_kind: EvidenceKind
    source_id: str
    support_pointer: str
    support_excerpt: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)

    def as_auditor_evidence(self) -> dict[str, str]:
        """Project to the existing v0.1.1 Auditor input contract."""
        return {
            "source_id": self.source_id,
            "support_pointer": self.support_pointer,
            "support_excerpt": self.support_excerpt,
        }


_MARKER_RE = re.compile(r"^\[(PARA|PAGE) (\d{4})\]\n", re.MULTILINE)


def _containers(rendered_text: str) -> dict[str, str]:
    """Return exact already-rendered PARA/PAGE container bodies keyed by `PARA 0001`, etc."""
    matches = list(_MARKER_RE.finditer(rendered_text))
    out: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(rendered_text)
        key = f"{match.group(1)} {match.group(2)}"
        out[key] = rendered_text[start:end].strip()
    return out


def resolve_cited_container(source: LoadedSemanticSource, support_pointer: str) -> str | None:
    """Resolve only the exact cited paragraph/page container; never adjacent context."""
    pointer = str(support_pointer or "").strip()
    return _containers(source.rendered_text).get(pointer)


def source_metadata_excerpt(source: LoadedSemanticSource) -> str:
    return (
        f"path={source.path}; media_type={source.media_type}; "
        f"published_at={source.published_at}; updated_at={source.updated_at}; "
        f"captured_at={source.captured_at}"
    )


def build_evidence_packet_v0_1(
    *,
    source: LoadedSemanticSource,
    primary_evidence: list[dict[str, Any]],
) -> tuple[list[EvidencePacketItemV0_1], list[str]]:
    """Build a bounded packet from existing citations plus deterministic metadata.

    Citation context is limited to the full container named by the existing support_pointer.
    No neighboring paragraph/page is retrieved. Containers exceeding the current Auditor
    excerpt bound are omitted explicitly rather than silently truncated.
    """
    packet: list[EvidencePacketItemV0_1] = []
    notes: list[str] = []
    seen: set[tuple[str, str, str]] = set()

    for raw in primary_evidence:
        source_id = str(raw.get("source_id") or "").strip()
        pointer = str(raw.get("support_pointer") or "").strip()
        excerpt = str(raw.get("support_excerpt") or "").strip()
        if source_id != source.source_id:
            raise ValueError(
                f"packet source mismatch: evidence={source_id!r}, loaded={source.source_id!r}"
            )
        if not pointer or not excerpt:
            raise ValueError("primary evidence requires support_pointer and support_excerpt")

        primary = EvidencePacketItemV0_1(
            evidence_kind="PRIMARY_EXCERPT",
            source_id=source_id,
            support_pointer=pointer,
            support_excerpt=excerpt,
        )
        key = (primary.evidence_kind, primary.support_pointer, primary.support_excerpt)
        if key not in seen:
            packet.append(primary)
            seen.add(key)

        container = resolve_cited_container(source, pointer)
        if container is None:
            notes.append(f"citation_container_unresolved:{pointer}")
            continue
        if container == excerpt:
            continue
        if len(container) > 1600:
            notes.append(f"citation_context_omitted_too_long:{pointer}:{len(container)}")
            continue

        context = EvidencePacketItemV0_1(
            evidence_kind="CITATION_CONTEXT",
            source_id=source_id,
            support_pointer=f"{pointer} [FULL CITED CONTAINER]",
            support_excerpt=container,
        )
        key = (context.evidence_kind, context.support_pointer, context.support_excerpt)
        if key not in seen:
            packet.append(context)
            seen.add(key)

    metadata = EvidencePacketItemV0_1(
        evidence_kind="SOURCE_METADATA",
        source_id=source.source_id,
        support_pointer="TRUSTED_SOURCE_METADATA",
        support_excerpt=source_metadata_excerpt(source),
    )
    key = (metadata.evidence_kind, metadata.support_pointer, metadata.support_excerpt)
    if key not in seen:
        packet.append(metadata)

    return packet, notes


def packet_to_auditor_evidence(
    packet: list[EvidencePacketItemV0_1],
) -> list[dict[str, str]]:
    return [item.as_auditor_evidence() for item in packet]


def packet_kind_counts(packet: list[EvidencePacketItemV0_1]) -> dict[str, int]:
    counts = {"PRIMARY_EXCERPT": 0, "CITATION_CONTEXT": 0, "SOURCE_METADATA": 0}
    for item in packet:
        counts[item.evidence_kind] += 1
    return counts
