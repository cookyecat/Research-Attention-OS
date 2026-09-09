from __future__ import annotations

from dataclasses import dataclass

from app.enums import CognitiveEffectKind


def _kind(effect) -> CognitiveEffectKind:
    op = effect.operation
    if isinstance(op, CognitiveEffectKind):
        return op
    return CognitiveEffectKind(str(getattr(op, "value", op)))


def has_jurisdiction_anchor(matches) -> bool:
    for match in matches or []:
        node_type = str(getattr(match, "node_type", "") or "").upper()
        relevance = str(getattr(match, "relevance_type", "") or "").upper()
        if node_type in {"GOAL", "PROJECT"}:
            return True
        if relevance in {"STRUCTURAL", "DECISION", "BOTTLENECK", "EVIDENCE"}:
            return True
        if bool(getattr(match, "structural", False)):
            return True
    return False


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
