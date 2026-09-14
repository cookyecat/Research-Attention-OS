from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class DiscoveredExternalItem:
    ref: str
    external_id: str | None = None
    title: str | None = None
    published_at: datetime | None = None
    metadata: dict = field(default_factory=dict)
