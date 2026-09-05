from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import AuthorType, CandidateType, ExpectedOutput
from app.models.claim import Claim
from app.models.evidence import EvidenceLink
from app.models.inference import Inference, InferenceSource
from app.models.kernel import KernelNode, KernelPatch
from app.models.observation import Observation
from app.models.scheduler import AttentionPlan, RuntimeContext
from app.models.source import Source
from app.models.watch import Watch, WatchTrigger
from app.services.cognitive_impact import CognitiveImpactAssessment, visible_prediction_from_frozen
from app.services.deltas import ModelDelta, suggest_watches
from app.services.extraction import (
    ExtractionResult,
    merge_extractions,
    observation_is_forbidden_inference,
)
from app.services.ingestion import attach_or_create_event
from app.services.kernel_commit import create_patch
from app.services.matching import KernelMatch
from app.services.scheduler import (
    RuntimeView,
    SchedulerFeatures,
    ground_features_to_matches,
    route,
    validate_plan,
)
from app.services.analysis_execution import (
    analysis_execution_digest,
    analysis_execution_snapshot,
    uses_embedding_retrieval,
)
from app.services.source_graph import freeze_analysis_relational_context


def _active_kernel(db: Session) -> list[KernelNode]:
    return (
        db.execute(
            select(KernelNode).where(
                KernelNode.deleted_at.is_(None),
                KernelNode.status.notin_(["DEPRECATED", "ABANDONED", "COMPLETED"]),
            )
        )
        .scalars()
        .all()
    )


def persist_extraction(
    db: Session,
    source: Source,
    extraction: ExtractionResult,
    event_id: UUID | None,
    analysis_run_id: UUID | None = None,
) -> tuple[list[Claim], list[Observation], list[Inference], list[EvidenceLink]]:
    claims: list[Claim] = []
    observations: list[Observation] = []
    inferences: list[Inference] = []
    for item in extraction.claims:
        row = Claim(
            source_id=source.id,
            event_id=event_id,
            text=item.text,
            normalized_text=item.text.lower(),
            claim_type=item.claim_type,
            attributed_to=item.attributed_to,
            attribution_type=item.attribution_type,
            confidence_extraction=item.confidence_extraction,
            analysis_run_id=analysis_run_id,
            source_span_text=item.source_span_text,
            source_start_offset=item.source_start_offset,
            source_end_offset=item.source_end_offset,
            chunk_id=item.chunk_id,
        )
        db.add(row)
        claims.append(row)
    for item in extraction.observations:
        if observation_is_forbidden_inference(item.text):
            inf = Inference(
                text=item.text,
                author_type=AuthorType.AI,
                confidence=item.confidence,
                scope="rejected-as-observation",
                analysis_run_id=analysis_run_id,
            )
            db.add(inf)
            inferences.append(inf)
            continue
        row = Observation(
            source_id=source.id,
            event_id=event_id,
            observer_type=item.observer_type,
            text=item.text,
            observation_type=item.observation_type,
            confidence=item.confidence,
            analysis_run_id=analysis_run_id,
            source_span_text=item.source_span_text,
            source_start_offset=item.source_start_offset,
            source_end_offset=item.source_end_offset,
            chunk_id=item.chunk_id,
        )
        db.add(row)
        observations.append(row)
    db.flush()
    for item in extraction.inferences:
        inf = Inference(
            text=item.text,
            author_type=item.author_type,
            confidence=item.confidence,
            analysis_run_id=analysis_run_id,
        )
        db.add(inf)
        db.flush()
        db.add(
            InferenceSource(
                inference_id=inf.id,
                source_object_type="SOURCE",
                source_object_id=source.id,
            )
        )
        if claims:
            db.add(
                InferenceSource(
                    inference_id=inf.id,
                    source_object_type="CLAIM",
                    source_object_id=claims[0].id,
                )
            )
        inferences.append(inf)
    db.flush()
    links: list[EvidenceLink] = []
    for ev in extraction.evidence:
        src_id = None
        tgt_id = None
        if ev.source_role == "OBSERVATION" and ev.source_index < len(observations):
            src_id = observations[ev.source_index].id
        elif ev.source_role == "CLAIM" and ev.source_index < len(claims):
            src_id = claims[ev.source_index].id
        if ev.target_role == "CLAIM" and ev.target_index < len(claims):
            tgt_id = claims[ev.target_index].id
        if src_id is None or tgt_id is None:
            continue
        link = EvidenceLink(
            source_object_type=ev.source_role,
            source_object_id=src_id,
            target_object_type=ev.target_role,
            target_object_id=tgt_id,
            stance=ev.stance,
            strength=ev.strength,
            confidence=ev.confidence,
            scope=ev.scope,
            proposed_by="AI",
            accepted_by_user=None,
            analysis_run_id=analysis_run_id,
        )
        db.add(link)
        links.append(link)
    db.flush()
    return claims, observations, inferences, links


def extract_source(
    db: Session,
    source: Source,
    extra_sources: list[Source] | None = None,
    *,
    provider=None,
    analysis_run_id: UUID | None = None,
    independent_source_count: int | None = None,
) -> tuple[ExtractionResult, list[Claim], list[Observation], list[Inference], list[EvidenceLink]]:
    from app.cognitive.factory import get_provider
    from app.services.chunking import split_source
    from app.services.extraction import dedup_extraction

    provider = provider or get_provider()

    def _extract_one(src: Source) -> ExtractionResult:
        full = src.content_text or ""
        chunks = split_source(full)
        parts: list[ExtractionResult] = []
        for chunk in chunks:
            part = provider.extract_information(chunk.text, src.source_type, src.title)
            _stamp_chunk_provenance(part, chunk, full)
            parts.append(part)
        merged = merge_extractions(*parts) if len(parts) > 1 else parts[0]
        return dedup_extraction(merged)

    primary = _extract_one(source)
    parts = [primary]
    extras = extra_sources or []
    extras = sorted(extras, key=lambda s: str(s.id))
    for extra in extras:
        parts.append(_extract_one(extra))
    merged = merge_extractions(*parts) if len(parts) > 1 else primary
    evidence_source_count = (
        independent_source_count if independent_source_count is not None else 1 + len(extras)
    )
    merged = provider.reason_evidence(merged, independent_source_count=evidence_source_count)
    event = attach_or_create_event(db, source, merged.event_title or source.title, merged.event_summary)
    claims, observations, inferences, links = persist_extraction(
        db, source, merged, event.id, analysis_run_id=analysis_run_id
    )
    for extra in extras:
        attach_or_create_event(db, extra, merged.event_title or extra.title, merged.event_summary)
    return merged, claims, observations, inferences, links


def _stamp_chunk_provenance(part: ExtractionResult, chunk, full_text: str) -> None:
    from app.services.chunking import locate_span

    for item in [*part.claims, *part.observations, *part.inferences]:
        if not item.chunk_id:
            item.chunk_id = chunk.chunk_id
        span = item.source_span_text or item.text
        item.source_span_text = span
        if item.source_start_offset is None:
            start, end = locate_span(full_text, span, hint=chunk.start)
            item.source_start_offset = start
            item.source_end_offset = end


def _runtime_view(ctx: RuntimeContext | None) -> RuntimeView:
    if ctx is None:
        return RuntimeView()
    deadline_minutes = None
    if ctx.deadline_at:
        deadline_minutes = (ctx.deadline_at - datetime.now(timezone.utc)).total_seconds() / 60.0
    return RuntimeView(
        current_task=ctx.current_task,
        session_topic=ctx.session_topic,
        available_attention_minutes=ctx.available_attention_minutes,
        interruptibility=ctx.interruptibility,
        cognitive_capacity=ctx.cognitive_capacity,
        deadline_minutes=deadline_minutes,
    )


def _expected_output(value) -> ExpectedOutput:
    if isinstance(value, ExpectedOutput):
        return value
    return ExpectedOutput(str(getattr(value, "value", value) or ExpectedOutput.NONE))


def _placeholder_delta(authorized: ExpectedOutput, features: SchedulerFeatures) -> ModelDelta:
    if authorized == ExpectedOutput.NONE:
        return ModelDelta(
            summary="Downstream synthesis skipped because ExpectedOutput is NONE.",
            admission_allowed=False,
            rationale="Attention Policy did not authorize a downstream cognitive artifact.",
            evidence_maturity=features.evidence_maturity,
        )
    if authorized == ExpectedOutput.WATCH:
        return ModelDelta(
            summary="Watch obligation authorized. KernelPatch is not authorized.",
            admission_allowed=False,
            rationale="ExpectedOutput WATCH authorizes a Watch, not a Kernel mutation proposal.",
            evidence_maturity=features.evidence_maturity,
        )
    return ModelDelta(
        summary=f"ExpectedOutput {authorized.value} has no specialized artifact implementation.",
        admission_allowed=False,
        rationale=f"Fail closed: {authorized.value} is not executed as a generic KernelPatch.",
        evidence_maturity=features.evidence_maturity,
    )


def _execute_authorized_artifacts(
    authorized: ExpectedOutput,
    *,
    provider,
    blob,
    extraction,
    matches,
    features,
    nodes,
    assessment,
    evidence_link_ids: list[str],
) -> tuple[ModelDelta, list]:
    if authorized == ExpectedOutput.SUMMARY:
        return (
            provider.propose_model_delta(
                blob, extraction, matches, features, nodes, assessment=assessment
            ),
            [],
        )
    if authorized == ExpectedOutput.KERNEL_PATCH:
        delta = provider.propose_model_delta(
            blob, extraction, matches, features, nodes, assessment=assessment
        )
        return (
            delta,
            provider.propose_patches(
                blob,
                delta,
                matches,
                features,
                nodes,
                evidence_link_ids,
                assessment=assessment,
                extraction=extraction,
            ),
        )
    return _placeholder_delta(authorized, features), []


def _fulfill_watch_obligation(
    db: Session,
    *,
    draft,
    source: Source,
    matches: list[KernelMatch],
    plan: AttentionPlan,
    analysis_run_id,
) -> list[Watch]:
    """Create at least one Watch from the Plan's own watch semantics."""
    triggers = list(draft.watch_triggers or ["NEW_EVIDENCE"])
    title = next((m.title for m in matches if m.title), None)
    target_ref = title or source.title or str(source.id)
    watch = Watch(
        target_type="KERNEL" if matches else "SOURCE",
        target_ref=str(target_ref),
        status="ACTIVE",
        created_reason=draft.reason or "AttentionPlan assumed future attention responsibility.",
        kernel_target_ids=[str(m.node_id) for m in matches],
        analysis_run_id=analysis_run_id,
        attention_plan_id=plan.id,
    )
    db.add(watch)
    db.flush()
    for trig in triggers:
        db.add(WatchTrigger(watch_id=watch.id, trigger_type=str(trig), trigger_config={}))
    return [watch]


def _persist_explicit_watch_override(
    db: Session,
    *,
    suggestions: list[dict],
    matches: list[KernelMatch],
    plan: AttentionPlan,
    analysis_run_id,
) -> list[Watch]:
    """Caller override. Not Attention Policy authorization."""
    created: list[Watch] = []
    kernel_ids = [str(m.node_id) for m in matches]
    for sug in suggestions:
        watch = Watch(
            target_type=sug["target_type"],
            target_ref=sug["target_ref"],
            status="ACTIVE",
            created_reason=sug["created_reason"],
            kernel_target_ids=kernel_ids,
            analysis_run_id=analysis_run_id,
            attention_plan_id=plan.id,
        )
        db.add(watch)
        db.flush()
        for trig in sug.get("triggers") or ["NEW_EVIDENCE"]:
            db.add(WatchTrigger(watch_id=watch.id, trigger_type=str(trig), trigger_config={}))
        created.append(watch)
    return created


def _persist_authorized_artifacts(
    db: Session,
    *,
    authorized: ExpectedOutput,
    patch_drafts: list,
    draft,
    source: Source,
    matches: list[KernelMatch],
    plan: AttentionPlan,
    analysis_run_id,
    persist_suggested_watches: bool,
    watch_suggestions: list[dict],
) -> tuple[list[KernelPatch], list[Watch]]:
    patches: list[KernelPatch] = []
    if authorized == ExpectedOutput.KERNEL_PATCH:
        for pd in patch_drafts:
            patches.append(
                create_patch(
                    db,
                    target_object_type=pd.target_object_type,
                    target_object_id=pd.target_object_id,
                    change_type=pd.change_type,
                    current_state=pd.current_state,
                    proposed_state=pd.proposed_state,
                    reasoning=pd.reasoning,
                    evidence_link_ids=pd.evidence_link_ids,
                    suggested_confidence_change=pd.suggested_confidence_change,
                    analysis_run_id=analysis_run_id,
                    attention_plan_id=plan.id,
                )
            )
    created_watches: list[Watch] = []
    assume_future = bool(getattr(draft, "watch_after_processing", False))
    if assume_future:
        created_watches = _fulfill_watch_obligation(
            db, draft=draft, source=source, matches=matches, plan=plan, analysis_run_id=analysis_run_id
        )
    elif persist_suggested_watches:
        created_watches = _persist_explicit_watch_override(
            db,
            suggestions=watch_suggestions,
            matches=matches,
            plan=plan,
            analysis_run_id=analysis_run_id,
        )
    debug = dict(plan.score_debug or {})
    debug["authorized_artifacts"] = {
        "expected_output": authorized.value if isinstance(authorized, ExpectedOutput) else str(authorized),
        "kernel_patch_ids": [str(p.id) for p in patches],
        "watch_ids": [str(w.id) for w in created_watches],
        "explicit_watch_override": bool(persist_suggested_watches and not assume_future),
        "policy_authorized_watch": assume_future,
        "watch_after_processing": assume_future,
    }
    plan.score_debug = debug
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(plan, "score_debug")
    return patches, created_watches


def run_pipeline(
    db: Session,
    source_id: UUID,
    *,
    extra_source_ids: list[UUID] | None = None,
    runtime_context_id: UUID | None = None,
    runtime: RuntimeView | None = None,
    persist_suggested_watches: bool = False,
    reprocess: bool = False,
    provider=None,
) -> dict:
    from app.cognitive.factory import get_provider
    from app.cognitive.versions import IMPACT_ASSESSOR_VERSION, PIPELINE_VERSION
    from app.services.analysis_runs import (
        acquire_run,
        complete_run,
        fail_run,
        hydrate_run,
        canonical_extra_sources,
        compute_identity,
        fresh_kernel_snapshot_hash,
        input_hash,
        kernel_snapshot_hash,
        plan_public,
        run_public,
    )
    from app.services.cognitive_impact import epistemic_text
    from app.services.embeddings import embedding_model_label, load_node_embeddings, retrieve_ids_pgvector
    from app.services.retrieval import query_instruct_enabled, try_embed_query

    source = db.get(Source, source_id)
    if source is None:
        raise ValueError("Source not found")
    extras = [db.get(Source, sid) for sid in extra_source_ids or []]
    extras = canonical_extra_sources([s for s in extras if s is not None])
    provider = provider or get_provider()
    nodes = _active_kernel(db)
    in_hash = input_hash(source, extras)
    k_hash = kernel_snapshot_hash(nodes)
    event_source_ids = [source.id] + [e.id for e in extras]
    rel_ctx = freeze_analysis_relational_context(db, event_source_ids)
    exec_snapshot = analysis_execution_snapshot(provider)
    exec_digest = analysis_execution_digest(provider, snapshot=exec_snapshot)
    provider_type = getattr(provider, "provider_type", "rule")
    model_name = settings.llm_model if str(provider_type).startswith("model") else None
    emb_version = embedding_model_label()
    ident = compute_identity(
        input_digest=in_hash,
        kernel_digest=k_hash,
        provider_type=provider_type,
        model_name=model_name,
        embedding_model_version=emb_version,
        relational_digest=rel_ctx.digest,
        execution_digest=exec_digest,
    )
    kind, run = acquire_run(
        db,
        source_id=source.id,
        extra_ids=[str(e.id) for e in extras],
        identity=ident,
        in_hash=in_hash,
        k_hash=k_hash,
        provider_type=provider_type,
        model_name=model_name,
        embedding_model_version=emb_version,
        reprocess=reprocess,
    )
    if kind == "existing" and run.status == "COMPLETED":
        if runtime is not None:
            return _reschedule(
                db,
                run,
                runtime,
                source,
                persist_suggested_watches=persist_suggested_watches,
                runtime_context_id=runtime_context_id,
            )
        return hydrate_run(db, run)
    if kind == "existing" and run.status == "RUNNING":
        import time

        for _ in range(40):
            db.expire(run)
            db.refresh(run)
            if run.status == "COMPLETED":
                if runtime is not None:
                    return _reschedule(
                        db, run, runtime, source, persist_suggested_watches=persist_suggested_watches,
                        runtime_context_id=runtime_context_id,
                    )
                return hydrate_run(db, run)
            if run.status in {"FAILED", "SUPERSEDED"}:
                break
            time.sleep(0.05)
        if run.status == "COMPLETED":
            return hydrate_run(db, run)
        if run.status == "RUNNING":
            raise RuntimeError("AnalysisRun already in progress for this identity")

    try:
        extraction, claims, observations, inferences, links = extract_source(
            db,
            source,
            extras,
            provider=provider,
            analysis_run_id=run.id,
            independent_source_count=rel_ctx.independent_sources,
        )
        blob = " ".join(
            [source.content_text or "", source.title or ""] + [e.content_text or "" for e in extras]
        )
        epi = epistemic_text(extraction)
        locate_query = " ".join(
            part
            for part in (
                source.title or "",
                epi,
                (source.content_text or "")[:2000],
            )
            if part
        ).strip() or blob[:4000]
        qvec, emb_model = None, "none"
        ranked_ids = None
        node_emb = None
        if uses_embedding_retrieval(provider):
            qvec, emb_model = try_embed_query(locate_query[:4000])
            if qvec:
                ranked_ids = retrieve_ids_pgvector(db, qvec, model=emb_model)
                try:
                    node_emb = load_node_embeddings(db, expected_model=emb_model, expected_dim=len(qvec))
                except Exception:
                    node_emb = None
            live_kernel_hash = fresh_kernel_snapshot_hash(db)
            if live_kernel_hash != k_hash:
                raise RuntimeError(
                    "Kernel snapshot changed during analysis; refusing hybrid K0 identity / K1 retrieval"
                )
        matches = provider.match_kernel(
            extraction,
            nodes,
            extra_text=locate_query or blob,
            query_embedding=qvec,
            node_embeddings=node_emb,
            ranked_ids=ranked_ids,
        )
        retrieval = dict(getattr(provider, "last_retrieval", None) or {})
        if not retrieval:
            retrieval = {
                "embedding_used": bool(qvec),
                "lexical_fallback": qvec is None,
                "method": "lexical" if qvec is None else "embedding",
                "query_instruct_applied": query_instruct_enabled() and bool(qvec),
            }
        retrieval["embedding_model"] = retrieval.get("embedding_model") or (
            emb_model if emb_model and emb_model != "none" else settings.embedding_model
        )
        retrieval.setdefault("query_instruct_applied", query_instruct_enabled())
        independence = rel_ctx.report()
        is_duplicate = rel_ctx.is_duplicate
        assessment = provider.assess_cognitive_impact(
            blob,
            extraction,
            matches,
            is_duplicate=is_duplicate,
            independent_source_count=rel_ctx.independent_sources,
            secondary_report_count=rel_ctx.secondary_reports,
            nodes=nodes,
        )
        features = assessment.features
        features = ground_features_to_matches(features, matches)
        ctx = db.get(RuntimeContext, runtime_context_id) if runtime_context_id else None
        view = runtime or _runtime_view(ctx)
        draft = validate_plan(route(features, view, assessment=assessment, matches=matches))
        plan = AttentionPlan(
            candidate_type=CandidateType.SOURCE,
            candidate_id=source.id,
            disposition=draft.disposition.value,
            processing_modes=[],
            urgency=draft.urgency,
            cognitive_budget_minutes=draft.cognitive_budget_minutes,
            kernel_target_ids=[str(m.node_id) for m in matches],
            expected_output=draft.expected_output,
            reason=draft.reason,
            watch_after_processing=draft.watch_after_processing,
            scheduler_version=settings.scheduler_version,
            attention_policy_version=settings.attention_policy_version,
            runtime_context_id=runtime_context_id,
            runtime_snapshot=_snapshot_runtime(view),
            analysis_run_id=run.id,
            created_at=datetime.now(timezone.utc),
            score_debug={
                "features": features.as_dict(),
                "cognitive_impact": assessment.as_dict(),
                "impact_assessor_version": IMPACT_ASSESSOR_VERSION,
                "matches": [
                    {
                        "node_id": str(m.node_id),
                        "node_type": m.node_type,
                        "title": m.title,
                        "score": m.score,
                        "reason": m.reason,
                        "structural": m.structural,
                        "relevance_type": getattr(m, "relevance_type", "TOPIC"),
                    }
                    for m in matches
                ],
                "independence": independence,
            },
        )
        db.add(plan)
        db.flush()
        authorized = _expected_output(draft.expected_output)
        delta, patch_drafts = _execute_authorized_artifacts(
            authorized,
            provider=provider,
            blob=blob,
            extraction=extraction,
            matches=matches,
            features=features,
            nodes=nodes,
            assessment=assessment,
            evidence_link_ids=[str(link.id) for link in links],
        )
        watch_suggestions = suggest_watches(blob, features, delta)
        patches, created_watches = _persist_authorized_artifacts(
            db,
            authorized=authorized,
            patch_drafts=patch_drafts,
            draft=draft,
            source=source,
            matches=matches,
            plan=plan,
            analysis_run_id=run.id,
            persist_suggested_watches=persist_suggested_watches,
            watch_suggestions=watch_suggestions,
        )
        db.flush()
        fallback_used = bool(getattr(provider, "fallback_used", False))
        stage_provenance = getattr(provider, "stage_provenance", None)
        payload = serialize_analysis(
            source,
            extraction,
            claims,
            observations,
            inferences,
            links,
            matches,
            plan,
            delta,
            patches,
            watch_suggestions,
            created_watches,
            features,
            retrieval=retrieval,
            assessment=assessment,
        )
        from app.services.impact_input import capture_impact_input

        payload["impact_input"] = capture_impact_input(
            source_text=blob,
            extraction=extraction,
            matches=matches,
            nodes=nodes,
            is_duplicate=is_duplicate,
            independent_source_count=rel_ctx.independent_sources,
            secondary_report_count=rel_ctx.secondary_reports,
            analysis_run_id=str(run.id),
            input_hash=in_hash,
            kernel_snapshot_hash=k_hash,
            assessment=assessment,
        )
        payload["relational_context"] = rel_ctx.as_dict()
        payload["execution_digest"] = exec_digest
        payload["execution_snapshot"] = exec_snapshot
        payload["analysis_run"] = {
            "id": str(run.id),
            "identity_key": ident,
            "provider_type": provider_type,
            "fallback_used": fallback_used,
            "pipeline_version": PIPELINE_VERSION,
        }
        complete_run(
            run,
            payload,
            fallback_used=fallback_used,
            meta=getattr(provider, "last_meta", None),
            stage_provenance=stage_provenance,
        )
        payload["analysis_run"] = run_public(run)
        return payload
    except Exception as exc:
        fail_run(run, str(exc))
        try:
            db.commit()
        except Exception:
            db.rollback()
        raise


def _snapshot_runtime(view: RuntimeView) -> dict:
    return {
        "current_task": view.current_task,
        "session_topic": view.session_topic,
        "available_attention_minutes": view.available_attention_minutes,
        "interruptibility": view.interruptibility,
        "cognitive_capacity": view.cognitive_capacity,
        "deadline_minutes": view.deadline_minutes,
    }


def _reschedule(
    db: Session,
    run,
    runtime: RuntimeView,
    source: Source,
    persist_suggested_watches: bool = False,
    runtime_context_id: UUID | None = None,
) -> dict:
    from app.cognitive.factory import get_provider
    from app.services.analysis_runs import hydrate_run, plan_public
    from app.services.cognitive_impact import assessment_from_dict
    from app.services.impact_input import (
        extraction_from_snapshot,
        kernel_nodes_from_snapshot,
        matches_from_snapshot,
    )
    from app.services.scheduler import SchedulerFeatures, matches_from_debug

    stored_payload = dict(run.result_payload or {})
    original_plan = stored_payload.get("attention_plan")
    original_payload = deepcopy(run.result_payload) if isinstance(run.result_payload, dict) else run.result_payload
    payload = hydrate_run(db, run)
    feat = payload.get("features") or {}
    features = SchedulerFeatures(**{k: v for k, v in feat.items() if k in SchedulerFeatures.__dataclass_fields__})
    orig_debug = (original_plan or {}).get("score_debug") if isinstance(original_plan, dict) else {}
    orig_debug = orig_debug if isinstance(orig_debug, dict) else {}
    impact = orig_debug.get("cognitive_impact") or stored_payload.get("cognitive_impact")
    debug_matches = orig_debug.get("matches")
    if not debug_matches:
        debug_matches = ((payload.get("attention_plan") or {}).get("score_debug") or {}).get("matches")
    snapshot = stored_payload.get("impact_input") if isinstance(stored_payload.get("impact_input"), dict) else {}
    matches = matches_from_snapshot(snapshot) if snapshot.get("matches") else matches_from_debug(debug_matches)
    assessment = assessment_from_dict(impact) if not hasattr(impact, "effects") else impact
    extraction = extraction_from_snapshot(snapshot) if snapshot else extraction_from_snapshot({"extraction": {}})
    blob = str(snapshot.get("source_text") or source.content_text or "")
    live = {n.id: n for n in _active_kernel(db)}
    nodes = []
    for match in matches:
        if match.node_id in live:
            nodes.append(live[match.node_id])
    for standin in kernel_nodes_from_snapshot(snapshot):
        if standin.id not in {n.id for n in nodes}:
            nodes.append(live.get(standin.id, standin))
    if not nodes:
        nodes = list(live.values())
    evidence_link_ids = [
        str(item["id"]) for item in (stored_payload.get("evidence_links") or []) if isinstance(item, dict) and item.get("id")
    ]
    draft = validate_plan(route(features, runtime, assessment=assessment or impact, matches=matches))
    plan = AttentionPlan(
        candidate_type=CandidateType.SOURCE,
        candidate_id=source.id,
        disposition=draft.disposition.value,
        processing_modes=[],
        urgency=draft.urgency,
        cognitive_budget_minutes=draft.cognitive_budget_minutes,
        kernel_target_ids=[str(m.node_id) for m in matches] or (payload.get("attention_plan") or {}).get("kernel_target_ids") or [],
        expected_output=draft.expected_output,
        reason=draft.reason,
        watch_after_processing=draft.watch_after_processing,
        scheduler_version=settings.scheduler_version,
        attention_policy_version=settings.attention_policy_version,
        runtime_context_id=runtime_context_id,
        runtime_snapshot=_snapshot_runtime(runtime),
        analysis_run_id=run.id,
        created_at=datetime.now(timezone.utc),
        score_debug=dict(orig_debug or (payload.get("attention_plan") or {}).get("score_debug") or {}),
    )
    db.add(plan)
    db.flush()
    authorized = _expected_output(draft.expected_output)
    provider = get_provider()
    delta, patch_drafts = _execute_authorized_artifacts(
        authorized,
        provider=provider,
        blob=blob,
        extraction=extraction,
        matches=matches,
        features=features,
        nodes=nodes,
        assessment=assessment or impact,
        evidence_link_ids=evidence_link_ids,
    )
    watch_suggestions = suggest_watches(blob, features, delta)
    new_patches, new_watches = _persist_authorized_artifacts(
        db,
        authorized=authorized,
        patch_drafts=patch_drafts,
        draft=draft,
        source=source,
        matches=matches,
        plan=plan,
        analysis_run_id=run.id,
        persist_suggested_watches=persist_suggested_watches,
        watch_suggestions=watch_suggestions,
    )
    db.flush()
    # Overlay latest plan on the HTTP response only. Never mutate completed AnalysisRun.
    response = dict(payload)
    public_plan = plan_public(plan)
    response["attention_plan"] = public_plan
    response["latest_attention_plan"] = public_plan
    response["original_attention_plan"] = original_plan
    response["update"] = public_plan["update"]
    response["delta_content"] = public_plan["delta_content"]
    response["disposition"] = public_plan["disposition"]
    response["authorized_kernel_patches"] = [_patch_dict(p) for p in new_patches]
    response["authorized_watches"] = [_watch_dict(w) for w in new_watches]
    if authorized == ExpectedOutput.SUMMARY:
        response["latest_model_delta"] = {
            "summary": delta.summary,
            "rationale": getattr(delta, "rationale", ""),
        }
    assert run.result_payload == original_payload
    assert run.result_payload.get("attention_plan") == original_plan
    return response


def serialize_analysis(
    source: Source,
    extraction: ExtractionResult,
    claims: list[Claim],
    observations: list[Observation],
    inferences: list[Inference],
    links: list[EvidenceLink],
    matches: list[KernelMatch],
    plan: AttentionPlan,
    delta,
    patches: list[KernelPatch],
    watch_suggestions: list[dict],
    created_watches: list[Watch],
    features: SchedulerFeatures,
    retrieval: dict | None = None,
    assessment: CognitiveImpactAssessment | None = None,
) -> dict:
    visible = visible_prediction_from_frozen(
        frozen_impact=assessment,
        frozen_matches=matches,
        disposition=plan.disposition,
    )
    update = visible["update"]
    delta_content = visible["delta_content"]
    return {
        "source_id": str(source.id),
        "disposition": plan.disposition,
        "update": update,
        "delta_content": delta_content,
        "claims": [_claim_dict(c) for c in claims],
        "observations": [_obs_dict(o) for o in observations],
        "inferences": [_inf_dict(i) for i in inferences],
        "evidence_links": [_link_dict(x) for x in links],
        "separations": {
            "current_facts": extraction.current_facts,
            "future_plans": extraction.future_plans,
            "technical_claims": extraction.technical_claims,
            "promotional_framing": extraction.promotional_framing,
        },
        "kernel_matches": [
            {
                "node_id": str(m.node_id),
                "node_type": m.node_type,
                "title": m.title,
                "score": m.score,
                "reason": m.reason,
                    "structural": m.structural,
                    "relevance_type": getattr(m, "relevance_type", "TOPIC"),
                }
            for m in matches
        ],
        "attention_plan": {
            "id": str(plan.id),
            "disposition": plan.disposition,
            "update": update,
            "urgency": plan.urgency,
            "cognitive_budget_minutes": plan.cognitive_budget_minutes,
            "kernel_target_ids": plan.kernel_target_ids,
            "expected_output": plan.expected_output,
            "reason": plan.reason,
            "watch_after_processing": plan.watch_after_processing,
            "scheduler_version": plan.scheduler_version,
            "attention_policy_version": plan.attention_policy_version,
            "runtime_context_id": str(plan.runtime_context_id) if plan.runtime_context_id else None,
            "runtime_snapshot": plan.runtime_snapshot or {},
            "score_debug": plan.score_debug,
        },
        "model_delta": {
            "summary": delta.summary,
            "what_could_change": delta.what_could_change,
            "distinctions": delta.distinctions,
            "questions": delta.questions,
            "admission_allowed": delta.admission_allowed,
            "affected_kernel_nodes": getattr(delta, "affected_kernel_nodes", []),
            "possible_hypotheses": getattr(delta, "possible_hypotheses", []),
            "decision_implications": getattr(delta, "decision_implications", []),
            "epistemic_risk": getattr(delta, "epistemic_risk", ""),
            "evidence_maturity": getattr(delta, "evidence_maturity", None),
            "rationale": getattr(delta, "rationale", ""),
        },
        "kernel_patches": [_patch_dict(p) for p in patches],
        "watch_suggestions": watch_suggestions,
        "watches": [_watch_dict(w) for w in created_watches],
        "features": features.as_dict(),
        "cognitive_impact": assessment.as_dict() if assessment is not None else None,
        "evidence_stage_skipped": bool(extraction.evidence_stage_skipped),
        "evidence_skip_reason": extraction.evidence_skip_reason,
        "retrieval": retrieval or {
            "embedding_model": None,
            "embedding_used": False,
            "lexical_fallback": True,
            "method": "lexical",
            "query_instruct_applied": False,
        },
    }


def _claim_dict(c: Claim) -> dict:
    return {
        "id": str(c.id),
        "text": c.text,
        "claim_type": c.claim_type,
        "attributed_to": c.attributed_to,
        "attribution_type": c.attribution_type,
        "source_span_text": c.source_span_text,
        "source_start_offset": c.source_start_offset,
        "source_end_offset": c.source_end_offset,
        "chunk_id": c.chunk_id,
    }


def _obs_dict(o: Observation) -> dict:
    return {
        "id": str(o.id),
        "text": o.text,
        "observer_type": o.observer_type,
        "observation_type": o.observation_type,
        "source_span_text": o.source_span_text,
        "source_start_offset": o.source_start_offset,
        "source_end_offset": o.source_end_offset,
        "chunk_id": o.chunk_id,
    }


def _inf_dict(i: Inference) -> dict:
    return {"id": str(i.id), "text": i.text, "author_type": i.author_type, "confidence": i.confidence}


def _link_dict(x: EvidenceLink) -> dict:
    return {
        "id": str(x.id),
        "source_object_type": x.source_object_type,
        "source_object_id": str(x.source_object_id),
        "target_object_type": x.target_object_type,
        "target_object_id": str(x.target_object_id),
        "stance": x.stance,
        "strength": x.strength,
    }


def _patch_dict(p: KernelPatch) -> dict:
    return {
        "id": str(p.id),
        "target_object_type": p.target_object_type,
        "target_object_id": str(p.target_object_id) if p.target_object_id else None,
        "change_type": p.change_type,
        "status": p.status,
        "reasoning": p.reasoning,
        "proposed_state": p.proposed_state,
        "current_state": p.current_state,
        "suggested_confidence_change": p.suggested_confidence_change,
        "analysis_run_id": str(p.analysis_run_id) if p.analysis_run_id else None,
        "attention_plan_id": str(p.attention_plan_id) if p.attention_plan_id else None,
    }


def _watch_dict(w: Watch) -> dict:
    return {
        "id": str(w.id),
        "target_ref": w.target_ref,
        "status": w.status,
        "created_reason": w.created_reason,
        "analysis_run_id": str(w.analysis_run_id) if w.analysis_run_id else None,
        "attention_plan_id": str(w.attention_plan_id) if w.attention_plan_id else None,
    }
