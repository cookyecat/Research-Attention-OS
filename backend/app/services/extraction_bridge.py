"""Narrow production seam for alternative semantic extraction paths.

The production pipeline owns this interface. Candidate Sensor/Auditor implementations
may satisfy it from eval/live without making backend/app depend on research modules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.models.source import Source
from app.services.extraction import ExtractionResult


@dataclass
class ExtractionBridgeResult:
    extraction: ExtractionResult
    diagnostics: dict[str, Any] = field(default_factory=dict)


class ExtractionBridge(Protocol):
    """Injectable representation boundary upstream of production Locate/Impact."""

    def execution_snapshot(self) -> dict[str, Any]:
        """Return deterministic identity/provenance fields; never include secrets."""
        ...

    def extract(
        self,
        source: Source,
        extra_sources: list[Source],
    ) -> ExtractionBridgeResult:
        """Produce one audited production ExtractionResult for the supplied source set."""
        ...
