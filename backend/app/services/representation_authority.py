from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from app.models.event import RepresentationAuditRun
from app.services.representation_evidence import RepresentationEvidenceBundle, stable_digest

AUTHORITY_PREDICATE_CONTRACT = "representation-authority-predicates-v0.2"
AUTHORITY_POLICY_VERSION = "representation-authority-shadow-v0.2"
TRUSTED_EXPLICIT_DETECTORS = {"PARSER", "METADATA", "USER"}


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower().strip()
    return re.sub(r"\s+", " ", text)


def _semantic_fingerprint(frame: dict) -> str | None:
    actors = sorted(
        {
            (_norm(row.get("name")), _norm(row.get("role")))
            for row in frame.get("actors") or []
            if isinstance(row, dict) and (row.get("name") or row.get("role"))
        }
    )
    actions = sorted(
        {
            (_norm(row.get("description")), _norm(row.get("temporal_status")))
            for row in frame.get("actions") or []
            if isinstance(row, dict) and row.get("description")
        }
    )
    affected = sorted(
        {
            (_norm(row.get("description")), _norm(row.get("reference_scope")))
            for row in frame.get("affected_systems_populations") or []
            if isinstance(row, dict) and row.get("description")
        }
    )
    payload = {
        "actors": actors,
        "actions": actions,
        "affected_systems_populations": affected,
    }
    if not actors and not actions and not affected:
        return None
    return stable_digest(payload)


def _evidence_map(bundle: RepresentationEvidenceBundle) -> dict[str, dict]:
    return {
        str(row["evidence_id"]): row
        for row in bundle.payload.get("evidence") or []
        if isinstance(row, dict) and row.get("evidence_id")
    }


def build_authority_predicate_snapshot(
    bundle: RepresentationEvidenceBundle,
    *,
    execution_context: dict,
) -> dict:
    evidence = _evidence_map(bundle)
    source_a = dict((evidence.get("SOURCE_A") or {}).get("data") or {})
    source_b = dict((evidence.get("SOURCE_B") or {}).get("data") or {})
    frame_a = dict((evidence.get("FRAME_A") or {}).get("data") or {})
    frame_b = dict((evidence.get("FRAME_B") or {}).get("data") or {})

    external_a = set(source_a.get("external_item_ids") or [])
    external_b = set(source_b.get("external_item_ids") or [])
    fp_a = _semantic_fingerprint(frame_a)
    fp_b = _semantic_fingerprint(frame_b)

    graph_facts = []
    for row in bundle.payload.get("evidence") or []:
        if not isinstance(row, dict) or row.get("kind") != "EXISTING_SOURCE_GRAPH_FACT":
            continue
        data = dict(row.get("data") or {})
        graph_facts.append(
            {
                "evidence_id": row.get("evidence_id"),
                "direction": data.get("direction"),
                "relationship": data.get("relationship"),
                "detected_by": data.get("detected_by"),
                "authority_eligible": bool(data.get("authority_eligible", True)),
            }
        )
    graph_facts.sort(
        key=lambda row: (
            str(row.get("direction") or ""),
            str(row.get("relationship") or ""),
            str(row.get("detected_by") or ""),
            str(row.get("evidence_id") or ""),
        )
    )

    provenance_a = dict(frame_a.get("semantic_provenance") or {})
    provenance_b = dict(frame_b.get("semantic_provenance") or {})
    attestation = dict(execution_context.get("attestation") or {})
    capabilities = dict(execution_context.get("capabilities") or {})

    snapshot = {
        "predicate_contract": AUTHORITY_PREDICATE_CONTRACT,
        "bundle_version": bundle.payload.get("bundle_version"),
        "bundle_digest": bundle.digest,
        "source_identity": {
            "same_source_id": source_a.get("source_id") == source_b.get("source_id"),
            "same_external_item_id": bool(external_a & external_b),
            "shared_external_item_ids": sorted(external_a & external_b),
            "same_canonical_url": bool(
                source_a.get("canonical_url")
                and source_a.get("canonical_url") == source_b.get("canonical_url")
            ),
            "same_content_hash": bool(
                source_a.get("content_hash")
                and source_a.get("content_hash") == source_b.get("content_hash")
            ),
        },
        "frame_authority": {
            "frame_a_semantic_audited": provenance_a.get("authority") == "SEMANTIC_AUDITED",
            "frame_b_semantic_audited": provenance_b.get("authority") == "SEMANTIC_AUDITED",
            "both_semantic_audited": (
                provenance_a.get("authority") == "SEMANTIC_AUDITED"
                and provenance_b.get("authority") == "SEMANTIC_AUDITED"
            ),
            "frame_a_routable": provenance_a.get("routing_status") == "ROUTABLE",
            "frame_b_routable": provenance_b.get("routing_status") == "ROUTABLE",
        },
        "event_semantic_exactness": {
            "event_semantic_fingerprint_a": fp_a,
            "event_semantic_fingerprint_b": fp_b,
            "exact_event_semantic_fingerprint": bool(fp_a and fp_b and fp_a == fp_b),
        },
        "provenance": {
            "explicit_graph_facts": graph_facts,
        },
        "origin_execution": {
            "purpose": execution_context.get("purpose"),
            "runtime_profile_hash": execution_context.get("runtime_profile_hash"),
            "attestation_status": attestation.get("status"),
            "attestation_mismatches": list(attestation.get("mismatches") or []),
            "cognition_capability": capabilities.get("cognition"),
            "side_effects_authorized": bool(
                (execution_context.get("authority") or {}).get("side_effects_authorized")
            ),
        },
    }
    return snapshot


def predicate_snapshot_digest(snapshot: dict) -> str:
    return stable_digest(snapshot)


def _origin_authority_eligible(snapshot: dict) -> bool:
    origin = dict(snapshot.get("origin_execution") or {})
    return bool(
        origin.get("purpose") == "CANONICAL"
        and origin.get("attestation_status") == "ATTESTED"
        and not origin.get("attestation_mismatches")
        and origin.get("cognition_capability") == "READY"
        and origin.get("runtime_profile_hash")
    )


def _base_outcome(value: str, outcome: str, *reasons: str) -> dict:
    return {
        "judgment": value,
        "outcome": outcome,
        "reason_codes": [reason for reason in reasons if reason],
    }


def _simulate_event_identity(judgment: dict, predicates: dict) -> dict:
    value = str(judgment.get("value") or "")
    support = set(judgment.get("support_ids") or [])
    conflicts = set(judgment.get("conflict_ids") or [])
    if value == "UNCERTAIN":
        return _base_outcome(value, "UNRESOLVED", "AUDITOR_UNCERTAIN")
    if value == "DIFFERENT_EVENT":
        return _base_outcome(
            value,
            "CANDIDATE_ONLY",
            "NEGATIVE_RELATION_NO_AUTHORITY_PROJECTION_V01",
        )
    if value != "SAME_EVENT":
        return _base_outcome(value, "REJECTED", "UNKNOWN_EVENT_IDENTITY_LABEL")

    frame_auth = dict(predicates.get("frame_authority") or {})
    source_identity = dict(predicates.get("source_identity") or {})
    semantic = dict(predicates.get("event_semantic_exactness") or {})

    if not {"FRAME_A", "FRAME_B"} <= support:
        return _base_outcome(value, "REJECTED", "MISSING_COMPARATIVE_FRAME_SUPPORT")
    if conflicts:
        return _base_outcome(value, "CANDIDATE_ONLY", "CITED_CONFLICTING_EVIDENCE")
    if not frame_auth.get("both_semantic_audited"):
        return _base_outcome(value, "CANDIDATE_ONLY", "SEMANTIC_INPUT_NOT_FULLY_AUDITED")
    if not _origin_authority_eligible(predicates):
        return _base_outcome(value, "UNRESOLVED", "ORIGIN_EXECUTION_NOT_AUTHORITY_ELIGIBLE")

    strong_same_resource_anchor = bool(
        source_identity.get("same_external_item_id")
        and source_identity.get("same_canonical_url")
        and semantic.get("exact_event_semantic_fingerprint")
    )
    if strong_same_resource_anchor:
        return _base_outcome(
            value,
            "WOULD_AUTHORIZE",
            "SAME_EXTERNAL_ITEM_EXACT_EVENT_SEMANTICS",
        )
    return _base_outcome(
        value,
        "CANDIDATE_ONLY",
        "INSUFFICIENT_DETERMINISTIC_SAME_EVENT_ANCHOR",
    )


def _expected_graph_direction(direction: str) -> str | None:
    if direction == "A_FROM_B":
        return "A_TO_B"
    if direction == "B_FROM_A":
        return "B_TO_A"
    return None


def _simulate_provenance(judgment: dict, predicates: dict) -> dict:
    value = str(judgment.get("value") or "")
    direction = str(judgment.get("direction") or "")
    conflicts = set(judgment.get("conflict_ids") or [])

    if value == "UNKNOWN":
        return {
            **_base_outcome(value, "UNRESOLVED", "PROVENANCE_UNKNOWN"),
            "direction": direction,
        }
    if value == "INDEPENDENT":
        return {
            **_base_outcome(value, "CANDIDATE_ONLY", "POSITIVE_INDEPENDENCE_PREDICATE_NOT_AVAILABLE_V01"),
            "direction": direction,
        }
    if value not in {"REPOST", "DERIVED_FROM"}:
        return {
            **_base_outcome(value, "REJECTED", "UNKNOWN_PROVENANCE_LABEL"),
            "direction": direction,
        }
    expected_direction = _expected_graph_direction(direction)
    if expected_direction is None:
        return {
            **_base_outcome(value, "REJECTED", "MISSING_DIRECTIONAL_PROVENANCE"),
            "direction": direction,
        }
    if conflicts:
        return {
            **_base_outcome(value, "CANDIDATE_ONLY", "CITED_CONFLICTING_EVIDENCE"),
            "direction": direction,
        }
    if not _origin_authority_eligible(predicates):
        return {
            **_base_outcome(value, "UNRESOLVED", "ORIGIN_EXECUTION_NOT_AUTHORITY_ELIGIBLE"),
            "direction": direction,
        }

    facts = list((predicates.get("provenance") or {}).get("explicit_graph_facts") or [])
    match = next(
        (
            row
            for row in facts
            if row.get("relationship") == value
            and row.get("direction") == expected_direction
            and row.get("detected_by") in TRUSTED_EXPLICIT_DETECTORS
            and row.get("authority_eligible") is True
        ),
        None,
    )
    if match is not None:
        return {
            **_base_outcome(
                value,
                "WOULD_AUTHORIZE",
                "MATCHING_TRUSTED_EXPLICIT_DIRECTED_PROVENANCE_FACT",
            ),
            "direction": direction,
            "evidence_id": match.get("evidence_id"),
        }
    return {
        **_base_outcome(
            value,
            "CANDIDATE_ONLY",
            "NO_MATCHING_TRUSTED_EXPLICIT_DIRECTED_PROVENANCE_FACT",
        ),
        "direction": direction,
    }


def _simulate_relation_context(judgment: dict) -> dict:
    value = str(judgment.get("value") or "")
    if value == "UNCERTAIN":
        return _base_outcome(value, "UNRESOLVED", "RELATION_CONTEXT_UNCERTAIN")
    if value in {"RELATED", "UNRELATED"}:
        return _base_outcome(value, "CANDIDATE_ONLY", "NO_RELATION_CONTEXT_AUTHORITY_PROJECTION_V01")
    return _base_outcome(value, "REJECTED", "UNKNOWN_RELATION_CONTEXT_LABEL")


def simulate_representation_authority(audit: RepresentationAuditRun) -> dict:
    """Pure deterministic E1 simulation. Never reads DB or invokes a model."""
    refs = dict(audit.evidence_bundle_refs or {})
    predicates = refs.get("authority_predicates")
    expected_digest = refs.get("authority_predicates_digest")
    if not isinstance(predicates, dict):
        return {
            "mode": "SHADOW_AUTHORITY_SIMULATION",
            "policy_version": AUTHORITY_POLICY_VERSION,
            "mutates_graph": False,
            "audit_run_id": str(audit.id),
            "eligible": False,
            "error": "MISSING_FROZEN_PREDICATE_SNAPSHOT",
            "outcomes": {},
        }
    actual_digest = predicate_snapshot_digest(predicates)
    if not expected_digest or expected_digest != actual_digest:
        return {
            "mode": "SHADOW_AUTHORITY_SIMULATION",
            "policy_version": AUTHORITY_POLICY_VERSION,
            "mutates_graph": False,
            "audit_run_id": str(audit.id),
            "eligible": False,
            "error": "PREDICATE_SNAPSHOT_DIGEST_MISMATCH",
            "outcomes": {},
        }
    if predicates.get("predicate_contract") != AUTHORITY_PREDICATE_CONTRACT:
        return {
            "mode": "SHADOW_AUTHORITY_SIMULATION",
            "policy_version": AUTHORITY_POLICY_VERSION,
            "mutates_graph": False,
            "audit_run_id": str(audit.id),
            "eligible": False,
            "error": "UNSUPPORTED_PREDICATE_CONTRACT",
            "outcomes": {},
        }

    judgments = dict(audit.judgments or {})
    outcomes = {
        "event_identity": _simulate_event_identity(
            dict(judgments.get("event_identity") or {}),
            predicates,
        ),
        "provenance_dependency": _simulate_provenance(
            dict(judgments.get("provenance_dependency") or {}),
            predicates,
        ),
        "relation_context": _simulate_relation_context(
            dict(judgments.get("relation_context") or {})
        ),
    }
    counts: dict[str, int] = {}
    for row in outcomes.values():
        outcome = str(row.get("outcome") or "UNKNOWN")
        counts[outcome] = counts.get(outcome, 0) + 1
    return {
        "mode": "SHADOW_AUTHORITY_SIMULATION",
        "policy_version": AUTHORITY_POLICY_VERSION,
        "predicate_contract": AUTHORITY_PREDICATE_CONTRACT,
        "predicate_digest": actual_digest,
        "mutates_graph": False,
        "audit_run_id": str(audit.id),
        "eligible": True,
        "origin_authority_eligible": _origin_authority_eligible(predicates),
        "outcome_counts": counts,
        "outcomes": outcomes,
    }
