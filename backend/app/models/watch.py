from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Watch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "watches"

    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_ref: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")
    created_reason: Mapped[str] = mapped_column(Text, nullable=False)
    kernel_target_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    triggers: Mapped[list["WatchTrigger"]] = relationship(back_populates="watch", cascade="all, delete-orphan")


class WatchTrigger(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "watch_triggers"

    watch_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("watches.id"), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String, nullable=False)
    trigger_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    watch: Mapped[Watch] = relationship(back_populates="triggers")
