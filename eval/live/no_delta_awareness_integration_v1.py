"""Integrated no-Delta AWARE research harness v1.

Composition only:
    D = Standing Attention Jurisdiction
    S = Material Consequence
    P = Collective Attention Salience

Frozen policy gate:
    AWARE iff S and (D or P)

This module does not redefine D, S, P, or the production Scheduler. It adapts the
three research estimators to the Scheduler's existing AwarenessSignals placeholder
and preserves component diagnostics for attribution.
"""

from __future__ import annotations

from typing import Any, Literal

from app.enums import Disposition
from app.services.scheduler import AwarenessSignals, SchedulerFeatures, route

from eval.live.collective_attention_v1 import (
    estimate_collective_attention_v1,
    load_collective_attention_profile,
)
from eval.live.material_consequence_v1 import (
    estimate_material_consequence_v1,
    load_material_consequence_profile,
)
from eval.live.standing_radar_fit_v3 import (
    estimate_standing_radar_fit_v3,
    load_standing_radar_profile,
)

INTEGRATION_VERSION = "no-delta-awareness-integration-v1"
POLICY_GATE_VERSION = "aware-iff-s-and-d-or-p-v1"

DLabel = Literal["IN", "OUT"]
SLabel = Literal["MATERIAL", "NOT_MATERIAL"]
PLabel = Literal["SALIENT", "NOT_SALIENT"]


def awareness_signals_from_dsp(d: DLabel, s: SLabel, p: PLabel) -> AwarenessSignals:
    """Map frozen semantic labels onto the Scheduler's existing oracle signal slots."""
    if d not in {"IN", "OUT"}:
        raise ValueError(f"invalid D label: {d}")
    if s not in {"MATERIAL", "NOT_MATERIAL"}:
        raise ValueError(f"invalid S label: {s}")
    if p not in {"SALIENT", "NOT_SALIENT"}:
        raise ValueError(f"invalid P label: {p}")
    return AwarenessSignals(
        domain_fit=d == "IN",
        event_significance=s == "MATERIAL",
        attention_momentum=p == "SALIENT",
    )


def expected_gate_disposition(d: DLabel, s: SLabel, p: PLabel) -> Disposition:
    """Frozen semantic gate, kept explicit for wiring verification."""
    aware = s == "MATERIAL" and (d == "IN" or p == "SALIENT")
    return Disposition.AWARE if aware else Disposition.DROP


def neutral_scheduler_features() -> SchedulerFeatures:
    """Minimal compatibility projection for a frozen Delta=NONE integration test."""
    return SchedulerFeatures(
        topic_relevance=0.0,
        structural_relevance=0.0,
        decision_relevance=0.0,
        novelty=0.0,
        credibility=0.0,
        kernel_delta=0.0,
        bottleneck_alignment=0.0,
        disagreement=0.0,
        actionability=0.0,
        temporal_value=0.0,
        cognitive_cost=0.0,
    )


def route_no_delta_from_dsp(d: DLabel, s: SLabel, p: PLabel):
    """Run the real Scheduler with Delta=NONE and D/S/P-derived AwarenessSignals."""
    signals = awareness_signals_from_dsp(d, s, p)
    return route(neutral_scheduler_features(), awareness=signals)


def estimate_integrated_no_delta_awareness_v1(
    event_text: str,
    p_packet: dict[str, Any],
    *,
    d_profile: dict[str, Any] | None = None,
    s_profile: dict[str, Any] | None = None,
    p_profile: dict[str, Any] | None = None,
    d_chat_fn=None,
    s_chat_fn=None,
    p_chat_fn=None,
) -> dict[str, Any]:
    """Estimate D/S/P independently, then compose them through the real Scheduler.

    Component failures remain visible. The function never invents a final
    AWARE/DROP outcome when any required component is non-scorable.
    """
    d_profile = d_profile if d_profile is not None else load_standing_radar_profile()
    s_profile = s_profile if s_profile is not None else load_material_consequence_profile()
    p_profile = p_profile if p_profile is not None else load_collective_attention_profile()

    d_out = estimate_standing_radar_fit_v3(event_text, profile=d_profile, chat_fn=d_chat_fn)
    s_out = estimate_material_consequence_v1(event_text, profile=s_profile, chat_fn=s_chat_fn)
    p_out = estimate_collective_attention_v1(p_packet, profile=p_profile, chat_fn=p_chat_fn)

    component_scorable = {
        "D": bool(d_out.get("scorable")),
        "S": bool(s_out.get("scorable")),
        "P": bool(p_out.get("scorable")),
    }
    if not all(component_scorable.values()):
        return {
            "integration_version": INTEGRATION_VERSION,
            "policy_gate_version": POLICY_GATE_VERSION,
            "scorable": False,
            "disposition": None,
            "component_scorable": component_scorable,
            "D": d_out,
            "S": s_out,
            "P": p_out,
        }

    d_label: DLabel = d_out["standing_radar_fit"]
    s_label: SLabel = s_out["material_consequence"]
    p_label: PLabel = p_out["collective_attention_salience"]

    draft = route_no_delta_from_dsp(d_label, s_label, p_label)
    expected = expected_gate_disposition(d_label, s_label, p_label)

    return {
        "integration_version": INTEGRATION_VERSION,
        "policy_gate_version": POLICY_GATE_VERSION,
        "scorable": True,
        "disposition": draft.disposition.value,
        "reason": draft.reason,
        "gate_wiring_matches": draft.disposition == expected,
        "labels": {"D": d_label, "S": s_label, "P": p_label},
        "component_scorable": component_scorable,
        "D": d_out,
        "S": s_out,
        "P": p_out,
    }
