"""Shared semantic primitive types for Phase17 world-state representation."""
from __future__ import annotations

from typing import Literal

PrimitiveFamily = Literal[
    "STATE",
    "STRUCTURE",
    "PROCESS",
    "FORM",
    "DISPOSITION",
    "QUALITY",
    "RELATION",
    "OTHER",
]

ReferentScope = Literal["TARGET_INTRINSIC", "TARGET_RELATION"]


def referent_scope_for_family(family: PrimitiveFamily) -> ReferentScope:
    """Derive the only valid referent scope for a primitive family."""
    return "TARGET_RELATION" if family == "RELATION" else "TARGET_INTRINSIC"
