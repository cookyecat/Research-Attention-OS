from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.config import settings
from app.models.delivery import DeliveryEnvelope
from app.models.event import Event
from app.models.scheduler import AttentionPlan
from app.models.source import Source

DELIVERY_POLICY_VERSION = "delivery-policy-v0.1"


@dataclass(frozen=True)
class DeliveryPolicyDecision:
    delivery_class: str
    state: str
    channels: tuple[str, ...]


def _value(value) -> str:
    return str(getattr(value, "value", value))
def delivery_policy(disposition, urgency) -> DeliveryPolicyDecision:
    disp = _value(disposition).upper()
    urg = _value(urgency).upper()
    if disp == "DROP":
        return DeliveryPolicyDecision("SUPPRESSED", "SUPPRESSED", ())
    if disp == "AWARE":
        return DeliveryPolicyDecision("PASSIVE", "PASSIVE", ("IN_APP_DIGEST",))
    if disp == "WATCH":
        return DeliveryPolicyDecision("HELD_BY_WATCH", "HELD", ())
    if disp == "ENGAGE":
        channels = ["IN_APP_REALTIME"]
        if urg in {"PRIORITY", "PREEMPT"}:
            channels.extend(["EMAIL", "PUSH"])
        return DeliveryPolicyDecision("INTERRUPT", "PENDING", tuple(channels))
    raise ValueError(f"Unknown Attention disposition: {disp}")


def _channel_status(channels: tuple[str, ...]) -> dict:
    status: dict[str, dict] = {}
    for channel in channels:
        state = "PENDING"
        if channel == "IN_APP_DIGEST":
            state = "PASSIVE"
        elif channel == "EMAIL" and not (settings.delivery_email_to and settings.delivery_smtp_host):
            state = "UNAVAILABLE"
        elif channel == "PUSH" and not settings.delivery_push_webhook_url:
            state = "UNAVAILABLE"
        status[channel] = {"state": state, "attempts": 0, "sent_at": None, "last_error": None}
    return status
def _payload_for_plan(db: Session, plan: AttentionPlan) -> dict:
    source = None
    event = None
    candidate_type = _value(plan.candidate_type).upper()
    if candidate_type == "SOURCE":
        source = db.get(Source, plan.candidate_id)
    elif candidate_type == "EVENT":
        event = db.get(Event, plan.candidate_id)
    return {
        "attention_plan_id": str(plan.id),
        "candidate_type": _value(plan.candidate_type),
        "candidate_id": str(plan.candidate_id),
        "source_id": str(source.id) if source is not None else None,
        "event_id": str(event.id) if event is not None else None,
        "title": source.title if source is not None else (event.title if event is not None else None),
        "summary": event.summary if event is not None else None,
        "event_type": event.event_type if event is not None else None,
        "actors": list(event.actors or []) if event is not None else [],
        "action": event.action if event is not None else None,
        "object": event.object if event is not None else None,
        "current_state": event.current_state if event is not None else None,
        "time_context": event.time_context if event is not None else None,
        "location": event.location if event is not None else None,
        "canonical_url": source.canonical_url if source is not None else None,
        "disposition": _value(plan.disposition),
        "urgency": _value(plan.urgency),
        "expected_output": _value(plan.expected_output),
        "reason": plan.reason,
        "attention_created_at": plan.created_at.isoformat() if plan.created_at else None,
    }


def ensure_delivery_envelope(db: Session, plan: AttentionPlan) -> tuple[DeliveryEnvelope, bool]:
    existing = db.execute(
        select(DeliveryEnvelope).where(DeliveryEnvelope.attention_plan_id == plan.id)
    ).scalars().first()
    if existing is not None:
        return existing, False
    decision = delivery_policy(plan.disposition, plan.urgency)
    envelope = DeliveryEnvelope(
        attention_plan_id=plan.id,
        candidate_type=_value(plan.candidate_type),
        candidate_id=plan.candidate_id,
        disposition=_value(plan.disposition),
        urgency=_value(plan.urgency),
        delivery_class=decision.delivery_class,
        state=decision.state,
        channels=list(decision.channels),
        channel_status=_channel_status(decision.channels),
        payload=_payload_for_plan(db, plan),
        policy_version=DELIVERY_POLICY_VERSION,
    )
    db.add(envelope)
    db.flush()
    return envelope, True
def _refresh_state(envelope: DeliveryEnvelope) -> None:
    if envelope.state in {"SUPPRESSED", "PASSIVE", "HELD", "ACKNOWLEDGED", "DISMISSED"}:
        return
    statuses = [str((entry or {}).get("state") or "") for entry in (envelope.channel_status or {}).values()]
    if not statuses:
        return
    terminal = {"SENT", "UNAVAILABLE", "FAILED", "PASSIVE"}
    if any(state == "PENDING" for state in statuses):
        envelope.state = "PENDING"
        return
    if all(state in terminal for state in statuses):
        if any(state == "SENT" for state in statuses):
            envelope.state = "DELIVERED"
            envelope.delivered_at = envelope.delivered_at or datetime.now(timezone.utc)
        else:
            envelope.state = "FAILED"


def mark_delivery_channel(
    db: Session,
    envelope: DeliveryEnvelope,
    channel: str,
    *,
    state: str,
    error: str | None = None,
) -> DeliveryEnvelope:
    status = dict(envelope.channel_status or {})
    entry = dict(status.get(channel) or {"state": "PENDING", "attempts": 0, "sent_at": None, "last_error": None})
    entry["attempts"] = int(entry.get("attempts") or 0) + 1
    entry["state"] = state
    entry["last_error"] = error
    if state == "SENT":
        entry["sent_at"] = datetime.now(timezone.utc).isoformat()
    status[channel] = entry
    envelope.channel_status = status
    if error:
        envelope.last_error = error[:2000]
    flag_modified(envelope, "channel_status")
    _refresh_state(envelope)
    db.flush()
    return envelope
def acknowledge_delivery(db: Session, envelope: DeliveryEnvelope, outcome: str) -> DeliveryEnvelope:
    normalized = str(outcome or "").strip().upper()
    if normalized not in {"ACKNOWLEDGED", "DISMISSED"}:
        raise ValueError("Delivery outcome must be ACKNOWLEDGED or DISMISSED")
    envelope.user_outcome = normalized
    envelope.acknowledged_at = datetime.now(timezone.utc)
    envelope.state = normalized
    db.flush()
    return envelope


def envelope_out(envelope: DeliveryEnvelope) -> dict:
    return {
        "id": str(envelope.id),
        "attention_plan_id": str(envelope.attention_plan_id),
        "candidate_type": envelope.candidate_type,
        "candidate_id": str(envelope.candidate_id),
        "disposition": envelope.disposition,
        "urgency": envelope.urgency,
        "delivery_class": envelope.delivery_class,
        "state": envelope.state,
        "channels": list(envelope.channels or []),
        "channel_status": dict(envelope.channel_status or {}),
        "payload": dict(envelope.payload or {}),
        "policy_version": envelope.policy_version,
        "available_at": envelope.available_at.isoformat() if envelope.available_at else None,
        "delivered_at": envelope.delivered_at.isoformat() if envelope.delivered_at else None,
        "acknowledged_at": envelope.acknowledged_at.isoformat() if envelope.acknowledged_at else None,
        "user_outcome": envelope.user_outcome,
        "last_error": envelope.last_error,
        "created_at": envelope.created_at.isoformat() if envelope.created_at else None,
    }
def delivery_authority(db: Session, envelope: DeliveryEnvelope) -> dict:
    """Return whether a persisted envelope is backed by an authoritative AnalysisRun."""
    from app.execution_integrity import stored_run_authority
    from app.models.analysis import AnalysisRun

    plan = db.get(AttentionPlan, envelope.attention_plan_id)
    if plan is None:
        return {"authoritative": False, "reason": "missing-attention-plan"}
    if plan.analysis_run_id is None:
        return {"authoritative": False, "reason": "missing-analysis-run"}
    run = db.get(AnalysisRun, plan.analysis_run_id)
    if run is None:
        return {"authoritative": False, "reason": "missing-analysis-run"}
    return stored_run_authority(run)


def list_visible_deliveries(db: Session, *, limit: int = 100) -> list[DeliveryEnvelope]:
    rows = list(
        db.execute(
            select(DeliveryEnvelope)
            .where(DeliveryEnvelope.delivery_class.in_(["PASSIVE", "INTERRUPT"]))
            .order_by(DeliveryEnvelope.created_at.desc())
            .limit(max(1, min(int(limit), 500)))
        ).scalars().all()
    )
    return [row for row in rows if delivery_authority(db, row).get("authoritative")]


def pending_realtime_deliveries(db: Session, *, limit: int = 20) -> list[DeliveryEnvelope]:
    rows = db.execute(
        select(DeliveryEnvelope)
        .where(
            DeliveryEnvelope.delivery_class == "INTERRUPT",
            DeliveryEnvelope.state.in_(["PENDING", "DELIVERED"]),
        )
        .order_by(DeliveryEnvelope.created_at)
        .limit(max(1, min(int(limit), 100)))
    ).scalars().all()
    return [
        row for row in rows
        if ((row.channel_status or {}).get("IN_APP_REALTIME") or {}).get("state") == "PENDING"
        and delivery_authority(db, row).get("authoritative")
    ]


def delivery_metrics(db: Session) -> dict:
    rows = list(db.execute(select(DeliveryEnvelope)).scalars().all())
    by_class: dict[str, int] = {}
    by_state: dict[str, int] = {}
    human_interruptions = 0
    for row in rows:
        by_class[row.delivery_class] = by_class.get(row.delivery_class, 0) + 1
        by_state[row.state] = by_state.get(row.state, 0) + 1
        if ((row.channel_status or {}).get("IN_APP_REALTIME") or {}).get("state") == "SENT":
            human_interruptions += 1
    return {
        "policy_version": DELIVERY_POLICY_VERSION,
        "total_envelopes": len(rows),
        "by_delivery_class": by_class,
        "by_state": by_state,
        "human_interruptions": human_interruptions,
    }
