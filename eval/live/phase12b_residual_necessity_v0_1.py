from __future__ import annotations

from collections import Counter
from typing import Iterable


def summarize_feedback(rows: Iterable) -> dict:
    rows = list(rows)
    scopes = Counter()
    provenance = Counter()
    classes = Counter()
    eligible = []
    unresolved = 0
    for row in rows:
        attr = row.attribution if isinstance(getattr(row, "attribution", None), dict) else {}
        scope = str(attr.get("causal_scope") or "MISSING")
        prov = str(attr.get("evidence_provenance") or "MISSING")
        cls = str(attr.get("feedback_class") or "MISSING")
        scopes[scope] += 1
        provenance[prov] += 1
        classes[cls] += 1
        if scope == "UNRESOLVED" or not attr:
            unresolved += 1
        if bool(attr.get("personalization_eligible")):
            eligible.append(str(row.id))
    if not eligible:
        evidence_state = "NO_ELIGIBLE_RESIDUAL_EVIDENCE"
        calibration = "IDENTITY_RETAINED"
    elif len(eligible) == 1:
        evidence_state = "ISOLATED_ELIGIBLE_RESIDUAL"
        calibration = "IDENTITY_RETAINED_PENDING_REPLICATION"
    else:
        evidence_state = "REPEATED_ELIGIBLE_RESIDUAL_REQUIRES_REVIEW"
        calibration = "REVIEW_BEFORE_12C"
    return {
        "total_feedback_rows": len(rows),
        "personalization_eligible_rows": len(eligible),
        "personalization_eligible_ids": eligible,
        "unresolved_or_missing_attribution_rows": unresolved,
        "causal_scope_counts": dict(sorted(scopes.items())),
        "provenance_counts": dict(sorted(provenance.items())),
        "feedback_class_counts": dict(sorted(classes.items())),
        "residual_evidence_state": evidence_state,
        "calibration_decision": calibration,
    }
