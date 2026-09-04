from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.enums import CognitiveEffectKind, KernelNodeType, PatchChangeType
from app.models.kernel import KernelNode
from app.services.cognitive_impact import (
    CognitiveImpactAssessment,
    canonical_delta_content,
    is_update_eligible_node,
    primary_update,
    select_primary_effect,
)
from app.services.extraction import ExtractionResult
from app.services.matching import KernelMatch
from app.services.scheduler import SchedulerFeatures


@dataclass
class ModelDelta:
    """Prose / synthesis artifact for Δ_t. Not a second cognitive-transition algebra."""

    summary: str
    what_could_change: list[str] = field(default_factory=list)
    distinctions: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    admission_allowed: bool = False
    affected_kernel_nodes: list[dict] = field(default_factory=list)
    possible_hypotheses: list[str] = field(default_factory=list)
    decision_implications: list[str] = field(default_factory=list)
    epistemic_risk: str = ""
    evidence_maturity: float = 0.4
    rationale: str = ""


@dataclass
class PatchDraft:
    target_object_type: KernelNodeType
    target_object_id: UUID | None
    change_type: PatchChangeType
    current_state: dict | None
    proposed_state: dict
    reasoning: str
    suggested_confidence_change: dict | None = None
    evidence_link_ids: list[str] = field(default_factory=list)


def _kind(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    raw = str(value).strip()
    return raw or None


def _node_state(node: KernelNode) -> dict:
    return {
        "id": str(node.id),
        "node_type": node.node_type,
        "title": node.title,
        "status": node.status,
        "payload": node.payload,
        "current_version": node.current_version,
    }


def _affected_from_update(update: dict) -> list[dict]:
    op = _kind(update.get("operation"))
    nid = update.get("target_node_id")
    if not op:
        return []
    if op == CognitiveEffectKind.OPEN_NEW:
        return [{"id": None, "operation": op, "impact": None}]
    if nid:
        return [{"id": str(nid), "operation": op, "impact": None}]
    return []


def model_delta_from_transition(
    assessment: CognitiveImpactAssessment | None,
    extraction: ExtractionResult | None = None,
    *,
    prose: ModelDelta | None = None,
) -> ModelDelta:
    """Bind ModelDelta to Δ_t. Optional LLM prose is synthesis around Δ_t, not a second update."""
    update = primary_update(assessment)
    primary = select_primary_effect(assessment)
    op = _kind(update.get("operation"))
    maturity = 0.4
    if extraction is not None:
        maturity = float(getattr(extraction, "evidence_maturity", None) or 0.4)
    if prose is not None:
        maturity = float(prose.evidence_maturity or maturity)

    summary = canonical_delta_content(assessment)
    if primary is None or not op:
        return ModelDelta(
            summary=summary,
            what_could_change=[],
            distinctions=[],
            questions=[],
            admission_allowed=False,
            affected_kernel_nodes=[],
            possible_hypotheses=[],
            decision_implications=[],
            epistemic_risk=prose.epistemic_risk if prose else "",
            evidence_maturity=maturity,
            rationale="Δ_t is NONE. Synthesis must not invent a cognitive change.",
        )

    return ModelDelta(
        summary=summary,
        what_could_change=list(prose.what_could_change) if prose and prose.what_could_change else [primary.reason or summary],
        distinctions=list(prose.distinctions) if prose else [],
        questions=list(prose.questions) if prose else [],
        admission_allowed=True,
        affected_kernel_nodes=_affected_from_update(update),
        possible_hypotheses=list(prose.possible_hypotheses) if prose else [],
        decision_implications=list(prose.decision_implications) if prose else [],
        epistemic_risk=prose.epistemic_risk if prose else "",
        evidence_maturity=maturity,
        rationale=f"Prose for Δ_t={op}. Not an independent cognitive update.",
    )


def build_model_delta(
    text: str,
    extraction: ExtractionResult,
    matches: list[KernelMatch],
    features: SchedulerFeatures,
    nodes: list[KernelNode],
    *,
    assessment: CognitiveImpactAssessment | None = None,
) -> ModelDelta:
    del text, matches, features, nodes
    return model_delta_from_transition(assessment, extraction)


def _open_new_type(extraction: ExtractionResult | None) -> KernelNodeType:
    if extraction is None:
        return KernelNodeType.QUESTION
    if extraction.technical_claims:
        return KernelNodeType.MODEL
    claims = getattr(extraction, "claims", None) or []
    if any(str(getattr(c, "claim_type", "")).upper() == "TECHNICAL" for c in claims):
        return KernelNodeType.MODEL
    return KernelNodeType.QUESTION


def _open_new_title(extraction: ExtractionResult | None, delta: ModelDelta | None, reason: str) -> str:
    if delta and delta.questions:
        title = str(delta.questions[0]).strip()
        if title:
            return title[:200]
    if extraction is not None:
        if extraction.event_title:
            return str(extraction.event_title)[:200]
        for claim in extraction.claims or []:
            text = str(getattr(claim, "text", "") or "").strip()
            if text:
                return text[:200]
        for inference in extraction.inferences or []:
            text = str(getattr(inference, "text", "") or "").strip()
            if text:
                return text[:200]
    clipped = (reason or "").strip()
    return clipped[:200] if clipped else "New cognitive branch"


# Domain-model statuses per Kernel object. Not a new mutation algebra.
LEGAL_NODE_STATUSES: dict[str, frozenset[str]] = {
    "BELIEF": frozenset({"TENTATIVE", "ACTIVE", "CONTESTED", "REVISED", "DEPRECATED"}),
    "MODEL": frozenset({"PROPOSED", "ACTIVE", "CONTESTED", "REVISED", "DEPRECATED"}),
    "QUESTION": frozenset({"OPEN", "WATCHING", "ACTIVE", "ANSWERED", "ABANDONED"}),
    "HYPOTHESIS": frozenset({"PROPOSED", "TESTING", "SUPPORTED", "REFUTED", "INCONCLUSIVE"}),
    "DECISION": frozenset({"PENDING", "DECIDED", "REVISIT_REQUIRED", "SUPERSEDED"}),
    "BOTTLENECK": frozenset({"IDENTIFIED", "ACTIVE", "RESOLVING", "RESOLVED", "OBSOLETE"}),
}


def proposed_state_is_legal(node_type: str | KernelNodeType | None, proposed: dict | None) -> bool:
    """Proposed KernelPatch state must match the target object's own status schema."""
    kind = str(getattr(node_type, "value", node_type) or "").upper()
    if not kind or not isinstance(proposed, dict):
        return False
    allowed = LEGAL_NODE_STATUSES.get(kind)
    if not allowed:
        return False
    status = proposed.get("status")
    if status is None:
        return False
    return str(status).upper() in allowed


def _revise_draft(
    node: KernelNode,
    operation: str,
    reason: str,
    evidence_link_ids: list[str],
) -> PatchDraft | None:
    """Type-specific REVISE. No cross-type status/confidence heuristic.

    Δ_t names the direction. If this node type has no legal, interpretable
    proposed state for that direction, return None (zero patch).
    """
    kind = str(node.node_type or "").upper()
    if kind not in {"BELIEF", "MODEL"}:
        return None
    if operation != CognitiveEffectKind.CHALLENGE:
        return None
    if str(node.status or "").upper() == "CONTESTED":
        return None
    payload = dict(node.payload or {})
    proposed = {
        "title": node.title,
        "status": "CONTESTED",
        "payload": payload,
    }
    if not proposed_state_is_legal(kind, proposed):
        return None
    return PatchDraft(
        target_object_type=KernelNodeType(kind),
        target_object_id=node.id,
        change_type=PatchChangeType.REVISE,
        current_state=_node_state(node),
        proposed_state=proposed,
        reasoning=(
            "CHALLENGE: existing Belief/Model should be marked CONTESTED. "
            f"{reason} Patch stays PROPOSED until human Accept/Modify."
        ),
        suggested_confidence_change=None,
        evidence_link_ids=evidence_link_ids,
    )


def _create_open_new_draft(
    extraction: ExtractionResult | None,
    reason: str,
    delta: ModelDelta | None,
    evidence_link_ids: list[str],
) -> PatchDraft:
    node_type = _open_new_type(extraction)
    title = _open_new_title(extraction, delta, reason)
    payload: dict = {}
    if node_type == KernelNodeType.QUESTION:
        payload = {"text": title}
        status = "OPEN"
    else:
        payload = {"description": title, "model_type": "CONCEPTUAL"}
        status = "PROPOSED"
    return PatchDraft(
        target_object_type=node_type,
        target_object_id=None,
        change_type=PatchChangeType.CREATE,
        current_state=None,
        proposed_state={
            "title": title,
            "status": status,
            "payload": payload,
            "node_type": node_type.value,
        },
        reasoning=(
            "OPEN_NEW: no existing Kernel node is the correct landing point. "
            f"{reason} Patch stays PROPOSED until human Accept/Modify."
        ),
        evidence_link_ids=evidence_link_ids,
    )


def patch_consistent_with_update(draft: PatchDraft, update: dict) -> bool:
    """Any auto-proposed patch must trace to Δ_t operation/target."""
    op = _kind(update.get("operation"))
    tid = update.get("target_node_id")
    if not op:
        return False
    if op == CognitiveEffectKind.OPEN_NEW:
        return draft.change_type == PatchChangeType.CREATE and draft.target_object_id is None
    if op in {CognitiveEffectKind.REINFORCE, CognitiveEffectKind.CHALLENGE}:
        if draft.change_type != PatchChangeType.REVISE or draft.target_object_id is None or not tid:
            return False
        return str(draft.target_object_id) == str(tid)
    return False


def propose_patches(
    text: str,
    delta: ModelDelta,
    matches: list[KernelMatch],
    features: SchedulerFeatures,
    nodes: list[KernelNode],
    evidence_link_ids: list[str],
    *,
    assessment: CognitiveImpactAssessment | None = None,
    extraction: ExtractionResult | None = None,
) -> list[PatchDraft]:
    """P_t = G(E_t, K_t, Δ_t). Independent cognitive heuristics are not a source of truth."""
    del text, matches, features
    update = primary_update(assessment)
    primary = select_primary_effect(assessment)
    op = _kind(update.get("operation"))
    if primary is None or not op:
        return []

    evidence_ids = list(evidence_link_ids or [])
    drafts: list[PatchDraft] = []
    if op == CognitiveEffectKind.OPEN_NEW:
        drafts.append(_create_open_new_draft(extraction, primary.reason, delta, evidence_ids))
    elif op in {CognitiveEffectKind.REINFORCE, CognitiveEffectKind.CHALLENGE}:
        by_id = {n.id: n for n in nodes}
        raw_id = update.get("target_node_id")
        node = None
        if raw_id:
            try:
                node = by_id.get(UUID(str(raw_id)))
            except (TypeError, ValueError):
                node = None
            if node is None:
                for candidate in nodes:
                    if str(candidate.id) == str(raw_id):
                        node = candidate
                        break
        if node is None or not is_update_eligible_node(node.node_type):
            return []
        draft = _revise_draft(node, op, primary.reason, evidence_ids)
        if draft is None:
            return []
        drafts.append(draft)
    return [
        d
        for d in drafts
        if patch_consistent_with_update(d, update)
        and proposed_state_is_legal(d.target_object_type, d.proposed_state)
    ]


def suggest_watches(text: str, features: SchedulerFeatures, delta: ModelDelta) -> list[dict]:
    del text, delta
    suggestions: list[dict] = []

    def add(target_type: str, ref: str, reason: str, triggers: list[str]) -> None:
        suggestions.append(
            {
                "target_type": target_type,
                "target_ref": ref,
                "created_reason": reason,
                "triggers": triggers,
            }
        )

    if features.evidence_maturity < 0.5 and (features.kernel_delta >= 0.45 or features.topic_relevance >= 0.45):
        add("METHOD", "paper release", "Promising method, insufficient evidence — you do not need to remember to come back.", ["PAPER_RELEASE"])
        add("METHOD", "code release", "Implementation evidence still missing.", ["CODE_RELEASE"])
        add("METHOD", "independent replication", "Single demo/success is not confirmation.", ["INDEPENDENT_REPLICATION"])
    return suggestions
