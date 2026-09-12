from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Literal
from uuid import UUID

from pydantic import Field
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cognitive.schemas import StrictModel
from app.db import Base
from app.enums import CognitiveEffectKind, PatchChangeType
from app.models.kernel import KernelNode, KernelVersion
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment, node_proposition, resolve_target_importance
from app.services.kernel_commit import create_patch, commit_patch
from app.services.matching import KernelMatch
from app.services.scheduler import SchedulerFeatures
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_perf_challenge_nodes

VERSION = "phase9a-kernel-causal-alignment-v0.2"
CONTRACT_VERSION = "phase9a-relation-only-cardinal-free-v0.2"
TARGET_CODE = "CF-B-PERF"
DIRECT_SUPPORT_UNIT_ID = "RS05-U01"
ASSIMILATED_PROPOSITION = (
    "For a small 64x64 bf16 matrix multiplication with bias, kernel preparation and launch "
    "overhead dominate useful GPU computation."
)

SYSTEM_PROMPT = """Map Auditor-admitted semantic evidence to all distinct material cognitive relations on the supplied Cognitive Kernel.

You only perform Relation Mapping. You do NOT choose Attention, bind evidence IDs, judge evidence sufficiency, choose jurisdiction, estimate magnitude, epistemic strength, importance, confidence, priority, or ranking.

REINFORCE means the supplied evidence strengthens or confirms the existing target proposition at matching scope.
CHALLENGE means the supplied evidence directly requires the existing target proposition to be weakened, restricted, modified, or overturned.
OPEN_NEW means no existing supplied target is the right landing spot and the evidence opens a genuinely new cognitive branch.

REINFORCE and CHALLENGE require target_kernel_node_id to name an eligible supplied target. OPEN_NEW requires target_kernel_node_id = null. Scope alignment is mandatory. Evidence that is merely topical is not a cognitive relation. If there is no material relation, return an empty effects list.

Return every distinct material relation. Do not vote, rank, select a public update, or infer downstream policy. Return JSON only."""


class RelationEffect(StrictModel):
    operation: Literal["REINFORCE", "CHALLENGE", "OPEN_NEW"]
    target_kernel_node_id: UUID | None = None
    reason: str = Field(min_length=1)


class RelationResponse(StrictModel):
    effects: list[RelationEffect] = Field(default_factory=list)


@dataclass
class ArmMaterialization:
    arm: str
    nodes: list[KernelNode]
    kernel_snapshot: list[dict]
    patch: dict | None
    target_versions: list[dict]


def fixture_code(node: KernelNode) -> str:
    return str((node.payload or {}).get("phase6b_fixture_code") or node.title)


def target_node(nodes: list[KernelNode]) -> KernelNode:
    return next(node for node in nodes if fixture_code(node) == TARGET_CODE)


def node_snapshot(node: KernelNode) -> dict:
    return {
        "id": str(node.id),
        "code": fixture_code(node),
        "node_type": node.node_type,
        "title": node.title,
        "status": node.status,
        "payload": dict(node.payload or {}),
        "current_version": int(node.current_version),
    }


def _seed_temp_kernel(db) -> list[KernelNode]:
    nodes = build_phase6b_perf_challenge_nodes()
    for node in nodes:
        db.add(node)
        db.add(KernelVersion(kernel_node_id=node.id, version=1, snapshot=node_snapshot(node), committed_by="USER"))
    db.flush()
    return nodes


def _accept_without_embedding(db, patch_id):
    import app.services.embeddings as embeddings
    original = embeddings.refresh_node_embedding
    embeddings.refresh_node_embedding = lambda *_a, **_k: None
    try:
        return commit_patch(db, patch_id, action="accept")
    finally:
        embeddings.refresh_node_embedding = original


def materialize_rs05_arm(arm: str) -> ArmMaterialization:
    if arm not in {"K0", "K1-S", "K1-I"}:
        raise ValueError(f"unknown arm: {arm}")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    try:
        nodes = _seed_temp_kernel(db)
        target = target_node(nodes)
        patch_row = None
        if arm != "K0":
            proposed_payload = dict(target.payload or {})
            proposed_title = target.title
            if arm == "K1-S":
                proposed_title = ASSIMILATED_PROPOSITION
                proposed_payload["proposition"] = ASSIMILATED_PROPOSITION
                proposed_payload["importance"] = 0.9
            else:
                proposed_payload["importance"] = 0.2
            patch = create_patch(
                db,
                target_object_type="BELIEF",
                target_object_id=target.id,
                change_type=PatchChangeType.REVISE,
                current_state=node_snapshot(target),
                proposed_state={"title": proposed_title, "payload": proposed_payload},
                reasoning=f"Phase 9A v0.2 preregistered isolated Kernel intervention {arm}.",
                proposed_by="USER",
            )
            _accept_without_embedding(db, patch.id)
            patch_row = {
                "id": str(patch.id),
                "status": str(patch.status),
                "change_type": str(patch.change_type),
                "target_object_id": str(patch.target_object_id),
                "proposed_state": patch.proposed_state,
            }
        db.commit()
        nodes = list(db.execute(select(KernelNode).order_by(KernelNode.node_type, KernelNode.title)).scalars())
        target = target_node(nodes)
        versions = list(db.execute(select(KernelVersion).where(KernelVersion.kernel_node_id == target.id).order_by(KernelVersion.version)).scalars())
        result = ArmMaterialization(
            arm=arm,
            nodes=nodes,
            kernel_snapshot=[node_snapshot(node) for node in nodes],
            patch=patch_row,
            target_versions=[{
                "version": int(row.version),
                "snapshot": row.snapshot,
                "patch_id": str(row.patch_id) if row.patch_id else None,
                "committed_by": row.committed_by,
            } for row in versions],
        )
        db.expunge_all()
        return result
    finally:
        db.close()
        engine.dispose()


def frozen_rs05_match(nodes: list[KernelNode]) -> list[KernelMatch]:
    target = target_node(nodes)
    return [KernelMatch(
        node_id=target.id,
        node_type=target.node_type,
        title=target.title,
        score=1.0,
        reason="Phase 9A v0.2 frozen RS05 target identity (CF-B-PERF).",
        structural=False,
        relevance_type="EVIDENCE",
    )]


def canonical_units(units: list[dict]) -> list[dict]:
    return [{
        "unit_id": str(unit.get("unit_id") or ""),
        "statement": str(unit.get("statement") or ""),
        "epistemic_status": str(unit.get("epistemic_status") or ""),
        "confidence": str(unit.get("confidence") or ""),
    } for unit in units]


def relation_user_prompt(units: list[dict], matches: list[KernelMatch], nodes: list[KernelNode]) -> str:
    by_id = {node.id: node for node in nodes}
    locations = []
    for match in matches:
        node = by_id[match.node_id]
        payload = node.payload or {}
        locations.append({
            "id": str(node.id),
            "type": node.node_type,
            "title": node.title,
            "proposition": node_proposition(node),
            "scope": payload.get("scope") if isinstance(payload, dict) else None,
            "relevance_type": match.relevance_type,
        })
    shape = {"effects": [{"operation": "REINFORCE", "target_kernel_node_id": None, "reason": "semantic relation"}]}
    return (
        "Audited canonical semantic units:\n" + json.dumps(canonical_units(units), ensure_ascii=False, sort_keys=True)
        + "\n\nFrozen Kernel location and eligible target:\n" + json.dumps(locations, ensure_ascii=False, sort_keys=True)
        + "\n\nReturn JSON exactly in this shape:\n" + json.dumps(shape, ensure_ascii=False, sort_keys=True)
    )


def validate_relation(effect: RelationEffect, nodes: list[KernelNode]) -> tuple[bool, str | None]:
    target = target_node(nodes)
    if effect.operation == "OPEN_NEW":
        return (effect.target_kernel_node_id is None, None if effect.target_kernel_node_id is None else "OPEN_NEW_TARGET_NOT_NULL")
    if effect.target_kernel_node_id is None:
        return False, "TARGET_NULL"
    if effect.target_kernel_node_id != target.id:
        return False, "TARGET_NOT_FROZEN_CF_B_PERF"
    return True, None


def normalize_relations(effects: list[RelationEffect]) -> list[RelationEffect]:
    seen = set()
    out = []
    for effect in effects:
        key = (effect.operation, str(effect.target_kernel_node_id) if effect.target_kernel_node_id else None)
        if key in seen:
            continue
        seen.add(key)
        out.append(effect)
    return out


def target_polarity_state(effects: list[RelationEffect], nodes: list[KernelNode]) -> str:
    target = target_node(nodes)
    ops = {e.operation for e in effects if e.target_kernel_node_id == target.id and e.operation in {"REINFORCE", "CHALLENGE"}}
    if ops == {"CHALLENGE"}:
        return "CHALLENGE_ONLY"
    if ops == {"REINFORCE"}:
        return "REINFORCE_ONLY"
    if ops == {"CHALLENGE", "REINFORCE"}:
        return "BOTH"
    return "NONE"


def relation_key(effect: CognitiveEffect, nodes: list[KernelNode]) -> tuple[str, str]:
    operation = effect.operation.value if hasattr(effect.operation, "value") else str(effect.operation)
    target = target_node(nodes)
    if effect.target_kernel_node_id == target.id:
        return operation, TARGET_CODE
    return operation, "OPEN_NEW" if effect.target_kernel_node_id is None else str(effect.target_kernel_node_id)


def authorize_relations(effects: list[RelationEffect], *, arm: str, nodes: list[KernelNode]) -> tuple[CognitiveImpactAssessment, list[dict]]:
    if arm not in {"K0", "K1-S", "K1-I"}:
        raise ValueError(arm)
    target = target_node(nodes)
    expected_operation = "REINFORCE" if arm == "K1-S" else "CHALLENGE"
    authorized: list[CognitiveEffect] = []
    traces = []
    for effect in effects:
        keep = effect.operation == expected_operation and effect.target_kernel_node_id == target.id
        reason = "DIRECT_RS05_U01" if keep else (
            "OPEN_NEW_NO_PREREGISTERED_JURISDICTION" if effect.operation == "OPEN_NEW" else "OPPOSITE_TO_PREREGISTERED_EVIDENCE"
        )
        trace = {
            "operation": effect.operation,
            "target_kernel_node_id": str(effect.target_kernel_node_id) if effect.target_kernel_node_id else None,
            "support_unit_ids": [DIRECT_SUPPORT_UNIT_ID] if effect.target_kernel_node_id == target.id else [],
            "grounding": "DIRECT" if keep else "INSUFFICIENT",
            "keep": keep,
            "authority_reason": reason,
        }
        if keep:
            importance = resolve_target_importance(node=target, node_type=target.node_type, llm_estimate=0.0)
            trace["importance_value"] = float(importance)
            trace["importance_band"] = "HIGH" if float(importance) >= 0.55 else "LOW"
            trace["epistemic_band"] = "SUFFICIENT"
            authorized.append(CognitiveEffect(
                target_kernel_node_id=target.id,
                operation=CognitiveEffectKind(effect.operation),
                change_magnitude=0.0,
                epistemic_strength=1.0,
                target_importance=float(importance),
                reason=effect.reason,
                exploration_candidate=False,
                target_node_type=target.node_type,
            ))
        traces.append(trace)
    return CognitiveImpactAssessment(effects=authorized, raw_effects=[]), traces


def neutral_features() -> SchedulerFeatures:
    return SchedulerFeatures(
        topic_relevance=0.0, structural_relevance=0.0, decision_relevance=0.0,
        novelty=0.0, credibility=0.0, kernel_delta=0.0, bottleneck_alignment=0.0,
        disagreement=0.0, actionability=0.0, temporal_value=0.0, cognitive_cost=0.0,
    )
