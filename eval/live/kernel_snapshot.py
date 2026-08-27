"""Fixed Kernel Snapshot catalogs for Live Eval Human Gold.

`target_node_id` is a selectable reference into this snapshot — not a topic tag,
not an ontology type, and not a recommendation from the current model prediction.
Annotators pick by title; the program stores `id`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KernelSnapshotRef:
    id: str
    title: str


# Keep titles in sync with backend/app/testing/kernel_fixture.py (mvp).
# Picker surface is id + title only; node types are intentionally omitted.
MVP_KERNEL_SNAPSHOT: tuple[KernelSnapshotRef, ...] = (
    KernelSnapshotRef("G1", "Build better embodied and multi-agent intelligence systems."),
    KernelSnapshotRef("P1", "Motor Intelligence"),
    KernelSnapshotRef(
        "BT1",
        "Lack of latency × energy × task-success evaluation for high-frequency embodied control.",
    ),
    KernelSnapshotRef("Q1", "Should high-frequency motor control depend on a large unified model?"),
    KernelSnapshotRef(
        "B1",
        "Large unified models may be unsuitable for the fastest embodied-control loop.",
    ),
    KernelSnapshotRef(
        "M1",
        "Embodied intelligence contains partially separable cognitive intelligence and temporal motor intelligence.",
    ),
    KernelSnapshotRef("P2", "Collective Intelligence"),
    KernelSnapshotRef("Q2", "Can shared world models reduce explicit multi-agent communication?"),
    KernelSnapshotRef(
        "B2",
        "True swarm-style collective intelligence requires meaningful decentralized local intelligence.",
    ),
    KernelSnapshotRef(
        "D1",
        "Evaluate startup equity terms independently from employment obligations.",
    ),
)

KERNEL_SNAPSHOTS = {
    "mvp": MVP_KERNEL_SNAPSHOT,
}


def snapshot_for_fixture(fixture: str | None) -> tuple[KernelSnapshotRef, ...]:
    return KERNEL_SNAPSHOTS.get(fixture or "mvp", MVP_KERNEL_SNAPSHOT)


def kernel_snapshot_picker(fixture: str | None = "mvp") -> list[dict[str, str]]:
    """Selectable Kernel Snapshot references for annotation. No ontology types."""
    return [{"id": node.id, "title": node.title} for node in snapshot_for_fixture(fixture)]


def snapshot_node_by_id(node_id: str | None, *, fixture: str | None = "mvp") -> KernelSnapshotRef | None:
    if not node_id:
        return None
    for node in snapshot_for_fixture(fixture):
        if node.id == node_id:
            return node
    return None


def resolve_snapshot_node_id(raw: str | None, *, fixture: str | None = "mvp") -> str | None:
    """Resolve a picker id or exact title to the snapshot node id. None / NONE / blank → None."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.upper() == "NONE":
        return None
    for node in snapshot_for_fixture(fixture):
        if text == node.id or text.lower() == node.title.lower():
            return node.id
    return text
