from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from typing import Callable

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.delivery import DeliveryEnvelope
from app.services.delivery import mark_delivery_channel


class DeliveryTransportError(RuntimeError):
    pass


def _email_recipients() -> list[str]:
    raw = settings.delivery_email_to or ""
    return [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]


def _delivery_text(envelope: DeliveryEnvelope) -> str:
    payload = envelope.payload or {}
    title = payload.get("title") or "RAOS attention item"
    reason = payload.get("reason") or ""
    url = payload.get("canonical_url") or ""
    return f"{title}\n\nRAOS: {envelope.disposition} / {envelope.urgency}\n{reason}\n\n{url}".strip()
def send_email_delivery(envelope: DeliveryEnvelope) -> None:
    recipients = _email_recipients()
    if not recipients or not settings.delivery_smtp_host:
        raise DeliveryTransportError("Email transport is not configured")
    sender = settings.delivery_smtp_from or settings.delivery_smtp_username or "raos@localhost"
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = f"RAOS · {envelope.urgency} · {(envelope.payload or {}).get('title') or 'Attention'}"
    message.set_content(_delivery_text(envelope))
    try:
        smtp_cls = smtplib.SMTP_SSL if settings.delivery_smtp_ssl else smtplib.SMTP
        with smtp_cls(settings.delivery_smtp_host, settings.delivery_smtp_port, timeout=20) as smtp:
            if settings.delivery_smtp_starttls and not settings.delivery_smtp_ssl:
                smtp.starttls()
            if settings.delivery_smtp_username:
                smtp.login(settings.delivery_smtp_username, settings.delivery_smtp_password or "")
            refused = smtp.send_message(message)
            if refused:
                raise DeliveryTransportError(f"SMTP refused {len(refused)} recipient(s)")
    except Exception as exc:
        raise DeliveryTransportError(str(exc)) from exc


def send_push_delivery(envelope: DeliveryEnvelope) -> None:
    if not settings.delivery_push_webhook_url:
        raise DeliveryTransportError("Push webhook transport is not configured")
    payload = {
        "event": "raos_attention",
        "delivery_id": str(envelope.id),
        "attention_plan_id": str(envelope.attention_plan_id),
        "disposition": envelope.disposition,
        "urgency": envelope.urgency,
        "payload": envelope.payload or {},
    }
    try:
        response = httpx.post(settings.delivery_push_webhook_url, json=payload, timeout=20)
        response.raise_for_status()
    except Exception as exc:
        raise DeliveryTransportError(str(exc)) from exc
