from __future__ import annotations

from copy import deepcopy
from uuid import UUID

from app.enums import (
    AttributionType,
    AuthorType,
    ClaimType,
    ObservationType,
    ObserverType,
)
from app.models.event import EventEvidenceFrame
from app.services.extraction import (
    ExtractedClaim,
    ExtractedInference,
    ExtractedObservation,
    ExtractionResult,
    _claim_type_for,
    _evidence_maturity,
)

FRAME_CONDITIONED_COGNITION_CONTRACT = "frame-conditioned-cognition-input-v0.1"


class FrameConditionedCognitionError(RuntimeError):
    pass


def _confidence(value: str | None) -> float:
    return {
        "HIGH": 0.9,
        "MEDIUM": 0.7,
        "LOW": 0.5,
        "UNKNOWN": 0.6,
    }.get(str(value or "UNKNOWN").upper(), 0.6)


def _validate_units(frame: EventEvidenceFrame) -> list[dict]:
    payload = dict(frame.frame_payload or {})
    units = payload.get("audited_semantic_units")
    if not isinstance(units, list) or not units:
        raise FrameConditionedCognitionError(
            "EventEvidenceFrame lacks audited_semantic_units; "
            "summary-only frame cognition is forbidden"
        )

    out: list[dict] = []
    seen: set[str] = set()
    for index, raw in enumerate(units):
        if not isinstance(raw, dict):
            raise FrameConditionedCognitionError(
                f"audited semantic unit {index} is not an object"
            )
        unit_id = str(raw.get("unit_id") or "").strip()
        statement = str(raw.get("statement") or "").strip()
        if not unit_id or not statement:
            raise FrameConditionedCognitionError(
                f"audited semantic unit {index} lacks unit_id/statement"
            )
        if unit_id in seen:
            raise FrameConditionedCognitionError(
                f"duplicate audited semantic unit id: {unit_id}"
            )
        supports = raw.get("supports")
        if not isinstance(supports, list) or not supports:
            raise FrameConditionedCognitionError(
                f"audited semantic unit {unit_id} lacks evidence supports"
            )
        normalized_supports: list[dict] = []
        for support_index, support in enumerate(supports):
            if not isinstance(support, dict):
                raise FrameConditionedCognitionError(
                    f"support {support_index} for {unit_id} is not an object"
                )
            excerpt = str(support.get("support_excerpt") or "").strip()
            pointer = str(support.get("support_pointer") or "").strip()
            if not excerpt or not pointer:
                raise FrameConditionedCognitionError(
                    f"support {support_index} for {unit_id} lacks pointer/excerpt"
                )
            normalized_supports.append(deepcopy(support))
        seen.add(unit_id)
        out.append(
            {
                "unit_id": unit_id,
                "statement": statement,
                "epistemic_status": str(
                    raw.get("epistemic_status") or "SOURCE_CLAIM"
                ),
                "confidence": str(raw.get("confidence") or "UNKNOWN"),
                "supports": normalized_supports,
            }
        )
    return out


def event_frame_to_extraction(frame: EventEvidenceFrame) -> ExtractionResult:
    """Project one audited Event frame into the frozen cognition input shape.

    This function never reads/re-extracts Source prose. It consumes only
    audited units persisted with the frame and therefore preserves the
    Sensor/Auditor evidence boundary.
    """

    payload = dict(frame.frame_payload or {})
    units = _validate_units(frame)
    result = ExtractionResult()

    for unit in units:
        statement = unit["statement"]
        status = unit["epistemic_status"]
        confidence = _confidence(unit["confidence"])
        supports = deepcopy(unit["supports"])
        span = "\n".join(
            str(support.get("support_excerpt") or "") for support in supports
        ) or statement

        if status == "DIRECT_OBSERVATION":
            result.observations.append(
                ExtractedObservation(
                    text=statement,
                    observer_type=ObserverType.SYSTEM_EXTRACTED,
                    observation_type=ObservationType.OTHER,
                    confidence=confidence,
                    source_span_text=span,
                    semantic_unit_id=unit["unit_id"],
                    semantic_supports=supports,
                )
            )
        elif status == "EXTRACTOR_INFERENCE":
            result.inferences.append(
                ExtractedInference(
                    text=statement,
                    author_type=AuthorType.AI,
                    confidence=confidence,
                    source_roles=["audited_event_frame"],
                    source_span_text=span,
                    semantic_unit_id=unit["unit_id"],
                    semantic_supports=supports,
                )
            )
        else:
            claim_type = _claim_type_for(statement)
            result.claims.append(
                ExtractedClaim(
                    text=statement,
                    claim_type=claim_type,
                    attributed_to="source",
                    attribution_type=AttributionType.UNKNOWN,
                    confidence_extraction=confidence,
                    temporal_status=(
                        "FUTURE" if claim_type == ClaimType.PREDICTIVE else "CURRENT"
                    ),
                    source_span_text=span,
                    semantic_unit_id=unit["unit_id"],
                    semantic_supports=supports,
                )
            )
            if claim_type == ClaimType.PREDICTIVE:
                result.future_plans.append(statement)
            elif claim_type == ClaimType.PROMOTIONAL:
                result.promotional_framing.append(statement)
            elif claim_type == ClaimType.TECHNICAL:
                result.technical_claims.append(statement)
            elif claim_type != ClaimType.OPINION:
                result.current_facts.append(statement)

    result.event_title = payload.get("event_title")
    result.event_summary = (
        payload.get("event_summary")
        or "\n".join(unit["statement"] for unit in units)[:2000]
        or None
    )
    result.evidence_maturity = _evidence_maturity(result)
    result.analysis_provenance = {
        "contract": FRAME_CONDITIONED_COGNITION_CONTRACT,
        "frame_id": str(frame.id),
        "frame_contract_version": frame.frame_contract_version,
        "frame_digest": frame.frame_digest,
        "semantic_input_digest": frame.semantic_input_digest,
        "event_key": payload.get("event_key"),
        "primary_source_id": str(frame.source_id),
        "source_snapshot_id": (
            str(frame.source_snapshot_id) if frame.source_snapshot_id else None
        ),
        "source_analysis_run_id": (
            str(frame.analysis_run_id) if frame.analysis_run_id else None
        ),
        "decision_scope": "EVENT_FRAME",
    }
    return result


def frame_identity(frame: EventEvidenceFrame) -> dict:
    payload = dict(frame.frame_payload or {})
    return {
        "contract": FRAME_CONDITIONED_COGNITION_CONTRACT,
        "frame_id": str(frame.id),
        "source_id": str(frame.source_id),
        "event_key": payload.get("event_key"),
        "frame_digest": frame.frame_digest,
        "semantic_input_digest": frame.semantic_input_digest,
    }
