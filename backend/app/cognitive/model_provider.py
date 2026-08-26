from __future__ import annotations

import json
from uuid import UUID

from app.cognitive.client import SchemaValidationError, chat_json, chat_json_schema, estimate_cost_usd
from app.cognitive.runtime import STAGE_RUNTIME
from app.cognitive.prompts import (
    DELTA_SYSTEM,
    DELTA_USER,
    EVIDENCE_SYSTEM,
    EVIDENCE_USER,
    EXTRACT_SYSTEM,
    extraction_user_prompt,
    JUDGMENT_SYSTEM,
    JUDGMENT_USER,
    MATCH_SYSTEM,
    MATCH_USER,
)
from app.cognitive.schemas import (
    EvidenceReasoningResponse,
    ExtractionResponse,
    KernelMatchResponse,
    ModelDeltaResponse,
    SchedulerJudgmentResponse,
)
from app.cognitive.validators import validate_evidence_strength, validate_extraction
from app.config import settings
from app.enums import AuthorType
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
from app.services.retrieval import retrieve_kernel_candidates_traced, try_embed_query
from app.services.scheduler import SchedulerFeatures


class ModelBackedCognitiveProvider:
    """Open-world understanding via validated structured JSON + epistemic constitution validator."""

    provider_type = "model"

    def __init__(self, chat_fn=chat_json):
        self._chat = chat_fn
        self.last_meta: dict = {
            "latency_ms": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "estimated_cost_usd": None,
            "model": None,
            "validation_events": [],
        }
        self.last_validation_events: list[dict] = []
        self.last_stage_runtime: dict = {}
        self.last_retrieval: dict | None = None

    def _set_stage_runtime(self, stage: str, *, llm_called: bool) -> dict:
        if stage in STAGE_RUNTIME:
            runtime = {**STAGE_RUNTIME[stage].as_dict(), "stage": stage, "llm_called": llm_called}
        else:
            runtime = {
                "thinking": None,
                "reasoning_effort": None,
                "timeout": None,
                "stage": stage,
                "llm_called": llm_called,
            }
        self.last_stage_runtime = runtime
        return runtime

    def _complete(self, system: str, user: str, schema_cls, *, stage: str):
        budget = self._set_stage_runtime(stage, llm_called=True)
        obj, meta, events = chat_json_schema(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            schema_cls,
            chat_fn=self._chat,
            thinking=budget["thinking"],
            reasoning_effort=budget["reasoning_effort"],
            timeout=budget["timeout"],
        )
        self.last_validation_events = events
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
        self.last_meta["thinking"] = budget["thinking"]
        self.last_meta["reasoning_effort"] = budget["reasoning_effort"]
        self.last_meta["timeout"] = budget["timeout"]
        existing = list(self.last_meta.get("validation_events") or [])
        existing.extend(events)
        self.last_meta["validation_events"] = existing
        return obj

    def extract_information(self, text: str, source_type: str, title: str | None = None) -> ExtractionResult:
        parsed: ExtractionResponse = self._complete(
            EXTRACT_SYSTEM,
            extraction_user_prompt(source_type, title, text),
            ExtractionResponse,
            stage="extraction",
        )
        result = ExtractionResult(
            event_title=parsed.event_title,
            event_summary=parsed.event_summary,
            marketing_heavy=parsed.marketing_heavy,
            current_facts=list(parsed.current_facts),
            future_plans=list(parsed.future_plans),
            technical_claims=list(parsed.technical_claims),
            promotional_framing=list(parsed.promotional_framing),
        )
        for item in parsed.claims:
            result.claims.append(
                ExtractedClaim(
                    text=item.text,
                    claim_type=item.claim_type,
                    attributed_to=item.attributed_to,
                    attribution_type=item.attribution_type,
                    confidence_extraction=item.extraction_confidence,
                    temporal_status=item.temporal_status,
                    source_span_text=item.source_span or item.text,
                    source_start_offset=item.source_start_offset,
                    source_end_offset=item.source_end_offset,
                    chunk_id=item.chunk_id,
                )
            )
        for item in parsed.observations:
            result.observations.append(
                ExtractedObservation(
                    text=item.text,
                    observer_type=item.observer,
                    observation_type=item.observation_type,
                    confidence=item.confidence,
                    source_span_text=item.source_span or item.text,
                    source_start_offset=item.source_start_offset,
                    source_end_offset=item.source_end_offset,
                    chunk_id=item.chunk_id,
                )
            )
        for item in parsed.inferences:
            result.inferences.append(
                ExtractedInference(
                    text=item.text,
                    author_type=AuthorType.AI,
                    confidence=item.confidence,
                    source_roles=[item.derived_from or "model"],
                )
            )
        return validate_extraction(result)

    def match_kernel(
        self,
        extraction: ExtractionResult,
        nodes: list[KernelNode],
        extra_text: str = "",
        *,
        query_embedding=None,
        node_embeddings=None,
        ranked_ids=None,
    ) -> list[KernelMatch]:
        blob = " ".join(
            [extra_text]
            + [c.text for c in extraction.claims]
            + [o.text for o in extraction.observations]
        )
        qvec = query_embedding
        emb_model = None
        if qvec is None:
            qvec, emb_model = try_embed_query(blob[:4000])
        candidates, trace = retrieve_kernel_candidates_traced(
            blob,
            nodes,
            query_embedding=qvec,
            node_embeddings=node_embeddings,
            ranked_ids=ranked_ids,
            embedding_model=emb_model or settings.embedding_model,
        )
        self.last_retrieval = trace.as_dict()
        if not candidates:
            candidates = nodes[:12]
        payload = []
        allowed = {n.id for n in candidates}
        for node in candidates:
            payload.append(
                {
                    "kernel_node_id": str(node.id),
                    "node_type": node.node_type,
                    "title": node.title,
                    "text": node_text(node)[:800],
                }
            )
        parsed: KernelMatchResponse = self._complete(
            MATCH_SYSTEM,
            MATCH_USER.format(
                text=blob[:8000],
                claims=json.dumps([c.text for c in extraction.claims]),
                observations=json.dumps([o.text for o in extraction.observations]),
                kernel_candidates=json.dumps(payload),
            ),
            KernelMatchResponse,
            stage="matching",
        )
        by_id = {n.id: n for n in nodes}
        unknown = [m.kernel_node_id for m in parsed.matches if m.kernel_node_id not in by_id]
        if unknown:
            raise SchemaValidationError(
                "kernel_node_id is not a known Kernel node",
                errors=[{"loc": ["matches"], "msg": f"unknown ids: {unknown}"}],
                retry_used=True,
            )
        matches: list[KernelMatch] = []
        for item in parsed.matches:
            if item.kernel_node_id not in allowed and item.kernel_node_id not in by_id:
                continue
            node = by_id[item.kernel_node_id]
            rtype = item.relevance_type
            matches.append(
                KernelMatch(
                    node_id=node.id,
                    node_type=node.node_type,
                    title=node.title,
                    score=item.score,
                    reason=item.reason,
                    structural=rtype == "STRUCTURAL",
                    relevance_type=rtype,
                )
            )
        return matches

    def reason_evidence(self, extraction: ExtractionResult) -> ExtractionResult:
        if not extraction.claims or not (extraction.observations or extraction.inferences):
            self._set_stage_runtime("evidence", llm_called=False)
            return extraction
        parsed: EvidenceReasoningResponse = self._complete(
            EVIDENCE_SYSTEM,
            EVIDENCE_USER.format(
                claims=json.dumps([{"i": i, "text": c.text} for i, c in enumerate(extraction.claims)]),
                observations=json.dumps([{"i": i, "text": o.text} for i, o in enumerate(extraction.observations)]),
                inferences=json.dumps([{"i": i, "text": inf.text} for i, inf in enumerate(extraction.inferences)]),
            ),
            EvidenceReasoningResponse,
            stage="evidence",
        )
        links = []
        n_obs = len(extraction.observations)
        n_claims = len(extraction.claims)
        n_inf = len(extraction.inferences)
        for item in parsed.links:
            if item.source_role == "OBSERVATION" and item.source_index >= n_obs:
                raise SchemaValidationError(
                    "evidence source_index out of range",
                    errors=[{"loc": ["links", "source_index"], "msg": "out of range"}],
                    retry_used=True,
                )
            if item.source_role == "CLAIM" and item.source_index >= n_claims:
                raise SchemaValidationError(
                    "evidence source_index out of range",
                    errors=[{"loc": ["links", "source_index"], "msg": "out of range"}],
                    retry_used=True,
                )
            if item.source_role == "INFERENCE" and item.source_index >= n_inf:
                raise SchemaValidationError(
                    "evidence source_index out of range",
                    errors=[{"loc": ["links", "source_index"], "msg": "out of range"}],
                    retry_used=True,
                )
            if item.target_role == "CLAIM" and item.target_index >= n_claims:
                raise SchemaValidationError(
                    "evidence target_index out of range",
                    errors=[{"loc": ["links", "target_index"], "msg": "out of range"}],
                    retry_used=True,
                )
            stance, strength = validate_evidence_strength(
                item.stance.value,
                item.strength.value,
                extraction.evidence_maturity,
            )
            links.append(
                ExtractedEvidence(
                    source_role=item.source_role,
                    source_index=item.source_index,
                    target_role=item.target_role,
                    target_index=item.target_index,
                    stance=item.stance.__class__(stance),
                    strength=item.strength.__class__(strength),
                    confidence=min(item.confidence, 0.85),
                    scope=item.scope,
                )
            )
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
        parsed: SchedulerJudgmentResponse = self._complete(
            JUDGMENT_SYSTEM,
            JUDGMENT_USER.format(
                text=text[:8000],
                matches=json.dumps(
                    [
                        {
                            "id": str(m.node_id),
                            "type": m.node_type,
                            "title": m.title,
                            "score": m.score,
                            "rel": m.relevance_type,
                        }
                        for m in matches
                    ]
                ),
                is_duplicate=is_duplicate,
                independent_source_count=independent_source_count,
                secondary_report_count=secondary_report_count,
            ),
            SchedulerJudgmentResponse,
            stage="judgment",
        )
        threatened = threatens_active_work
        if threatened is None:
            threatened = parsed.threatens_active_work
        return SchedulerFeatures(
            topic_relevance=parsed.topic_relevance,
            structural_relevance=parsed.structural_relevance,
            decision_relevance=parsed.decision_relevance,
            novelty=parsed.novelty,
            credibility=parsed.credibility,
            kernel_delta=parsed.kernel_delta,
            bottleneck_alignment=parsed.bottleneck_alignment,
            disagreement=parsed.disagreement,
            actionability=parsed.actionability,
            temporal_value=parsed.temporal_value,
            cognitive_cost=parsed.cognitive_cost,
            is_duplicate=is_duplicate,
            evidence_maturity=parsed.evidence_maturity,
            threatens_active_work=bool(threatened),
            marketing_heavy=parsed.marketing_heavy or extraction.marketing_heavy,
            sources_conflict=bool(extraction.evidence),
            independent_source_count=independent_source_count,
            secondary_report_count=secondary_report_count,
            high_quality_technical=parsed.high_quality_technical,
            foundational_paper=parsed.foundational_paper,
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
        parsed: ModelDeltaResponse = self._complete(
            DELTA_SYSTEM,
            DELTA_USER.format(
                text=text[:8000],
                matches=json.dumps([{"id": str(m.node_id), "title": m.title, "reason": m.reason} for m in matches]),
                kernel=json.dumps(kernel_snap),
            ),
            ModelDeltaResponse,
            stage="delta",
        )
        affected = [{"id": item.id, "impact": item.impact} for item in parsed.affected_kernel_nodes]
        return ModelDelta(
            summary=parsed.summary,
            what_could_change=list(parsed.what_could_change),
            distinctions=list(parsed.distinctions),
            questions=list(parsed.new_questions),
            admission_allowed=parsed.admission_allowed,
            affected_kernel_nodes=affected,
            possible_hypotheses=list(parsed.possible_hypotheses),
            decision_implications=list(parsed.decision_implications),
            epistemic_risk=parsed.epistemic_risk,
            evidence_maturity=parsed.evidence_maturity,
            rationale=parsed.rationale,
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
        self._set_stage_runtime("patches", llm_called=False)
        return propose_patches(text, delta, matches, features, nodes, evidence_link_ids)
