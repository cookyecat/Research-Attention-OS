from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.execution_integrity import require_side_effects_authorized
from app.models.delivery import DeliveryEnvelope
from app.services.delivery import (
    acknowledge_delivery,
    delivery_metrics,
    envelope_out,
    list_visible_deliveries,
    mark_delivery_channel,
    pending_realtime_deliveries,
)

router = APIRouter()


def _require_delivery_write_authority() -> None:
    try:
        require_side_effects_authorized()
    except RuntimeError as exc:
        raise HTTPException(403, str(exc)) from exc



@router.get("")
def list_deliveries(
    limit: int = Query(default=100, ge=1, le=500),
    delivery_class: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_db),
):
    if delivery_class is None and state is None:
        rows = list_visible_deliveries(db, limit=limit)
    else:
        q = select(DeliveryEnvelope)
        if delivery_class:
            q = q.where(DeliveryEnvelope.delivery_class == delivery_class.upper())
        if state:
            q = q.where(DeliveryEnvelope.state == state.upper())
        rows = list(db.execute(q.order_by(DeliveryEnvelope.created_at.desc()).limit(limit)).scalars().all())
    return [envelope_out(row) for row in rows]


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    return delivery_metrics(db)


@router.post("/{delivery_id}/acknowledge")
def acknowledge(delivery_id: UUID, db: Session = Depends(get_db)):
    _require_delivery_write_authority()
    row = db.get(DeliveryEnvelope, delivery_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return envelope_out(acknowledge_delivery(db, row, "ACKNOWLEDGED"))


@router.post("/{delivery_id}/dismiss")
def dismiss(delivery_id: UUID, db: Session = Depends(get_db)):
    _require_delivery_write_authority()
    row = db.get(DeliveryEnvelope, delivery_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return envelope_out(acknowledge_delivery(db, row, "DISMISSED"))


@router.websocket("/ws")
async def realtime_delivery(websocket: WebSocket, db: Session = Depends(get_db)):
    try:
        require_side_effects_authorized()
    except RuntimeError:
        await websocket.close(code=1008, reason="Phase13 side-effect authority required")
        return
    await websocket.accept()
    try:
        while True:
            rows = pending_realtime_deliveries(db, limit=20)
            for row in rows:
                await websocket.send_json(envelope_out(row))
                mark_delivery_channel(db, row, "IN_APP_REALTIME", state="SENT")
            db.commit()
            # Keep the connection durable without coupling delivery latency to cognition.
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return
