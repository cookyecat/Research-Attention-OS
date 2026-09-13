from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.acquisition import AcquisitionObservation, ExternalInformationItem, InformationSnapshot, SourceDefinition
from app.services.acquisition import poll_due_sources, poll_source_by_id

router = APIRouter()


class SourceDefinitionCreate(BaseModel):
    name: str
    source_type: str = "RSS"
    locator: str
    enabled: bool = True
    poll_interval_seconds: int = Field(default=1800, ge=1)


class SourceDefinitionUpdate(BaseModel):
    name: str | None = None
    locator: str | None = None
    enabled: bool | None = None
    poll_interval_seconds: int | None = Field(default=None, ge=1)


def _source_out(row: SourceDefinition) -> dict:
    return {
        "id": str(row.id),
        "name": row.name,
        "source_type": row.source_type,
        "locator": row.locator,
        "enabled": row.enabled,
        "poll_interval_seconds": row.poll_interval_seconds,
        "last_polled_at": row.last_polled_at.isoformat() if row.last_polled_at else None,
    }


@router.post("/sources")
def create_acquisition_source(body: SourceDefinitionCreate, db: Session = Depends(get_db)):
    if body.source_type.upper() != "RSS":
        raise HTTPException(400, "Acquisition v0.1 supports RSS only")
    row = SourceDefinition(
        name=body.name,
        source_type=body.source_type.upper(),
        locator=body.locator,
        enabled=body.enabled,
        poll_interval_seconds=body.poll_interval_seconds,
    )
    db.add(row)
    db.flush()
    return _source_out(row)


@router.get("/sources")
def list_acquisition_sources(db: Session = Depends(get_db)):
    rows = db.execute(select(SourceDefinition).order_by(SourceDefinition.created_at)).scalars().all()
    return [_source_out(row) for row in rows]




@router.patch("/sources/{source_id}")
def update_acquisition_source(source_id: UUID, body: SourceDefinitionUpdate, db: Session = Depends(get_db)):
    row = db.get(SourceDefinition, source_id)
    if row is None:
        raise HTTPException(404, "Acquisition Source not found")
    for field in ("name", "locator", "enabled", "poll_interval_seconds"):
        value = getattr(body, field)
        if value is not None:
            setattr(row, field, value)
    db.flush()
    return _source_out(row)


@router.post("/sources/{source_id}/poll")
def poll_acquisition_source(
    source_id: UUID,
    limit: int = Query(default=5, ge=1, le=100),
    analyze: bool = True,
    db: Session = Depends(get_db),
):
    try:
        return poll_source_by_id(db, source_id, limit=limit, analyze=analyze)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/poll-due")
def poll_due(limit_per_source: int = Query(default=5, ge=1, le=100), analyze: bool = True, db: Session = Depends(get_db)):
    return {"polls": poll_due_sources(db, limit_per_source=limit_per_source, analyze=analyze)}


@router.get("/items")
def list_external_items(db: Session = Depends(get_db)):
    rows = db.execute(select(ExternalInformationItem).order_by(ExternalInformationItem.created_at.desc())).scalars().all()
    out = []
    for item in rows:
        observations = db.execute(
            select(AcquisitionObservation).where(AcquisitionObservation.external_item_id == item.id)
        ).scalars().all()
        snapshots = db.execute(
            select(InformationSnapshot).where(InformationSnapshot.external_item_id == item.id)
        ).scalars().all()
        out.append({
            "id": str(item.id),
            "identity_key": item.identity_key,
            "title": item.title,
            "canonical_url": item.canonical_url,
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "observation_count": len(observations),
            "snapshot_count": len(snapshots),
            "raos_source_ids": [str(row.raos_source_id) for row in snapshots],
        })
    return out
