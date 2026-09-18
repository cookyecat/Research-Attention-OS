from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.enums import DetectedBy, SourceEdgeRelationship
from app.models.event import Event, EventSource
from app.services.analysis_runs import compute_identity
from app.services.ingestion import ingest_text
from app.services.pipeline import run_pipeline
from app.services.representation_snapshot import freeze_representation_snapshot
from app.services.source_graph import persist_source_edge
from app.testing.kernel_fixture import seed_mvp_kernel


def test_representation_snapshot_is_deterministic(db):
    source = ingest_text(db, "A stable source about a robotics result.", title="Stable source")
    first = freeze_representation_snapshot(db, source)
    second = freeze_representation_snapshot(db, source)

    assert first.graph_digest == second.graph_digest
    assert first.decision_representation_digest == second.decision_representation_digest
    assert first.as_dict() == second.as_dict()


def test_candidate_event_and_related_edge_change_graph_not_decision_digest(db):
    source = ingest_text(db, "One report about an AI launch.", title="AI launch")
    related = ingest_text(db, "A related but different AI device story.", title="Related device")
    before = freeze_representation_snapshot(db, source)

    event = Event(
        title="Tentative AI launch",
        event_type="PRODUCT_ANNOUNCEMENT",
        summary="Candidate world-event hypothesis.",
        confidence=0.6,
        status="CANDIDATE",
    )
    db.add(event)
    db.flush()
    db.add(EventSource(event_id=event.id, source_id=source.id, relationship="REPORTS", confidence=0.6))
    persist_source_edge(
        db,
        source.id,
        related.id,
        SourceEdgeRelationship.DISCUSSES,
        confidence=0.8,
        detected_by=DetectedBy.AI,
        evidence="Related topic, different event.",
    )
    db.flush()

    after = freeze_representation_snapshot(db, source)
    assert before.graph_digest != after.graph_digest
    assert before.decision_representation_digest == after.decision_representation_digest
def test_independence_relation_changes_decision_representation_digest(db):
    primary = ingest_text(db, "Primary report.", title="Primary")
    secondary = ingest_text(db, "Secondary rewrite.", title="Secondary")
    before = freeze_representation_snapshot(db, primary, [secondary])

    persist_source_edge(
        db,
        secondary.id,
        primary.id,
        SourceEdgeRelationship.DERIVED_FROM,
        confidence=0.95,
        detected_by=DetectedBy.METADATA,
        evidence="Explicit derivation.",
    )
    db.flush()

    after = freeze_representation_snapshot(db, primary, [secondary])
    assert before.graph_digest != after.graph_digest
    assert before.decision_representation_digest != after.decision_representation_digest
    assert after.relational_context.secondary_reports == 1


def test_collective_attention_evidence_changes_decision_digest_and_identity(db):
    source = ingest_text(db, "One article whose audience evidence arrives later.", title="Late P evidence")
    before = freeze_representation_snapshot(db, source)

    meta = dict(source.raw_metadata or {})
    meta["collective_attention_evidence_packets"] = {
        "wechat": {"read_count": 120000, "captured_at": "2026-09-18T12:00:00Z"}
    }
    source.raw_metadata = meta
    db.flush()
    after = freeze_representation_snapshot(db, source)

    assert before.decision_representation_digest != after.decision_representation_digest

    common = dict(
        input_digest="same-source-input",
        kernel_digest="same-kernel",
        provider_type="rule",
        model_name=None,
        embedding_model_version="none",
        execution_digest="same-execution",
    )
    first_identity = compute_identity(
        **common,
        decision_representation_digest=before.decision_representation_digest,
    )
    second_identity = compute_identity(
        **common,
        decision_representation_digest=after.decision_representation_digest,
    )
    assert first_identity != second_identity
def test_pipeline_payload_records_frozen_representation_snapshot(db):
    seed_mvp_kernel(db)
    source = ingest_text(
        db,
        "A technical note about motor intelligence and latency tradeoffs.",
        title="Representation payload probe",
    )

    result = run_pipeline(db, source.id, reprocess=True)

    snapshot = result["representation_snapshot"]
    assert snapshot["primary_source_id"] == str(source.id)
    assert snapshot["graph_digest"]
    assert snapshot["decision_representation_digest"]
    assert snapshot["schema_version"] == "world-representation-v0.1"
    assert snapshot["decision_version"] == "decision-representation-v0.1"
    provenance = result["impact_input"]["extraction"]["analysis_provenance"]
    assert provenance["representation_graph_digest"] == snapshot["graph_digest"]
    assert (
        provenance["decision_representation_digest"]
        == snapshot["decision_representation_digest"]
    )


class _MutatingRepresentationProvider(RuleBasedCognitiveProvider):
    def __init__(self, db, source):
        self._db = db
        self._source = source

    def match_kernel(self, extraction, nodes, extra_text="", **kwargs):
        meta = dict(self._source.raw_metadata or {})
        meta["collective_attention_evidence_packets"] = {
            "late-signal": {"observed": True, "captured_at": "2026-09-18T12:00:00Z"}
        }
        self._source.raw_metadata = meta
        self._db.flush()
        return super().match_kernel(extraction, nodes, extra_text=extra_text, **kwargs)
def test_pipeline_fails_closed_if_decision_representation_changes_mid_run(db):
    seed_mvp_kernel(db)
    source = ingest_text(
        db,
        "A technical note about embodied intelligence and latency.",
        title="Representation drift probe",
    )
    provider = _MutatingRepresentationProvider(db, source)

    import pytest

    with pytest.raises(
        RuntimeError,
        match="Decision-relevant Representation Snapshot changed during analysis",
    ):
        run_pipeline(
            db,
            source.id,
            provider=provider,
            reprocess=True,
        )


def test_cites_changes_graph_digest_not_decision_representation_digest(db):
    source = ingest_text(db, "Article with an explicit outbound reference.", title="Article")
    target = ingest_text(db, "Referenced source.", title="Referenced source")
    before = freeze_representation_snapshot(db, source)

    persist_source_edge(
        db,
        source.id,
        target.id,
        SourceEdgeRelationship.CITES,
        confidence=1.0,
        detected_by=DetectedBy.PARSER,
        evidence="Explicit href",
    )
    db.flush()

    after = freeze_representation_snapshot(db, source)
    assert before.graph_digest != after.graph_digest
    assert before.decision_representation_digest == after.decision_representation_digest
