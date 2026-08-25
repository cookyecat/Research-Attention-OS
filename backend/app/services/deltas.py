from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.enums import KernelNodeType, PatchChangeType
from app.models.kernel import KernelNode
from app.services.extraction import ExtractionResult
from app.services.matching import KernelMatch, node_text
from app.services.scheduler import SchedulerFeatures


@dataclass
class ModelDelta:
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


def is_raw_news_fact(text: str) -> bool:
    low = text.lower()
    launchy = any(p in low for p in ("launches", "launch robot", "unveils", "releases today", "announces today"))
    no_model = not any(
        p in low
        for p in (
            "scale differently",
            "separable",
            "belief",
            "architecture should",
            "evaluation",
            "hypothesis",
        )
    )
    return launchy and no_model and "repeated evidence" not in low


def build_model_delta(
    text: str,
    extraction: ExtractionResult,
    matches: list[KernelMatch],
    features: SchedulerFeatures,
    nodes: list[KernelNode],
) -> ModelDelta:
    distinctions: list[str] = []
    questions: list[str] = []
    changes: list[str] = []
    low = text.lower()

    if any(m.node_type in {"MODEL", "BELIEF", "PROJECT", "BOTTLENECK"} for m in matches) and any(
        k in low for k in ("motor", "continuous", "pause", "embodied", "folding")
    ):
        distinctions.append(
            "Potential distinction between high-level cognitive/task intelligence and temporal motor performance."
        )
        changes.append("Model of embodied intelligence may need a sharper cognitive vs temporal-motor split.")

    if "end-to-end" in low:
        questions.append("At which temporal/control layers should end-to-end learning apply?")
        changes.append(
            "Do not reduce the end-to-end vs hierarchical debate to a binary good/bad; refine the layer question."
        )
        distinctions.append("End-to-end learning applicability may vary by temporal/control layer.")

    if any(m.structural for m in matches):
        distinctions.extend(
            [
                "Equity ownership ≠ corporate role",
                "Corporate role ≠ employment relationship",
                "Employment relationship ≠ contractual restrictions",
            ]
        )
        changes.append("Active Decision about startup equity vs employment flexibility may need review.")

    if features.disagreement >= 0.7:
        belief = next((m for m in matches if m.node_type == "BELIEF"), None)
        if belief:
            changes.append(f"Active Belief '{belief.title or belief.node_id}' may be contested; VERIFY before revision.")

    if "shared world" in low or "one world" in low:
        changes.append("Collective-intelligence Belief/Question about shared world models vs local intelligence may update.")

    admission = bool(changes or distinctions or questions) and not is_raw_news_fact(text)
    if is_raw_news_fact(text):
        admission = False
        changes = []
    if "repeated evidence suggests" in low and "scale differently" in low:
        admission = True
        distinctions.append("Semantic task intelligence and temporal motor intelligence may scale differently.")
        changes.append("A stable Belief or Model could be admitted if the researcher accepts the patch.")

    summary = changes[0] if changes else "No committed Kernel change is implied yet."
    return ModelDelta(
        summary=summary,
        what_could_change=changes,
        distinctions=distinctions,
        questions=questions,
        admission_allowed=admission,
    )


def propose_patches(
    text: str,
    delta: ModelDelta,
    matches: list[KernelMatch],
    features: SchedulerFeatures,
    nodes: list[KernelNode],
    evidence_link_ids: list[str],
) -> list[PatchDraft]:
    if is_raw_news_fact(text):
        return []
    by_id = {n.id: n for n in nodes}
    drafts: list[PatchDraft] = []

    if features.disagreement >= 0.7:
        belief_matches = [m for m in matches if m.node_type == "BELIEF"]
        for match in belief_matches:
            node = by_id.get(match.node_id)
            if not node:
                continue
            payload = dict(node.payload or {})
            old_conf = float(payload.get("confidence") or 0.5)
            new_payload = dict(payload)
            new_payload["status"] = "CONTESTED"
            drafts.append(
                PatchDraft(
                    target_object_type=KernelNodeType.BELIEF,
                    target_object_id=node.id,
                    change_type=PatchChangeType.REVISE,
                    current_state=_node_state(node),
                    proposed_state={
                        "title": node.title,
                        "status": "CONTESTED",
                        "payload": new_payload,
                    },
                    reasoning=(
                        "High-relevance evidence/claims conflict with this Belief. "
                        "Patch stays PROPOSED until explicit human Accept/Modify. "
                        "AI must not silently rewrite researcher state."
                    ),
                    suggested_confidence_change={"from": old_conf, "to": round(max(0.05, old_conf - 0.08), 3)},
                    evidence_link_ids=evidence_link_ids,
                )
            )

    if any("cognitive" in d.lower() and "motor" in d.lower() for d in delta.distinctions):
        model_match = next((m for m in matches if m.node_type == "MODEL"), None)
        model = by_id.get(model_match.node_id) if model_match else None
        if model:
            payload = dict(model.payload or {})
            drafts.append(
                PatchDraft(
                    target_object_type=KernelNodeType.MODEL,
                    target_object_id=model.id,
                    change_type=PatchChangeType.REVISE,
                    current_state=_node_state(model),
                    proposed_state={
                        "title": model.title,
                        "status": "CONTESTED",
                        "payload": {
                            **payload,
                            "pending_distinction": "high-level cognitive/task intelligence vs temporal motor performance",
                        },
                    },
                    reasoning=(
                        "Model Delta: potential split between cognitive/task intelligence and temporal motor "
                        "performance. Patch remains PROPOSED until human Accept/Modify."
                    ),
                    evidence_link_ids=evidence_link_ids,
                )
            )

    if delta.questions:
        q = delta.questions[0]
        drafts.append(
            PatchDraft(
                target_object_type=KernelNodeType.QUESTION,
                target_object_id=None,
                change_type=PatchChangeType.CREATE,
                current_state=None,
                proposed_state={
                    "title": q,
                    "status": "OPEN",
                    "payload": {"text": q, "scope": "embodied control layers", "project_ids": []},
                },
                reasoning="Model Delta raises a more precise question rather than a binary verdict.",
                evidence_link_ids=evidence_link_ids,
            )
        )

    if any("scale differently" in d.lower() for d in delta.distinctions) or "scale differently" in text.lower():
        drafts.append(
            PatchDraft(
                target_object_type=KernelNodeType.MODEL,
                target_object_id=None,
                change_type=PatchChangeType.CREATE,
                current_state=None,
                proposed_state={
                    "title": "Separable scaling of semantic task vs temporal motor intelligence",
                    "status": "PROPOSED",
                    "payload": {
                        "description": "Repeated evidence suggests semantic task intelligence and temporal motor intelligence scale differently.",
                        "model_type": "CONCEPTUAL",
                        "node_data": {},
                        "edge_data": {},
                    },
                },
                reasoning="Satisfies Kernel admission: stable model-level distinction with sustained research relevance.",
                evidence_link_ids=evidence_link_ids,
            )
        )

    # Deduplicate identical CREATE titles
    seen = set()
    unique = []
    for d in drafts:
        key = (d.change_type, d.target_object_id, (d.proposed_state or {}).get("title"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(d)
    return unique


def _node_state(node: KernelNode) -> dict:
    return {
        "id": str(node.id),
        "node_type": node.node_type,
        "title": node.title,
        "status": node.status,
        "payload": node.payload,
        "current_version": node.current_version,
    }


def suggest_watches(text: str, features: SchedulerFeatures, delta: ModelDelta) -> list[dict]:
    low = text.lower()
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

    if "worlddreamer" in low or "orbitbench" in low or "in-orbit" in low:
        add("MODEL", "WorldDreamer technical report", "Promised technical report not yet treated as evidence.", ["PAPER_RELEASE"])
        add("BENCHMARK", "OrbitBench release", "OrbitBench is planned, not already released.", ["BENCHMARK_UPDATE", "PAPER_RELEASE"])
        add("METHOD", "in-orbit results", "First in-orbit validation is a future trigger.", ["NEW_EVIDENCE"])
        add("METHOD", "independent replication", "Marketing language is not proof; wait for independent replication.", ["INDEPENDENT_REPLICATION"])
    elif features.evidence_maturity < 0.5 and (features.kernel_delta >= 0.45 or features.topic_relevance >= 0.45):
        add("METHOD", "paper release", "Promising method, insufficient evidence — you do not need to remember to come back.", ["PAPER_RELEASE"])
        add("METHOD", "code release", "Implementation evidence still missing.", ["CODE_RELEASE"])
        add("METHOD", "independent replication", "Single demo/success is not confirmation.", ["INDEPENDENT_REPLICATION"])
        if "latency" in low or "energy" in low or "embodied" in low:
            add("BENCHMARK", "latency results", "Bottleneck is latency × energy × task-success.", ["BENCHMARK_UPDATE"])
            add("BENCHMARK", "energy results", "Energy cost of unified-model control is unresolved.", ["BENCHMARK_UPDATE"])
    return suggestions
