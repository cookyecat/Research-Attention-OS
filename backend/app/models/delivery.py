from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base
from app.models.base import UUIDPrimaryKeyMixin


class DeliveryEnvelope(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "delivery_envelopes"

    attention_plan_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("attention_plans.id"), nullable=False, unique=True, index=True
    )
    candidate_type: Mapped[str] = mapped_column(String, nullable=False)
    candidate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    disposition: Mapped[str] = mapped_column(String, nullable=False, index=True)
    urgency: Mapped[str] = mapped_column(String, nullable=False)
    delivery_class: Mapped[str] = mapped_column(String, nullable=False, index=True)
    state: Mapped[str] = mapped_column(String, nullable=False, index=True)
    channels: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    channel_status: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_outcome: Mapped[str | None] = mapped_column(String, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
