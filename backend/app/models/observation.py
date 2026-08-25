from uuid import UUID

from sqlalchemy import Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Observation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "observations"

    source_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("sources.id"), nullable=True, index=True)
    event_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("events.id"), nullable=True)
    observer_type: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    observation_type: Mapped[str] = mapped_column(String, nullable=False)
    measured_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    temporal_policy_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
