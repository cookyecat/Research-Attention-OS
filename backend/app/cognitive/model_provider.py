from __future__ import annotations

import json

from app.cognitive.client import chat_json, estimate_cost_usd
from app.cognitive.prompts import (
    DELTA_SYSTEM,
    DELTA_USER,
    EVIDENCE_SYSTEM,
    EVIDENCE_USER,
    EXTRACT_SYSTEM,
    EXTRACT_USER,
    JUDGMENT_SYSTEM,
    JUDGMENT_USER,
    MATCH_SYSTEM,
    MATCH_USER,
)
from app.cognitive.validators import validate_evidence_strength, validate_extraction
from app.config import settings
from app.enums import AttributionType, AuthorType, ClaimType, ObservationType, ObserverType, Stance, Strength
from app.models.kernel import KernelNode
from app.services.deltas import ModelDelta, PatchDraft, propose_patches
from app.services.extraction import (
    ExtractedClaim,
    ExtractedEvidence,
    ExtractedInference,
    ExtractedObservation,
    ExtractionResult,
)
from app.services.matching import KernelMatch, node_text
from app.services.retrieval import retrieve_kernel_candidates, try_embed_query
from app.services.scheduler import SchedulerFeatures


def _enum(cls, value, default):
    if value is None:
        return default
    try:
        return cls(str(value).upper())
    except ValueError:
        return default


class ModelBackedCognitiveProvider:
    """Open-world understanding via OpenAI-compatible structured JSON + deterministic validators."""

    provider_type = "model"

    def __init__(self, chat_fn=chat_json):
        self._chat = chat_fn
        self.last_meta: dict = {
            "latency_ms": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "estimated_cost_usd": 0.0,
            "model": None,
        }

    def _complete(self, system: str, user: str) -> dict:
        parsed, meta = self._chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        self.last_meta["latency_ms"] = int(self.last_meta.get("latency_ms") or 0) + int(meta.get("latency_ms") or 0)
        self.last_meta["prompt_tokens"] = int(self.last_meta.get("prompt_tokens") or 0) + int(meta.get("prompt_tokens") or 0)
        self.last_meta["completion_tokens"] = int(self.last_meta.get("completion_tokens") or 0) + int(
            meta.get("completion_tokens") or 0
        )
        self.last_meta["model"] = meta.get("model") or self.last_meta.get("model")
        self.last_meta["estimated_cost_usd"] = estimate_cost_usd(
            int(self.last_meta["prompt_tokens"]),
            int(self.last_meta["completion_tokens"]),
        )
        return parsed

    def extract_information(self, text: str, source_type: str, title: str | None = None) -> ExtractionResult:
        data = self._complete(
            EXTRACT_SYSTEM,
            EXTRACT_USER.format(source_type=source_type, title=title or "", text=text[:12000]),
        )
        result = ExtractionResult(
            event_title=data.get("event_title"),
            event_summary=data.get("event_summary"),
            marketing_heavy=bool(data.get("marketing_heavy")),
            current_facts=list(data.get("current_facts") or []),
            future_plans=list(data.get("future_plans") or []),
            technical_claims=list(data.get("technical_claims") or []),
            promotional_framing=list(data.get("promotional_framing") or []),
        )
        for raw in data.get("claims") or []:
            result.claims.append(
                ExtractedClaim(
                    text=raw.get("text") or "",
                    claim_type=_enum(ClaimType, raw.get("claim_type"), ClaimType.FACTUAL),
                    attributed_to=raw.get("attributed_to"),
                    attribution_type=_enum(AttributionType, raw.get("attribution_type"), AttributionType.UNKNOWN),
                    confidence_extraction=float(raw.get("extraction_confidence") or 0.6),
                    temporal_status=str(raw.get("temporal_status") or "CURRENT"),
                )
            )
        for raw in data.get("observations") or []:
            result.observations.append(
                ExtractedObservation(
                    text=raw.get("text") or "",
                    observer_type=_enum(ObserverType, raw.get("observer"), ObserverType.SYSTEM_EXTRACTED),
                    observation_type=_enum(ObservationType, raw.get("observation_type"), ObservationType.OTHER),
                    confidence=float(raw.get("confidence") or 0.6),
                )
            )
        for raw in data.get("inferences") or []:
            result.inferences.append(
                ExtractedInference(
                    text=raw.get("text") or "",
                    author_type=AuthorType.AI,
                    confidence=float(raw.get("confidence") or 0.4),
                    source_roles=[str(raw.get("derived_from") or "model")],
                )
            )
        return validate_extraction(result)

    def match_kernel(
        self,
        extraction: ExtractionResult,
        nodes: list[KernelNode],
        extra_text: str = "",
    ) -> list[KernelMatch]:
        blob = " ".join(
            [extra_text]
            + [c.text for c in extraction.claims]
            + [o.text for o in extraction.observations]
        )
        qvec, _model = try_embed_query(blob[:4000])
        candidates = retrieve_kernel_candidates(blob, nodes, query_embedding=qvec)
        if not candidates:
            candidates = nodes[:12]
        payload = []
        for node in candidates:
            payload.append(
                {
                    "kernel_node_id": str(node.id),
                    "node_type": node.node_type,
                    "title": node.title,
                    "text": node_text(node)[:800],
                }
            )
        data = self._complete(
            MATCH_SYSTEM,
            MATCH_USER.format(
                text=blob[:8000],
                claims=json.dumps([c.text for c in extraction.claims]),
                observations=json.dumps([o.text for o in extraction.observations]),
                kernel_candidates=json.dumps(payload),
            ),
        )
        by_id = {str(n.id): n for n in nodes}
        matches: list[KernelMatch] = []
        for raw in data.get("matches") or []:
            node = by_id.get(str(raw.get("kernel_node_id")))
            if node is None:
                continue
            rtype = str(raw.get("relevance_type") or "TOPIC").upper()
            matches.append(
                KernelMatch(
                    node_id=node.id,
                    node_type=node.node_type,
                    title=node.title,
                    score=float(raw.get("score") or 0.5),
                    reason=str(raw.get("reason") or rtype),
                    structural=rtype == "STRUCTURAL",
                    relevance_type=rtype,
                )
            )
        return matches

    def reason_evidence(self, extraction: ExtractionResult) -> ExtractionResult:
        if not extraction.claims or not (extraction.observations or extraction.inferences):
            return extraction
        data = self._complete(
            EVIDENCE_SYSTEM,
            EVIDENCE_USER.format(
                claims=json.dumps([{"i": i, "text": c.text} for i, c in enumerate(extraction.claims)]),
                observations=json.dumps([{"i": i, "text": o.text} for i, o in enumerate(extraction.observations)]),
                inferences=json.dumps([{"i": i, "text": inf.text} for i, inf in enumerate(extraction.inferences)]),
            ),
        )
        links = []
        for raw in data.get("links") or []:
            stance, strength = validate_evidence_strength(
                str(raw.get("stance") or "NEUTRAL"),
                str(raw.get("strength") or "WEAK"),
                extraction.evidence_maturity,
            )
            try:
                links.append(
                    ExtractedEvidence(
                        source_role=str(raw.get("source_role") or "OBSERVATION"),
                        source_index=int(raw.get("source_index") or 0),
                        target_role=str(raw.get("target_role") or "CLAIM"),
                        target_index=int(raw.get("target_index") or 0),
                        stance=Stance(stance),
                        strength=Strength(strength),
                        confidence=min(float(raw.get("confidence") or 0.5), 0.85),
                        scope=raw.get("scope"),
                    )
                )
            except ValueError:
                continue
        extraction.evidence = links
        return extraction

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
    ) -> SchedulerFeatures:
        data = self._complete(
            JUDGMENT_SYSTEM,
            JUDGMENT_USER.format(
                text=text[:8000],
                matches=json.dumps([{"id": str(m.node_id), "type": m.node_type, "title": m.title, "score": m.score, "rel": m.relevance_type} for m in matches]),
                is_duplicate=is_duplicate,
                independent_source_count=independent_source_count,
                secondary_report_count=secondary_report_count,
            ),
        )
        threatened = threatens_active_work
        if threatened is None:
            threatened = bool(data.get("threatens_active_work"))
        return SchedulerFeatures(
            topic_relevance=float(data.get("topic_relevance") or 0),
            structural_relevance=float(data.get("structural_relevance") or 0),
            decision_relevance=float(data.get("decision_relevance") or 0),
            novelty=float(data.get("novelty") or 0.5),
            credibility=float(data.get("credibility") or 0.5),
            kernel_delta=float(data.get("kernel_delta") or 0),
            bottleneck_alignment=float(data.get("bottleneck_alignment") or 0),
            disagreement=float(data.get("disagreement") or 0),
            actionability=float(data.get("actionability") or 0),
            temporal_value=float(data.get("temporal_value") or 0.4),
            cognitive_cost=float(data.get("cognitive_cost") or 5),
            is_duplicate=is_duplicate,
            evidence_maturity=float(data.get("evidence_maturity") or extraction.evidence_maturity),
            threatens_active_work=bool(threatened),
            marketing_heavy=bool(data.get("marketing_heavy") or extraction.marketing_heavy),
            sources_conflict=bool(extraction.evidence),
            independent_source_count=independent_source_count,
            secondary_report_count=secondary_report_count,
            high_quality_technical=bool(data.get("high_quality_technical")),
            foundational_paper=bool(data.get("foundational_paper")),
        )

    def propose_model_delta(
        self,
        text: str,
        extraction: ExtractionResult,
        matches: list[KernelMatch],
        features: SchedulerFeatures,
        nodes: list[KernelNode],
    ) -> ModelDelta:
        kernel_snap = [
            {"id": str(n.id), "type": n.node_type, "title": n.title, "payload": n.payload}
            for n in nodes
            if any(m.node_id == n.id for m in matches)
        ]
        data = self._complete(
            DELTA_SYSTEM,
            DELTA_USER.format(
                text=text[:8000],
                matches=json.dumps([{"id": str(m.node_id), "title": m.title, "reason": m.reason} for m in matches]),
                kernel=json.dumps(kernel_snap),
            ),
        )
        return ModelDelta(
            summary=str(data.get("summary") or "No committed Kernel change is implied yet."),
            what_could_change=list(data.get("what_could_change") or []),
            distinctions=list(data.get("distinctions") or []),
            questions=list(data.get("new_questions") or []),
            admission_allowed=bool(data.get("admission_allowed")),
            affected_kernel_nodes=list(data.get("affected_kernel_nodes") or []),
            possible_hypotheses=list(data.get("possible_hypotheses") or []),
            decision_implications=list(data.get("decision_implications") or []),
            epistemic_risk=str(data.get("epistemic_risk") or ""),
            evidence_maturity=float(data.get("evidence_maturity") or features.evidence_maturity),
            rationale=str(data.get("rationale") or ""),
        )

    def propose_patches(
        self,
        text: str,
        delta: ModelDelta,
        matches: list[KernelMatch],
        features: SchedulerFeatures,
        nodes: list[KernelNode],
        evidence_link_ids: list[str],
    ) -> list[PatchDraft]:
        # Patches remain deterministic from delta + admission rules (no silent Kernel writes).
        return propose_patches(text, delta, matches, features, nodes, evidence_link_ids)
