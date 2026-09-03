from __future__ import annotations

from app.cognitive.base import CognitiveAnalysisProvider
from app.models.kernel import KernelNode
from app.services.cognitive_impact import CognitiveImpactAssessment, assess_impact_from_rules
from app.services.deltas import ModelDelta, PatchDraft, build_model_delta, propose_patches
from app.services.extraction import ExtractionResult, extract_from_text
from app.services.matching import KernelMatch, match_kernel
from app.services.scheduler import SchedulerFeatures


class RuleBasedCognitiveProvider:
    """Regression baseline / fallback / guardrail. Preserves A–O semantics."""

    provider_type = "rule"

    def extract_information(self, text: str, source_type: str, title: str | None = None) -> ExtractionResult:
        return extract_from_text(text, source_type, title)

    def match_kernel(
        self,
        extraction: ExtractionResult,
        nodes: list[KernelNode],
        extra_text: str = "",
        **_kwargs,
    ) -> list[KernelMatch]:
        return match_kernel(extraction, nodes, extra_text=extra_text)

    def reason_evidence(self, extraction: ExtractionResult, **_kwargs) -> ExtractionResult:
        return extraction

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
        nodes=None,
    ) -> CognitiveImpactAssessment:
        assessment = assess_impact_from_rules(
            text,
            extraction,
            matches,
            is_duplicate=is_duplicate,
            independent_source_count=independent_source_count,
            secondary_report_count=secondary_report_count,
            threatens_active_work=threatens_active_work,
            nodes=nodes,
        )
        self.last_raw_effects = list(assessment.raw_effects or [])
        return assessment

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
        nodes=None,
    ) -> SchedulerFeatures:
        return self.assess_cognitive_impact(
            text,
            extraction,
            matches,
            is_duplicate=is_duplicate,
            independent_source_count=independent_source_count,
            secondary_report_count=secondary_report_count,
            threatens_active_work=threatens_active_work,
            nodes=nodes,
        ).features

    def propose_model_delta(
        self,
        text: str,
        extraction: ExtractionResult,
        matches: list[KernelMatch],
        features: SchedulerFeatures,
        nodes: list[KernelNode],
    ) -> ModelDelta:
        return build_model_delta(text, extraction, matches, features, nodes)

    def propose_patches(
        self,
        text: str,
        delta: ModelDelta,
        matches: list[KernelMatch],
        features: SchedulerFeatures,
        nodes: list[KernelNode],
        evidence_link_ids: list[str],
    ) -> list[PatchDraft]:
        return propose_patches(text, delta, matches, features, nodes, evidence_link_ids)
