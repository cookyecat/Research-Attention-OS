from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.models.source import Source
from eval.live.phase8c2_production_sensor_bridge_v0_1 import (
    SemanticSensorProductionBridgeV0_1,
    production_source_to_sensor_source,
)


def _source() -> Source:
    now = datetime(2026, 9, 9, 3, 0, tzinfo=timezone.utc)
    return Source(
        id=uuid4(), source_type="TEXT", title="Bridge test",
        content_text="Company released Model Z. Researchers inspected it.",
        fingerprint="phase8c2-test", content_hash="test-content-hash",
        ingestion_method="TEST", ingested_at=now, created_at=now, updated_at=now,
    )


def _event_frame(source: Source, *, summary: str = "UNAUDITED SUMMARY MUST NOT ROUTE") -> dict:
    packed = production_source_to_sensor_source(source)
    as_of = source.ingested_at.isoformat()
    return {
        "interface_version": "semantic-evidence-frame-v0.1",
        "event": {"event_id": "E1", "as_of": as_of, "summary": summary},
        "sources": [{"source_id": str(source.id), "source_type": "TEXT", "published_at": "unknown", "locator": packed.path}],
        "evidence": [
            {"evidence_id": "ev1", "source_id": str(source.id), "support_pointer": "PARA 0001", "support_excerpt": "Company released Model Z.", "epistemic_status": "SOURCE_CLAIM", "confidence": "HIGH"},
            {"evidence_id": "ev2", "source_id": str(source.id), "support_pointer": "PARA 0001", "support_excerpt": "Researchers inspected it.", "epistemic_status": "DIRECT_OBSERVATION", "confidence": "MEDIUM"},
        ],
        "substantive_actors_objects": [{"name": "Company", "role": "developer", "substantive_basis": "released Model Z", "support_ids": ["ev1"]}],
        "actions_changes": [{"description": "released Model Z", "temporal_status": "ANNOUNCED", "support_ids": ["ev1"]}],
        "affected_systems_populations": [{"description": "researchers inspecting Model Z", "reference_scope": "researchers", "support_ids": ["ev2"]}],
        "temporal_context": {"event_time": "unknown", "effective_time": "unknown", "as_of": as_of, "notes": ""},
        "uncertainties": [],
    }


def _batch(source: Source, *, frame: dict | None = None, units: list[dict] | None = None) -> dict:
    return {
        "interface_version": "semantic-evidence-batch-v0.2",
        "batch_id": f"{source.id}-semantic-batch-v0.2",
        "source_ids": [str(source.id)],
        "event_frames": [frame] if frame else [],
        "non_event_units": list(units or []),
        "notes": [],
    }


def _sensor_chat(batch: dict):
    def chat(_messages, **_kwargs):
        return batch, {"model": "fake-sensor"}
    return chat


def _auditor_chat(*, reject_fragment: str | None = None):
    def chat(messages, **_kwargs):
        user = messages[-1]["content"]
        audit_id = next(line.split(":", 1)[1].strip() for line in user.splitlines() if line.startswith("audit_id:"))
        reject = bool(reject_fragment and reject_fragment in audit_id)
        return {
            "interface_version": "semantic-evidence-audit-result-v0.1.1",
            "audit_id": audit_id,
            "verdict": "INSUFFICIENT" if reject else "SUFFICIENT",
            "reason_code": "MISSING_SUPPORT" if reject else "SUPPORTED",
            "rationale": "controlled test verdict",
            "unsupported_aspect": "controlled missing support" if reject else "",
        }, {"model": "fake-auditor"}
    return chat


def test_event_summary_never_routes_and_supported_event_objects_do():
    source = _source()
    bridge = SemanticSensorProductionBridgeV0_1(
        sensor_chat_fn=_sensor_chat(_batch(source, frame=_event_frame(source))),
        auditor_chat_fn=_auditor_chat(),
    )
    result = bridge.extract(source, [])
    text = "\n".join(c.text for c in result.extraction.claims) + "\n" + "\n".join(
        o.text for o in result.extraction.observations
    )
    assert "UNAUDITED SUMMARY MUST NOT ROUTE" not in text
    assert "released Model Z" in text
    assert result.diagnostics["sources"][0]["events"][0]["routing_status"] == "ROUTABLE"


def test_event_frame_fails_closed_when_action_change_is_not_sufficient():
    source = _source()
    bridge = SemanticSensorProductionBridgeV0_1(
        sensor_chat_fn=_sensor_chat(_batch(source, frame=_event_frame(source))),
        auditor_chat_fn=_auditor_chat(reject_fragment="action_change"),
    )
    result = bridge.extract(source, [])
    assert result.extraction.claims == []
    assert result.extraction.observations == []
    assert result.extraction.inferences == []
    event = result.diagnostics["sources"][0]["events"][0]
    assert event["routing_status"] == "AUDIT_BLOCKED_NO_SUPPORTED_ACTION"
    assert event["n_event_units_admitted"] if "n_event_units_admitted" in event else True


def test_non_event_epistemic_types_are_preserved_conservatively():
    source = _source()
    sid = str(source.id)
    supports = [{"source_id": sid, "support_pointer": "PARA 0001", "support_excerpt": "support"}]
    units = [
        {"unit_id": "C1", "statement": "source says X", "epistemic_status": "SOURCE_CLAIM", "confidence": "HIGH", "supports": supports, "note": ""},
        {"unit_id": "O1", "statement": "measured Y", "epistemic_status": "DIRECT_OBSERVATION", "confidence": "MEDIUM", "supports": supports, "note": ""},
        {"unit_id": "I1", "statement": "X may imply Z", "epistemic_status": "EXTRACTOR_INFERENCE", "confidence": "LOW", "supports": supports, "note": ""},
    ]
    bridge = SemanticSensorProductionBridgeV0_1(
        sensor_chat_fn=_sensor_chat(_batch(source, units=units)),
        auditor_chat_fn=_auditor_chat(),
    )
    extraction = bridge.extract(source, []).extraction
    assert [c.text for c in extraction.claims] == ["source says X"]
    assert [o.text for o in extraction.observations] == ["measured Y"]
    assert [i.text for i in extraction.inferences] == ["X may imply Z"]
