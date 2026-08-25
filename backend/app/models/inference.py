from uuid import UUID

from sqlalchemy import Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Inference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inferences"

    text: Mapped[str] = mapped_column(Text, nullable=False)
    author_type: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)

    sources: Mapped[list["InferenceSource"]] = relationship(
        back_populates="inference", cascade="all, delete-orphan"
    )


class InferenceSource(Base):
    __tablename__ = "inference_sources"

    inference_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("inferences.id"), primary_key=True)
    source_object_type: Mapped[str] = mapped_column(String, primary_key=True)
    source_object_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)

    inference: Mapped[Inference] = relationship(back_populates="sources")
