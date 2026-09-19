from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.representation_authority import (
    AUTHORITY_POLICY_VERSION,
    AUTHORITY_PREDICATE_CONTRACT,
    predicate_snapshot_digest,
    simulate_representation_authority,
)


def _predicates(**overrides):
    base = {
        "predicate_contract": AUTHORITY_PREDICATE_CONTRACT,
        "bundle_version": "representation-evidence-bundle-v0.3",
        "bundle_digest": "b" * 64,
        "source_identity": {
            "same_source_id": False,
            "same_external_item_id": False,
            "shared_external_item_ids": [],
            "same_canonical_url": False,
            "same_content_hash": False,
        },
        "frame_authority": {
            "frame_a_semantic_audited": True,
            "frame_b_semantic_audited": True,
            "both_semantic_audited": True,
            "frame_a_routable": True,
            "frame_b_routable": True,
        },
        "event_semantic_exactness": {
            "event_semantic_fingerprint_a": "a" * 64,
            "event_semantic_fingerprint_b": "b" * 64,
            "exact_event_semantic_fingerprint": False,
        },
        "provenance": {"explicit_graph_facts": []},
        "origin_execution": {
            "purpose": "CANONICAL",
            "runtime_profile_hash": "p" * 64,
            "attestation_status": "ATTESTED",
            "attestation_mismatches": [],
            "cognition_capability": "READY",
            "side_effects_authorized": True,
        },
    }
    for key, value in overrides.items():
        base[key] = value
    return base


def _audit(*, predicates=None, judgments=None):
    refs = {}
    if predicates is not None:
        refs = {
            "authority_predicates": predicates,
            "authority_predicates_digest": predicate_snapshot_digest(predicates),
        }
    return SimpleNamespace(
        id=uuid4(),
        evidence_bundle_refs=refs,
        judgments=judgments
        or {
            "event_identity": {
                "value": "SAME_EVENT",
                "support_ids": ["FRAME_A", "FRAME_B"],
                "conflict_ids": [],
            },
            "provenance_dependency": {
                "value": "UNKNOWN",
                "direction": "UNKNOWN",
                "support_ids": [],
                "conflict_ids": [],
            },
            "relation_context": {
                "value": "RELATED",
                "support_ids": ["FRAME_A", "FRAME_B"],
                "conflict_ids": [],
            },
        },
    )


def test_e1_old_audit_without_frozen_predicates_fails_closed():
    result = simulate_representation_authority(_audit(predicates=None))
    assert result["eligible"] is False
    assert result["error"] == "MISSING_FROZEN_PREDICATE_SNAPSHOT"
    assert result["mutates_graph"] is False


def test_e1_cross_publication_same_event_remains_candidate_only():
    result = simulate_representation_authority(_audit(predicates=_predicates()))
    event = result["outcomes"]["event_identity"]
    assert event["outcome"] == "CANDIDATE_ONLY"
    assert "INSUFFICIENT_DETERMINISTIC_SAME_EVENT_ANCHOR" in event["reason_codes"]
    assert result["mutates_graph"] is False


def test_e1_same_external_item_exact_semantics_can_would_authorize():
    predicates = _predicates()
    predicates["source_identity"].update(
        {
            "same_external_item_id": True,
            "shared_external_item_ids": ["external-1"],
            "same_canonical_url": True,
            # Different content hashes are expected for immutable Source versions.
            "same_content_hash": False,
        }
    )
    predicates["event_semantic_exactness"].update(
        {
            "event_semantic_fingerprint_b": predicates["event_semantic_exactness"][
                "event_semantic_fingerprint_a"
            ],
            "exact_event_semantic_fingerprint": True,
        }
    )
    result = simulate_representation_authority(_audit(predicates=predicates))
    event = result["outcomes"]["event_identity"]
    assert event["outcome"] == "WOULD_AUTHORIZE"
    assert event["reason_codes"] == ["SAME_EXTERNAL_ITEM_EXACT_EVENT_SEMANTICS"]
    assert result["origin_authority_eligible"] is True
    assert result["mutates_graph"] is False


def test_e1_same_url_without_external_item_or_exact_semantics_is_not_enough():
    predicates = _predicates()
    predicates["source_identity"]["same_canonical_url"] = True
    result = simulate_representation_authority(_audit(predicates=predicates))
    assert result["outcomes"]["event_identity"]["outcome"] == "CANDIDATE_ONLY"


def test_e1_non_attested_origin_never_would_authorize():
    predicates = _predicates()
    predicates["source_identity"].update(
        {
            "same_external_item_id": True,
            "shared_external_item_ids": ["external-1"],
            "same_canonical_url": True,
        }
    )
    predicates["event_semantic_exactness"].update(
        {
            "event_semantic_fingerprint_b": predicates["event_semantic_exactness"][
                "event_semantic_fingerprint_a"
            ],
            "exact_event_semantic_fingerprint": True,
        }
    )
    predicates["origin_execution"]["attestation_status"] = "FAILED"
    result = simulate_representation_authority(_audit(predicates=predicates))
    assert result["outcomes"]["event_identity"]["outcome"] == "UNRESOLVED"
    assert result["origin_authority_eligible"] is False


def test_e1_provenance_requires_matching_direction_and_trusted_explicit_detector():
    predicates = _predicates()
    predicates["provenance"]["explicit_graph_facts"] = [
        {
            "evidence_id": "GRAPH_EDGE_0",
            "direction": "A_TO_B",
            "relationship": "DERIVED_FROM",
            "detected_by": "PARSER",
            "authority_eligible": True,
        }
    ]
    judgments = {
        "event_identity": {
            "value": "UNCERTAIN",
            "support_ids": [],
            "conflict_ids": [],
        },
        "provenance_dependency": {
            "value": "DERIVED_FROM",
            "direction": "A_FROM_B",
            "support_ids": ["GRAPH_EDGE_0"],
            "conflict_ids": [],
        },
        "relation_context": {
            "value": "UNCERTAIN",
            "support_ids": [],
            "conflict_ids": [],
        },
    }
    result = simulate_representation_authority(_audit(predicates=predicates, judgments=judgments))
    prov = result["outcomes"]["provenance_dependency"]
    assert prov["outcome"] == "WOULD_AUTHORIZE"
    assert prov["direction"] == "A_FROM_B"

    predicates["provenance"]["explicit_graph_facts"][0]["detected_by"] = "AI"
    result2 = simulate_representation_authority(_audit(predicates=predicates, judgments=judgments))
    assert result2["outcomes"]["provenance_dependency"]["outcome"] == "CANDIDATE_ONLY"


def test_e1_predicate_digest_tamper_fails_closed():
    predicates = _predicates()
    audit = _audit(predicates=predicates)
    audit.evidence_bundle_refs["authority_predicates_digest"] = "0" * 64
    result = simulate_representation_authority(audit)
    assert result["eligible"] is False
    assert result["error"] == "PREDICATE_SNAPSHOT_DIGEST_MISMATCH"


def test_e1_replay_is_deterministic_and_policy_versioned():
    audit = _audit(predicates=_predicates())
    a = simulate_representation_authority(audit)
    b = simulate_representation_authority(audit)
    assert a == b
    assert a["policy_version"] == AUTHORITY_POLICY_VERSION
