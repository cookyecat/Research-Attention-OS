"""Research-aligned no-Delta situational-awareness path.

This module wires the already validated D/S/P research contracts into online dogfood.
It owns composition only; it does not redefine D, S, P, or cognitive-effect semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

from app.enums import Disposition
from app.services.scheduler import AwarenessSignals

CONTRACT_VERSION = "no-delta-dsp-v1"
ARTICLE_AGGREGATION_VERSION = "any-event-aware-else-all-drop-v1"


def _load_research_contracts():
    repo_root = Path(__file__).resolve().parents[3]
    root = str(repo_root)
    if root not in sys.path:
        sys.path.insert(0, root)
    from eval.live.standing_radar_fit_v4 import estimate_standing_radar_fit_v4, ESTIMATOR_VERSION as d_version, PROFILE_ID as d_profile
    from eval.live.material_consequence_v1 import estimate_material_consequence_v1, ESTIMATOR_VERSION as s_version
    from eval.live.collective_attention_v1 import estimate_collective_attention_v1, ESTIMATOR_VERSION as p_version
    from eval.live.no_delta_awareness_integration_v1_1 import determine_gate_disposition, INTEGRATION_VERSION
    return estimate_standing_radar_fit_v4, estimate_material_consequence_v1, estimate_collective_attention_v1, determine_gate_disposition, d_version, d_profile, s_version, p_version, INTEGRATION_VERSION


@dataclass(frozen=True)
class NoDeltaAwarenessDecision:
    applicable: bool
    final_determined: bool
    disposition: Disposition | None
    awareness_signals: AwarenessSignals | None
    witness_event_id: str | None
    trace: dict[str, Any]


def execution_snapshot() -> dict[str, Any]:
    _, _, _, _, d_version, d_profile, s_version, p_version, integration_version = _load_research_contracts()
    return {
        "contract_version": CONTRACT_VERSION,
        "d_estimator": d_version,
        "d_profile": d_profile,
        "s_estimator": s_version,
        "p_estimator": p_version,
        "unknown_composition": integration_version,
        "semantic_gate": "AWARE iff S AND (D OR P)",
        "article_aggregation": ARTICLE_AGGREGATION_VERSION,
        "p_from_article_text": False,
    }


def _audited_events(extraction_diagnostics: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for source_row in extraction_diagnostics.get("sources") or []:
        for event in source_row.get("events") or []:
            projection = event.get("audited_projection") or {}
            if projection.get("routing_status") != "ROUTABLE":
                continue
            text = str(projection.get("rendered_event_text") or "").strip()
            if text:
                out.append({
                    "source_id": str(source_row.get("source_id") or ""),
                    "event_id": str(projection.get("event_id") or event.get("event_id") or "unknown-event"),
                    "event_text": text,
                })
    return out


def _packet_for_event(p_packets: dict[str, Any] | None, event_id: str) -> dict[str, Any] | None:
    if not p_packets:
        return None
    packet = p_packets.get(event_id)
    return packet if isinstance(packet, dict) else None


def _component_state(output: dict[str, Any], key: str):
    return output.get(key) if output.get("scorable") else None


def evaluate_no_delta_awareness(
    extraction_diagnostics: dict[str, Any],
    *,
    p_packets: dict[str, Any] | None = None,
    d_chat_fn=None,
    s_chat_fn=None,
    p_chat_fn=None,
) -> NoDeltaAwarenessDecision:
    (
        estimate_d,
        estimate_s,
        estimate_p,
        determine_gate,
        *_versions,
    ) = _load_research_contracts()
    events = _audited_events(extraction_diagnostics)
    if not events:
        return NoDeltaAwarenessDecision(
            applicable=False,
            final_determined=True,
            disposition=Disposition.DROP,
            awareness_signals=None,
            witness_event_id=None,
            trace={
                "contract_version": CONTRACT_VERSION,
                "applicable": False,
                "reason": "No routable audited event projection; DSP event path not applicable.",
                "events": [],
            },
        )

    rows: list[dict[str, Any]] = []
    aware_witness: tuple[dict[str, Any], str, str | None, str] | None = None
    has_unresolved = False
    for event in events:
        event_text = event["event_text"]
        d_out = estimate_d(event_text, chat_fn=d_chat_fn)
        s_out = estimate_s(event_text, chat_fn=s_chat_fn)
        d = _component_state(d_out, "standing_radar_fit")
        s = _component_state(s_out, "material_consequence")
        p_out: dict[str, Any] = {
            "scorable": False,
            "measurement_status": "not_observed",
            "collective_attention_salience": None,
            "reason": "No external collective-attention evidence packet supplied.",
        }
        packet = _packet_for_event(p_packets, event["event_id"])
        if packet is not None:
            p_out = estimate_p(packet, chat_fn=p_chat_fn)
        p = _component_state(p_out, "collective_attention_salience")
        disposition = determine_gate(d, s, p)
        if disposition is None:
            has_unresolved = True
        elif disposition == Disposition.AWARE and aware_witness is None:
            aware_witness = (event, d, p, s)
        rows.append({
            **event,
            "D": d_out,
            "S": s_out,
            "P": p_out,
            "component_states": {"D": d, "S": s, "P": p},
            "final_determined": disposition is not None,
            "disposition": disposition.value if disposition is not None else None,
        })

    if aware_witness is not None:
        event, d, p, s = aware_witness
        signals = AwarenessSignals(
            domain_fit=True if d == "IN" else False,
            event_significance=True if s == "MATERIAL" else False,
            attention_momentum=True if p == "SALIENT" else None,
        )
        return NoDeltaAwarenessDecision(
            applicable=True,
            final_determined=True,
            disposition=Disposition.AWARE,
            awareness_signals=signals,
            witness_event_id=event["event_id"],
            trace={
                "contract_version": CONTRACT_VERSION,
                "applicable": True,
                "final_determined": True,
                "disposition": "AWARE",
                "witness_event_id": event["event_id"],
                "events": rows,
            },
        )

    if has_unresolved:
        return NoDeltaAwarenessDecision(
            applicable=True,
            final_determined=False,
            disposition=None,
            awareness_signals=None,
            witness_event_id=None,
            trace={
                "contract_version": CONTRACT_VERSION,
                "applicable": True,
                "final_determined": False,
                "disposition": None,
                "reason": "At least one audited event remains unresolved under UNKNOWN-aware D/S/P composition.",
                "events": rows,
            },
        )

    return NoDeltaAwarenessDecision(
        applicable=True,
        final_determined=True,
        disposition=Disposition.DROP,
        awareness_signals=None,
        witness_event_id=None,
        trace={
            "contract_version": CONTRACT_VERSION,
            "applicable": True,
            "final_determined": True,
            "disposition": "DROP",
            "events": rows,
        },
    )


def awareness_signals_from_trace(trace: dict[str, Any] | None) -> AwarenessSignals | None:
    if not isinstance(trace, dict) or trace.get("disposition") != "AWARE":
        return None
    witness = str(trace.get("witness_event_id") or "")
    for row in trace.get("events") or []:
        if str(row.get("event_id") or "") != witness:
            continue
        states = row.get("component_states") or {}
        d, s, p = states.get("D"), states.get("S"), states.get("P")
        return AwarenessSignals(
            domain_fit=True if d == "IN" else False if d == "OUT" else None,
            event_significance=True if s == "MATERIAL" else False if s == "NOT_MATERIAL" else None,
            attention_momentum=True if p == "SALIENT" else False if p == "NOT_SALIENT" else None,
        )
    return None
