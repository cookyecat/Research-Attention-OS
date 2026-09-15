from __future__ import annotations

import argparse
import time

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models.delivery import DeliveryEnvelope
from app.services.delivery import mark_delivery_channel
from app.services.delivery_transports import DeliveryTransportError, send_email_delivery, send_push_delivery


def deliver_external_once(limit: int = 20) -> dict:
    counts = {"checked": 0, "email_sent": 0, "push_sent": 0, "failed": 0}
    with SessionLocal() as db:
        rows = list(
            db.execute(
                select(DeliveryEnvelope)
                .where(DeliveryEnvelope.delivery_class == "INTERRUPT")
                .order_by(DeliveryEnvelope.created_at)
                .limit(max(1, min(int(limit), 100)))
            ).scalars().all()
        )
        for row in rows:
            status = dict(row.channel_status or {})
            for channel, sender, key in (
                ("EMAIL", send_email_delivery, "email_sent"),
                ("PUSH", send_push_delivery, "push_sent"),
            ):
                entry = dict(status.get(channel) or {})
                if entry.get("state") != "PENDING":
                    continue
                counts["checked"] += 1
                try:
                    sender(row)
                    mark_delivery_channel(db, row, channel, state="SENT")
                    counts[key] += 1
                except DeliveryTransportError as exc:
                    mark_delivery_channel(db, row, channel, state="FAILED", error=str(exc))
                    counts["failed"] += 1
            db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=float, default=settings.delivery_poll_seconds)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    while True:
        deliver_external_once(args.limit)
        if args.once:
            break
        time.sleep(max(0.2, args.interval))


if __name__ == "__main__":
    main()
