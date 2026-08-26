from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from app.models.kernel import KernelNode
from app.services.extraction import ExtractionResult
from app.services.matching import KernelMatch
from app.services.cognitive_impact import CognitiveImpactAssessment
from app.services.scheduler import SchedulerFeatures
from app.services.deltas import ModelDelta, PatchDraft


@dataclass
class ProviderMeta:
    provider_type: str
    model_name: str | None = None
    prompt_version: str | None = None
    fallback_used: bool = False
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    embedding_model_version: str = "none"


class CognitiveAnalysisProvider(Protocol):
    provider_type: str

    def extract_information(
        self,
        text: str,
        source_type: str,
        title: str | None = None,
    ) -> ExtractionResult: ...

    def match_kernel(
        self,
        extraction: ExtractionResult,
        nodes: list[KernelNode],
        extra_text: str = "",
    ) -> list[KernelMatch]: ...

    def reason_evidence(
        self,
        extraction: ExtractionResult,
        *,
        independent_source_count: int = 1,
    ) -> ExtractionResult: ...

    def assess_cognitive_impact(
        self,
        text: str,
        extraction: ExtractionResult,
        matches: list[KernelMatch],
        *,
        is_duplicate: bool = False,
        independent_source_count: int = 1,
        secondary_report_count: int = 0,
        threatens_active_work: bool | None = None,
        nodes: list[KernelNode] | None = None,
    ) -> CognitiveImpactAssessment: ...

    def judge_features(
        self,
        text: str,
        extraction: ExtractionResult,
        matches: list[KernelMatch],
        *,
        is_duplicate: bool = False,
        independent_source_count: int = 1,
        secondary_report_count: int = 0,
        threatens_active_work: bool | None = None,
        nodes: list[KernelNode] | None = None,
    ) -> SchedulerFeatures: ...

    def propose_model_delta(
        self,
        text: str,
        extraction: ExtractionResult,
        matches: list[KernelMatch],
        features: SchedulerFeatures,
        nodes: list[KernelNode],
    ) -> ModelDelta: ...

    def propose_patches(
        self,
        text: str,
        delta: ModelDelta,
        matches: list[KernelMatch],
        features: SchedulerFeatures,
        nodes: list[KernelNode],
        evidence_link_ids: list[str],
    ) -> list[PatchDraft]: ...
