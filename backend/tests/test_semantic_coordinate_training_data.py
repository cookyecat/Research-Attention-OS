import pytest

from app.services.semantic_coordinate.training_data import (
    DirectAnswerDatasetV01,
    DirectAnswerTrainingExampleV01,
)


def _example(**updates):
    payload = {
        "event_group": "jev-early-validation",
        "domain_group": "ai-model-evaluation",
        "split_group": "event:jev-early-validation",
        "ordinal": 5,
        "proposition_key": "P003",
        "slot_key": "S009",
        "proposition": "Jev generates decisions faster in the demo.",
        "primitive_family": "QUALITY",
        "referent_scope": "TARGET_INTRINSIC",
        "state_question": (
            "What operational performance characteristics does this system have?"
        ),
        "slot_label": "Operational performance",
        "label": "DIRECT",
        "label_authority": "HUMAN_REVIEWED",
        "hard_negative": False,
        "note": "concrete observed performance -> performance coordinate",
        "provenance_artifact": "eval/live/results/example.json",
        "source_contract": "event-world-proposition-flatmap-v0.7",
    }
    payload.update(updates)
    return DirectAnswerTrainingExampleV01(**payload)


def test_training_example_id_is_stable_and_semantic():
    first = _example()
    second = _example(
        proposition="  Jev   generates decisions faster in the demo. "
    )
    assert first.example_id == second.example_id
    assert first.proposition == "Jev generates decisions faster in the demo."


def test_training_example_rejects_referent_scope_mismatch():
    with pytest.raises(ValueError, match="referent_scope"):
        _example(referent_scope="TARGET_RELATION")


def test_direct_example_cannot_be_hard_negative():
    with pytest.raises(ValueError, match="hard_negative"):
        _example(hard_negative=True)


def test_dataset_reports_authority_and_label_counts():
    direct = _example()
    negative = _example(
        event_group="jev-early-validation",
        ordinal=8,
        proposition_key="P004",
        slot_key="S009",
        proposition="Jev is designed as a decision model.",
        state_question=(
            "What capabilities or behaviors has this system demonstrated?"
        ),
        slot_label="Demonstrated capabilities",
        label="NOT_DIRECT",
        hard_negative=True,
        note="designed != demonstrated",
    )
    dataset = DirectAnswerDatasetV01(
        dataset_id="phase17.3-ks-f-direct-answer-v0.1",
        status="DEVELOPMENT_ONLY",
        examples=(direct, negative),
    )
    assert dataset.label_counts() == {
        "DIRECT": 1,
        "NOT_DIRECT": 1,
    }
    assert dataset.authority_counts() == {"HUMAN_REVIEWED": 2}
    assert dataset.event_groups() == ("jev-early-validation",)


def test_dataset_rejects_duplicate_semantic_pair():
    example = _example()
    with pytest.raises(ValueError, match="duplicate"):
        DirectAnswerDatasetV01(
            dataset_id="duplicate",
            status="DEVELOPMENT_ONLY",
            examples=(example, example),
        )
