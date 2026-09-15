"""Human Feedback Loop v0.1 — structured Confirm / Correct on AttentionPlan."""

from __future__ import annotations

from copy import deepcopy
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import CognitiveEffectKind, Disposition, FeedbackKind
from app.models.analysis import AnalysisRun
from app.models.kernel import KernelNode
from app.models.scheduler import AttentionFeedback, AttentionPlan
from app.services.cognitive_impact import is_update_eligible_node, visible_prediction_from_frozen

DISPOSITIONS = frozenset(d.value for d in Disposition)
UPDATE_OPERATIONS = frozenset(o.value for o in CognitiveEffectKind)
TARGETED_OPERATIONS = frozenset(
    {CognitiveEffectKind.REINFORCE.value, CognitiveEffectKind.CHALLENGE.value}
)

CAUSAL_SCOPES = frozenset({
    "PERCEPTION_ERROR",
    "COGNITION_ERROR",
    "AWARENESS_ERROR",
    "RUNTIME_CAPTURE_ERROR",
    "CORE_POLICY_ERROR",
    "USER_POLICY_RESIDUAL",
    "DELIVERY_PREFERENCE",
    "ACTOR_CONTEXT_ERROR",
})
EVIDENCE_PROVENANCE = frozenset({
    "HUMAN_EXPLICIT",
    "ASSISTANT_PROXY",
    "PASSIVE_BEHAVIOR",
    "AGENT_CONTEXT",
    "SYSTEM_INFERRED",
})


def _operation_value(raw) -> str | None:
    if raw is None:
        return None
    if hasattr(raw, "value"):
        raw = raw.value
    op = str(raw).upper()
    return op if op in UPDATE_OPERATIONS else None


def public_update(raw) -> dict | None:
    """Compatibility normalize for stored AnalysisRun payloads.

    Historical `{operation: null}` and retired ops become no-update. OPEN_NEW
    targets are dropped. Human Correction must not use this path.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    operation = _operation_value(raw.get("operation"))
    if operation is None:
        return None
    target = raw.get("target_node_id")
    target_node_id = str(target) if target else None
    if operation == CognitiveEffectKind.OPEN_NEW.value:
        target_node_id = None
    return {"operation": operation, "target_node_id": target_node_id}


def frozen_judgment_inputs(plan: AttentionPlan, run: AnalysisRun | None) -> tuple[dict | None, list]:
    """Frozen cognitive impact + Locate matches for THIS plan.

    Plan score_debug first. If missing, the associated AnalysisRun's original
    frozen provenance. Never the latest other plan's matches.
    """
    from app.services.scheduler import matches_from_debug

    plan_debug = plan.score_debug if isinstance(getattr(plan, "score_debug", None), dict) else {}
    impact = plan_debug.get("cognitive_impact")
    matches_raw = plan_debug.get("matches")

    payload = run.result_payload if run is not None and isinstance(run.result_payload, dict) else {}
    stored_plan = payload.get("attention_plan") if isinstance(payload.get("attention_plan"), dict) else {}
    stored_debug = stored_plan.get("score_debug") if isinstance(stored_plan.get("score_debug"), dict) else {}

    if impact is None:
        impact = stored_debug.get("cognitive_impact") or payload.get("cognitive_impact")
    if not matches_raw:
        matches_raw = stored_debug.get("matches")
    return impact, matches_from_debug(matches_raw)


def system_prediction_from_plan(plan: AttentionPlan, run: AnalysisRun | None) -> dict:
    """What the user is currently asked to Confirm/Correct on THIS AttentionPlan.

    Disposition comes from the plan. Update × DeltaContent are the current v2.1
    interpretation of that plan's frozen AnalysisRun judgment. Historical
    AttentionFeedback rows are never rewritten.
    """
    impact, matches = frozen_judgment_inputs(plan, run)
    visible = visible_prediction_from_frozen(
        frozen_impact=impact,
        frozen_matches=matches,
        disposition=plan.disposition,
    )
    return {
        "disposition": visible["disposition"],
        "update": public_update(visible["update"]),
        "delta_content": visible["delta_content"],
    }


def _validate_disposition(disposition) -> None:
    if disposition not in DISPOSITIONS:
        raise HTTPException(422, f"Invalid disposition: {disposition}")


def _strict_correction_update(raw) -> dict | None:
    """Validate a Human Correction Update against the public contract. No silent coercion."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise HTTPException(422, "update must be an object or null")
    raw_op = raw.get("operation")
    if raw_op is None:
        if raw.get("target_node_id"):
            raise HTTPException(422, "update.operation is required when setting target_node_id")
        return None
    if hasattr(raw_op, "value"):
        raw_op = raw_op.value
    op = str(raw_op).upper()
    if op not in UPDATE_OPERATIONS:
        raise HTTPException(422, f"Invalid update operation: {raw_op}")
    target = raw.get("target_node_id")
    target_node_id = str(target) if target else None
    if op == CognitiveEffectKind.OPEN_NEW.value and target_node_id:
        raise HTTPException(422, "OPEN_NEW requires target_node_id to be null")
    if op in TARGETED_OPERATIONS and not target_node_id:
        raise HTTPException(422, f"{op} requires target_node_id")
    return {"operation": op, "target_node_id": target_node_id}


def _validate_update_target(db: Session, update: dict | None) -> None:
    if not update:
        return
    op = update.get("operation")
    if op not in TARGETED_OPERATIONS:
        return
    raw_id = update.get("target_node_id")
    try:
        node_id = UUID(str(raw_id))
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, "target_node_id must be a Kernel node UUID") from exc
    node = db.get(KernelNode, node_id)
    if node is None or node.deleted_at is not None:
        raise HTTPException(422, "target_node_id must refer to an existing Kernel node")
    if not is_update_eligible_node(node.node_type):
        raise HTTPException(422, f"{node.node_type} is not an update-eligible Kernel node")


def _diff_fields(system: dict, user: dict) -> list[str]:
    corrected: list[str] = []
    if system.get("disposition") != user.get("disposition"):
        corrected.append("disposition")
    sys_up = public_update(system.get("update"))
    usr_up = public_update(user.get("update"))
    if sys_up is None and usr_up is None:
        pass
    elif sys_up is None or usr_up is None:
        corrected.append("update")
    else:
        if sys_up.get("operation") != usr_up.get("operation"):
            corrected.append("update.operation")
        if sys_up.get("target_node_id") != usr_up.get("target_node_id"):
            corrected.append("update.target_node_id")
    if (system.get("delta_content") or "") != (user.get("delta_content") or ""):
        corrected.append("delta_content")
    return corrected


def merge_correction(system: dict, overrides: dict, db: Session | None = None) -> dict:
    """Apply partial human overrides. Omitted keys keep system values; explicit null is a value."""
    merged = deepcopy(system)
    merged["update"] = public_update(merged.get("update"))

    if "disposition" in overrides:
        if overrides["disposition"] is None:
            raise HTTPException(422, "disposition cannot be null")
        merged["disposition"] = overrides["disposition"]

    if "update" in overrides:
        patch = overrides["update"]
        if patch is None:
            merged["update"] = None
        elif isinstance(patch, dict):
            if "operation" in patch and patch["operation"] is None:
                merged["update"] = None
            else:
                current = dict(merged["update"] or {})
                if "operation" in patch:
                    raw_op = patch["operation"]
                    op = str(raw_op).upper() if raw_op is not None else None
                    if op not in UPDATE_OPERATIONS:
                        raise HTTPException(422, f"Invalid update operation: {raw_op}")
                    current["operation"] = op
                if "target_node_id" in patch:
                    current["target_node_id"] = (
                        str(patch["target_node_id"]) if patch["target_node_id"] else None
                    )
                elif current.get("operation") == CognitiveEffectKind.OPEN_NEW.value:
                    current["target_node_id"] = None
                merged["update"] = current
        else:
            raise HTTPException(422, "update must be an object or null")

    if "delta_content" in overrides:
        merged["delta_content"] = overrides["delta_content"] if overrides["delta_content"] is not None else ""

    _validate_disposition(merged.get("disposition"))
    if merged.get("update") is not None:
        merged["update"] = _strict_correction_update(merged["update"])
    if db is not None:
        _validate_update_target(db, merged.get("update"))
    return merged


def _feedback_class(kind: str, corrected_fields: list[str]) -> str:
    if str(kind).upper() == FeedbackKind.CONFIRM.value:
        return "CONFIRMATION"
    cognitive = any(field == "delta_content" or field == "update" or field.startswith("update.") for field in corrected_fields)
    policy = "disposition" in corrected_fields
    if cognitive and policy:
        return "MIXED_CORRECTION"
    if cognitive:
        return "COGNITIVE_ADJUDICATION"
    if policy:
        return "ATTENTION_POLICY_CORRECTION"
    return "UNRESOLVED"


def build_attribution(
    *,
    kind: str,
    corrected_fields: list[str],
    causal_scope: str | None,
    evidence_provenance: str | None,
    rationale: str | None,
) -> dict:
    feedback_class = _feedback_class(kind, corrected_fields)
    provenance = str(evidence_provenance or "HUMAN_EXPLICIT").upper()
    if provenance not in EVIDENCE_PROVENANCE:
        raise HTTPException(422, f"Invalid evidence_provenance: {evidence_provenance}")

    explicit_scope = str(causal_scope).upper() if causal_scope else None
    if explicit_scope is not None and explicit_scope not in CAUSAL_SCOPES:
        raise HTTPException(422, f"Invalid causal_scope: {causal_scope}")

    if str(kind).upper() == FeedbackKind.CONFIRM.value:
        scope = "NONE"
        scope_source = "CONFIRMATION"
    elif explicit_scope is not None:
        scope = explicit_scope
        scope_source = "EXPLICIT"
    elif feedback_class == "COGNITIVE_ADJUDICATION":
        scope = "COGNITION_ERROR"
        scope_source = "CONSERVATIVE_DERIVATION"
    else:
        scope = "UNRESOLVED"
        scope_source = "UNRESOLVED"

    if scope == "USER_POLICY_RESIDUAL" and feedback_class != "ATTENTION_POLICY_CORRECTION":
        raise HTTPException(422, "USER_POLICY_RESIDUAL requires a disposition-only Attention-policy correction")
    if scope == "COGNITION_ERROR" and feedback_class not in {"COGNITIVE_ADJUDICATION", "MIXED_CORRECTION"}:
        raise HTTPException(422, "COGNITION_ERROR requires a cognitive adjudication field")

    personalization_eligible = (
        scope == "USER_POLICY_RESIDUAL"
        and feedback_class == "ATTENTION_POLICY_CORRECTION"
        and provenance == "HUMAN_EXPLICIT"
    )
    return {
        "causal_scope": scope,
        "scope_source": scope_source,
        "feedback_class": feedback_class,
        "evidence_provenance": provenance,
        "personalization_eligible": personalization_eligible,
        "rationale": str(rationale) if rationale else None,
    }


def feedback_public(row: AttentionFeedback) -> dict:
    return {
        "id": str(row.id),
        "attention_plan_id": str(row.attention_plan_id),
        "analysis_run_id": str(row.analysis_run_id) if row.analysis_run_id else None,
        "kind": row.feedback_kind,
        "system_prediction": row.system_prediction,
        "user_correction": row.user_correction,
        "corrected_fields": row.corrected_fields or [],
        "attribution": row.attribution or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def feedback_for_plan(db: Session, plan_id: UUID) -> list[AttentionFeedback]:
    return (
        db.execute(
            select(AttentionFeedback)
            .where(AttentionFeedback.attention_plan_id == plan_id)
            .order_by(AttentionFeedback.created_at.desc(), AttentionFeedback.id.desc())
        )
        .scalars()
        .all()
    )


def feedback_for_run(db: Session, run_id: UUID) -> list[AttentionFeedback]:
    return (
        db.execute(
            select(AttentionFeedback)
            .where(AttentionFeedback.analysis_run_id == run_id)
            .order_by(AttentionFeedback.created_at.desc(), AttentionFeedback.id.desc())
        )
        .scalars()
        .all()
    )


def overrides_from_body(body) -> dict:
    """Build correction overrides. Presence in model_fields_set distinguishes omit vs explicit null."""
    overrides: dict = {}
    if "disposition" in body.model_fields_set:
        overrides["disposition"] = body.disposition
    if "update" in body.model_fields_set:
        if body.update is None:
            overrides["update"] = None
        else:
            patch: dict = {}
            if "operation" in body.update.model_fields_set:
                patch["operation"] = body.update.operation
            if "target_node_id" in body.update.model_fields_set:
                patch["target_node_id"] = (
                    str(body.update.target_node_id) if body.update.target_node_id else None
                )
            overrides["update"] = patch
    if "delta_content" in body.model_fields_set:
        overrides["delta_content"] = body.delta_content
    return overrides


def record_feedback(
    db: Session,
    *,
    plan_id: UUID,
    kind: str,
    overrides: dict | None = None,
    causal_scope: str | None = None,
    evidence_provenance: str | None = "HUMAN_EXPLICIT",
    attribution_rationale: str | None = None,
) -> AttentionFeedback:
    plan = db.get(AttentionPlan, plan_id)
    if plan is None:
        raise HTTPException(404, "AttentionPlan not found")
    if plan.analysis_run_id:
        from app.services.analysis_runs import attention_plans_for_run

        latest_plans = attention_plans_for_run(db, plan.analysis_run_id)
        if latest_plans and latest_plans[0].id != plan.id:
            raise HTTPException(422, "Feedback must target the latest AttentionPlan for this AnalysisRun")

    run = db.get(AnalysisRun, plan.analysis_run_id) if plan.analysis_run_id else None
    system = system_prediction_from_plan(plan, run)
    _validate_disposition(system.get("disposition"))

    kind_upper = str(kind).upper()
    if kind_upper not in {FeedbackKind.CONFIRM.value, FeedbackKind.CORRECT.value}:
        raise HTTPException(422, "kind must be CONFIRM or CORRECT")

    if kind_upper == FeedbackKind.CONFIRM.value:
        user = deepcopy(system)
        corrected_fields: list[str] = []
    else:
        if not overrides:
            raise HTTPException(422, "CORRECT requires at least one field to change")
        user = merge_correction(system, overrides, db=db)
        corrected_fields = _diff_fields(system, user)
        if not corrected_fields:
            raise HTTPException(422, "CORRECT must change at least one field from the system prediction")

    attribution = build_attribution(
        kind=kind_upper,
        corrected_fields=corrected_fields,
        causal_scope=causal_scope,
        evidence_provenance=evidence_provenance,
        rationale=attribution_rationale,
    )

    row = AttentionFeedback(
        attention_plan_id=plan.id,
        analysis_run_id=plan.analysis_run_id,
        feedback_kind=kind_upper,
        system_prediction=system,
        user_correction=user,
        corrected_fields=corrected_fields,
        attribution=attribution,
        system_attention_state=system.get("disposition"),
        user_attention_state=user.get("disposition"),
        system_modes=[],
        user_modes=[],
    )
    db.add(row)
    db.flush()
    return row
