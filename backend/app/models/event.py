from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Event(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "events"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    status: Mapped[str] = mapped_column(String, nullable=False, default="CANDIDATE")

    source_links: Mapped[list["EventSource"]] = orm_relationship(back_populates="event", cascade="all, delete-orphan")


class EventSource(Base):
    __tablename__ = "event_sources"

    event_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("events.id"), primary_key=True)
    source_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("sources.id"), primary_key=True)
    relationship: Mapped[str] = mapped_column(String, nullable=False, default="REPORTS")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    event: Mapped[Event] = orm_relationship(back_populates="source_links")
