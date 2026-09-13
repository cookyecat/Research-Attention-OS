from app.enums import Disposition
from app.services.no_delta_awareness import (
    evaluate_no_delta_awareness,
    execution_snapshot,
)


def _diagnostics():
    return {
        "sources": [{
            "source_id": "source-1",
            "events": [{
                "event_id": "E1",
                "audited_projection": {
                    "event_id": "E1",
                    "routing_status": "ROUTABLE",
                    "rendered_event_text": "Audited event representation:\nActions / changes:\n- [OBSERVED] A consequential AI event occurred.",
                },
            }],
        }],
    }


def _d(label):
    def chat(messages, **kwargs):
        return {
            "standing_radar_fit": label,
            "substantive_anchors": ["AI"],
            "matched_clauses": ["AI clause"] if label == "IN" else [],
            "reason": "test",
        }, {"model": "fake-d"}
    return chat


def _s(label):
    def chat(messages, **kwargs):
        return {
            "material_consequence": label,
            "affected_shared_systems": ["AI ecosystem"] if label == "MATERIAL" else [],
            "material_changes": ["system changed"] if label == "MATERIAL" else [],
            "reason": "test",
        }, {"model": "fake-s"}
    return chat


def test_d_in_s_material_p_unknown_is_aware():
    out = evaluate_no_delta_awareness(
        _diagnostics(),
        d_chat_fn=_d("IN"),
        s_chat_fn=_s("MATERIAL"),
    )
    assert out.final_determined is True
    assert out.disposition == Disposition.AWARE
    assert out.awareness_signals is not None
    assert out.awareness_signals.domain_fit is True
    assert out.awareness_signals.event_significance is True
    assert out.awareness_signals.attention_momentum is None


def test_s_not_material_short_circuits_to_drop_with_p_unknown():
    out = evaluate_no_delta_awareness(
        _diagnostics(),
        d_chat_fn=_d("OUT"),
        s_chat_fn=_s("NOT_MATERIAL"),
    )
    assert out.final_determined is True
    assert out.disposition == Disposition.DROP


def test_d_out_s_material_p_unknown_remains_unresolved():
    out = evaluate_no_delta_awareness(
        _diagnostics(),
        d_chat_fn=_d("OUT"),
        s_chat_fn=_s("MATERIAL"),
    )
    assert out.applicable is True
    assert out.final_determined is False
    assert out.disposition is None


def test_execution_snapshot_binds_frozen_research_contracts():
    snap = execution_snapshot()
    assert snap["contract_version"] == "no-delta-dsp-v1"
    assert snap["d_estimator"] == "standing-radar-fit-estimator-v4"
    assert snap["s_estimator"] == "material-consequence-estimator-v1"
    assert snap["p_estimator"] == "collective-attention-estimator-v1"
    assert snap["semantic_gate"] == "AWARE iff S AND (D OR P)"
    assert snap["p_from_article_text"] is False


def test_p_counterfactual_does_not_change_in_material_case():
    from eval.live.no_delta_awareness_integration_v1_1 import determine_gate_disposition

    for p in (None, "SALIENT", "NOT_SALIENT"):
        out = determine_gate_disposition("IN", "MATERIAL", p)
        assert out == Disposition.AWARE


def test_awareness_trace_roundtrip_preserves_unknown_p():
    from app.services.no_delta_awareness import awareness_signals_from_trace

    out = evaluate_no_delta_awareness(
        _diagnostics(), d_chat_fn=_d("IN"), s_chat_fn=_s("MATERIAL")
    )
    signals = awareness_signals_from_trace(out.trace)
    assert signals is not None
    assert signals.domain_fit is True
    assert signals.event_significance is True
    assert signals.attention_momentum is None
