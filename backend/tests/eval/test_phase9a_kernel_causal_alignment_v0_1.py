from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment
from eval.live.phase9a_kernel_causal_alignment_v0_1 import (
    ASSIMILATED_PROPOSITION,
    TARGET_CODE,
    bind_kernel_importance,
    fixture_code,
    materialize_rs05_arm,
)


def _target(arm):
    return next(node for node in arm.nodes if fixture_code(node) == TARGET_CODE)


def test_phase9a_materializes_isolated_kernel_versions_through_production_patch_path():
    k0 = materialize_rs05_arm("K0")
    k1s = materialize_rs05_arm("K1-S")
    k1i = materialize_rs05_arm("K1-I")
    t0, ts, ti = _target(k0), _target(k1s), _target(k1i)
    assert t0.id == ts.id == ti.id
    assert t0.current_version == 1
    assert ts.current_version == ti.current_version == 2
    assert len(k0.target_versions) == 1
    assert len(k1s.target_versions) == len(k1i.target_versions) == 2
    assert ts.title == ASSIMILATED_PROPOSITION
    assert ts.payload["proposition"] == ASSIMILATED_PROPOSITION
    assert ts.payload["importance"] == 0.9
    assert ti.title == t0.title
    assert ti.payload["proposition"] == t0.payload["proposition"]
    assert ti.payload["importance"] == 0.2
    assert k1s.patch and "ACCEPTED" in k1s.patch["status"]
    assert k1i.patch and "ACCEPTED" in k1i.patch["status"]


def test_phase9a_binds_explicit_kernel_importance_over_llm_estimate():
    arm = materialize_rs05_arm("K1-I")
    target = _target(arm)
    assessment = CognitiveImpactAssessment(
        effects=[
            CognitiveEffect(
                target_kernel_node_id=target.id,
                operation=CognitiveEffectKind.CHALLENGE,
                change_magnitude=0.9,
                epistemic_strength=0.9,
                target_importance=0.95,
                reason="test",
                target_node_type="BELIEF",
            ),
            CognitiveEffect(
                target_kernel_node_id=None,
                operation=CognitiveEffectKind.OPEN_NEW,
                change_magnitude=0.6,
                epistemic_strength=0.7,
                target_importance=0.33,
                reason="open",
            ),
        ]
    )
    rebound = bind_kernel_importance(assessment, arm.nodes)
    assert rebound.effects[0].target_importance == 0.2
    assert rebound.effects[1].target_importance == 0.33
