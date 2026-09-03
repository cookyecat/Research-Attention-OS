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


# Locate-only measurement cues. Impact still decides whether cognition changes.
MEASUREMENT_LOCATE_CUES = (
    "profiler",
    "torch.profiler",
    "cuda",
    "kernel launch",
    "perfetto",
    "overhead-bound",
    "耗时",
    "延迟",
    "性能剖析",
    "瓶颈",
)
LOCATE_MEASUREMENT_EXPAND = (
    " latency energy evaluation bottleneck high-frequency embodied control"
)


def query_has_measurement_locate_cues(text: str) -> bool:
    low = (text or "").lower()
    return any(cue in low for cue in MEASUREMENT_LOCATE_CUES)


def expand_locate_query(query_text: str) -> str:
    """Inject English measurement tokens so lexical/embedding Locate can reach BT1."""
    text = query_text or ""
    if not text or not query_has_measurement_locate_cues(text):
        return text
    if "latency energy evaluation bottleneck" in text.lower():
        return text
    return text + LOCATE_MEASUREMENT_EXPAND


def backfill_measurement_bottleneck_matches(
    matches: list[KernelMatch],
    candidates: list[KernelNode],
    query_text: str,
) -> list[KernelMatch]:
    """Keep a retrieved latency/evaluation Bottleneck that the matcher omitted.

    Locate prefers recall. Impact still filters false-positive updates.
    """
    if not query_has_measurement_locate_cues(query_text):
        return matches
    have = {m.node_id for m in matches}
    extra: list[KernelMatch] = []
    for node in candidates:
        if node.id in have or node.deleted_at is not None:
            continue
        if str(node.node_type or "").upper() != "BOTTLENECK":
            continue
        nlow = node_text(node).lower()
        if not any(k in nlow for k in ("latency", "energy", "evaluation", "bottleneck")):
            continue
        extra.append(
            KernelMatch(
                node_id=node.id,
                node_type=node.node_type,
                title=node.title,
                score=0.45,
                reason="locate recall: measurement/profiler write-up near a latency-evaluation bottleneck",
                structural=False,
                relevance_type="BOTTLENECK",
            )
        )
    return matches + extra


EQUITY_STRUCTURE = {
    "equity", "minority", "ownership", "shareholder", "employment", "employee",
    "contract", "investment", "investor", "shares", "role",
}
EMBODIED_MOTOR = {
    "embodied", "motor", "latency", "energy", "control", "humanoid", "robot",
    "folding", "high-frequency", "temporal", "end-to-end", "hierarchical",
}
COLLECTIVE = {
    "swarm", "multi-agent", "world-model", "world", "collective", "shared",
    "orbit", "bodies", "decentralized", "communication",
}


def match_kernel(extraction: ExtractionResult, nodes: list[KernelNode], extra_text: str = "") -> list[KernelMatch]:
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
        ntokens = tokenize(ntext)
        score = _overlap(cand_tokens, ntokens)
        # Phrase bonuses
        reason_bits = []
        low = blob.lower()
        nlow = ntext.lower()
        if node.node_type == "DECISION" and (EQUITY_STRUCTURE & cand_tokens) and (EQUITY_STRUCTURE & ntokens):
            score = max(score, 0.82)
            reason_bits.append("structural analogy: equity ownership vs employment/role")
            matches.append(
                KernelMatch(
                    node_id=node.id,
                    node_type=node.node_type,
                    title=node.title,
                    score=score,
                    reason="; ".join(reason_bits) or "lexical overlap",
                    structural=True,
                    relevance_type="STRUCTURAL",
                )
            )
            continue
        robotish = any(
            k in low
            for k in ("folding", "agent brain", "humanoid", "embodied", "motor", "high-frequency", "control loop")
        )
        if robotish and any(k in nlow for k in ("motor", "embodied", "latency", "end-to-end", "humanoid", "intelligence")):
            score = max(score, 0.7)
            reason_bits.append("embodied/motor control overlap")
        if any(k in low for k in ("swarm", "collective", "world model", "multi-agent", "shared world", "one world", "many bodies", "orbit")) and any(
            k in nlow for k in ("swarm", "collective", "world", "multi-agent", "shared", "communication", "decentralized")
        ):
            score = max(score, 0.72)
            reason_bits.append("collective/world-model overlap")
        if "bottleneck" in nlow or node.node_type == "BOTTLENECK":
            if any(
                k in low
                for k in (
                    "latency",
                    "energy",
                    "evaluation",
                    "high-frequency",
                    "motor",
                    "profiler",
                    "cuda",
                    "耗时",
                    "延迟",
                    "性能剖析",
                )
            ):
                score = max(score, 0.68)
                reason_bits.append("bottleneck alignment")
        if score >= 0.28:
            matches.append(
                KernelMatch(
                    node_id=node.id,
                    node_type=node.node_type,
                    title=node.title,
                    score=round(min(score, 1.0), 4),
                    reason="; ".join(reason_bits) or "lexical overlap with kernel node",
                    structural=False,
                    relevance_type=(
                        "BOTTLENECK"
                        if node.node_type == "BOTTLENECK"
                        else "DECISION"
                        if node.node_type == "DECISION"
                        else "TOPIC"
                    ),
                )
            )
    matches.sort(key=lambda m: m.score, reverse=True)
    return backfill_measurement_bottleneck_matches(matches, nodes, blob)
