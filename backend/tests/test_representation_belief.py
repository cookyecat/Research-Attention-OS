from __future__ import annotations

from types import SimpleNamespace

from app.models.event import RepresentationAuditRun
from app.services.event_evidence_frames import persist_event_evidence_frames
from app.services.ingestion import ingest_text
from app.services.representation_belief import (
    REPRESENTATION_BELIEF_VIEW_CONTRACT,
    belief_history_from_audits,
    frame_pair_belief_history,
)


def _frames(db):
    a = ingest_text(db, "A substantive source.", title="A")
    b = ingest_text(db, "B substantive source.", title="B")
    db.flush()
    provenance = {"mode": "AUDITED_BRIDGE", "authority": "SEMANTIC_AUDITED"}
    rows = []
    for source, key, summary in [
        (a, "a-1", "Company launched Product A."),
        (b, "b-1", "Company launched Product A."),
    ]:
        diagnostics = {
            "sources": [{
                "source_id": str(source.id),
                "events": [{
                    "audited_projection": {
                        "event_id": key,
                        "routing_status": "ROUTABLE",
                        "sensor_event_summary_diagnostic_only": summary,
                        "actor_objects": [{"name": "Company", "role": "actor"}],
                        "actions_changes": [{"description": summary, "temporal_status": "ENACTED"}],
                        "affected_systems_populations": [],
                        "uncertainties": [],
                    }
                }],
            }]
        }
        frames = persist_event_evidence_frames(
            db,
            source=source,
            extraction=SimpleNamespace(),
            claims=[],
            observations=[],
            analysis_run_id=None,
            extraction_diagnostics=diagnostics,
            semantic_provenance=provenance,
        )
        rows.append(frames[0])
    db.flush()
    return a, b, rows[0], rows[1]


def _audit(db, frame_a, frame_b, *, identity_key, digest, label, created_suffix=0):
    row = RepresentationAuditRun(
        identity_key=identity_key,
        workspace_id="local-default",
        audit_type="FRAME_PAIR",
        subject_type="EVENT_FRAME",
        subject_id=frame_a.id,
        object_type="EVENT_FRAME",
        object_id=frame_b.id,
        input_evidence_digest=digest,
        input_frame_ids=[str(frame_a.id), str(frame_b.id)],
        evidence_bundle_refs={"bundle_version": "test"},
        auditor_contract_version="representation-auditor-frame-pair-v0.7",
        provider="test-provider",
        model="test-model",
        judgments={
            "event_identity": {
                "value": label,
                "support_ids": ["FRAME_A", "FRAME_B"] if label != "UNCERTAIN" else [],
                "conflict_ids": [],
                "rationale": "fixture",
                "missing_evidence": [],
            },
            "provenance_dependency": {
                "value": "UNKNOWN",
                "direction": "UNKNOWN",
                "support_ids": [],
                "conflict_ids": [],
                "rationale": "fixture",
                "missing_evidence": [],
            },
            "relation_context": {
                "value": "RELATED",
                "support_ids": ["FRAME_A", "FRAME_B"],
                "conflict_ids": [],
                "rationale": "fixture",
                "missing_evidence": [],
            },
        },
        supporting_evidence=[],
        conflicting_evidence=[],
        uncertainty={},
        proposed_transition={},
        authority_policy_version="shadow-none-v0.1",
        authority_result="SHADOW_ONLY",
    )
    db.add(row)
    db.flush()
    return row


def test_single_same_event_realization_preserves_large_uncertainty(db):
    _a, _b, fa, fb = _frames(db)
    row = _audit(
        db,
        fa,
        fb,
        identity_key="belief-single",
        digest="1" * 64,
        label="SAME_EVENT",
    )

    result = belief_history_from_audits([row])
    epoch = result["latest_epoch"]
    opinion = epoch["operational_opinion"]

    assert result["belief_contract"] == REPRESENTATION_BELIEF_VIEW_CONTRACT
    assert epoch["counts"] == {
        "SAME_EVENT": 1,
        "DIFFERENT_EVENT": 0,
        "UNCERTAIN": 0,
    }
    assert opinion["belief_same_mass"] == 0.333333
    assert opinion["disbelief_same_mass"] == 0.0
    assert opinion["uncertainty_mass"] == 0.666667
    assert opinion["projected_same_probability_proxy"] == 0.666667
    assert opinion["calibrated_world_truth_probability"] is False
    assert result["topology_commitment_authority"] == "NONE"


def test_uncertain_realization_adds_uncommitted_mass_not_negative_evidence(db):
    _a, _b, fa, fb = _frames(db)
    rows = [
        _audit(db, fa, fb, identity_key="belief-s1", digest="2" * 64, label="SAME_EVENT"),
        _audit(db, fa, fb, identity_key="belief-d1", digest="2" * 64, label="DIFFERENT_EVENT"),
        _audit(db, fa, fb, identity_key="belief-u1", digest="2" * 64, label="UNCERTAIN"),
        _audit(db, fa, fb, identity_key="belief-s2", digest="2" * 64, label="SAME_EVENT"),
    ]

    result = belief_history_from_audits(rows)
    epoch = result["latest_epoch"]
    opinion = epoch["operational_opinion"]

    assert epoch["counts"] == {
        "SAME_EVENT": 2,
        "DIFFERENT_EVENT": 1,
        "UNCERTAIN": 1,
    }
    assert epoch["response_distribution"] == {
        "SAME_EVENT": 0.5,
        "DIFFERENT_EVENT": 0.25,
        "UNCERTAIN": 0.25,
    }
    assert epoch["response_entropy_bits"] == 1.5
    assert opinion["belief_same_mass"] == 0.333333
    assert opinion["disbelief_same_mass"] == 0.166667
    assert opinion["uncertainty_mass"] == 0.5
    assert opinion["projected_same_probability_proxy"] == 0.583333


def test_evidence_digest_change_creates_new_epoch_and_jsd(db):
    _a, _b, fa, fb = _frames(db)
    rows = [
        _audit(db, fa, fb, identity_key="epoch-a1", digest="a" * 64, label="SAME_EVENT"),
        _audit(db, fa, fb, identity_key="epoch-a2", digest="a" * 64, label="SAME_EVENT"),
        _audit(db, fa, fb, identity_key="epoch-b1", digest="b" * 64, label="DIFFERENT_EVENT"),
        _audit(db, fa, fb, identity_key="epoch-b2", digest="b" * 64, label="DIFFERENT_EVENT"),
    ]

    result = belief_history_from_audits(rows)
    assert result["epoch_count"] == 2
    assert result["epochs"][0]["jsd_from_previous_compatible_epoch_bits"] is None
    assert result["epochs"][1]["jsd_from_previous_compatible_epoch_bits"] == 1.0
    assert result["epochs"][0]["response_distribution"]["SAME_EVENT"] == 1.0
    assert result["epochs"][1]["response_distribution"]["DIFFERENT_EVENT"] == 1.0


def test_db_pair_history_is_orientation_invariant(db):
    _a, _b, fa, fb = _frames(db)
    _audit(db, fa, fb, identity_key="orientation-ab", digest="c" * 64, label="SAME_EVENT")
    _audit(db, fb, fa, identity_key="orientation-ba", digest="c" * 64, label="SAME_EVENT")
    db.commit()

    forward = frame_pair_belief_history(db, fa.id, fb.id)
    reverse = frame_pair_belief_history(db, fb.id, fa.id)
    assert forward == reverse
    assert forward["latest_epoch"]["sample_count"] == 2


def test_source_pair_limit_does_not_truncate_realizations(db):
    from app.services.representation_belief import source_representation_beliefs

    source_a, source_b, fa, fb = _frames(db)
    for index, label in enumerate(["SAME_EVENT", "SAME_EVENT", "DIFFERENT_EVENT", "UNCERTAIN"]):
        _audit(
            db,
            fa,
            fb,
            identity_key=f"limit-realization-{index}",
            digest="9" * 64,
            label=label,
        )
    db.commit()

    result = source_representation_beliefs(db, source_a.id, limit=1)
    assert result["pair_count"] == 1
    assert result["returned_pair_count"] == 1
    assert result["beliefs"][0]["latest_epoch"]["sample_count"] == 4
    assert result["beliefs"][0]["latest_epoch"]["counts"] == {
        "SAME_EVENT": 2,
        "DIFFERENT_EVENT": 1,
        "UNCERTAIN": 1,
    }
