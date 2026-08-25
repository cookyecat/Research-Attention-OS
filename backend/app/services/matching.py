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
            if any(k in low for k in ("latency", "energy", "evaluation", "high-frequency", "motor")):
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
    return matches
