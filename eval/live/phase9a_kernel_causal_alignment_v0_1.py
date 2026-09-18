from __future__ import annotations

from dataclasses import dataclass, replace
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.enums import PatchChangeType
from app.models.kernel import KernelNode, KernelVersion
from app.services.cognitive_impact import CognitiveImpactAssessment, resolve_target_importance
from app.services.kernel_commit import create_patch, commit_patch
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_perf_challenge_nodes

VERSION = "phase9a-kernel-causal-alignment-v0.1"
TARGET_CODE = "CF-B-PERF"
ASSIMILATED_PROPOSITION = (
    "For a small 64x64 bf16 matrix multiplication with bias, kernel preparation and launch "
    "overhead dominate useful GPU computation."
)

@dataclass
class ArmMaterialization:
    arm: str
    nodes: list[KernelNode]
    kernel_snapshot: list[dict]
    patch: dict | None
    target_versions: list[dict]

def fixture_code(node: KernelNode) -> str:
    return str((node.payload or {}).get("phase6b_fixture_code") or node.title)


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


def bind_kernel_importance(
    assessment: CognitiveImpactAssessment,
    nodes: list[KernelNode],
) -> CognitiveImpactAssessment:
    by_id = {node.id: node for node in nodes}
    rebound = []
    for effect in assessment.effects:
        node = by_id.get(effect.target_kernel_node_id) if effect.target_kernel_node_id else None
        if node is None:
            rebound.append(effect)
            continue
        rebound.append(
            replace(
                effect,
                target_importance=resolve_target_importance(
                    node=node,
                    node_type=node.node_type,
                    llm_estimate=effect.target_importance,
                ),
            )
        )
    return replace(assessment, effects=rebound)

def _seed_temp_kernel(db) -> list[KernelNode]:
    nodes = build_phase6b_perf_challenge_nodes()
    for node in nodes:
        db.add(node)
        db.add(
            KernelVersion(
                kernel_node_id=node.id,
                version=1,
                snapshot=node_snapshot(node),
                committed_by="USER",
            )
        )
    db.flush()
    return nodes


def _target(nodes: list[KernelNode]) -> KernelNode:
    return next(node for node in nodes if fixture_code(node) == TARGET_CODE)


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
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    try:
        nodes = _seed_temp_kernel(db)
        target = _target(nodes)
        patch_row = None
        if arm != "K0":
            proposed_payload = dict(target.payload or {})
            proposed_title = target.title
            if arm == "K1-S":
                proposed_title = ASSIMILATED_PROPOSITION
                proposed_payload["proposition"] = ASSIMILATED_PROPOSITION
                proposed_payload["importance"] = 0.9
            elif arm == "K1-I":
                proposed_payload["importance"] = 0.2
            patch = create_patch(
                db,
                target_object_type="BELIEF",
                target_object_id=target.id,
                change_type=PatchChangeType.REVISE,
                current_state=node_snapshot(target),
                proposed_state={"title": proposed_title, "payload": proposed_payload},
                reasoning=f"Phase 9A preregistered isolated Kernel intervention {arm}.",
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
        target = _target(nodes)
        versions = list(
            db.execute(
                select(KernelVersion)
                .where(KernelVersion.kernel_node_id == target.id)
                .order_by(KernelVersion.version)
            ).scalars()
        )
        result = ArmMaterialization(
            arm=arm,
            nodes=nodes,
            kernel_snapshot=[node_snapshot(node) for node in nodes],
            patch=patch_row,
            target_versions=[
                {
                    "version": int(row.version),
                    "snapshot": row.snapshot,
                    "patch_id": str(row.patch_id) if row.patch_id else None,
                    "committed_by": row.committed_by,
                }
                for row in versions
            ],
        )
        db.expunge_all()
        return result
    finally:
        db.close()
        engine.dispose()

def frozen_rs05_critical_match(nodes: list[KernelNode]):
    """Freeze the Phase 8C.12/10A critical update-eligible RS05 target identity."""
    from app.cognitive.schemas import KernelMatchItem

    target = _target(nodes)
    return [
        KernelMatchItem(
            kernel_node_id=target.id,
            relevance_type="EVIDENCE",
            score=1.0,
            reason="Phase 9A frozen critical RS05 belief jurisdiction (CF-B-PERF).",
        )
    ]
