from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.kernel import KernelNode, KernelPatch, KernelVersion
from app.models.scheduler import AttentionPlan
from app.schemas.api import KernelNodeCreate, PatchModifyIn
from app.services.kernel_commit import commit_patch
from app.testing.kernel_fixture import seed_mvp_kernel

router = APIRouter()


@router.get("")
def get_kernel(db: Session = Depends(get_db)):
    nodes = db.execute(select(KernelNode).where(KernelNode.deleted_at.is_(None))).scalars().all()
    grouped: dict[str, list] = {}
    for node in nodes:
        grouped.setdefault(node.node_type, []).append(
            {
                "id": str(node.id),
                "node_type": node.node_type,
                "title": node.title,
                "status": node.status,
                "current_version": node.current_version,
                "payload": node.payload,
            }
        )
    return grouped


@router.post("/seed")
def seed_kernel(db: Session = Depends(get_db)):
    existing = db.execute(select(func.count()).select_from(KernelNode)).scalar_one()
    if existing:
        return {"seeded": False, "reason": "kernel already has nodes"}
    nodes = seed_mvp_kernel(db)
    return {"seeded": True, "ids": {code: str(n.id) for code, n in nodes.items()}}


@router.post("/nodes")
def create_node(body: KernelNodeCreate, db: Session = Depends(get_db)):
    # User-authored bootstrap only. AI must use KernelPatch.
    node = KernelNode(
        node_type=body.node_type,
        title=body.title,
        status=body.status,
        payload=body.payload,
        current_version=1,
    )
    db.add(node)
    db.flush()
    db.add(
        KernelVersion(
            kernel_node_id=node.id,
            version=1,
            snapshot={
                "id": str(node.id),
                "node_type": node.node_type,
                "title": node.title,
                "status": node.status,
                "payload": node.payload,
                "current_version": 1,
            },
            committed_by="USER",
        )
    )
    return {"id": str(node.id), "node_type": node.node_type, "current_version": 1}


@router.get("/nodes/{node_id}/versions")
def node_versions(node_id: UUID, db: Session = Depends(get_db)):
    rows = (
        db.execute(select(KernelVersion).where(KernelVersion.kernel_node_id == node_id).order_by(KernelVersion.version))
        .scalars()
        .all()
    )
    return [
        {
            "id": str(r.id),
            "version": r.version,
            "snapshot": r.snapshot,
            "patch_id": str(r.patch_id) if r.patch_id else None,
            "committed_by": r.committed_by,
            "committed_at": r.committed_at.isoformat() if r.committed_at else None,
        }
        for r in rows
    ]


@router.post("/patches")
def create_user_patch(body: dict, db: Session = Depends(get_db)):
    from app.services.kernel_commit import create_patch

    patch = create_patch(
        db,
        target_object_type=body["target_object_type"],
        target_object_id=UUID(body["target_object_id"]) if body.get("target_object_id") else None,
        change_type=body["change_type"],
        current_state=body.get("current_state"),
        proposed_state=body["proposed_state"],
        reasoning=body["reasoning"],
        proposed_by=body.get("proposed_by") or "USER",
        evidence_link_ids=body.get("evidence_link_ids") or [],
        suggested_confidence_change=body.get("suggested_confidence_change"),
    )
    return {"id": str(patch.id), "status": patch.status}


@router.get("/patches")
def list_patches(db: Session = Depends(get_db)):
    rows = db.execute(select(KernelPatch).order_by(KernelPatch.created_at.desc())).scalars().all()
    return [_patch(p) for p in rows]


@router.get("/patches/{patch_id}")
def get_patch(patch_id: UUID, db: Session = Depends(get_db)):
    patch = db.get(KernelPatch, patch_id)
    if patch is None:
        raise HTTPException(404, "not found")
    return _patch(patch)


@router.post("/patches/{patch_id}/accept")
def accept_patch(patch_id: UUID, db: Session = Depends(get_db)):
    return _patch(commit_patch(db, patch_id, action="accept"))


@router.post("/patches/{patch_id}/modify")
def modify_patch(patch_id: UUID, body: PatchModifyIn, db: Session = Depends(get_db)):
    return _patch(commit_patch(db, patch_id, action="modify", modified_state=body.modified_state))


@router.post("/patches/{patch_id}/reject")
def reject_patch(patch_id: UUID, db: Session = Depends(get_db)):
    return _patch(commit_patch(db, patch_id, action="reject"))


@router.get("/attention")
def list_attention(db: Session = Depends(get_db)):
    plans = db.execute(select(AttentionPlan).order_by(AttentionPlan.created_at.desc())).scalars().all()
    return [
        {
            "id": str(p.id),
            "candidate_type": p.candidate_type,
            "candidate_id": str(p.candidate_id),
            "attention_state": p.attention_state,
            "processing_modes": p.processing_modes,
            "urgency": p.urgency,
            "reason": p.reason,
            "expected_output": p.expected_output,
            "cognitive_budget_minutes": p.cognitive_budget_minutes,
            "kernel_target_ids": p.kernel_target_ids,
            "score_debug": p.score_debug,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in plans
    ]


def _patch(p: KernelPatch) -> dict:
    return {
        "id": str(p.id),
        "target_object_type": p.target_object_type,
        "target_object_id": str(p.target_object_id) if p.target_object_id else None,
        "change_type": p.change_type,
        "status": p.status,
        "reasoning": p.reasoning,
        "proposed_state": p.proposed_state,
        "current_state": p.current_state,
        "suggested_confidence_change": p.suggested_confidence_change,
        "reviewed_by_user_at": p.reviewed_by_user_at.isoformat() if p.reviewed_by_user_at else None,
    }
