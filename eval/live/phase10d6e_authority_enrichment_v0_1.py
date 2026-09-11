from __future__ import annotations

from dataclasses import replace

from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import CognitiveEffect

VERSION = "phase10d6e-authority-enrichment-v0.1"
ACTIVE_RESPONSIBILITY_TYPES = frozenset({"QUESTION", "BOTTLENECK", "DECISION"})


def _kind(effect: CognitiveEffect) -> CognitiveEffectKind:
    op = effect.operation
    return op if isinstance(op, CognitiveEffectKind) else CognitiveEffectKind(str(getattr(op, "value", op)))


def explicit_importance_band(node) -> int | None:
    payload = getattr(node, "payload", None) or {}
    if not isinstance(payload, dict):
        return None
    for key in ("importance", "priority"):
        raw = payload.get(key)
        if raw is None:
            continue
        if isinstance(raw, str):
            token = raw.strip().upper()
            if token in {"HIGH", "PRIORITY", "CRITICAL", "ACTIVE"}:
                return 1
            if token in {"LOW", "BACKGROUND", "INACTIVE"}:
                return 0
        try:
            return int(float(raw) >= 0.55)
        except (TypeError, ValueError):
            continue
    return None


def evidence_summary(units: list[dict]) -> dict:
    source_ids = {
        str(s.get("source_id"))
        for unit in units
        for s in (unit.get("supports") or [])
        if s.get("source_id")
    }
    return {
        "has_supported_unit": any(bool(unit.get("supports")) for unit in units),
        "has_direct_observation": any(str(unit.get("epistemic_status") or "") == "DIRECT_OBSERVATION" for unit in units),
        "independent_support_sources": len(source_ids),
    }


def importance_band_c1(effect: CognitiveEffect, *, nodes, matches) -> int:
    by_id = {str(node.id): node for node in nodes}
    op = _kind(effect)
    if op == CognitiveEffectKind.OPEN_NEW:
        # OPEN_NEW can inherit only explicit high priority from an admitted jurisdiction anchor.
        for match in matches or []:
            node = by_id.get(str(match.node_id))
            if node is None:
                continue
            node_type = str(getattr(node, "node_type", "") or "").upper()
            rel = str(getattr(match, "relevance_type", "") or "").upper()
            anchor = node_type in {"GOAL", "PROJECT"} or rel in {"STRUCTURAL", "DECISION", "BOTTLENECK", "EVIDENCE"}
            if anchor and explicit_importance_band(node) == 1:
                return 1
        return 0

    node = by_id.get(str(effect.target_kernel_node_id)) if effect.target_kernel_node_id else None
    if node is None:
        return 0
    explicit = explicit_importance_band(node)
    if explicit is not None:
        return explicit
    return int(str(getattr(node, "node_type", "") or "").upper() in ACTIVE_RESPONSIBILITY_TYPES)


def epistemic_band_c1(effect: CognitiveEffect, *, units: list[dict]) -> int:
    summary = evidence_summary(units)
    if _kind(effect) == CognitiveEffectKind.OPEN_NEW:
        return int(summary["has_supported_unit"])
    return int(summary["has_direct_observation"] or summary["independent_support_sources"] >= 2)


def epistemic_band_c2(effect: CognitiveEffect, *, units: list[dict]) -> int:
    del effect
    return int(evidence_summary(units)["has_supported_unit"])


def enrich_effect(effect: CognitiveEffect, *, nodes, matches, units: list[dict], policy: str) -> tuple[CognitiveEffect, dict]:
    importance = importance_band_c1(effect, nodes=nodes, matches=matches)
    if policy == "C1_CONSERVATIVE":
        epistemic = epistemic_band_c1(effect, units=units)
    elif policy == "C2_AUDITOR_TRUST_UPPER_BOUND":
        epistemic = epistemic_band_c2(effect, units=units)
    else:
        raise ValueError(f"unknown authority policy {policy}")
    enriched = replace(effect, target_importance=float(importance), epistemic_strength=float(epistemic))
    return enriched, {
        "importance_band": "HIGH" if importance else "LOW",
        "epistemic_band": "SUFFICIENT" if epistemic else "WEAK",
        "ordinal_compatibility_encoding": {"HIGH/SUFFICIENT": 1.0, "LOW/WEAK": 0.0},
    }
