"""v2.1 frozen invariants: Location ≠ Update, Δ_t as unique transition truth."""

from __future__ import annotations

from uuid import uuid4

from app.enums import ClaimType, CognitiveEffectKind, PatchChangeType
from app.models.kernel import KernelNode
from app.services.cognitive_impact import (
    LOCATION_NODE_TYPES,
    UPDATE_ELIGIBLE_NODE_TYPES,
    CognitiveEffect,
    CognitiveImpactAssessment,
    ground_effects,
    is_location_node,
    is_update_eligible_node,
    primary_update,
    select_primary_effect,
)
from app.services.deltas import ModelDelta, PatchDraft, patch_consistent_with_update, propose_patches
from app.services.extraction import ExtractedClaim, ExtractionResult
from app.services.matching import KernelMatch, match_kernel
from app.services.scheduler import SchedulerFeatures


def _match(node_type: str, title: str | None = None, score: float = 0.9) -> KernelMatch:
    return KernelMatch(
        node_id=uuid4(),
        node_type=node_type,
        title=title or node_type,
        score=score,
        reason="test locate",
        relevance_type="TOPIC",
    )


def _effect(match: KernelMatch | None, kind: CognitiveEffectKind, **overrides) -> CognitiveEffect:
    base = dict(
        target_kernel_node_id=match.node_id if match else None,
        operation=kind,
        change_magnitude=0.8,
        epistemic_strength=0.4,
        target_importance=0.75,
        reason="test effect",
        exploration_candidate=kind == CognitiveEffectKind.OPEN_NEW,
    )
    base.update(overrides)
    return CognitiveEffect(**base)


def _extraction(*texts: str) -> ExtractionResult:
    claims = [ExtractedClaim(text=t, claim_type=ClaimType.TECHNICAL) for t in texts]
    return ExtractionResult(claims=claims, technical_claims=list(texts), evidence_maturity=0.5)


def _features() -> SchedulerFeatures:
    return SchedulerFeatures(
        topic_relevance=0.7,
        structural_relevance=0.1,
        decision_relevance=0.2,
        novelty=0.6,
        credibility=0.7,
        kernel_delta=0.7,
        bottleneck_alignment=0.2,
        disagreement=0.1,
        actionability=0.4,
        temporal_value=0.4,
        cognitive_cost=8.0,
        evidence_maturity=0.5,
        change_magnitude=0.7,
        epistemic_strength=0.4,
        target_importance=0.7,
        attention_cost=8.0,
    )


def _node(match: KernelMatch, payload: dict | None = None) -> KernelNode:
    node = KernelNode(
        node_type=match.node_type,
        title=match.title,
        status="ACTIVE",
        payload=payload or {"proposition": match.title, "confidence": 0.5},
        current_version=1,
    )
    node.id = match.node_id
    return node


def test_location_and_update_eligible_types_are_disjoint():
    assert LOCATION_NODE_TYPES.isdisjoint(UPDATE_ELIGIBLE_NODE_TYPES)
    for kind in ("GOAL", "PROJECT"):
        assert is_location_node(kind)
        assert not is_update_eligible_node(kind)
    for kind in ("BELIEF", "MODEL", "QUESTION", "HYPOTHESIS", "DECISION", "BOTTLENECK"):
        assert is_update_eligible_node(kind)
        assert not is_location_node(kind)


def test_locate_may_hit_goal_and_project():
    goal = KernelNode(node_type="GOAL", title="Build better motor control", status="ACTIVE", payload={})
    project = KernelNode(node_type="PROJECT", title="Motor Intelligence", status="ACTIVE", payload={})
    goal.id = uuid4()
    project.id = uuid4()
    extraction = _extraction("A motor control paper on temporal intelligence.")
    matches = match_kernel(extraction, [goal, project], extra_text="motor control temporal intelligence")
    located = {m.node_type for m in matches}
    assert "GOAL" in located or "PROJECT" in located


def test_grounding_discards_location_reinforce_even_when_scope_overlaps():
    project = _match("PROJECT", "Motor Intelligence temporal control")
    extraction = _extraction("A paper on motor intelligence and temporal control.")
    raw = [_effect(project, CognitiveEffectKind.REINFORCE, reason="same project topic")]
    grounded = ground_effects(raw, [project], extraction, independent_source_count=1)
    assert grounded == []
    assert primary_update(CognitiveImpactAssessment(effects=grounded))["operation"] is None


def test_grounding_discards_goal_challenge():
    goal = _match("GOAL", "Build better embodied intelligence")
    extraction = _extraction("Embodied intelligence claims are overstated.")
    raw = [_effect(goal, CognitiveEffectKind.CHALLENGE)]
    grounded = ground_effects(raw, [goal], extraction, independent_source_count=2)
    assert grounded == []


def test_update_eligible_types_remain_legal_targets():
    extraction = _extraction("Latency evaluation must split energy and task-success.")
    for kind in ("BELIEF", "MODEL", "QUESTION", "HYPOTHESIS", "DECISION", "BOTTLENECK"):
        match = _match(kind, "Latency evaluation of energy and task-success")
        raw = [_effect(match, CognitiveEffectKind.REINFORCE)]
        grounded = ground_effects(raw, [match], extraction, independent_source_count=2)
        assert grounded, kind
        update = primary_update(CognitiveImpactAssessment(effects=grounded))
        assert update["operation"] == CognitiveEffectKind.REINFORCE
        assert update["target_node_id"] == str(match.node_id)


def test_public_update_cannot_select_location_node():
    project = _match("PROJECT")
    model = _match("MODEL", "Separable temporal motor intelligence")
    extraction = _extraction("Evidence supports a temporal motor intelligence split.")
    raw = [
        _effect(project, CognitiveEffectKind.REINFORCE, change_magnitude=0.99, target_importance=0.99),
        _effect(model, CognitiveEffectKind.REINFORCE, change_magnitude=0.7, target_importance=0.75),
    ]
    grounded = ground_effects(raw, [project, model], extraction, independent_source_count=2)
    update = primary_update(CognitiveImpactAssessment(effects=grounded))
    assert update["target_node_id"] == str(model.node_id)
    assert update["operation"] == CognitiveEffectKind.REINFORCE


def test_challenge_patch_revises_delta_target_only():
    model = _match("MODEL", "Existing model M1")
    other = _match("QUESTION", "Unrelated question")
    node = _node(model)
    unused = _node(other)
    assessment = CognitiveImpactAssessment(
        effects=[
            _effect(
                model,
                CognitiveEffectKind.CHALLENGE,
                reason="Source contests M1 at matching scope.",
                target_node_type="MODEL",
            )
        ]
    )
    stray = ModelDelta(
        summary="ignore",
        questions=["Should we open a new question about something else?"],
        distinctions=["cognitive vs motor"],
    )
    drafts = propose_patches(
        "scale differently cognitive motor",
        stray,
        [model, other],
        _features(),
        [node, unused],
        [],
        assessment=assessment,
        extraction=_extraction("Direct evidence that M1 is too strong as stated."),
    )
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.change_type == PatchChangeType.REVISE
    assert draft.target_object_id == model.node_id
    assert draft.target_object_type.value == "MODEL"
    assert patch_consistent_with_update(draft, primary_update(assessment))


def test_open_new_patch_is_create_without_existing_target():
    project = _match("PROJECT", "Motor Intelligence")
    assessment = CognitiveImpactAssessment(
        effects=[
            _effect(
                None,
                CognitiveEffectKind.OPEN_NEW,
                reason="No existing Kernel node captures this branch.",
            )
        ]
    )
    stray = ModelDelta(
        summary="old heuristic",
        questions=["A precise new research question?"],
        distinctions=["scale differently"],
    )
    drafts = propose_patches(
        "scale differently",
        stray,
        [project],
        _features(),
        [_node(project)],
        [],
        assessment=assessment,
        extraction=_extraction("A new architecture paper introduces an abstraction."),
    )
    assert len(drafts) == 1
    assert drafts[0].change_type == PatchChangeType.CREATE
    assert drafts[0].target_object_id is None
    assert patch_consistent_with_update(drafts[0], primary_update(assessment))


def test_none_delta_does_not_emit_heuristic_patches():
    model = _match("MODEL")
    stray = ModelDelta(
        summary="would have created a model",
        questions=["At which layers?"],
        distinctions=["cognitive vs motor", "scale differently"],
    )
    drafts = propose_patches(
        "Repeated evidence suggests semantic task intelligence and temporal motor intelligence scale differently.",
        stray,
        [model],
        _features(),
        [_node(model)],
        [],
        assessment=CognitiveImpactAssessment(effects=[]),
        extraction=_extraction("scale differently"),
    )
    assert drafts == []


def test_lexical_locate_has_no_domain_bonus_tables():
    import inspect

    import app.services.matching as matching

    for name in ("EQUITY_STRUCTURE", "EMBODIED_MOTOR", "COLLECTIVE"):
        assert not hasattr(matching, name)
    source = inspect.getsource(matching.match_kernel)
    assert "folding" not in source
    assert "humanoid" not in source
    assert "swarm" not in source
    assert "orbit" not in source


def test_propose_patches_without_delta_assessment_is_empty():
    model = _match("MODEL")
    stray = ModelDelta(summary="unbound prose", questions=["Open a new question?"], distinctions=["scale differently"])
    drafts = propose_patches(
        "scale differently",
        stray,
        [model],
        _features(),
        [_node(model)],
        [],
    )
    assert drafts == []


def test_select_primary_rejects_typed_location_effect_without_grounding():
    project = _match("PROJECT")
    leaked = _effect(project, CognitiveEffectKind.REINFORCE, target_node_type="PROJECT")
    assessment = CognitiveImpactAssessment(effects=[leaked])
    assert select_primary_effect(assessment) is None
    assert primary_update(assessment)["operation"] is None
