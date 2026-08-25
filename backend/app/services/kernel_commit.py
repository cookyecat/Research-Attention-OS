from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import PROTECTED_KERNEL_TYPES, KernelNodeType, PatchChangeType, PatchStatus
from app.models.kernel import KernelNode, KernelPatch, KernelVersion


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _snapshot(node: KernelNode) -> dict:
    return {
        "id": str(node.id),
        "node_type": node.node_type,
        "title": node.title,
        "status": node.status,
        "payload": node.payload,
        "current_version": node.current_version,
    }


def create_patch(
    db: Session,
    *,
    target_object_type: str,
    target_object_id: UUID | None,
    change_type: str,
    current_state: dict | None,
    proposed_state: dict,
    reasoning: str,
    proposed_by: str = "AI",
    evidence_link_ids: list | None = None,
    suggested_confidence_change: dict | None = None,
    analysis_run_id: UUID | None = None,
) -> KernelPatch:
    patch = KernelPatch(
        target_object_type=target_object_type,
        target_object_id=target_object_id,
        change_type=change_type,
        current_state=current_state,
        proposed_state=proposed_state,
        evidence_link_ids=evidence_link_ids or [],
        reasoning=reasoning,
        suggested_confidence_change=suggested_confidence_change,
        status=PatchStatus.PROPOSED,
        proposed_by=proposed_by,
        analysis_run_id=analysis_run_id,
    )
    db.add(patch)
    db.flush()
    return patch


def _apply_state(node: KernelNode, proposed: dict) -> None:
    if "title" in proposed:
        node.title = proposed["title"]
    if "status" in proposed:
        node.status = proposed["status"]
    if "payload" in proposed:
        node.payload = proposed["payload"]
    if "node_type" in proposed:
        node.node_type = proposed["node_type"]


def commit_patch(db: Session, patch_id: UUID, *, action: str, modified_state: dict | None = None) -> KernelPatch:
    """Transactionally apply an accepted/modified patch. Never mutates on PROPOSED."""
    patch = db.get(KernelPatch, patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="KernelPatch not found")
    if patch.status != PatchStatus.PROPOSED:
        raise HTTPException(status_code=409, detail=f"Patch already {patch.status}")

    if action == "reject":
        patch.status = PatchStatus.REJECTED
        patch.reviewed_by_user_at = _utcnow()
        db.flush()
        return patch

    if action not in {"accept", "modify"}:
        raise HTTPException(status_code=400, detail="action must be accept, modify, or reject")

    proposed = dict(patch.proposed_state or {})
    if action == "modify":
        if not modified_state:
            raise HTTPException(status_code=400, detail="modify requires modified_state")
        proposed.update(modified_state)
        patch.proposed_state = proposed
        patch.status = PatchStatus.MODIFIED
    else:
        patch.status = PatchStatus.ACCEPTED
    patch.reviewed_by_user_at = _utcnow()

    node: KernelNode | None = None
    if patch.target_object_id:
        try:
            node = db.execute(
                select(KernelNode).where(KernelNode.id == patch.target_object_id).with_for_update()
            ).scalar_one_or_none()
        except Exception:
            node = None
        if node is None:
            node = db.get(KernelNode, patch.target_object_id)
        if node is None:
            raise HTTPException(status_code=404, detail="Target kernel node not found")
        new_version = node.current_version + 1
        _apply_state(node, proposed)
        node.current_version = new_version
        node.updated_at = _utcnow()
        db.add(
            KernelVersion(
                kernel_node_id=node.id,
                version=new_version,
                snapshot=_snapshot(node),
                patch_id=patch.id,
                committed_by="USER",
            )
        )
    else:
        if patch.change_type != PatchChangeType.CREATE:
            raise HTTPException(status_code=400, detail="Missing target for non-CREATE patch")
        node_type = proposed.get("node_type") or patch.target_object_type
        node = KernelNode(
            node_type=node_type,
            title=proposed.get("title"),
            status=proposed.get("status") or "ACTIVE",
            payload=proposed.get("payload") or {},
            current_version=1,
        )
        db.add(node)
        db.flush()
        patch.target_object_id = node.id
        db.add(
            KernelVersion(
                kernel_node_id=node.id,
                version=1,
                snapshot=_snapshot(node),
                patch_id=patch.id,
                committed_by="USER",
            )
        )
    db.flush()
    return patch


def assert_no_direct_kernel_write(node_type: str) -> None:
    if node_type in {t.value for t in PROTECTED_KERNEL_TYPES}:
        raise HTTPException(
            status_code=403,
            detail="AI cannot silently rewrite Belief/Model/Hypothesis/Decision; use KernelPatch.",
        )
