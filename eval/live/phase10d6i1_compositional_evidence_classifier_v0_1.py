from __future__ import annotations

import json
from typing import Literal
from pydantic import Field

from app.cognitive.schemas import StrictModel

VERSION = "phase10d6i1-compositional-evidence-form-classifier-v0.1"
ProvenanceRole = Literal["PRIMARY_SOURCE", "SECONDARY_SOURCE", "DERIVED", "UNKNOWN"]
EvidenceForm = Literal[
    "MEASUREMENT_RESULT", "MEASUREMENT_PROTOCOL", "TECHNICAL_DESCRIPTION",
    "EVENT_OR_STATE_REPORT", "EVALUATIVE_ASSERTION", "LIMITATION_OR_UNCERTAINTY",
    "ANALYTIC_INFERENCE",
]

SYSTEM_PROMPT = """Classify evidence objects for Research Attention OS.
Do not judge truth, importance, Attention, or cognitive relation direction. Do not output confidence, strength, probability, or any numeric authority score.

provenance_role:
- PRIMARY_SOURCE: original organization/research team/platform describing its own release, system, study, measurement, or directly controlled state.
- SECONDARY_SOURCE: journalism or institutional/third-party science communication summarizing results, claims, or events originating in underlying research/other actors.
- DERIVED: analyst/system inference rather than direct source-grounded statement.
- UNKNOWN: cannot be resolved.

evidence_forms: return every materially present form, minimum 1 maximum 3:
- MEASUREMENT_RESULT: observed qualitative/quantitative result from experiment, benchmark, evaluation, survey, or measurement.
- MEASUREMENT_PROTOCOL: study/evaluation setup, population, conditions, interfaces, procedure, or measurement method.
- TECHNICAL_DESCRIPTION: architecture, mechanism, interface, configuration, implementation, or concrete system behavior.
- EVENT_OR_STATE_REPORT: occurrence, release, availability, policy, deployment, historical event, or current state.
- EVALUATIVE_ASSERTION: capability, safety, quality, importance, opinion, prediction, or broad interpretation not itself established as a measured result in this unit.
- LIMITATION_OR_UNCERTAINTY: explicit caveat, unknown, missing evidence, limitation, confounder, or scope constraint.
- ANALYTIC_INFERENCE: analyst/system-derived interpretation beyond the direct source statement.

Mixed units may legitimately have multiple forms. Include a form only when it is materially present in the unit, not merely implied by the surrounding source. Preserve item_id exactly. Return JSON only."""

class CompositionalEvidenceClassification(StrictModel):
    item_id: str = Field(min_length=1)
    provenance_role: ProvenanceRole
    evidence_forms: set[EvidenceForm] = Field(min_length=1, max_length=3)
    reason: str = Field(min_length=1)

class CompositionalEvidenceResponse(StrictModel):
    classifications: list[CompositionalEvidenceClassification]

def build_user_prompt(items:list[dict]) -> str:
    shape={'classifications':[{'item_id':'case::unit','provenance_role':'PRIMARY_SOURCE','evidence_forms':['MEASUREMENT_PROTOCOL','MEASUREMENT_RESULT'],'reason':'short categorical rationale'}]}
    return 'Evidence items:\n'+json.dumps(items,ensure_ascii=False)+'\n\nReturn JSON in exactly this shape:\n'+json.dumps(shape,ensure_ascii=False)
