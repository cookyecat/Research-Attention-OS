from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models.event import Event, EventEvidenceFrame, EventLineage, RepresentationAuditRun
from app.services.event_evidence_frames import persist_event_evidence_frames
from app.services.ingestion import ingest_text
from app.services.representation_consistency import (
    RepresentationConsistencyError,
    validate_lineage_edge,
)
from app.services.representation_snapshot import freeze_representation_snapshot
from app.services.same_event_candidates import same_event_candidates


def _extraction(title: str, summary: str):
    return SimpleNamespace(
        event_title=title,
        event_summary=summary,
        evidence_maturity=0.8,
    )


def _persist_legacy_frame(db, source, extraction):
    rows = persist_event_evidence_frames(
        db,
        source=source,
        extraction=extraction,
        claims=[],
        observations=[],
        analysis_run_id=None,
        extraction_diagnostics={"mode": "legacy"},
        semantic_provenance={"mode": "LEGACY_EXTRACTION", "authority": "UNAUDITED_LEGACY"},
    )
    assert len(rows) == 1
    return rows[0]


def test_event_evidence_frame_is_idempotent_for_same_analysis_identity(db):
    source = ingest_text(db, "Anthropic expanded CI capacity for agentic coding.", title="CI scaling")
    db.flush()

    first = _persist_legacy_frame(
        db, source, _extraction("Anthropic scales CI", "Anthropic expanded CI for agentic coding.")
    )
    second = _persist_legacy_frame(
        db, source, _extraction("Anthropic scales CI", "Anthropic expanded CI for agentic coding.")
    )

    assert first.id == second.id
    assert db.execute(select(EventEvidenceFrame)).scalars().all() == [first]
    assert first.workspace_id == "local-default"
    assert first.frame_payload["source"]["source_id"] == str(source.id)


def test_frame_aware_candidate_retrieval_remains_shadow_and_does_not_change_representation_digest(db):
    primary = ingest_text(db, "Primary source body.", title="Infrastructure note")
    same = ingest_text(db, "Secondary source body.", title="Engineering update")
    unrelated = ingest_text(db, "Unrelated body.", title="Astronomy weekly")
    db.flush()

    _persist_legacy_frame(
        db,
        primary,
        _extraction("Anthropic scales CI for agentic coding", "Agentic coding increased CI load and Anthropic scaled test impact analysis."),
    )
    _persist_legacy_frame(
        db,
        same,
        _extraction("Scaling CI under agentic coding load", "Anthropic scaled test impact analysis because agentic coding increased CI load."),
    )
    _persist_legacy_frame(
        db,
        unrelated,
        _extraction("New exoplanet image", "A telescope published a new exoplanet image."),
    )
    db.flush()

    before = freeze_representation_snapshot(db, primary)
    result = same_event_candidates(db, primary.id, limit=10)
    after = freeze_representation_snapshot(db, primary)

    assert result["authority"] == "NONE"
    assert result["mutates_graph"] is False
    assert len(result["candidate_set_digest"]) == 64
    by_id = {row["source_id"]: row for row in result["candidates"]}
    assert str(same.id) in by_id
    assert by_id[str(same.id)]["retrieval_method"] == "source-title+event-frame+time-v0.2"
    assert by_id[str(same.id)]["features"]["event_frame_sequence"] > 0
    assert before.graph_digest == after.graph_digest
    assert before.decision_representation_digest == after.decision_representation_digest


def test_shadow_audit_record_does_not_create_authoritative_event_membership(db):
    a = ingest_text(db, "A", title="A")
    b = ingest_text(db, "B", title="B")
    db.flush()

    audit = RepresentationAuditRun(
        identity_key="shadow-audit-test",
        workspace_id="local-default",
        audit_type="FRAME_PAIR",
        subject_type="SOURCE",
        subject_id=a.id,
        object_type="SOURCE",
        object_id=b.id,
        input_evidence_digest="e" * 64,
        input_frame_ids=[],
        evidence_bundle_refs={},
        auditor_contract_version="representation-auditor-shadow-v0.1",
        judgments={"event_identity": "SAME_EVENT"},
        supporting_evidence=[],
        conflicting_evidence=[],
        uncertainty={},
        proposed_transition={},
        authority_policy_version="shadow-none-v0.1",
        authority_result="SHADOW_ONLY",
    )
    db.add(audit)
    db.flush()

    assert audit.authority_result == "SHADOW_ONLY"
    assert db.execute(select(Event)).scalars().all() == []


def test_lineage_validator_rejects_cycles(db):
    a = Event(title="A", summary="", status="CANDIDATE")
    b = Event(title="B", summary="", status="CANDIDATE")
    c = Event(title="C", summary="", status="CANDIDATE")
    db.add_all([a, b, c])
    db.flush()
    db.add_all(
        [
            EventLineage(
                predecessor_event_id=a.id,
                successor_event_id=b.id,
                relationship="SUPERSEDED_BY",
                workspace_id="local-default",
            ),
            EventLineage(
                predecessor_event_id=b.id,
                successor_event_id=c.id,
                relationship="SUPERSEDED_BY",
                workspace_id="local-default",
            ),
        ]
    )
    db.flush()

    validate_lineage_edge(db, predecessor_event_id=a.id, successor_event_id=c.id)
    with pytest.raises(RepresentationConsistencyError, match="cycle"):
        validate_lineage_edge(db, predecessor_event_id=c.id, successor_event_id=a.id)


def test_pipeline_persists_shadow_frame_without_changing_public_extraction_contract(db):
    from app.cognitive.rule_provider import RuleBasedCognitiveProvider
    from app.testing.kernel_fixture import seed_mvp_kernel
    from app.services.pipeline import run_pipeline

    seed_mvp_kernel(db)
    source = ingest_text(
        db,
        "Anthropic expanded CI capacity for agentic coding.",
        title="Pipeline frame persistence",
    )
    result = run_pipeline(
        db,
        source.id,
        provider=RuleBasedCognitiveProvider(),
        allow_watch_creation=False,
    )

    frames = db.execute(
        select(EventEvidenceFrame).where(EventEvidenceFrame.source_id == source.id)
    ).scalars().all()
    assert len(frames) == 1
    frame = frames[0]
    assert str(frame.analysis_run_id) == result["analysis_run"]["id"]
    assert frame.frame_payload["semantic_provenance"]["mode"] == "LEGACY_EXTRACTION"
    assert frame.frame_payload["semantic_provenance"]["authority"] == "UNAUDITED_LEGACY"
    assert result["extraction_path"]["diagnostics"] == {"mode": "legacy"}


def test_audited_bridge_persists_zero_to_many_real_event_projections(db):
    source = ingest_text(db, "One article with two audited event propositions.", title="multi event")
    db.flush()
    diagnostics = {
        "mode": "bridge",
        "sources": [{
            "source_id": str(source.id),
            "events": [
                {
                    "audited_projection": {
                        "event_id": "evt-1",
                        "routing_status": "ROUTABLE",
                        "sensor_event_summary_diagnostic_only": "Company launched Product A.",
                        "actor_objects": [{"name": "Company", "role": "launcher"}],
                        "actions_changes": [{"description": "Company launched Product A.", "temporal_status": "ENACTED"}],
                        "affected_systems_populations": [],
                        "uncertainties": [],
                        "rendered_event_text": "Company launched Product A.",
                    },
                    "audit": {"n_admitted_edges": 1},
                },
                {
                    "audited_projection": {
                        "event_id": "evt-2",
                        "routing_status": "ROUTABLE",
                        "sensor_event_summary_diagnostic_only": "Company announced Product B pricing.",
                        "actor_objects": [{"name": "Company", "role": "announcer"}],
                        "actions_changes": [{"description": "Company announced Product B pricing.", "temporal_status": "ANNOUNCED"}],
                        "affected_systems_populations": [],
                        "uncertainties": [],
                        "rendered_event_text": "Company announced Product B pricing.",
                    },
                    "audit": {"n_admitted_edges": 1},
                },
            ],
        }],
    }
    rows = persist_event_evidence_frames(
        db,
        source=source,
        extraction=SimpleNamespace(),
        claims=[],
        observations=[],
        analysis_run_id=None,
        extraction_diagnostics=diagnostics,
        semantic_provenance={"mode": "AUDITED_BRIDGE", "authority": "SEMANTIC_AUDITED"},
    )
    assert len(rows) == 2
    assert {row.frame_payload["event_key"] for row in rows} == {"evt-1", "evt-2"}
    assert all(row.frame_payload["semantic_provenance"]["audited_projection"] is True for row in rows)

    empty = ingest_text(db, "No admitted event.", title="no event")
    db.flush()
    empty_rows = persist_event_evidence_frames(
        db,
        source=empty,
        extraction=SimpleNamespace(),
        claims=[],
        observations=[],
        analysis_run_id=None,
        extraction_diagnostics={"mode": "bridge", "sources": [{"source_id": str(empty.id), "events": []}]},
        semantic_provenance={"mode": "AUDITED_BRIDGE", "authority": "SEMANTIC_AUDITED"},
    )
    assert empty_rows == []
