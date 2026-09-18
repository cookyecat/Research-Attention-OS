from __future__ import annotations

import argparse
import time

from dotenv import load_dotenv


def deliver_external_once(limit: int = 20) -> dict:
    # Runtime imports are intentionally delayed so --env-file can establish
    # the same delivery transport contract as the HTTP backend before config
    # is materialized.
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models.delivery import DeliveryEnvelope
    from app.execution_integrity import health_contract
    from app.services.delivery import delivery_authority, mark_delivery_channel
    from app.services.delivery_transports import (
        DeliveryTransportError,
        send_email_delivery,
        send_push_delivery,
    )

    counts = {"checked": 0, "email_sent": 0, "push_sent": 0, "failed": 0, "authority_blocked": 0}
    health = health_contract()
    if not ((health.get("authority") or {}).get("side_effects_authorized")):
        counts["authority_blocked"] = 1
        return counts
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
            if not delivery_authority(db, row).get("authoritative"):
                counts["authority_blocked"] += 1
                continue
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
    parser = argparse.ArgumentParser(description="RAOS Delivery Plane external transport worker")
    parser.add_argument("--interval", type=float, default=None)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--env-file", default=None, help="dotenv file loaded before RAOS runtime imports")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=False)

    from app.config import settings

    interval = settings.delivery_poll_seconds if args.interval is None else args.interval
    while True:
        deliver_external_once(args.limit)
        if args.once:
            break
        time.sleep(max(0.2, interval))


if __name__ == "__main__":
    main()
