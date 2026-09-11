from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
from eval.live.run_phase10d5_production_semantic_parity_audit_v0_1 import reconstruct_effects


def _node(nodes, code):
    return next(n for n in nodes if (n.payload or {}).get("phase6b_fixture_code") == code)


def test_production_importance_rebind_uses_kernel_type_prior_for_targeted_effect():
    nodes = build_phase6b_mvp_kernel_nodes()
    belief = _node(nodes, "B1")
    sample = {
        "effects": [{
            "operation": "CHALLENGE",
            "target_kernel_node_id": str(belief.id),
            "change_magnitude_debug_only": 0.7,
            "epistemic_strength": 0.9,
            "target_importance": 0.2,
            "reason": "fixture",
        }]
    }
    raw = reconstruct_effects(sample, nodes, production_importance=False)[0]
    prod = reconstruct_effects(sample, nodes, production_importance=True)[0]
    assert raw.target_importance == 0.2
    assert prod.target_importance == 0.75


def test_production_importance_rebind_leaves_open_new_llm_estimate_unchanged():
    nodes = build_phase6b_mvp_kernel_nodes()
    sample = {
        "effects": [{
            "operation": "OPEN_NEW",
            "target_kernel_node_id": None,
            "change_magnitude_debug_only": 0.7,
            "epistemic_strength": 0.8,
            "target_importance": 0.3,
            "reason": "fixture",
        }]
    }
    prod = reconstruct_effects(sample, nodes, production_importance=True)[0]
    assert prod.target_importance == 0.3
