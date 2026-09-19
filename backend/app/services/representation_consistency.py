from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import EventLineage


class RepresentationConsistencyError(ValueError):
    pass


def validate_lineage_edge(
    db: Session,
    *,
    predecessor_event_id: UUID,
    successor_event_id: UUID,
) -> None:
    """Reject topology edges that would make Event hypothesis lineage cyclic."""
    if predecessor_event_id == successor_event_id:
        raise RepresentationConsistencyError("Event lineage cannot point to itself")

    # A new predecessor -> successor edge is invalid iff predecessor is already
    # reachable from successor. This is a graph invariant, not a semantic
    # SAME_EVENT judgment.
    adjacency: dict[UUID, set[UUID]] = {}
    for pred, succ in db.execute(
        select(EventLineage.predecessor_event_id, EventLineage.successor_event_id)
    ).all():
        adjacency.setdefault(pred, set()).add(succ)

    stack = [successor_event_id]
    seen: set[UUID] = set()
    while stack:
        current = stack.pop()
        if current == predecessor_event_id:
            raise RepresentationConsistencyError("Event lineage transition would create a cycle")
        if current in seen:
            continue
        seen.add(current)
        stack.extend(adjacency.get(current, ()))
