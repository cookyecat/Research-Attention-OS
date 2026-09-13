from __future__ import annotations

from dataclasses import dataclass

from app.enums import CognitiveEffectKind


def _kind(effect) -> CognitiveEffectKind:
    op = effect.operation
    if isinstance(op, CognitiveEffectKind):
        return op
    return CognitiveEffectKind(str(getattr(op, "value", op)))


def jurisdiction_anchor_matches(matches) -> list:
    anchors = []
    for match in matches or []:
        node_type = str(getattr(match, "node_type", "") or "").upper()
        relevance = str(getattr(match, "relevance_type", "") or "").upper()
        if (
            node_type in {"GOAL", "PROJECT"}
            or relevance in {"STRUCTURAL", "DECISION", "BOTTLENECK", "EVIDENCE"}
            or bool(getattr(match, "structural", False))
        ):
            anchors.append(match)
    return anchors


def has_jurisdiction_anchor(matches) -> bool:
    return bool(jurisdiction_anchor_matches(matches))


@dataclass(frozen=True)
class LegalPublicEffectAdmission:
    admission_id: str = "legal-public"
    version: str = "legal-public-v1"

    def execution_snapshot(self) -> dict:
        return {"admission_id": self.admission_id, "version": self.version}

    def admit(self, effects, matches):
        return list(effects or [])


@dataclass(frozen=True)
class AnchoredOpenNewAdmission:
    admission_id: str = "anchored-open-new"
    version: str = "anchored-open-new-v0.1"

    def execution_snapshot(self) -> dict:
        return {
            "admission_id": self.admission_id,
            "version": self.version,
            "open_new_requires_kernel_jurisdiction_anchor": True,
            "uses_raw_change_magnitude": False,
        }

    def admit(self, effects, matches):
        effects = list(effects or [])
        if has_jurisdiction_anchor(matches):
            return effects
        return [effect for effect in effects if _kind(effect) != CognitiveEffectKind.OPEN_NEW]


LEGAL_PUBLIC_EFFECT_ADMISSION = LegalPublicEffectAdmission()
ANCHORED_OPEN_NEW_ADMISSION = AnchoredOpenNewAdmission()


@dataclass(frozen=True)
class EffectAnchoredOpenNewAdmission:
    """OPEN_NEW is legal only with effect-specific jurisdiction provenance."""

    admission_id: str = "effect-anchored-open-new"
    version: str = "effect-anchored-open-new-v0.2"

    def execution_snapshot(self) -> dict:
        return {
            "admission_id": self.admission_id,
            "version": self.version,
            "open_new_requires_effect_jurisdiction_anchor": True,
            "uses_raw_change_magnitude": False,
        }

    def admit(self, effects, matches):
        known = {str(getattr(match, "node_id", "")) for match in (matches or [])}
        admitted = []
        for effect in effects or []:
            if _kind(effect) != CognitiveEffectKind.OPEN_NEW:
                admitted.append(effect)
                continue
            anchors = [str(x) for x in (getattr(effect, "jurisdiction_anchor_ids", None) or [])]
            if anchors and any(anchor in known for anchor in anchors):
                admitted.append(effect)
        return admitted


EFFECT_ANCHORED_OPEN_NEW_ADMISSION = EffectAnchoredOpenNewAdmission()
