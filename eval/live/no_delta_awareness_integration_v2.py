"""No-Delta AWARE integration v2 — D v4 profile uplift.

Development integration only. Frozen semantics remain unchanged:
    AWARE iff S and (D or P)

Only the D implementation binding changes from Standing Radar v3/profile v3
to Standing Radar v4/profile v4. S v1, P v1, and production Scheduler wiring
remain unchanged.
"""
from __future__ import annotations

from typing import Any

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from eval.live.no_delta_awareness_integration_v1 import (
    DLabel,
    PLabel,
    POLICY_GATE_VERSION,
    SLabel,
    awareness_signals_from_dsp,
    expected_gate_disposition,
    neutral_scheduler_features,
    route_no_delta_from_dsp,
)
from eval.live.collective_attention_v1 import (
    estimate_collective_attention_v1,
    load_collective_attention_profile,
)
from eval.live.material_consequence_v1 import (
    estimate_material_consequence_v1,
    load_material_consequence_profile,
)
from eval.live.standing_radar_fit_v4 import (
    estimate_standing_radar_fit_v4,
    load_standing_radar_profile,
)

INTEGRATION_VERSION = "no-delta-awareness-integration-v2-d-v4"


def estimate_integrated_no_delta_awareness_v2(
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
    """Compose D v4 + S v1 + P v1 through the frozen production gate."""
    d_profile = d_profile if d_profile is not None else load_standing_radar_profile()
    s_profile = s_profile if s_profile is not None else load_material_consequence_profile()
    p_profile = p_profile if p_profile is not None else load_collective_attention_profile()

    d_out = estimate_standing_radar_fit_v4(event_text, profile=d_profile, chat_fn=d_chat_fn)
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


__all__ = [
    "INTEGRATION_VERSION",
    "POLICY_GATE_VERSION",
    "awareness_signals_from_dsp",
    "expected_gate_disposition",
    "neutral_scheduler_features",
    "route_no_delta_from_dsp",
    "estimate_integrated_no_delta_awareness_v2",
]
