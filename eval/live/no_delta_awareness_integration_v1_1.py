"""Partial-observation composition for the frozen no-Delta AWARE gate.

This is a post-first-run integration revision. It does NOT change the frozen
semantic equation:

    AWARE iff S and (D or P)

It only corrects how estimator UNKNOWN / non-scorable component states propagate
through that equation. If every Boolean completion of the unknown components yields
the same disposition, the final action is logically determined and may be emitted.
Otherwise the final remains unresolved.

Examples:
    D=IN,  S=MATERIAL, P=UNKNOWN -> AWARE
    D=OUT, S=MATERIAL, P=UNKNOWN -> unresolved
    D=UNKNOWN, S=NOT_MATERIAL, P=UNKNOWN -> DROP
"""

from __future__ import annotations

from itertools import product
from typing import Literal

from app.enums import Disposition
from eval.live.no_delta_awareness_integration_v1 import expected_gate_disposition

INTEGRATION_VERSION = "no-delta-awareness-integration-v1.1"
SEMANTIC_GATE_VERSION = "aware-iff-s-and-d-or-p-v1"

DState = Literal["IN", "OUT"] | None
SState = Literal["MATERIAL", "NOT_MATERIAL"] | None
PState = Literal["SALIENT", "NOT_SALIENT"] | None


def _choices(value, positive, negative):
    if value is None:
        return (positive, negative)
    return (value,)


def determine_gate_disposition(
    d: DState,
    s: SState,
    p: PState,
) -> Disposition | None:
    """Return a final disposition iff it is invariant over all UNKNOWN completions."""
    outcomes = {
        expected_gate_disposition(dc, sc, pc)
        for dc, sc, pc in product(
            _choices(d, "IN", "OUT"),
            _choices(s, "MATERIAL", "NOT_MATERIAL"),
            _choices(p, "SALIENT", "NOT_SALIENT"),
        )
    }
    if len(outcomes) == 1:
        return next(iter(outcomes))
    return None


def determine_gate_from_component_outputs(
    d_out: dict,
    s_out: dict,
    p_out: dict,
) -> dict:
    """Compose estimator outputs without treating measurement uncertainty as False."""
    d = d_out.get("standing_radar_fit") if d_out.get("scorable") else None
    s = s_out.get("material_consequence") if s_out.get("scorable") else None
    p = p_out.get("collective_attention_salience") if p_out.get("scorable") else None

    disposition = determine_gate_disposition(d, s, p)
    return {
        "integration_version": INTEGRATION_VERSION,
        "semantic_gate_version": SEMANTIC_GATE_VERSION,
        "component_states": {"D": d, "S": s, "P": p},
        "final_determined": disposition is not None,
        "disposition": disposition.value if disposition is not None else None,
    }
