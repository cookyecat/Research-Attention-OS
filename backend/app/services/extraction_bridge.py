"""Narrow production seam for alternative semantic extraction paths.

The online pipeline owns this interface. Developer dogfood may execute a frozen research
implementation directly so research and online semantics share one truth source.
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


def research_aligned_extraction_bridge():
    """Load the exact closed Phase 8C.2 Sensor/Auditor bridge for dogfood.

    Developer dogfood intentionally executes the frozen research implementation directly.
    The repository root is added explicitly because uvicorn is normally launched from
    ``backend/``; this keeps one Sensor/Auditor truth source instead of copying it.
    """
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[3]
    root = str(repo_root)
    if root not in sys.path:
        sys.path.insert(0, root)
    from eval.live.phase8c2_production_sensor_bridge_v0_1 import SemanticSensorProductionBridgeV0_1

    return SemanticSensorProductionBridgeV0_1()
