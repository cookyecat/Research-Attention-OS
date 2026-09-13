from uuid import uuid4

from app.cognitive.research_aligned_contract import (
    GROUNDING_SYSTEM,
    JURISDICTION_SYSTEM,
    RELATION_MAPPING_SYSTEM,
    SUPPORT_BINDING_SYSTEM,
    canonical_semantic_units,
)
from app.cognitive.research_aligned_provider import ResearchAlignedCognitiveProvider
from app.enums import ClaimType, Disposition
from app.models.kernel import KernelNode
from app.services.analysis_execution import analysis_execution_snapshot
from app.services.cognitive_impact import project_assessment_to_effect
from app.services.extraction import ExtractedClaim, ExtractionResult
from app.services.matching import KernelMatch
from app.services.scheduler import RuntimeView, get_decision_strategy, route


def _meta():
    return {"latency_ms": 1, "prompt_tokens": 10, "completion_tokens": 5, "model": "fake-strong"}


def _claim_extraction(*, source_id="s1", secondary=False):
    ext = ExtractionResult(
        claims=[ExtractedClaim(
            text="Profiler evidence directly contradicts the current performance belief.",
            claim_type=ClaimType.FACTUAL,
            semantic_unit_id="u1",
            semantic_supports=[{
                "source_id": source_id,
                "support_pointer": "p1",
                "support_excerpt": "Profiler evidence directly contradicts the belief.",
            }],
        )]
    )
    ext.analysis_provenance = {
        "primary_source_id": source_id,
        "independent_source_ids": [] if secondary else [source_id],
        "secondary_source_ids": [source_id] if secondary else [],
    }
    return ext


def _belief_world():
    node = KernelNode(
        id=uuid4(),
        node_type="BELIEF",
        title="Computation dominates runtime.",
        status="ACTIVE",
        payload={"proposition": "Computation dominates runtime.", "importance": 0.9},
        current_version=1,
    )
    match = KernelMatch(
        node_id=node.id, node_type=node.node_type, title=node.title, score=1.0,
        reason="exact target", structural=False, relevance_type="EVIDENCE",
    )
    return node, match


def test_shared_prompts_are_byte_identical_to_closed_research_instruments():
    from eval.live.phase9a_kernel_causal_alignment_v0_2 import SYSTEM_PROMPT as p9
    from eval.live.run_phase10d6l3_decoupled_support_binding_v0_1 import SYSTEM_PROMPT as pbind
    from eval.live.run_phase10d6l4_grounding_capacity_bracketing_v0_1 import SYSTEM_PROMPT as pground
    from eval.live.run_phase10d6l4j_open_new_jurisdiction_capacity_v0_1 import SYSTEM_PROMPT as pjur

    assert RELATION_MAPPING_SYSTEM == p9
    assert SUPPORT_BINDING_SYSTEM == pbind
    assert GROUNDING_SYSTEM == pground
    assert JURISDICTION_SYSTEM == pjur


def test_sensor_unit_identity_and_support_provenance_survive_canonicalization():
    ext = _claim_extraction(source_id="source-a")
    units = canonical_semantic_units(ext)
    assert units[0]["source_unit_id"] == "u1"
    assert units[0]["unit_id"] == "source-a:u1"
    assert units[0]["supports"][0]["source_id"] == "source-a"


def test_targeted_direct_primary_relation_routes_cardinal_free_and_patches_same_cause():
    node, match = _belief_world()
    ext = _claim_extraction()

    def fake_chat(messages, **_kwargs):
        system = messages[0]["content"]
        if system == RELATION_MAPPING_SYSTEM:
            return {"effects": [{
                "operation": "CHALLENGE", "target_kernel_node_id": str(node.id), "reason": "direct contradiction"
            }]}, _meta()
        if system == SUPPORT_BINDING_SYSTEM:
            return {"bindings": [{
                "relation_id": "R001", "support_unit_ids": ["s1:u1"],
                "jurisdiction_anchor_ids": [], "reason": "exact support"
            }]}, _meta()
        if system == GROUNDING_SYSTEM:
            return {"items": [{"relation_id": "R001", "grounding_class": "DIRECT", "reason": "direct"}]}, _meta()
        raise AssertionError(system)

    provider = ResearchAlignedCognitiveProvider(chat_fn=fake_chat)
    assessment = provider.assess_cognitive_impact("", ext, [match], nodes=[node])
    assert len(assessment.effects) == 1
    effect = assessment.effects[0]
    assert effect.change_magnitude == 0.0
    assert effect.epistemic_strength == 1.0
    assert effect.target_importance == 1.0
    assert effect.support_unit_ids == ["s1:u1"]

    strategy = get_decision_strategy("pareto-multidelta-cardinal-free-effect-anchored-open-new")
    draft = route(assessment.features, RuntimeView(), assessment=assessment, matches=[match], decision_strategy=strategy)
    assert draft.disposition == Disposition.ENGAGE
    assert draft.decision_effect.as_dict() == effect.as_dict()
    assert draft.decision_scope_node_ids == [str(node.id)]

    projected = project_assessment_to_effect(assessment, draft.decision_effect)
    delta = provider.propose_model_delta("", ext, [match], assessment.features, [node], assessment=projected)
    patches = provider.propose_patches(
        "", delta, [match], assessment.features, [node], [], assessment=projected, extraction=ext
    )
    assert delta.summary == "direct contradiction"
    assert len(patches) == 1
    assert str(patches[0].target_object_id) == str(node.id)
    assert patches[0].proposed_state["status"] == "CONTESTED"


def test_direct_secondary_evidence_remains_relation_but_weak_authority():
    node, match = _belief_world()
    ext = _claim_extraction(secondary=True)

    def fake_chat(messages, **_kwargs):
        system = messages[0]["content"]
        if system == RELATION_MAPPING_SYSTEM:
            return {"effects": [{"operation": "CHALLENGE", "target_kernel_node_id": str(node.id), "reason": "reported contradiction"}]}, _meta()
        if system == SUPPORT_BINDING_SYSTEM:
            return {"bindings": [{"relation_id": "R001", "support_unit_ids": ["s1:u1"], "jurisdiction_anchor_ids": [], "reason": "support"}]}, _meta()
        if system == GROUNDING_SYSTEM:
            return {"items": [{"relation_id": "R001", "grounding_class": "DIRECT", "reason": "direct"}]}, _meta()
        raise AssertionError(system)

    provider = ResearchAlignedCognitiveProvider(chat_fn=fake_chat)
    assessment = provider.assess_cognitive_impact("", ext, [match], nodes=[node])
    effect = assessment.effects[0]
    assert effect.provenance_role == "SECONDARY_REPORT"
    assert effect.epistemic_strength == 0.0
    strategy = get_decision_strategy("pareto-multidelta-cardinal-free-effect-anchored-open-new")
    draft = route(assessment.features, RuntimeView(), assessment=assessment, matches=[match], decision_strategy=strategy)
    assert draft.disposition == Disposition.WATCH


def test_open_new_uses_effect_specific_jurisdiction_for_admission_and_scope():
    project = KernelNode(
        id=uuid4(), node_type="PROJECT", title="Motor Intelligence", status="ACTIVE",
        payload={"description": "Motor Intelligence", "scope": "embodied control", "importance": 0.9},
        current_version=1,
    )
    match = KernelMatch(
        node_id=project.id, node_type="PROJECT", title=project.title, score=0.9,
        reason="jurisdiction", structural=False, relevance_type="TOPIC",
    )
    ext = _claim_extraction()

    def fake_chat(messages, **_kwargs):
        system = messages[0]["content"]
        if system == RELATION_MAPPING_SYSTEM:
            return {"effects": [{"operation": "OPEN_NEW", "target_kernel_node_id": None, "reason": "new motor branch"}]}, _meta()
        if system == SUPPORT_BINDING_SYSTEM:
            return {"bindings": [{
                "relation_id": "R001", "support_unit_ids": ["s1:u1"],
                "jurisdiction_anchor_ids": [str(project.id)], "reason": "project owns branch"
            }]}, _meta()
        if system == JURISDICTION_SYSTEM:
            return {"items": [{
                "relation_id": "R001", "jurisdiction_class": "SUPPORTED_JURISDICTION", "reason": "scope contains branch"
            }]}, _meta()
        raise AssertionError(system)

    provider = ResearchAlignedCognitiveProvider(chat_fn=fake_chat)
    assessment = provider.assess_cognitive_impact("", ext, [match], nodes=[project])
    effect = assessment.effects[0]
    assert effect.jurisdiction_anchor_ids == [str(project.id)]
    strategy = get_decision_strategy("pareto-multidelta-cardinal-free-effect-anchored-open-new")
    draft = route(assessment.features, RuntimeView(), assessment=assessment, matches=[match], decision_strategy=strategy)
    assert draft.disposition == Disposition.ENGAGE
    assert draft.decision_scope_node_ids == [str(project.id)]
    assert draft.decision_scope_provenance == "effect-specific-jurisdiction"


def test_execution_identity_contains_full_research_contract_snapshot():
    provider = ResearchAlignedCognitiveProvider(chat_fn=lambda *_a, **_k: ({}, _meta()))
    snap = analysis_execution_snapshot(provider)
    assert snap["impact_contract"]["version"] == "research-aligned-cognition-v1"
    assert snap["cognition_contract"]["version"] == "research-aligned-cognition-v1"
    assert snap["cognition_contract"]["relation_cardinal_authority"] == "none"
