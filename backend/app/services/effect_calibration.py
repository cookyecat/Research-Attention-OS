from __future__ import annotations

from dataclasses import dataclass

from app.enums import CognitiveEffectKind, Disposition, ExpectedOutput, Urgency
from app.services.cognitive_impact import (
    LOW_EPISTEMIC,
    MATERIAL_CHANGE_MIN,
    MEANINGFUL_CHANGE,
    CognitiveEffect,
    effect_target_match,
)
from app.services.scheduler import PlanDraft, _budget, _cognitive_disposition


def _kind(effect: CognitiveEffect) -> CognitiveEffectKind:
    op = effect.operation
    if isinstance(op, CognitiveEffectKind):
        return op
    return CognitiveEffectKind(str(getattr(op, "value", op)))


def epistemic_band(value: float) -> int:
    return 0 if float(value) < LOW_EPISTEMIC else 1


def importance_band(value: float) -> int:
    return 0 if float(value) < 0.55 else 1


def active_role_band(effect: CognitiveEffect, matches) -> int:
    match = effect_target_match(effect, matches or [])
    node_type = str(getattr(match, "node_type", "") or "").upper()
    return int(node_type in {"QUESTION", "BOTTLENECK", "DECISION"})


def raw_change_band(value: float) -> int:
    value = float(value)
    if value <= 0:
        return 0
    if value < MATERIAL_CHANGE_MIN:
        return 1
    if value < MEANINGFUL_CHANGE:
        return 2
    return 3


@dataclass(frozen=True)
class RawCardinalCalibration:
    calibration_id: str = "raw-cardinal"
    version: str = "raw-cardinal-v1"

    def execution_snapshot(self) -> dict:
        return {"calibration_id": self.calibration_id, "version": self.version}

    def decision_vector(self, effect: CognitiveEffect, matches) -> tuple[int, int, int, int, int]:
        op = _kind(effect)
        return (
            raw_change_band(effect.change_magnitude),
            epistemic_band(effect.epistemic_strength),
            importance_band(effect.target_importance),
            int(op == CognitiveEffectKind.CHALLENGE),
            int(op == CognitiveEffectKind.OPEN_NEW),
        )

    def channel_plan(self, effect, *, features, matches) -> PlanDraft:
        return _cognitive_disposition(features, effect, matches or [], awareness=None)

    def representative_key(self, effect: CognitiveEffect, matches) -> tuple:
        change = round(float(effect.change_magnitude), 6)
        importance = round(float(effect.target_importance), 6)
        epi = round(float(effect.epistemic_strength), 6)
        nid = str(effect.target_kernel_node_id) if effect.target_kernel_node_id else ""
        return (round(change * importance, 6), change, importance, epi, nid)


RAW_CARDINAL_CALIBRATION = RawCardinalCalibration()
RAW_CARDINAL_CALIBRATION = RawCardinalCalibration()


@dataclass(frozen=True)
class MagnitudeFreeCalibration:
    calibration_id: str = "magnitude-free"
    version: str = "magnitude-free-v0.1"

    def execution_snapshot(self) -> dict:
        return {
            "calibration_id": self.calibration_id,
            "version": self.version,
            "uses_raw_change_magnitude": False,
            "authority": "operation+epistemic-band+importance-band+active-role-band",
        }

    def decision_vector(self, effect: CognitiveEffect, matches) -> tuple[int, int, int, int, int]:
        op = _kind(effect)
        return (
            epistemic_band(effect.epistemic_strength),
            importance_band(effect.target_importance),
            active_role_band(effect, matches),
            int(op == CognitiveEffectKind.CHALLENGE),
            int(op == CognitiveEffectKind.OPEN_NEW),
        )

    def channel_plan(self, effect, *, features, matches) -> PlanDraft:
        op = _kind(effect)
        match = effect_target_match(effect, matches or [])
        node_type = str(getattr(match, "node_type", "") or "").upper()
        important = importance_band(effect.target_importance) == 1
        sufficient = epistemic_band(effect.epistemic_strength) == 1

        if op == CognitiveEffectKind.CHALLENGE:
            if important and sufficient:
                return PlanDraft(
                    disposition=Disposition.ENGAGE,
                    expected_output=ExpectedOutput.KERNEL_PATCH,
                    reason="Magnitude-free: important, sufficiently supported CHALLENGE.",
                    cognitive_budget_minutes=_budget(Disposition.ENGAGE),
                )
            if important:
                return PlanDraft(
                    disposition=Disposition.WATCH,
                    expected_output=ExpectedOutput.WATCH,
                    reason="Magnitude-free: important CHALLENGE with weak epistemic support; verify rather than ignore.",
                    watch_after_processing=True,
                    cognitive_budget_minutes=_budget(Disposition.WATCH),
                )
            return PlanDraft(
                disposition=Disposition.AWARE,
                expected_output=ExpectedOutput.SUMMARY,
                reason="Magnitude-free: CHALLENGE exists but target importance is low.",
                cognitive_budget_minutes=_budget(Disposition.AWARE),
            )

        if op == CognitiveEffectKind.OPEN_NEW:
            if important and sufficient:
                return PlanDraft(
                    disposition=Disposition.ENGAGE,
                    expected_output=ExpectedOutput.SUMMARY,
                    reason="Magnitude-free: important, sufficiently supported OPEN_NEW branch.",
                    cognitive_budget_minutes=_budget(Disposition.ENGAGE),
                )
            if important or sufficient:
                return PlanDraft(
                    disposition=Disposition.WATCH,
                    expected_output=ExpectedOutput.WATCH,
                    reason="Magnitude-free: genuine OPEN_NEW branch worth keeping in view.",
                    watch_after_processing=True,
                    cognitive_budget_minutes=_budget(Disposition.WATCH),
                )
            return PlanDraft(
                disposition=Disposition.AWARE,
                expected_output=ExpectedOutput.SUMMARY,
                reason="Magnitude-free: OPEN_NEW is weakly anchored; awareness only.",
                cognitive_budget_minutes=_budget(Disposition.AWARE),
            )

        if node_type == "DECISION":
            return PlanDraft(
                disposition=Disposition.ENGAGE,
                expected_output=ExpectedOutput.DECISION_REVIEW,
                reason="Magnitude-free: CognitiveEffect lands on an active Decision.",
                cognitive_budget_minutes=_budget(Disposition.ENGAGE),
            )

        if node_type in {"QUESTION", "BOTTLENECK"} and important:
            return PlanDraft(
                disposition=Disposition.WATCH,
                expected_output=ExpectedOutput.WATCH,
                reason="Magnitude-free: REINFORCE on an important active QUESTION/BOTTLENECK.",
                watch_after_processing=True,
                cognitive_budget_minutes=_budget(Disposition.WATCH),
            )

        return PlanDraft(
            disposition=Disposition.AWARE,
            expected_output=ExpectedOutput.SUMMARY,
            reason="Magnitude-free: ordinary REINFORCE is awareness, not automatic deep attention.",
            cognitive_budget_minutes=_budget(Disposition.AWARE),
        )

    def representative_key(self, effect: CognitiveEffect, matches) -> tuple:
        op = _kind(effect)
        nid = str(effect.target_kernel_node_id) if effect.target_kernel_node_id else ""
        return (*self.decision_vector(effect, matches or []), op.value, nid)


MAGNITUDE_FREE_CALIBRATION = MagnitudeFreeCalibration()
