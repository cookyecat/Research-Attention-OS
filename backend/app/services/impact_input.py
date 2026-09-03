"""Frozen Cognitive Impact input reconstructed from a completed AnalysisRun."""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import AttributionType, AuthorType, ClaimType, ObservationType, ObserverType, Stance, Strength
from app.models.analysis import AnalysisRun
from app.models.kernel import KernelNode
from app.models.source import Source
from app.services.extraction import (
    ExtractedClaim,
    ExtractedEvidence,
    ExtractedInference,
    ExtractedObservation,
    ExtractionResult,
)
from app.services.matching import KernelMatch
from app.services.scheduler import matches_from_debug

SNAPSHOT_VERSION = "impact-input-v0.1"

_FINGERPRINT_KEYS = (
    "schema_version",
    "analysis_run_id",
    "input_hash",
    "kernel_snapshot_hash",
    "source_text",
    "extraction",
    "matches",
    "independence",
)


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, default=str, ensure_ascii=False, separators=(",", ":"))


def fingerprint_snapshot(snapshot: dict) -> str:
    body = {key: snapshot.get(key) for key in _FINGERPRINT_KEYS}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def _enum_value(enum_cls, raw, default):
    if raw is None:
        return default
    try:
        return enum_cls(str(raw))
    except ValueError:
        return default


def frozen_impact_input_from_run(db: Session, run: AnalysisRun) -> dict:
    """Reuse the inputs that entered Impact. Do not re-extract, match, or ingest."""
    if run.status != "COMPLETED":
        raise HTTPException(422, "AnalysisRun is not completed")
    payload = dict(run.result_payload or {})
    plan = payload.get("attention_plan") if isinstance(payload.get("attention_plan"), dict) else {}
    debug = plan.get("score_debug") if isinstance(plan.get("score_debug"), dict) else {}
    features = payload.get("features") if isinstance(payload.get("features"), dict) else {}
    independence = debug.get("independence") if isinstance(debug.get("independence"), dict) else {}

    source = db.get(Source, run.source_id)
    extra_bits: list[str] = []
    for raw_id in run.extra_source_ids or []:
        extra = db.get(Source, UUID(str(raw_id)))
        if extra is not None:
            extra_bits.append(extra.content_text or "")
    source_text = " ".join(
        part for part in ([source.content_text or "", source.title or ""] if source else []) + extra_bits if part
    )

    matches = payload.get("kernel_matches") or debug.get("matches") or []
    if not isinstance(matches, list):
        matches = []

    node_ids: list[UUID] = []
    for item in matches:
        if not isinstance(item, dict) or not item.get("node_id"):
            continue
        try:
            node_ids.append(UUID(str(item["node_id"])))
        except (TypeError, ValueError):
            continue
    kernel_nodes: list[dict] = []
    if node_ids:
        rows = db.execute(select(KernelNode).where(KernelNode.id.in_(node_ids))).scalars().all()
        by_id = {n.id: n for n in rows}
        for nid in node_ids:
            node = by_id.get(nid)
            if node is None:
                continue
            kernel_nodes.append(
                {
                    "id": str(node.id),
                    "node_type": node.node_type,
                    "title": node.title,
                    "status": node.status,
                    "payload": node.payload or {},
                }
            )

    independent_source_count = int(
        features.get("independent_source_count") or independence.get("independent_sources") or 1
    )
    secondary_report_count = int(
        features.get("secondary_report_count") or independence.get("secondary_reports") or 0
    )
    snapshot = {
        "schema_version": SNAPSHOT_VERSION,
        "analysis_run_id": str(run.id),
        "source_id": str(run.source_id),
        "input_hash": run.input_hash,
        "kernel_snapshot_hash": run.kernel_snapshot_hash,
        "source_text": source_text,
        "extraction": {
            "claims": payload.get("claims") or [],
            "observations": payload.get("observations") or [],
            "inferences": payload.get("inferences") or [],
            "evidence_links": payload.get("evidence_links") or [],
            "separations": payload.get("separations") or {},
            "marketing_heavy": bool(features.get("marketing_heavy")),
            "evidence_maturity": float(features.get("evidence_maturity") or 0.4),
            "evidence_stage_skipped": bool(
                payload.get("evidence_stage_skipped") or features.get("evidence_stage_skipped")
            ),
            "evidence_skip_reason": payload.get("evidence_skip_reason") or features.get("evidence_skip_reason"),
            "event_title": getattr(source, "title", None),
        },
        "matches": matches,
        "kernel_nodes": kernel_nodes,
        "independence": {
            "is_duplicate": bool(features.get("is_duplicate")),
            "independent_source_count": independent_source_count,
            "secondary_report_count": secondary_report_count,
            "threatens_active_work": bool(features.get("threatens_active_work")),
        },
        "original": {
            "disposition": payload.get("disposition"),
            "update": payload.get("update"),
            "cognitive_impact": payload.get("cognitive_impact") or debug.get("cognitive_impact"),
            "provider_type": run.provider_type,
            "model_name": run.model_name,
            "impact_assessor_version": debug.get("impact_assessor_version"),
        },
    }
    snapshot["input_fingerprint"] = fingerprint_snapshot(snapshot)
    return snapshot


def extraction_from_snapshot(snapshot: dict) -> ExtractionResult:
    ext = snapshot.get("extraction") or {}
    seps = ext.get("separations") if isinstance(ext.get("separations"), dict) else {}
    result = ExtractionResult(
        event_title=ext.get("event_title"),
        marketing_heavy=bool(ext.get("marketing_heavy")),
        evidence_maturity=float(ext.get("evidence_maturity") or 0.4),
        current_facts=list(seps.get("current_facts") or []),
        future_plans=list(seps.get("future_plans") or []),
        technical_claims=list(seps.get("technical_claims") or []),
        promotional_framing=list(seps.get("promotional_framing") or []),
        evidence_stage_skipped=bool(ext.get("evidence_stage_skipped")),
        evidence_skip_reason=ext.get("evidence_skip_reason"),
    )
    for item in ext.get("claims") or []:
        if not isinstance(item, dict) or not item.get("text"):
            continue
        result.claims.append(
            ExtractedClaim(
                text=item["text"],
                claim_type=_enum_value(ClaimType, item.get("claim_type"), ClaimType.FACTUAL),
                attributed_to=item.get("attributed_to"),
                attribution_type=_enum_value(
                    AttributionType, item.get("attribution_type"), AttributionType.UNKNOWN
                ),
            )
        )
    for item in ext.get("observations") or []:
        if not isinstance(item, dict) or not item.get("text"):
            continue
        result.observations.append(
            ExtractedObservation(
                text=item["text"],
                observer_type=_enum_value(ObserverType, item.get("observer_type"), ObserverType.USER),
                observation_type=_enum_value(
                    ObservationType, item.get("observation_type"), ObservationType.OTHER
                ),
            )
        )
    for item in ext.get("inferences") or []:
        if not isinstance(item, dict) or not item.get("text"):
            continue
        result.inferences.append(
            ExtractedInference(
                text=item["text"],
                author_type=_enum_value(AuthorType, item.get("author_type"), AuthorType.AI),
                confidence=float(item.get("confidence") or 0.5),
            )
        )
    for item in ext.get("evidence_links") or []:
        if not isinstance(item, dict):
            continue
        result.evidence.append(
            ExtractedEvidence(
                source_role=str(item.get("source_object_type") or item.get("source_role") or "CLAIM"),
                source_index=0,
                target_role=str(item.get("target_object_type") or item.get("target_role") or "CLAIM"),
                target_index=0,
                stance=_enum_value(Stance, item.get("stance"), Stance.SUPPORTS),
                strength=_enum_value(Strength, item.get("strength"), Strength.WEAK),
                confidence=float(item.get("confidence") or 0.5),
                scope=item.get("scope"),
            )
        )
    return result


def matches_from_snapshot(snapshot: dict) -> list[KernelMatch]:
    return matches_from_debug(snapshot.get("matches") or [])


def kernel_nodes_from_snapshot(snapshot: dict) -> list[KernelNode]:
    """Lightweight KernelNode stand-ins for Impact prompt/importance. Not persisted."""
    nodes: list[KernelNode] = []
    for item in snapshot.get("kernel_nodes") or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        node = KernelNode(
            node_type=str(item.get("node_type") or "BELIEF"),
            title=item.get("title"),
            status=str(item.get("status") or "ACTIVE"),
            payload=item.get("payload") if isinstance(item.get("payload"), dict) else {},
            current_version=1,
        )
        node.id = UUID(str(item["id"]))
        nodes.append(node)
    return nodes
