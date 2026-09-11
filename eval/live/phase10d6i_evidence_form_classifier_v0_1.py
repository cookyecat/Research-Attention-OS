from __future__ import annotations

import json
from typing import Literal
from pydantic import Field

from app.cognitive.schemas import StrictModel

VERSION = "phase10d6i-evidence-form-classifier-v0.1"

ProvenanceRole = Literal["PRIMARY_SOURCE", "SECONDARY_SOURCE", "DERIVED", "UNKNOWN"]
EvidenceForm = Literal[
    "MEASUREMENT_RESULT",
    "MEASUREMENT_PROTOCOL",
    "TECHNICAL_DESCRIPTION",
    "EVENT_OR_STATE_REPORT",
    "EVALUATIVE_ASSERTION",
    "LIMITATION_OR_UNCERTAINTY",
    "ANALYTIC_INFERENCE",
]

SYSTEM_PROMPT = """Classify evidence objects for Research Attention OS.
You are NOT judging whether a claim is true, important, attention-worthy, reinforcing, or challenging. Do not output confidence scores, probabilities, strength scores, or Attention actions.

Classify two orthogonal axes.

provenance_role:
- PRIMARY_SOURCE: the source is the original organization/research team/platform describing its own release, system, study, measurement, or directly controlled event/state.
- SECONDARY_SOURCE: journalism or another third party reports/summarizes claims, events, or results originating elsewhere.
- DERIVED: the unit is an analyst/system inference rather than a direct source-grounded statement.
- UNKNOWN: provenance cannot be resolved from supplied source context.

evidence_form:
- MEASUREMENT_RESULT: reports an observed qualitative or quantitative result from an experiment, benchmark, evaluation, or measurement.
- MEASUREMENT_PROTOCOL: describes study/evaluation setup, population, conditions, interfaces, or measurement procedure without primarily stating the result.
- TECHNICAL_DESCRIPTION: describes architecture, mechanism, interface, configuration, implementation, or concrete system behavior; not itself an experimental result.
- EVENT_OR_STATE_REPORT: reports an occurrence, release, availability, policy, deployment, historical event, or present state.
- EVALUATIVE_ASSERTION: capability, safety, quality, importance, opinion, prediction, or broad interpretation not directly presented as a measured result in this unit.
- LIMITATION_OR_UNCERTAINTY: explicitly records uncertainty, missing evidence, caveat, limitation, or unknown.
- ANALYTIC_INFERENCE: analyst/system-derived interpretation beyond the direct source statement.

For mixed units, choose the form that carries the unit's main evidential content. A study result is MEASUREMENT_RESULT even when the result is qualitative. A study setup is MEASUREMENT_PROTOCOL. A product/research source describing how a system is built is TECHNICAL_DESCRIPTION, not MEASUREMENT_RESULT unless an observed evaluation result is actually stated.
Return exactly one classification for every supplied item, preserving item_id. Return JSON only."""


class EvidenceClassification(StrictModel):
    item_id: str = Field(min_length=1)
    provenance_role: ProvenanceRole
    evidence_form: EvidenceForm
    reason: str = Field(min_length=1)


class EvidenceClassificationResponse(StrictModel):
    classifications: list[EvidenceClassification]


def build_user_prompt(items: list[dict]) -> str:
    shape = {
        "classifications": [
            {
                "item_id": "case::unit_id",
                "provenance_role": "PRIMARY_SOURCE",
                "evidence_form": "MEASUREMENT_RESULT",
                "reason": "short categorical rationale",
            }
        ]
    }
    return (
        "Evidence items:\n" + json.dumps(items, ensure_ascii=False)
        + "\n\nReturn JSON in exactly this shape:\n" + json.dumps(shape, ensure_ascii=False)
    )
