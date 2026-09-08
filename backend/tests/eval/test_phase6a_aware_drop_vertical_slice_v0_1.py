from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.collective_attention_v1 import validate_evidence_packet
from eval.live.run_phase6a_aware_drop_vertical_slice_v0_1 import (
    AUDIT_ARTIFACT,
    P_MANIFEST,
    _load_yaml,
    _validate_inputs,
    build_controlled_p_packet,
)


def test_controlled_p_manifest_exactly_covers_routable_events():
    audit = json.loads(AUDIT_ARTIFACT.read_text(encoding="utf-8"))
    manifest = _load_yaml(P_MANIFEST)
    routable = _validate_inputs(audit, manifest)
    assert len(routable) == 8
    assert {e["event_id"] for e in routable} == set(manifest["cases"])


def test_controlled_p_packets_validate_without_embedding_final_action():
    audit = json.loads(AUDIT_ARTIFACT.read_text(encoding="utf-8"))
    manifest = _load_yaml(P_MANIFEST)
    for event in _validate_inputs(audit, manifest):
        event_id = str(event["event_id"])
        text = str(event["audited_projection"]["rendered_event_text"])
        packet = build_controlled_p_packet(
            event_id,
            text,
            manifest["cases"][event_id],
            as_of=str(manifest["as_of"]),
        )
        obj = validate_evidence_packet(packet)
        dumped = obj.model_dump(mode="json")
        assert dumped["event"]["event_id"] == event_id
        serialized = json.dumps(dumped, ensure_ascii=False)
        assert "AWARE" not in serialized
        assert "DROP" not in serialized
        assert "synthetic" in dumped["collection_context"]["notes"].lower()


def test_manifest_exercises_both_salience_conditions():
    manifest = _load_yaml(P_MANIFEST)
    conditions = {case["condition"] for case in manifest["cases"].values()}
    assert conditions == {"strong_salience", "low_salience"}
