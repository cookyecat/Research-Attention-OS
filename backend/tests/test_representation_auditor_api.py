from types import SimpleNamespace

from app.models.event import RepresentationAuditRun
from app.services.event_evidence_frames import persist_event_evidence_frames
from app.services.ingestion import ingest_text


def _bridge_frames(db, source, prefix):
    diagnostics = {
        "sources": [{
            "source_id": str(source.id),
            "events": [
                {"audited_projection": {
                    "event_id": f"{prefix}-1",
                    "routing_status": "ROUTABLE",
                    "sensor_event_summary_diagnostic_only": f"{prefix} first event",
                    "actor_objects": [],
                    "actions_changes": [{"description": f"{prefix} first event"}],
                    "affected_systems_populations": [],
                    "uncertainties": [],
                }},
                {"audited_projection": {
                    "event_id": f"{prefix}-2",
                    "routing_status": "ROUTABLE",
                    "sensor_event_summary_diagnostic_only": f"{prefix} second event",
                    "actor_objects": [],
                    "actions_changes": [{"description": f"{prefix} second event"}],
                    "affected_systems_populations": [],
                    "uncertainties": [],
                }},
            ],
        }]
    }
    return persist_event_evidence_frames(
        db,
        source=source,
        extraction=SimpleNamespace(),
        claims=[],
        observations=[],
        analysis_run_id=None,
        extraction_diagnostics=diagnostics,
        semantic_provenance={"mode": "AUDITED_BRIDGE", "authority": "SEMANTIC_AUDITED"},
    )


def test_representation_debug_endpoints_expose_shadow_candidates_and_audits(client, db):
    a = ingest_text(db, "Valve launch and rendering.", title="Steam Frame launch")
    b = ingest_text(db, "Valve pricing and accessories.", title="Steam Frame price")
    db.flush()
    af = _bridge_frames(db, a, "a")
    bf = _bridge_frames(db, b, "b")
    db.add(
        RepresentationAuditRun(
            identity_key="api-shadow-audit",
            workspace_id="local-default",
            audit_type="FRAME_PAIR",
            subject_type="EVENT_FRAME",
            subject_id=af[0].id,
            object_type="EVENT_FRAME",
            object_id=bf[0].id,
            input_evidence_digest="d" * 64,
            input_frame_ids=[str(af[0].id), str(bf[0].id)],
            evidence_bundle_refs={"bundle_version": "test"},
            auditor_contract_version="representation-auditor-frame-pair-v0.7",
            provider="test",
            model="fixture",
            judgments={
                "event_identity": {"value": "DIFFERENT_EVENT", "support_ids": ["FRAME_A", "FRAME_B"]},
                "provenance_dependency": {"value": "UNKNOWN", "direction": "UNKNOWN", "support_ids": []},
                "relation_context": {"value": "RELATED", "support_ids": ["FRAME_A", "FRAME_B"]},
            },
            supporting_evidence=[],
            conflicting_evidence=[],
            uncertainty={},
            proposed_transition={},
            authority_policy_version="shadow-none-v0.1",
            authority_result="SHADOW_ONLY",
        )
    )
    db.commit()

    candidates = client.get(f"/sources/{a.id}/same-event-frame-candidates?source_limit=10&max_pairs=20")
    assert candidates.status_code == 200, candidates.text
    body = candidates.json()
    assert body["authority"] == "NONE"
    assert body["mutates_graph"] is False
    assert any(row["candidate_kind"] == "INTRA_SOURCE_FRAME_PAIR" for row in body["pairs"])
    assert any(
        row["candidate_kind"] == "CROSS_SOURCE_FRAME_PAIR" and row["source_id_b"] == str(b.id)
        for row in body["pairs"]
    )

    audits = client.get(f"/sources/{a.id}/representation-audits")
    assert audits.status_code == 200, audits.text
    audit_body = audits.json()
    assert audit_body["frame_count"] == 2
    assert audit_body["audit_count"] == 1
    assert audit_body["audits"][0]["authority_result"] == "SHADOW_ONLY"
    assert audit_body["audits"][0]["judgments"]["event_identity"]["value"] == "DIFFERENT_EVENT"

    beliefs = client.get(f"/sources/{a.id}/representation-beliefs")
    assert beliefs.status_code == 200, beliefs.text
    belief_body = beliefs.json()
    assert belief_body["pair_count"] == 1
    latest = belief_body["beliefs"][0]["latest_epoch"]
    assert latest["counts"]["DIFFERENT_EVENT"] == 1
    assert latest["operational_opinion"]["uncertainty_mass"] == 0.666667
    assert latest["operational_opinion"]["projected_same_probability_proxy"] == 0.333333
    assert latest["operational_opinion"]["calibrated_world_truth_probability"] is False
    assert belief_body["beliefs"][0]["mutates_graph"] is False
    assert belief_body["beliefs"][0]["topology_commitment_authority"] == "NONE"


def test_representation_beliefs_follow_external_item_version_history(client, db):
    from datetime import datetime, timezone

    from app.models.acquisition import ExternalInformationItem, InformationSnapshot

    old = ingest_text(db, "Historical version body.", title="Versioned article old")
    target = ingest_text(db, "Independent target body.", title="Target article")
    current = ingest_text(db, "Current version body.", title="Versioned article current")
    db.flush()

    old_frame = _bridge_frames(db, old, "old")[0]
    target_frame = _bridge_frames(db, target, "target")[0]

    item = ExternalInformationItem(
        identity_key="belief-version-family-item",
        item_type="ARTICLE",
        canonical_url="https://example.test/versioned",
        title="Versioned article",
    )
    db.add(item)
    db.flush()
    db.add_all(
        [
            InformationSnapshot(
                external_item_id=item.id,
                raos_source_id=old.id,
                captured_at=datetime(2026, 9, 18, 10, 0, tzinfo=timezone.utc),
                content_hash="old-version-hash",
                snapshot_metadata={},
            ),
            InformationSnapshot(
                external_item_id=item.id,
                raos_source_id=current.id,
                captured_at=datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc),
                content_hash="current-version-hash",
                snapshot_metadata={},
            ),
        ]
    )
    db.add(
        RepresentationAuditRun(
            identity_key="belief-version-family-audit",
            workspace_id="local-default",
            audit_type="FRAME_PAIR",
            subject_type="EVENT_FRAME",
            subject_id=old_frame.id,
            object_type="EVENT_FRAME",
            object_id=target_frame.id,
            input_evidence_digest="v" * 64,
            input_frame_ids=[str(old_frame.id), str(target_frame.id)],
            evidence_bundle_refs={"bundle_version": "test"},
            auditor_contract_version="representation-auditor-frame-pair-v0.7",
            provider="test",
            model="fixture",
            judgments={
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
            supporting_evidence=[],
            conflicting_evidence=[],
            uncertainty={},
            proposed_transition={},
            authority_policy_version="shadow-none-v0.1",
            authority_result="SHADOW_ONLY",
        )
    )
    db.commit()

    # Historical Source ids resolve to the current Source for ordinary user-space reads,
    # but probabilistic representation must preserve the whole immutable version family.
    response = client.get(f"/sources/{old.id}/representation-beliefs")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source_id"] == str(current.id)
    assert body["source_version_ids"] == [str(old.id), str(current.id)]
    assert body["pair_count"] == 1
    assert body["beliefs"][0]["latest_epoch"]["counts"]["SAME_EVENT"] == 1
