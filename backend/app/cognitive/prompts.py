import json

from app.cognitive.schemas import ExtractionResponse

EXTRACT_SYSTEM = """You are the extraction stage of Research Attention OS.
Documents are not the unit of cognition. Extract EventCandidate, Claims, Observations, and Inferences.

Constitution (Claim ≠ Observation ≠ Inference):
- Claim = an attributed assertion from the source ("someone said X"), not "X is true".
- A media/article/press report of an event is a Claim, never an Observation.
- Observation requires direct evidence: measurement, field note, system observation, or explicitly first-hand evidence (e.g. "in the video I saw", a measured latency). REPORTED_RESULT of a news story is not an Observation.
- Source-authored opinions, interpretations, predictions, and promotional conclusions remain attributed Claims (OPINION / PREDICTIVE / PROMOTIONAL). Do not put them in inferences.
- Inference is only for conclusions produced by RAOS itself from the extracted Claims/Observations. Never relabel a source author's inference as an AI Inference. Never copy "this probably means…" from the article into inferences.
- "Company says the robot generalizes zero-shot" is a Claim, never an Observation.
- Future plans (will be released, is planned) are PREDICTIVE claims, not current facts.
- Promotional language is PROMOTIONAL, not proof.

current_facts, future_plans, technical_claims, and promotional_framing MUST be arrays of strings, never objects.
Return JSON only. Extra fields are forbidden."""


def extraction_user_prompt(source_type: str, title: str | None, text: str) -> str:
    schema = json.dumps(ExtractionResponse.model_json_schema(), ensure_ascii=False, indent=2)
    return (
        f"Source type: {source_type}\n"
        f"Title: {title or ''}\n\n"
        f"Text:\n{text}\n\n"
        "Return a JSON object that validates against this authoritative schema.\n"
        "current_facts, future_plans, technical_claims, promotional_framing must be arrays of strings — never claim objects.\n\n"
        f"{schema}"
    )


MATCH_SYSTEM = """You match extracted information to a researcher's Cognitive Kernel.
Embedding retrieval already narrowed candidates. You decide relevance.

Two first-class relevance types:
- TOPIC: same subject matter (robotics article ↔ Motor Intelligence project)
- STRUCTURAL: analogical structure even if topic differs (consumer-brand minority equity ↔ robotics startup equity vs employment)

Also mark DECISION, BOTTLENECK, EVIDENCE when applicable.
Popularity is not importance. Disagreement is not low relevance.
Return JSON only."""

MATCH_USER = """Candidate text:
{text}

Extracted claims: {claims}
Observations: {observations}

Kernel candidates:
{kernel_candidates}

Return JSON:
{{
  "matches": [{{
    "kernel_node_id": "uuid",
    "relevance_type": "TOPIC|STRUCTURAL|DECISION|BOTTLENECK|EVIDENCE",
    "score": 0.0,
    "reason": ""
  }}]
}}
Only include matches that genuinely relate. Empty list is allowed."""

EVIDENCE_SYSTEM = """Relate Claims, Observations, and Inferences.
Stances: SUPPORTS, WEAKENS, REFUTES, NEUTRAL.
Insufficient evidence must not become a strong conclusion.
A demo with move-pause-move can WEAKEN a claim of continuous motion.
It must NOT REFUTE an entire architecture or infer "the system is scripted" without independent evidence.
Return JSON only."""

EVIDENCE_USER = """Claims: {claims}
Observations: {observations}
Inferences: {inferences}

Return JSON:
{{"links": [{{"source_role": "OBSERVATION|CLAIM|INFERENCE", "source_index": 0, "target_role": "CLAIM", "target_index": 0, "stance": "WEAKENS", "strength": "WEAK|MODERATE|STRONG", "confidence": 0.0, "scope": ""}}]}}"""

DELTA_SYSTEM = """You produce a Model Delta: what this information could change in the researcher's Kernel.
Output is a Proposal, never a commit.
Do not reduce debates to binary agree/disagree.
Prefer reframing into a more precise research question
(e.g. end-to-end vs hierarchical → at which temporal/control layers should end-to-end apply?).
Raw news facts almost never enter the Kernel.
Return JSON only."""

DELTA_USER = """Source text:
{text}

Kernel matches:
{matches}

Kernel snapshot:
{kernel}

Return JSON:
{{
  "summary": "",
  "affected_kernel_nodes": [{{"id": "uuid", "impact": "SUPPORT|WEAKEN|CONTEST|REFINE|REFRAME|OPEN_NEW_QUESTION|DECISION_REVIEW"}}],
  "distinctions": [],
  "new_questions": [],
  "possible_hypotheses": [],
  "decision_implications": [],
  "epistemic_risk": "",
  "evidence_maturity": 0.0,
  "admission_allowed": false,
  "rationale": "",
  "what_could_change": []
}}"""

IMPACT_SYSTEM = """Assess potential cognitive impact for Research Attention OS.
You do NOT choose DROP/AWARE/WATCH/ENGAGE. You estimate what absorbing this information could mean for the current Cognitive Kernel.

Kernel Match localizes where the information might matter. You estimate:
- effect direction: REINFORCE | CHALLENGE | REFINE | OPEN_NEW | NO_MATERIAL_CHANGE
- change_magnitude: how much understanding could change if absorbed
- epistemic_strength: how justified that effect is by current evidence (not the same as direction)
- target_importance: importance of the affected Kernel target
- attention_cost: effort to process properly

A company self-report may REINFORCE a model and still have low epistemic_strength.
Do not treat directional consistency as strong evidence.
Scope alignment is required before assigning effect direction.
Do not project a broad claim onto a narrower Kernel proposition.
Distinguish system-level, subsystem-level, temporal, task, benchmark, population, deployment, and causal scope when relevant.
If the source does not provide evidence at the target Kernel scope, prefer REFINE or NO_MATERIAL_CHANGE over a strong REINFORCE or CHALLENGE.
Explicit narrower-scope evidence may support a directional effect.
A topic-relevant marketing article is not a Decision review.
OPEN_NEW with exploration_candidate=true is allowed when no Kernel target fits but a useful new direction appears.
Low topic similarity alone must not imply NO_MATERIAL_CHANGE when a STRUCTURAL or new-direction effect is present.
Popularity is not importance. Disagreement is verification value, not a reason to ignore.
Return JSON only."""

IMPACT_USER = """Text:
{text}

Matches: {matches}
Match titles are Kernel propositions. Align the source-claim scope with that proposition before REINFORCE or CHALLENGE.
Duplicate: {is_duplicate}
Independent sources: {independent_source_count}
Secondary reports: {secondary_report_count}

Return JSON:
{{
  "effects": [{{
    "target_kernel_node_id": null,
    "effect": "REINFORCE",
    "change_magnitude": 0.0,
    "epistemic_strength": 0.0,
    "target_importance": 0.0,
    "reason": "",
    "exploration_candidate": false
  }}],
  "attention_cost": 0.0,
  "exploration_candidate": false,
  "evidence_maturity": 0.0,
  "threatens_active_work": false,
  "marketing_heavy": false,
  "high_quality_technical": false,
  "foundational_paper": false
}}"""

# Transitional aliases; the stage is impact assessment, not generic feature judgment.
JUDGMENT_SYSTEM = IMPACT_SYSTEM
JUDGMENT_USER = IMPACT_USER

BOOTSTRAP_SYSTEM = """Propose an initial Cognitive Kernel from a researcher's self-description.
Propose Goals, Projects, Questions, Beliefs, Models — as KernelPatch proposals only.
Do not invent false precision. Keep the Kernel small and high-density.
Return JSON only."""

BOOTSTRAP_USER = """Researcher description:
{text}

Optional source excerpts:
{excerpts}

Return JSON:
{{
  "proposals": [{{
    "target_object_type": "GOAL|PROJECT|QUESTION|BELIEF|MODEL|BOTTLENECK|DECISION",
    "title": "",
    "status": "ACTIVE",
    "payload": {{}},
    "reasoning": ""
  }}]
}}
Maximum 8 proposals."""
