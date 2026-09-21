from __future__ import annotations

import pytest

from app.services.benchmark_event_gold_projector import (
    BenchmarkEventGoldProjectionV01,
    project_audited_units_to_benchmark_event,
)


def _units():
    return [
        {
            "unit_id": "u1",
            "statement": "Jev is described as a decision-oriented model.",
            "epistemic_status": "SOURCE_CLAIM",
            "confidence": "HIGH",
        },
        {
            "unit_id": "u2",
            "statement": "The video channel asks viewers to subscribe.",
            "epistemic_status": "SOURCE_CLAIM",
            "confidence": "HIGH",
        },
    ]


def test_projector_is_selection_only_and_classifies_every_unit():
    def fake_chat(messages, **_kwargs):
        assert "benchmark Event-Gold semantic projector" in messages[0]["content"]
        return (
            {
                "contract": "benchmark-event-gold-semantic-projector-v0.2",
                "selections": [
                    {"unit_id": "u1", "decision": "IN_EVENT", "reason": "about Jev"},
                    {"unit_id": "u2", "decision": "OUT_OF_EVENT", "reason": "channel metadata"},
                ],
            },
            {"model": "fake"},
        )

    result = project_audited_units_to_benchmark_event(
        event_identity={
            "label": "Jev model launch / emergence and early validation episode"
        },
        audited_semantic_units=_units(),
        chat_fn=fake_chat,
    )

    assert isinstance(result, BenchmarkEventGoldProjectionV01)
    assert result.projected_unit_ids == ("u1",)


def test_projector_rejects_missing_unit_classification():
    def fake_chat(_messages, **_kwargs):
        return (
            {
                "contract": "benchmark-event-gold-semantic-projector-v0.2",
                "selections": [
                    {"unit_id": "u1", "decision": "IN_EVENT", "reason": "about Jev"}
                ],
            },
            {"model": "fake"},
        )

    with pytest.raises(ValueError, match="classify every supplied unit"):
        project_audited_units_to_benchmark_event(
            event_identity={"label": "Jev"},
            audited_semantic_units=_units(),
            chat_fn=fake_chat,
        )


def test_projector_rejects_invented_or_duplicate_unit_ids():
    def fake_chat(_messages, **_kwargs):
        return (
            {
                "contract": "benchmark-event-gold-semantic-projector-v0.2",
                "selections": [
                    {"unit_id": "u1", "decision": "IN_EVENT", "reason": "about Jev"},
                    {"unit_id": "u3", "decision": "OUT_OF_EVENT", "reason": "invented"},
                ],
            },
            {"model": "fake"},
        )

    with pytest.raises(ValueError, match="classify every supplied unit"):
        project_audited_units_to_benchmark_event(
            event_identity={"label": "Jev"},
            audited_semantic_units=_units(),
            chat_fn=fake_chat,
        )
