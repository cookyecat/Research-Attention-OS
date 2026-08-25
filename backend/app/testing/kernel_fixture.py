from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.kernel import KernelEdge, KernelNode, KernelVersion


def seed_mvp_kernel(db: Session) -> dict[str, KernelNode]:
    nodes: dict[str, KernelNode] = {}

    def add(code: str, node_type: str, title: str, status: str, payload: dict) -> KernelNode:
        node = KernelNode(node_type=node_type, title=title, status=status, payload=payload, current_version=1)
        db.add(node)
        db.flush()
        db.add(
            KernelVersion(
                kernel_node_id=node.id,
                version=1,
                snapshot={
                    "id": str(node.id),
                    "node_type": node_type,
                    "title": title,
                    "status": status,
                    "payload": payload,
                    "current_version": 1,
                },
                patch_id=None,
                committed_by="USER",
            )
        )
        nodes[code] = node
        return node

    g1 = add(
        "G1",
        "GOAL",
        "Build better embodied and multi-agent intelligence systems.",
        "ACTIVE",
        {"description": "Build better embodied and multi-agent intelligence systems.", "priority": 1},
    )
    p1 = add(
        "P1",
        "PROJECT",
        "Motor Intelligence",
        "ACTIVE",
        {"description": "Motor Intelligence", "goal_ids": [str(g1.id)], "current_bottleneck_ids": []},
    )
    bt1 = add(
        "BT1",
        "BOTTLENECK",
        "Lack of latency × energy × task-success evaluation for high-frequency embodied control.",
        "ACTIVE",
        {
            "description": "Lack of latency × energy × task-success evaluation for high-frequency embodied control.",
            "project_ids": [str(p1.id)],
            "severity": "HIGH",
        },
    )
    p1.payload = {**p1.payload, "current_bottleneck_ids": [str(bt1.id)]}
    add(
        "Q1",
        "QUESTION",
        "Should high-frequency motor control depend on a large unified model?",
        "OPEN",
        {
            "text": "Should high-frequency motor control depend on a large unified model?",
            "scope": "high-frequency embodied control",
            "project_ids": [str(p1.id)],
        },
    )
    add(
        "B1",
        "BELIEF",
        "Large unified models may be unsuitable for the fastest embodied-control loop.",
        "ACTIVE",
        {
            "proposition": "Large unified models may be unsuitable for the fastest embodied-control loop.",
            "scope": "high-frequency embodied control",
            "confidence": 0.68,
        },
    )
    add(
        "M1",
        "MODEL",
        "Embodied intelligence contains partially separable cognitive intelligence and temporal motor intelligence.",
        "ACTIVE",
        {
            "description": "Embodied intelligence contains partially separable cognitive intelligence and temporal motor intelligence.",
            "model_type": "CONCEPTUAL",
            "node_data": {},
            "edge_data": {},
        },
    )
    p2 = add(
        "P2",
        "PROJECT",
        "Collective Intelligence",
        "ACTIVE",
        {"description": "Collective Intelligence", "goal_ids": [str(g1.id)], "current_bottleneck_ids": []},
    )
    add(
        "Q2",
        "QUESTION",
        "Can shared world models reduce explicit multi-agent communication?",
        "OPEN",
        {
            "text": "Can shared world models reduce explicit multi-agent communication?",
            "scope": "large-scale multi-agent embodied systems",
            "project_ids": [str(p2.id)],
        },
    )
    add(
        "B2",
        "BELIEF",
        "True swarm-style collective intelligence requires meaningful decentralized local intelligence.",
        "ACTIVE",
        {
            "proposition": "True swarm-style collective intelligence requires meaningful decentralized local intelligence.",
            "scope": "large-scale multi-agent embodied systems",
            "confidence": 0.65,
        },
    )
    add(
        "D1",
        "DECISION",
        "Evaluate startup equity terms independently from employment obligations.",
        "PENDING",
        {
            "rationale": "Minority equity in a robotics startup must not be confused with future employment flexibility.",
            "project_ids": [],
        },
    )
    db.add(KernelEdge(source_node_id=p1.id, target_node_id=g1.id, relationship="RELATES_TO"))
    db.add(KernelEdge(source_node_id=p2.id, target_node_id=g1.id, relationship="RELATES_TO"))
    db.add(KernelEdge(source_node_id=bt1.id, target_node_id=p1.id, relationship="BLOCKS"))
    db.flush()
    return nodes
