from __future__ import annotations

from copy import deepcopy

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.kernel import KernelNode, KernelVersion
from app.services.kernel_commit import assert_no_direct_kernel_write, commit_patch, create_patch


def _seed_belief(db):
    node = KernelNode(
        node_type="BELIEF",
        title="Counterfactual performance belief",
        status="ACTIVE",
        payload={"proposition": "Computation dominates small GPU workloads.", "confidence": 0.8},
        current_version=1,
    )
    db.add(node)
    db.flush()
    db.add(KernelVersion(
        kernel_node_id=node.id,
        version=1,
        snapshot={"id": str(node.id), "node_type": node.node_type, "title": node.title, "status": node.status, "payload": deepcopy(node.payload), "current_version": 1},
        patch_id=None,
        committed_by="USER",
    ))
    db.flush()
    return node


def _propose(db, node):
    return create_patch(
        db,
        target_object_type="BELIEF",
        target_object_id=node.id,
        change_type="REVISE",
        current_state={"status": node.status, "payload": deepcopy(node.payload)},
        proposed_state={
            "status": "CONTESTED",
            "payload": {"proposition": node.payload["proposition"], "confidence": 0.45},
        },
        reasoning="CHALLENGE from audited evidence; human review required.",
        proposed_by="AI",
    )


def _versions(db, node):
    return db.execute(
        select(KernelVersion).where(KernelVersion.kernel_node_id == node.id).order_by(KernelVersion.version)
    ).scalars().all()


def test_proposed_patch_does_not_mutate_kernel(db):
    node = _seed_belief(db)
    before = (node.status, deepcopy(node.payload), node.current_version)
    patch = _propose(db, node)
    assert patch.status == "PROPOSED"
    assert (node.status, node.payload, node.current_version) == before
    assert len(_versions(db, node)) == 1


def test_reject_keeps_kernel_unchanged(db):
    node = _seed_belief(db)
    patch = _propose(db, node)
    before = (node.status, deepcopy(node.payload), node.current_version)
    out = commit_patch(db, patch.id, action="reject")
    assert out.status == "REJECTED"
    assert (node.status, node.payload, node.current_version) == before
    assert len(_versions(db, node)) == 1


def test_accept_commits_new_user_version(db, monkeypatch):
    monkeypatch.setattr("app.services.embeddings.refresh_node_embedding", lambda db, node: None)
    node = _seed_belief(db)
    patch = _propose(db, node)
    out = commit_patch(db, patch.id, action="accept")
    assert out.status == "ACCEPTED"
    assert node.status == "CONTESTED"
    assert node.payload["confidence"] == 0.45
    assert node.current_version == 2
    versions = _versions(db, node)
    assert len(versions) == 2
    assert versions[-1].patch_id == patch.id
    assert versions[-1].committed_by == "USER"


def test_modify_commits_human_modified_state(db, monkeypatch):
    monkeypatch.setattr("app.services.embeddings.refresh_node_embedding", lambda db, node: None)
    node = _seed_belief(db)
    patch = _propose(db, node)
    out = commit_patch(
        db,
        patch.id,
        action="modify",
        modified_state={"payload": {"proposition": node.payload["proposition"], "confidence": 0.6}},
    )
    assert out.status == "MODIFIED"
    assert node.status == "CONTESTED"
    assert node.payload["confidence"] == 0.6
    assert node.current_version == 2
    versions = _versions(db, node)
    assert versions[-1].patch_id == patch.id
    assert versions[-1].committed_by == "USER"


def test_protected_kernel_direct_write_is_blocked():
    with pytest.raises(HTTPException) as exc:
        assert_no_direct_kernel_write("BELIEF")
    assert exc.value.status_code == 403
