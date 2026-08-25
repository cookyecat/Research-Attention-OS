from uuid import UUID

from sqlalchemy import Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Claim(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "claims"

    source_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("sources.id"), nullable=False, index=True)
    event_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("events.id"), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    claim_type: Mapped[str] = mapped_column(String, nullable=False)
    attributed_to: Mapped[str | None] = mapped_column(Text, nullable=True)
    attribution_type: Mapped[str | None] = mapped_column(String, nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_extraction: Mapped[float | None] = mapped_column(Float, nullable=True)
    credibility_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    temporal_policy_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
