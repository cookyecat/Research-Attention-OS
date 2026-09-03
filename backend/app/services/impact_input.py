"""Frozen Cognitive Impact input for Replay / Attribution.

Replay must consume the semantic input Impact actually saw at AnalysisRun time,
not Kernel or Source rows as they exist at replay time.

Fidelity:
  EXACT — captured at pipeline completion from the Impact call arguments.
  RECONSTRUCTED — best-effort from historical payload fields; missing Kernel
  proposition/scope/importance are not filled from the live Kernel.
"""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.enums import AttributionType, AuthorType, ClaimType, ObservationType, ObserverType, Stance, Strength
from app.models.analysis import AnalysisRun
from app.models.kernel import KernelNode
from app.models.source import Source
from app.services.cognitive_impact import node_proposition, primary_update
from app.services.extraction import (
    ExtractedClaim,
    ExtractedEvidence,
    ExtractedInference,
    ExtractedObservation,
    ExtractionResult,
)
from app.services.matching import KernelMatch
from app.services.scheduler import matches_from_debug

SNAPSHOT_VERSION = "impact-input-v0.2"
FIDELITY_EXACT = "EXACT"
FIDELITY_RECONSTRUCTED = "RECONSTRUCTED"

# Semantic fields that actually enter Impact (prompt, rules, grounding, importance).
_FINGERPRINT_KEYS = (
    "schema_version",
    "source_text",
    "extraction",
    "matches",
    "kernel_targets",
    "independence",
)

FINGERPRINT_COVERAGE = {
    "source_text": "blob passed to assess_cognitive_impact",
    "extraction": (
        "claims(text, claim_type, attributed_to, attribution_type), "
        "observations(text, observer_type, observation_type), "
        "inferences(text, author_type, confidence), "
        "evidence(source_role, target_role, stance, strength, scope, confidence), "
        "separations, marketing_heavy, evidence_maturity, evidence_stage_skipped, "
        "evidence_skip_reason, event_title"
    ),
    "matches": "node_id, node_type, title, score, reason, structural, relevance_type",
    "kernel_targets": "id, type, title, proposition, scope, importance, priority",
    "independence": "is_duplicate, independent_source_count, secondary_report_count",
}

_TARGET_REQUIRED = ("id", "type", "title", "proposition", "scope", "importance", "priority")


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


def _as_str(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def canonical_extraction(raw) -> dict:
    """Impact-consumed extraction only. Claim/observation DB ids are omitted."""
    if raw is None:
        raw = {}
    if hasattr(raw, "claims"):
        claims = [
            {
                "text": item.text,
                "claim_type": _as_str(item.claim_type),
                "attributed_to": item.attributed_to,
                "attribution_type": _as_str(getattr(item, "attribution_type", None)),
            }
            for item in (raw.claims or [])
            if getattr(item, "text", None)
        ]
        observations = [
            {
                "text": item.text,
                "observer_type": _as_str(item.observer_type),
                "observation_type": _as_str(item.observation_type),
            }
            for item in (raw.observations or [])
            if getattr(item, "text", None)
        ]
        inferences = [
            {
                "text": item.text,
                "author_type": _as_str(item.author_type),
                "confidence": float(item.confidence or 0.5),
            }
            for item in (raw.inferences or [])
            if getattr(item, "text", None)
        ]
        evidence = [
            {
                "source_role": str(item.source_role),
                "target_role": str(item.target_role),
                "stance": _as_str(item.stance),
                "strength": _as_str(item.strength),
                "scope": getattr(item, "scope", None) or "",
                "confidence": float(getattr(item, "confidence", None) or 0.5),
            }
            for item in (raw.evidence or [])
        ]
        return {
            "claims": claims,
            "observations": observations,
            "inferences": inferences,
            "evidence": evidence,
            "separations": {
                "current_facts": list(raw.current_facts or []),
                "future_plans": list(raw.future_plans or []),
                "technical_claims": list(raw.technical_claims or []),
                "promotional_framing": list(raw.promotional_framing or []),
            },
            "marketing_heavy": bool(raw.marketing_heavy),
            "evidence_maturity": float(raw.evidence_maturity or 0.4),
            "evidence_stage_skipped": bool(raw.evidence_stage_skipped),
            "evidence_skip_reason": raw.evidence_skip_reason,
            "event_title": raw.event_title,
        }

    ext = raw if isinstance(raw, dict) else {}
    seps = ext.get("separations") if isinstance(ext.get("separations"), dict) else {}
    evidence_raw = ext.get("evidence")
    if not isinstance(evidence_raw, list):
        evidence_raw = ext.get("evidence_links") or []
    evidence = []
    for item in evidence_raw:
        if not isinstance(item, dict):
            continue
        evidence.append(
            {
                "source_role": str(item.get("source_role") or item.get("source_object_type") or "CLAIM"),
                "target_role": str(item.get("target_role") or item.get("target_object_type") or "CLAIM"),
                "stance": _as_str(item.get("stance")),
                "strength": _as_str(item.get("strength")),
                "scope": item.get("scope") or "",
                "confidence": float(item.get("confidence") or 0.5),
            }
        )
    return {
        "claims": [
            {
                "text": item.get("text"),
                "claim_type": _as_str(item.get("claim_type")),
                "attributed_to": item.get("attributed_to"),
                "attribution_type": _as_str(item.get("attribution_type")),
            }
            for item in (ext.get("claims") or [])
            if isinstance(item, dict) and item.get("text")
        ],
        "observations": [
            {
                "text": item.get("text"),
                "observer_type": _as_str(item.get("observer_type")),
                "observation_type": _as_str(item.get("observation_type")),
            }
            for item in (ext.get("observations") or [])
            if isinstance(item, dict) and item.get("text")
        ],
        "inferences": [
            {
                "text": item.get("text"),
                "author_type": _as_str(item.get("author_type")),
                "confidence": float(item.get("confidence") or 0.5),
            }
            for item in (ext.get("inferences") or [])
            if isinstance(item, dict) and item.get("text")
        ],
        "evidence": evidence,
        "separations": {
            "current_facts": list(seps.get("current_facts") or []),
            "future_plans": list(seps.get("future_plans") or []),
            "technical_claims": list(seps.get("technical_claims") or []),
            "promotional_framing": list(seps.get("promotional_framing") or []),
        },
        "marketing_heavy": bool(ext.get("marketing_heavy")),
        "evidence_maturity": float(ext.get("evidence_maturity") or 0.4),
        "evidence_stage_skipped": bool(ext.get("evidence_stage_skipped")),
        "evidence_skip_reason": ext.get("evidence_skip_reason"),
        "event_title": ext.get("event_title"),
    }


def canonical_matches(matches) -> list[dict]:
    out = []
    for item in matches or []:
        if hasattr(item, "node_id"):
            out.append(
                {
                    "node_id": str(item.node_id),
                    "node_type": item.node_type,
                    "title": item.title,
                    "score": float(item.score or 0.0),
                    "reason": item.reason or "",
                    "structural": bool(item.structural),
                    "relevance_type": getattr(item, "relevance_type", None) or "TOPIC",
                }
            )
            continue
        if not isinstance(item, dict) or not (item.get("node_id") or item.get("id")):
            continue
        out.append(
            {
                "node_id": str(item.get("node_id") or item.get("id")),
                "node_type": item.get("node_type") or item.get("type") or "",
                "title": item.get("title"),
                "score": float(item.get("score") or 0.0),
                "reason": str(item.get("reason") or ""),
                "structural": bool(item.get("structural")),
                "relevance_type": str(item.get("relevance_type") or "TOPIC"),
            }
        )
    return out


def canonical_independence(
    *,
    is_duplicate: bool,
    independent_source_count: int,
    secondary_report_count: int,
) -> dict:
    return {
        "is_duplicate": bool(is_duplicate),
        "independent_source_count": int(independent_source_count),
        "secondary_report_count": int(secondary_report_count),
    }


def freeze_kernel_target(node: KernelNode) -> dict:
    payload = node.payload if isinstance(node.payload, dict) else {}
    importance = payload.get("importance") if payload else None
    priority = payload.get("priority") if payload else None
    return {
        "id": str(node.id),
        "type": node.node_type,
        "title": node.title,
        "proposition": node_proposition(node),
        "scope": payload.get("scope") if payload else None,
        "importance": importance,
        "priority": priority,
    }


def target_from_match(match: dict) -> dict:
    title = match.get("title")
    return {
        "id": str(match.get("node_id") or match.get("id")),
        "type": match.get("node_type") or match.get("type") or "",
        "title": title,
        "proposition": title or "",
        "scope": None,
        "importance": None,
        "priority": None,
    }


def canonical_kernel_targets(targets) -> list[dict]:
    out = []
    for item in targets or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        out.append(
            {
                "id": str(item["id"]),
                "type": item.get("type") or item.get("node_type") or "",
                "title": item.get("title"),
                "proposition": item["proposition"] if "proposition" in item else (item.get("title") or ""),
                "scope": item.get("scope"),
                "importance": item.get("importance"),
                "priority": item.get("priority"),
            }
        )
    return out


def _serialize_primary(assessment) -> dict:
    raw = primary_update(assessment)
    op = raw.get("operation")
    if hasattr(op, "value"):
        op = op.value
    elif op is not None:
        op = str(op)
    return {"operation": op, "target_node_id": raw.get("target_node_id")}


def _serialize_effects(effects) -> list[dict]:
    out = []
    for item in effects or []:
        if hasattr(item, "as_dict"):
            out.append(item.as_dict())
        elif isinstance(item, dict):
            out.append(item)
    return out


def capture_impact_input(
    *,
    source_text: str,
    extraction: ExtractionResult,
    matches: list[KernelMatch],
    nodes: list[KernelNode] | None,
    is_duplicate: bool,
    independent_source_count: int,
    secondary_report_count: int,
    analysis_run_id: str | None = None,
    input_hash: str | None = None,
    kernel_snapshot_hash: str | None = None,
    assessment=None,
) -> dict:
    """Persist the Impact call arguments. Called at AnalysisRun completion."""
    nodes_by_id = {n.id: n for n in (nodes or [])}
    frozen_matches = canonical_matches(matches)
    kernel_targets = []
    for match in matches or []:
        node = nodes_by_id.get(match.node_id)
        if node is not None:
            kernel_targets.append(freeze_kernel_target(node))
        else:
            kernel_targets.append(target_from_match(canonical_matches([match])[0]))
    snapshot = {
        "schema_version": SNAPSHOT_VERSION,
        "input_fidelity": FIDELITY_EXACT,
        "analysis_run_id": analysis_run_id,
        "input_hash": input_hash,
        "kernel_snapshot_hash": kernel_snapshot_hash,
        "source_text": source_text or "",
        "extraction": canonical_extraction(extraction),
        "matches": frozen_matches,
        "kernel_targets": canonical_kernel_targets(kernel_targets),
        "independence": canonical_independence(
            is_duplicate=is_duplicate,
            independent_source_count=independent_source_count,
            secondary_report_count=secondary_report_count,
        ),
        "reconstruction_gaps": [],
        "fingerprint_coverage": FINGERPRINT_COVERAGE,
    }
    if assessment is not None:
        snapshot["original_stages"] = {
            "raw_effects": _serialize_effects(getattr(assessment, "raw_effects", None) or assessment.effects),
            "grounded_effects": _serialize_effects(assessment.effects),
            "primary_update": _serialize_primary(assessment),
        }
    snapshot["input_fingerprint"] = fingerprint_snapshot(snapshot)
    return snapshot


def stored_is_exact(stored: dict | None) -> bool:
    if not isinstance(stored, dict):
        return False
    if stored.get("input_fidelity") == FIDELITY_RECONSTRUCTED:
        return False
    if stored.get("schema_version") != SNAPSHOT_VERSION:
        return False
    if "source_text" not in stored or not isinstance(stored.get("source_text"), str):
        return False
    if not isinstance(stored.get("extraction"), dict):
        return False
    matches = stored.get("matches")
    targets = stored.get("kernel_targets")
    independence = stored.get("independence")
    if not isinstance(matches, list) or not isinstance(targets, list) or not isinstance(independence, dict):
        return False
    for key in ("is_duplicate", "independent_source_count", "secondary_report_count"):
        if key not in independence:
            return False
    target_ids = {str(item.get("id")) for item in targets if isinstance(item, dict) and item.get("id")}
    for match in matches:
        if not isinstance(match, dict):
            return False
        nid = match.get("node_id") or match.get("id")
        if nid and str(nid) not in target_ids:
            return False
    for target in targets:
        if not isinstance(target, dict):
            return False
        if any(field not in target for field in _TARGET_REQUIRED):
            return False
    return True


def _live_source_text(db: Session, run: AnalysisRun) -> str:
    source = db.get(Source, run.source_id)
    extra_bits: list[str] = []
    for raw_id in run.extra_source_ids or []:
        extra = db.get(Source, UUID(str(raw_id)))
        if extra is not None:
            extra_bits.append(extra.content_text or "")
    return " ".join(
        part for part in ([source.content_text or "", source.title or ""] if source else []) + extra_bits if part
    )


def _reconstruct_from_payload(db: Session, run: AnalysisRun, payload: dict) -> dict:
    """Best-effort freeze from historical AnalysisRun fields. Never reads live Kernel."""
    plan = payload.get("attention_plan") if isinstance(payload.get("attention_plan"), dict) else {}
    debug = plan.get("score_debug") if isinstance(plan.get("score_debug"), dict) else {}
    features = payload.get("features") if isinstance(payload.get("features"), dict) else {}
    independence_raw = debug.get("independence") if isinstance(debug.get("independence"), dict) else {}
    matches = canonical_matches(payload.get("kernel_matches") or debug.get("matches") or [])
    stored = payload.get("impact_input") if isinstance(payload.get("impact_input"), dict) else {}
    gaps = ["kernel_target_proposition", "kernel_target_scope", "kernel_target_importance"]
    source_text = stored.get("source_text")
    if not isinstance(source_text, str):
        source_text = _live_source_text(db, run)
        gaps.append("source_text")
    extraction_src = stored.get("extraction") if isinstance(stored.get("extraction"), dict) else None
    if extraction_src is None:
        extraction_src = {
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
            "event_title": debug.get("event_title"),
        }
        gaps.append("extraction_semantic")
    if stored.get("matches"):
        matches = canonical_matches(stored.get("matches"))
    targets = canonical_kernel_targets(stored.get("kernel_targets")) if stored.get("kernel_targets") else []
    if not targets:
        targets = [target_from_match(match) for match in matches]
    independence_src = stored.get("independence") if isinstance(stored.get("independence"), dict) else {}
    if all(
        key in independence_src
        for key in ("is_duplicate", "independent_source_count", "secondary_report_count")
    ):
        independence = canonical_independence(
            is_duplicate=bool(independence_src.get("is_duplicate")),
            independent_source_count=int(independence_src.get("independent_source_count") or 1),
            secondary_report_count=int(independence_src.get("secondary_report_count") or 0),
        )
    else:
        independence = canonical_independence(
            is_duplicate=bool(features.get("is_duplicate")),
            independent_source_count=int(
                features.get("independent_source_count") or independence_raw.get("independent_sources") or 1
            ),
            secondary_report_count=int(
                features.get("secondary_report_count") or independence_raw.get("secondary_reports") or 0
            ),
        )
        gaps.append("independence")
    snapshot = {
        "schema_version": SNAPSHOT_VERSION,
        "input_fidelity": FIDELITY_RECONSTRUCTED,
        "analysis_run_id": str(run.id),
        "input_hash": run.input_hash,
        "kernel_snapshot_hash": run.kernel_snapshot_hash,
        "source_text": source_text or "",
        "extraction": canonical_extraction(extraction_src),
        "matches": matches,
        "kernel_targets": canonical_kernel_targets(targets),
        "independence": independence,
        "reconstruction_gaps": sorted(set(gaps)),
        "fingerprint_coverage": FINGERPRINT_COVERAGE,
        "original_stages": stored.get("original_stages") if isinstance(stored.get("original_stages"), dict) else None,
    }
    snapshot["input_fingerprint"] = fingerprint_snapshot(snapshot)
    return snapshot


def _attach_original(snapshot: dict, run: AnalysisRun, payload: dict) -> dict:
    plan = payload.get("attention_plan") if isinstance(payload.get("attention_plan"), dict) else {}
    debug = plan.get("score_debug") if isinstance(plan.get("score_debug"), dict) else {}
    snapshot["original"] = {
        "disposition": payload.get("disposition"),
        "update": payload.get("update"),
        "cognitive_impact": payload.get("cognitive_impact") or debug.get("cognitive_impact"),
        "provider_type": run.provider_type,
        "model_name": run.model_name,
        "impact_assessor_version": debug.get("impact_assessor_version"),
        "fallback_used": bool(getattr(run, "fallback_used", False)),
    }
    if snapshot.get("original_stages") is None:
        stored = payload.get("impact_input") if isinstance(payload.get("impact_input"), dict) else {}
        snapshot["original_stages"] = stored.get("original_stages") if isinstance(stored.get("original_stages"), dict) else None
    return snapshot


def frozen_impact_input_from_run(db: Session, run: AnalysisRun) -> dict:
    """Replay input. Exact stored snapshot wins; otherwise reconstructed without live Kernel."""
    if run.status != "COMPLETED":
        raise HTTPException(422, "AnalysisRun is not completed")
    payload = dict(run.result_payload or {})
    stored = payload.get("impact_input") if isinstance(payload.get("impact_input"), dict) else None
    if stored_is_exact(stored):
        snapshot = {
            "schema_version": SNAPSHOT_VERSION,
            "input_fidelity": FIDELITY_EXACT,
            "analysis_run_id": stored.get("analysis_run_id") or str(run.id),
            "input_hash": stored.get("input_hash") or run.input_hash,
            "kernel_snapshot_hash": stored.get("kernel_snapshot_hash") or run.kernel_snapshot_hash,
            "source_text": stored.get("source_text") or "",
            "extraction": canonical_extraction(stored.get("extraction")),
            "matches": canonical_matches(stored.get("matches")),
            "kernel_targets": canonical_kernel_targets(stored.get("kernel_targets")),
            "independence": canonical_independence(
                is_duplicate=bool((stored.get("independence") or {}).get("is_duplicate")),
                independent_source_count=int((stored.get("independence") or {}).get("independent_source_count") or 1),
                secondary_report_count=int((stored.get("independence") or {}).get("secondary_report_count") or 0),
            ),
            "reconstruction_gaps": [],
            "fingerprint_coverage": FINGERPRINT_COVERAGE,
            "original_stages": stored.get("original_stages") if isinstance(stored.get("original_stages"), dict) else None,
        }
        snapshot["input_fingerprint"] = fingerprint_snapshot(snapshot)
        return _attach_original(snapshot, run, payload)
    snapshot = _reconstruct_from_payload(db, run, payload)
    return _attach_original(snapshot, run, payload)


def extraction_from_snapshot(snapshot: dict) -> ExtractionResult:
    ext = canonical_extraction(snapshot.get("extraction") or {})
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
        result.inferences.append(
            ExtractedInference(
                text=item["text"],
                author_type=_enum_value(AuthorType, item.get("author_type"), AuthorType.AI),
                confidence=float(item.get("confidence") or 0.5),
            )
        )
    for item in ext.get("evidence") or []:
        result.evidence.append(
            ExtractedEvidence(
                source_role=str(item.get("source_role") or "CLAIM"),
                source_index=0,
                target_role=str(item.get("target_role") or "CLAIM"),
                target_index=0,
                stance=_enum_value(Stance, item.get("stance"), Stance.SUPPORTS),
                strength=_enum_value(Strength, item.get("strength"), Strength.WEAK),
                confidence=float(item.get("confidence") or 0.5),
                scope=item.get("scope") or None,
            )
        )
    return result


def matches_from_snapshot(snapshot: dict) -> list[KernelMatch]:
    return matches_from_debug(snapshot.get("matches") or [])


def kernel_nodes_from_snapshot(snapshot: dict) -> list[KernelNode]:
    """Stand-in KernelNodes carrying only Impact-consumed target fields. Not persisted."""
    items = snapshot.get("kernel_targets") or snapshot.get("kernel_nodes") or []
    nodes: list[KernelNode] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        payload: dict = {}
        if item.get("proposition") not in (None, ""):
            payload["proposition"] = item["proposition"]
        if item.get("scope") not in (None, ""):
            payload["scope"] = item["scope"]
        if item.get("importance") is not None:
            payload["importance"] = item["importance"]
        if item.get("priority") is not None:
            payload["priority"] = item["priority"]
        if isinstance(item.get("payload"), dict):
            payload = {**item["payload"], **payload}
        node = KernelNode(
            node_type=str(item.get("type") or item.get("node_type") or "BELIEF"),
            title=item.get("title"),
            status=str(item.get("status") or "ACTIVE"),
            payload=payload,
            current_version=1,
        )
        node.id = UUID(str(item["id"]))
        nodes.append(node)
    return nodes
