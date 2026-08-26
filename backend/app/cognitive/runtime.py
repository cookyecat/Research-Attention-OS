"""Per-stage model runtime budget. Transport-agnostic; wire format is applied in the client."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

ThinkingMode = Literal["enabled", "disabled"]
ReasoningEffort = Literal["low", "high", "max"]


@dataclass(frozen=True)
class StageRuntime:
    thinking: ThinkingMode | None
    reasoning_effort: ReasoningEffort | None
    timeout: float

    def as_dict(self) -> dict:
        return asdict(self)


# Cognitive stages only. Patches stay deterministic and have no LLM budget.
STAGE_RUNTIME: dict[str, StageRuntime] = {
    "extraction": StageRuntime(thinking="disabled", reasoning_effort=None, timeout=60.0),
    "matching": StageRuntime(thinking="disabled", reasoning_effort=None, timeout=60.0),
    "judgment": StageRuntime(thinking="disabled", reasoning_effort=None, timeout=60.0),
    "impact": StageRuntime(thinking="disabled", reasoning_effort=None, timeout=60.0),
    "evidence": StageRuntime(thinking="enabled", reasoning_effort="low", timeout=120.0),
    "delta": StageRuntime(thinking="enabled", reasoning_effort="low", timeout=120.0),
}


def stage_runtime(stage: str) -> StageRuntime:
    return STAGE_RUNTIME.get(stage, StageRuntime(thinking=None, reasoning_effort=None, timeout=45.0))
