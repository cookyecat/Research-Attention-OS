from __future__ import annotations

from dataclasses import replace

from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import CognitiveEffect
from eval.live.phase10d6e_authority_enrichment_v0_1 import importance_band_c1

VERSION = "phase10d6k-evaluator-authority-v0.2"
REJECT_FITS = frozenset({"INSUFFICIENT", "CONTRADICTS_OPERATION"})
SUPPORTED_JURISDICTION = "SUPPORTED_JURISDICTION"
INSUFFICIENT_JURISDICTION = "INSUFFICIENT_JURISDICTION"


def strong_target_fit(label: str, operation: str, target: str | None) -> str:
    if label in {"A", "D"}:
        return "INSUFFICIENT"
    if label == "X":
        return "DIRECT" if operation == "REINFORCE" and target == "M1" else "INSUFFICIENT"
    if label == "N4":
        if operation == "REINFORCE" and target in {"B1", "M1"}:
            return "DIRECT"
        if operation == "REINFORCE" and target in {"BT1", "Q1"}:
            return "PARTIAL"
        return "INSUFFICIENT"
    raise ValueError(f"unknown strong-reference case: {label}")


def strong_jurisdiction(label: str) -> str:
    if label in {"A", "D"}:
        return INSUFFICIENT_JURISDICTION
    if label in {"X", "N4"}:
        return SUPPORTED_JURISDICTION
    raise ValueError(f"unknown strong-reference case: {label}")


def canonical_epistemic(
    operation: str,
    fit: str | None,
    jurisdiction: str | None,
    provenance_role: str,
    *,
    support_bound: bool,
) -> tuple[bool, int, str]:
    if operation == "OPEN_NEW":
        if not support_bound:
            return False, 0, "OPEN_NEW_NO_SUPPORT"
        if jurisdiction != SUPPORTED_JURISDICTION:
            return False, 0, "OPEN_NEW_INSUFFICIENT_JURISDICTION"
        sufficient = int(provenance_role == "PRIMARY_SOURCE")
        return True, sufficient, "OPEN_NEW_PRIMARY" if sufficient else "OPEN_NEW_SECONDARY_WEAK"
    if fit in REJECT_FITS:
        return False, 0, f"GROUNDING_{fit}"
    if fit == "DIRECT":
        sufficient = int(provenance_role == "PRIMARY_SOURCE")
        return True, sufficient, "DIRECT_PRIMARY" if sufficient else "DIRECT_SECONDARY_WEAK"
    if fit == "PARTIAL":
        return True, 0, "PARTIAL_WEAK"
    return False, 0, "GROUNDING_UNKNOWN"


def enrich_for_arm(
    effect: CognitiveEffect,
    *,
    arm: str,
    nodes,
    matches,
    fit: str | None,
    jurisdiction: str | None,
    provenance_role: str,
    support_bound: bool,
) -> tuple[CognitiveEffect | None, dict]:
    importance = importance_band_c1(effect, nodes=nodes, matches=matches)
    operation = effect.operation.value if isinstance(effect.operation, CognitiveEffectKind) else str(effect.operation)
    if arm == "K0_ALL_SUPPORT_SUFFICIENT":
        keep, epistemic, reason = True, 1, "UPPER_BOUND_ALL_SUFFICIENT"
    elif arm == "K1_SINGLE_SOURCE_WEAK":
        keep = True
        epistemic = 1 if operation == "OPEN_NEW" and support_bound else 0
        reason = "C1_OPEN_NEW_SUPPORTED" if epistemic else "C1_TARGETED_SINGLE_SOURCE_WEAK"
    elif arm in {"K2_WEAK_EVALUATOR_AUTHORITY", "K3_STRONG_EVALUATOR_AUTHORITY"}:
        keep, epistemic, reason = canonical_epistemic(
            operation, fit, jurisdiction, provenance_role, support_bound=support_bound
        )
    else:
        raise ValueError(f"unknown arm {arm}")
    trace = {
        "arm": arm,
        "keep": keep,
        "grounding_fit": fit,
        "jurisdiction_fit": jurisdiction,
        "provenance_role": provenance_role,
        "support_bound": support_bound,
        "importance_band": "HIGH" if importance else "LOW",
        "epistemic_band": "SUFFICIENT" if epistemic else "WEAK",
        "authority_reason": reason,
    }
    if not keep:
        return None, trace
    return replace(
        effect,
        change_magnitude=0.0,
        target_importance=float(importance),
        epistemic_strength=float(epistemic),
    ), trace
