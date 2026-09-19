from sqlalchemy import func, select

from app.models.event import EventSource
from app.models.source import SourceEdge
from app.services.ingestion import ingest_text
from app.services.same_event_candidates import same_event_candidates


def test_same_event_candidate_retrieval_is_shadow_only_and_ranks_plausible_pair(db):
    primary = ingest_text(
        db,
        "Google introduced a new family coordination agent.",
        title='Google announces new experimental "CC" AI agent for families',
        publisher="Ars Technica",
    )
    plausible = ingest_text(
        db,
        "Google described CC for families and groups.",
        title="CC is an AI agent for families and groups",
        publisher="Google",
    )
    unrelated = ingest_text(
        db,
        "A genomics transfer learning result.",
        title="Transfer learning for genomic prediction in underrepresented populations",
        publisher="Google Research",
    )
    db.flush()

    edge_count_before = db.scalar(select(func.count()).select_from(SourceEdge))
    event_link_count_before = db.scalar(select(func.count()).select_from(EventSource))

    result = same_event_candidates(db, primary.id, limit=10)

    assert result["mode"] == "SHADOW_CANDIDATE_RETRIEVAL"
    assert result["authority"] == "NONE"
    assert result["mutates_graph"] is False
    ids = [row["source_id"] for row in result["candidates"]]
    assert str(plausible.id) in ids
    assert ids.index(str(plausible.id)) < ids.index(str(unrelated.id))
    plausible_row = next(row for row in result["candidates"] if row["source_id"] == str(plausible.id))
    assert plausible_row["features"]["title_sequence"] > 0.4

    assert db.scalar(select(func.count()).select_from(SourceEdge)) == edge_count_before
    assert db.scalar(select(func.count()).select_from(EventSource)) == event_link_count_before


def test_frame_pair_expansion_preserves_all_latest_frames_without_authority(db):
    from types import SimpleNamespace

    from app.services.event_evidence_frames import persist_event_evidence_frames
    from app.services.same_event_candidates import same_event_frame_candidates
    from app.services.representation_snapshot import freeze_representation_snapshot

    primary = ingest_text(db, "Primary multi-event body.", title="Valve Steam Frame launch and rendering")
    candidate = ingest_text(db, "Candidate multi-event body.", title="Steam Frame pricing and launch")
    db.flush()

    diagnostics_primary = {
        "sources": [{
            "source_id": str(primary.id),
            "events": [
                {"audited_projection": {"event_id": "p1", "routing_status": "ROUTABLE", "sensor_event_summary_diagnostic_only": "Valve launched Steam Frame.", "actor_objects": [], "actions_changes": [{"description": "Valve launched Steam Frame."}], "affected_systems_populations": [], "uncertainties": []}},
                {"audited_projection": {"event_id": "p2", "routing_status": "ROUTABLE", "sensor_event_summary_diagnostic_only": "Valve described foveated rendering.", "actor_objects": [], "actions_changes": [{"description": "Valve described foveated rendering."}], "affected_systems_populations": [], "uncertainties": []}},
            ],
        }]
    }
    diagnostics_candidate = {
        "sources": [{
            "source_id": str(candidate.id),
            "events": [
                {"audited_projection": {"event_id": "c1", "routing_status": "ROUTABLE", "sensor_event_summary_diagnostic_only": "Valve announced Steam Frame pricing.", "actor_objects": [], "actions_changes": [{"description": "Valve announced Steam Frame pricing."}], "affected_systems_populations": [], "uncertainties": []}},
                {"audited_projection": {"event_id": "c2", "routing_status": "ROUTABLE", "sensor_event_summary_diagnostic_only": "Valve announced Steam Frame accessories.", "actor_objects": [], "actions_changes": [{"description": "Valve announced accessories."}], "affected_systems_populations": [], "uncertainties": []}},
            ],
        }]
    }
    provenance = {"mode": "AUDITED_BRIDGE", "authority": "SEMANTIC_AUDITED"}
    pframes = persist_event_evidence_frames(
        db, source=primary, extraction=SimpleNamespace(), claims=[], observations=[],
        analysis_run_id=None, extraction_diagnostics=diagnostics_primary, semantic_provenance=provenance,
    )
    cframes = persist_event_evidence_frames(
        db, source=candidate, extraction=SimpleNamespace(), claims=[], observations=[],
        analysis_run_id=None, extraction_diagnostics=diagnostics_candidate, semantic_provenance=provenance,
    )
    db.flush()

    before = freeze_representation_snapshot(db, primary)
    result = same_event_frame_candidates(db, primary.id, source_limit=10, max_pairs=20)
    after = freeze_representation_snapshot(db, primary)

    cross = [row for row in result["pairs"] if row["candidate_kind"] == "CROSS_SOURCE_FRAME_PAIR" and row["source_id_b"] == str(candidate.id)]
    intra = [row for row in result["pairs"] if row["candidate_kind"] == "INTRA_SOURCE_FRAME_PAIR"]
    assert len(pframes) == 2
    assert len(cframes) == 2
    assert len(cross) == 4  # 2 x 2, no representative-frame collapse
    assert len(intra) == 1
    assert result["authority"] == "NONE"
    assert result["mutates_graph"] is False
    assert len(result["frame_pair_candidate_set_digest"]) == 64
    assert before.graph_digest == after.graph_digest
    assert before.decision_representation_digest == after.decision_representation_digest
