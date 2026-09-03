"""Human Feedback Loop v0.1 — structured Confirm / Correct on AttentionPlan."""

from __future__ import annotations

from copy import deepcopy
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import CognitiveEffectKind, Disposition, FeedbackKind
from app.models.analysis import AnalysisRun
from app.models.scheduler import AttentionFeedback, AttentionPlan
from app.services.cognitive_impact import assessment_from_dict, primary_update

DISPOSITIONS = frozenset(d.value for d in Disposition)
UPDATE_OPERATIONS = frozenset(o.value for o in CognitiveEffectKind)


def _normalize_update(raw: dict | None) -> dict:
    base = raw if isinstance(raw, dict) else {}
    op = base.get("operation")
    operation = str(op).upper() if op is not None else None
    if operation not in UPDATE_OPERATIONS:
        operation = None
    target = base.get("target_node_id")
    target_node_id = str(target) if target else None
    if operation == CognitiveEffectKind.OPEN_NEW.value:
        target_node_id = None
    return {"operation": operation, "target_node_id": target_node_id}


def system_prediction_from_plan(plan: AttentionPlan, run: AnalysisRun | None = None) -> dict:
    """Immutable system judgment snapshot for provenance."""
    impact = (plan.score_debug or {}).get("cognitive_impact") if isinstance(plan.score_debug, dict) else None
    update = _normalize_update(primary_update(assessment_from_dict(impact)) if impact else None)
    delta_content = ""
    if run is not None and isinstance(run.result_payload, dict):
        delta_content = run.result_payload.get("delta_content") or ""
        if not delta_content:
            delta_content = (run.result_payload.get("model_delta") or {}).get("summary") or ""
    return {
        "disposition": plan.disposition,
        "update": update,
        "delta_content": delta_content,
    }


def _validate_public_contract(prediction: dict) -> None:
    disposition = prediction.get("disposition")
    if disposition not in DISPOSITIONS:
        raise HTTPException(422, f"Invalid disposition: {disposition}")
    update = _normalize_update(prediction.get("update"))
    op = update["operation"]
    target = update["target_node_id"]
    if op in {CognitiveEffectKind.REINFORCE.value, CognitiveEffectKind.CHALLENGE.value} and not target:
        raise HTTPException(422, f"{op} requires target_node_id")
    if op == CognitiveEffectKind.OPEN_NEW.value and target:
        raise HTTPException(422, "OPEN_NEW requires target_node_id to be null")
    prediction["update"] = update


def _diff_fields(system: dict, user: dict) -> list[str]:
    corrected: list[str] = []
    if system.get("disposition") != user.get("disposition"):
        corrected.append("disposition")
    sys_up = _normalize_update(system.get("update"))
    usr_up = _normalize_update(user.get("update"))
    if sys_up.get("operation") != usr_up.get("operation"):
        corrected.append("update.operation")
    if sys_up.get("target_node_id") != usr_up.get("target_node_id"):
        corrected.append("update.target_node_id")
    if (system.get("delta_content") or "") != (user.get("delta_content") or ""):
        corrected.append("delta_content")
    return corrected


def merge_correction(system: dict, overrides: dict) -> dict:
    """Apply partial human overrides onto the system prediction."""
    merged = deepcopy(system)
    merged["update"] = _normalize_update(merged.get("update"))
    if overrides.get("disposition") is not None:
        merged["disposition"] = overrides["disposition"]
    if overrides.get("update") is not None:
        patch = overrides["update"] if isinstance(overrides["update"], dict) else {}
        if patch.get("operation") is not None:
            merged["update"]["operation"] = str(patch["operation"]).upper()
        if "target_node_id" in patch:
            merged["update"]["target_node_id"] = str(patch["target_node_id"]) if patch["target_node_id"] else None
        if merged["update"]["operation"] == CognitiveEffectKind.OPEN_NEW.value:
            merged["update"]["target_node_id"] = None
    if "delta_content" in overrides and overrides["delta_content"] is not None:
        merged["delta_content"] = overrides["delta_content"]
    _validate_public_contract(merged)
    return merged


def feedback_public(row: AttentionFeedback) -> dict:
    return {
        "id": str(row.id),
        "attention_plan_id": str(row.attention_plan_id),
        "analysis_run_id": str(row.analysis_run_id) if row.analysis_run_id else None,
        "kind": row.feedback_kind,
        "system_prediction": row.system_prediction,
        "user_correction": row.user_correction,
        "corrected_fields": row.corrected_fields or [],
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


def record_feedback(
    db: Session,
    *,
    plan_id: UUID,
    kind: str,
    disposition: str | None = None,
    update: dict | None = None,
    delta_content: str | None = None,
) -> AttentionFeedback:
    plan = db.get(AttentionPlan, plan_id)
    if plan is None:
        raise HTTPException(404, "AttentionPlan not found")
    run = db.get(AnalysisRun, plan.analysis_run_id) if plan.analysis_run_id else None
    system = system_prediction_from_plan(plan, run)

    kind_upper = str(kind).upper()
    if kind_upper not in {FeedbackKind.CONFIRM.value, FeedbackKind.CORRECT.value}:
        raise HTTPException(422, "kind must be CONFIRM or CORRECT")

    if kind_upper == FeedbackKind.CONFIRM.value:
        user = deepcopy(system)
        corrected_fields: list[str] = []
    else:
        overrides: dict = {}
        if disposition is not None:
            overrides["disposition"] = disposition
        if update is not None:
            overrides["update"] = update
        if delta_content is not None:
            overrides["delta_content"] = delta_content
        if not overrides:
            raise HTTPException(422, "CORRECT requires at least one field to change")
        user = merge_correction(system, overrides)
        corrected_fields = _diff_fields(system, user)
        if not corrected_fields:
            raise HTTPException(422, "CORRECT must change at least one field from the system prediction")

    row = AttentionFeedback(
        attention_plan_id=plan.id,
        analysis_run_id=plan.analysis_run_id,
        feedback_kind=kind_upper,
        system_prediction=system,
        user_correction=user,
        corrected_fields=corrected_fields,
        system_attention_state=system.get("disposition"),
        user_attention_state=user.get("disposition"),
        system_modes=[],
        user_modes=[],
    )
    db.add(row)
    db.flush()
    return row
