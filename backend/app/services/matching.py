from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from app.models.kernel import KernelNode
from app.services.extraction import ExtractionResult

TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?")

STOP = {
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "with", "is", "are",
    "be", "as", "by", "at", "from", "that", "this", "it", "its", "may", "not",
}


def tokenize(text: str) -> set[str]:
    return {t for t in TOKEN_RE.findall(text.lower()) if t not in STOP and len(t) > 2}


def node_text(node: KernelNode) -> str:
    payload = node.payload or {}
    bits = [node.title or ""]
    for key in ("proposition", "scope", "description", "rationale", "text"):
        if payload.get(key):
            bits.append(str(payload[key]))
    return " ".join(bits)


@dataclass
class KernelMatch:
    node_id: UUID
    node_type: str
    title: str | None
    score: float
    reason: str
    structural: bool = False
    relevance_type: str = "TOPIC"


def _overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = a & b
    return len(inter) / max(1, min(len(a), len(b)))


def _relevance_type(node_type: str) -> str:
    kind = str(node_type or "").upper()
    if kind == "BOTTLENECK":
        return "BOTTLENECK"
    if kind == "DECISION":
        return "DECISION"
    return "TOPIC"


def match_kernel(extraction: ExtractionResult, nodes: list[KernelNode], extra_text: str = "") -> list[KernelMatch]:
    """Lexical Locate. Prefer recall; do not interpret cognitive update here."""
    blob = " ".join(
        [extra_text]
        + [c.text for c in extraction.claims]
        + [o.text for o in extraction.observations]
        + [i.text for i in extraction.inferences]
    )
    cand_tokens = tokenize(blob)
    matches: list[KernelMatch] = []
    for node in nodes:
        if node.deleted_at is not None:
            continue
        ntext = node_text(node)
        score = _overlap(cand_tokens, tokenize(ntext))
        if score < 0.28:
            continue
        matches.append(
            KernelMatch(
                node_id=node.id,
                node_type=node.node_type,
                title=node.title,
                score=round(min(score, 1.0), 4),
                reason="lexical overlap with kernel node",
                structural=False,
                relevance_type=_relevance_type(node.node_type),
            )
        )
    matches.sort(key=lambda m: m.score, reverse=True)
    return matches
