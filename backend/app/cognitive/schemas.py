"""JSON shapes expected from ModelBackedCognitiveProvider. Validated after parse."""

EXTRACT_SCHEMA = {
    "type": "object",
    "required": ["claims", "observations", "inferences"],
    "properties": {
        "event_title": {"type": ["string", "null"]},
        "event_summary": {"type": ["string", "null"]},
        "claims": {"type": "array"},
        "observations": {"type": "array"},
        "inferences": {"type": "array"},
        "current_facts": {"type": "array"},
        "future_plans": {"type": "array"},
        "technical_claims": {"type": "array"},
        "promotional_framing": {"type": "array"},
        "marketing_heavy": {"type": "boolean"},
    },
}

MATCH_SCHEMA = {
    "type": "object",
    "required": ["matches"],
    "properties": {
        "matches": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["kernel_node_id", "relevance_type"],
                "properties": {
                    "kernel_node_id": {"type": "string"},
                    "relevance_type": {
                        "enum": ["TOPIC", "STRUCTURAL", "DECISION", "BOTTLENECK", "EVIDENCE"]
                    },
                    "score": {"type": "number"},
                    "reason": {"type": "string"},
                },
            },
        }
    },
}

DELTA_SCHEMA = {
    "type": "object",
    "required": ["summary"],
    "properties": {
        "summary": {"type": "string"},
        "affected_kernel_nodes": {"type": "array"},
        "distinctions": {"type": "array"},
        "new_questions": {"type": "array"},
        "possible_hypotheses": {"type": "array"},
        "decision_implications": {"type": "array"},
        "epistemic_risk": {"type": "string"},
        "evidence_maturity": {"type": "number"},
        "admission_allowed": {"type": "boolean"},
        "rationale": {"type": "string"},
        "what_could_change": {"type": "array"},
    },
}
