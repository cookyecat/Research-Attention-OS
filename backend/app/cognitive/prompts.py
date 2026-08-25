EXTRACT_SYSTEM = """You are the extraction stage of Research Attention OS.
Documents are not the unit of cognition. Extract EventCandidate, Claims, Observations, and Inferences.

Constitution:
- Claim = attributed assertion ("someone said X"), not "X is true".
- Observation = directly observed phenomenon or measurement. Never store interpretations as observations.
- Inference = derived conclusion (probably, therefore, suggests, indicates, we believe).
- "Company says the robot generalizes zero-shot" is a Claim, never an Observation.
- Future plans (will be released, is planned) are PREDICTIVE claims, not current facts.
- Promotional language is PROMOTIONAL, not proof.
Return JSON only."""

EXTRACT_USER = """Source type: {source_type}
Title: {title}

Text:
{text}

Return JSON:
{{
  "event_title": string|null,
  "event_summary": string|null,
  "claims": [{{"text": "", "attributed_to": null, "attribution_type": "AUTHOR|FOUNDER|COMPANY|PAPER|RESEARCHER|USER|UNKNOWN", "claim_type": "FACTUAL|TECHNICAL|PREDICTIVE|OPINION|PROMOTIONAL", "temporal_status": "CURRENT|FUTURE", "extraction_confidence": 0.0, "source_span": ""}}],
  "observations": [{{"text": "", "observer": "USER|PAPER|SYSTEM_EXTRACTED|INDEPENDENT_SOURCE", "observation_type": "DIRECT_VISUAL|MEASUREMENT|REPORTED_RESULT|USER_FIELD_NOTE|OTHER", "confidence": 0.0, "source_span": ""}}],
  "inferences": [{{"text": "", "derived_from": "", "confidence": 0.0}}],
  "current_facts": [],
  "future_plans": [],
  "technical_claims": [],
  "promotional_framing": [],
  "marketing_heavy": false
}}"""

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

JUDGMENT_SYSTEM = """Judge scheduler features for Research Attention OS.
You do NOT choose DROP/AWARE/WATCH/ENGAGE. You only score features.
Disagreement with an active Belief is verification value, not a reason to ignore.
Structural relevance is first-class.
Popularity is not importance.
Return JSON only."""

JUDGMENT_USER = """Text:
{text}

Matches: {matches}
Duplicate: {is_duplicate}
Independent sources: {independent_source_count}
Secondary reports: {secondary_report_count}

Return JSON:
{{
  "topic_relevance": 0.0,
  "structural_relevance": 0.0,
  "decision_relevance": 0.0,
  "novelty": 0.0,
  "credibility": 0.0,
  "kernel_delta": 0.0,
  "bottleneck_alignment": 0.0,
  "disagreement": 0.0,
  "actionability": 0.0,
  "temporal_value": 0.0,
  "cognitive_cost": 0.0,
  "evidence_maturity": 0.0,
  "threatens_active_work": false,
  "marketing_heavy": false,
  "high_quality_technical": false,
  "foundational_paper": false
}}"""

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
