from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.enums import CognitiveEffectKind, Urgency
from app.services.brain_world_model import (
    BrainWorldSnapshot,
    explicit_runtime_fact,
    model_inference_fact,
    runtime_view_from_brain_snapshot,
    trusted_bool,
)
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment
from app.services.matching import KernelMatch
from app.services.scheduler import SchedulerFeatures, route, validate_plan

PROBE_VERSION = "phase7c-brain-authority-probe-v0.1"


@dataclass(frozen=True)
class ProbeCase:
    case_id: str
    snapshot: BrainWorldSnapshot
    expected_preempt: bool
    note: str


def _now() -> datetime:
    return datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
def _material_reinforce():
    match = KernelMatch(
        node_id=uuid4(), node_type="BELIEF", title="Controlled belief",
        score=0.9, reason="controlled Phase 7C probe", structural=False,
        relevance_type="TOPIC",
    )
    effect = CognitiveEffect(
        target_kernel_node_id=match.node_id,
        operation=CognitiveEffectKind.REINFORCE,
        change_magnitude=0.8,
        epistemic_strength=0.7,
        target_importance=0.8,
        reason="controlled material cognitive effect",
        exploration_candidate=False,
        target_node_type="BELIEF",
    )
    return match, CognitiveImpactAssessment(
        effects=[effect], attention_cost=8.0, exploration_candidate=False
    )


def _features(threatens_active_work: bool) -> SchedulerFeatures:
    return SchedulerFeatures(
        topic_relevance=0.8, structural_relevance=0.0, decision_relevance=0.0,
        novelty=0.6, credibility=0.8, kernel_delta=0.8, bottleneck_alignment=0.0,
        disagreement=0.0, actionability=0.4, temporal_value=0.5, cognitive_cost=8.0,
        threatens_active_work=threatens_active_work,
    )
def cases() -> list[ProbeCase]:
    now = _now()
    inferred = model_inference_fact(
        "threatens_active_work", True, observed_at=now,
        provenance="model guessed active-work overlap", confidence=0.95,
    )
    current_task = explicit_runtime_fact(
        "current_task", "Write current paper", observed_at=now,
        provenance="explicit user runtime",
    )
    trusted_threat = explicit_runtime_fact(
        "threatens_active_work", True, observed_at=now,
        provenance="explicit trusted runtime signal",
    )
    expired_threat = explicit_runtime_fact(
        "threatens_active_work", True,
        observed_at=now - timedelta(hours=2),
        valid_until=now - timedelta(minutes=1),
        provenance="expired trusted runtime signal",
    )
    return [
        ProbeCase("A_MODEL_GUESS_ONLY", BrainWorldSnapshot(now, (), (inferred,)), False,
                  "Model inference alone cannot authorize PREEMPT."),
        ProbeCase("B_TASK_WITH_MODEL_GUESS", BrainWorldSnapshot(now, (current_task,), (inferred,)), False,
                  "Knowing the current task does not make a guessed overlap authoritative."),
        ProbeCase("C_AUTHORITATIVE_THREAT", BrainWorldSnapshot(now, (current_task, trusted_threat)), True,
                  "Explicit trusted overlap may authorize PREEMPT."),
        ProbeCase("D_EXPIRED_THREAT", BrainWorldSnapshot(now, (current_task, expired_threat)), False,
                  "Expired authority cannot remain current state."),
    ]
def run_case(case: ProbeCase) -> dict:
    match, assessment = _material_reinforce()
    trusted_threat = trusted_bool(case.snapshot, "threatens_active_work", now=_now())
    features = _features(trusted_threat)
    view = runtime_view_from_brain_snapshot(case.snapshot, now=_now())
    plan = validate_plan(route(features, view, assessment=assessment, matches=[match]))
    actual_preempt = plan.urgency == Urgency.PREEMPT
    return {
        "case_id": case.case_id,
        "expected_preempt": case.expected_preempt,
        "actual_preempt": actual_preempt,
        "match": actual_preempt == case.expected_preempt,
        "trusted_threat": trusted_threat,
        "disposition": plan.disposition.value,
        "urgency": plan.urgency.value,
        "expected_output": plan.expected_output.value,
        "note": case.note,
        "brain_snapshot": case.snapshot.as_dict(),
        "plan_reason": plan.reason,
    }


def run_all() -> list[dict]:
    return [run_case(case) for case in cases()]
