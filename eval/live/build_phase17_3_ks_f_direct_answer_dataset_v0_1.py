"""Build Phase17.3-KS-F reviewed Direct-Answer dataset v0.1."""
from pathlib import Path
import json
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from app.services.semantic_coordinate.training_data import (
    DirectAnswerDatasetV01,
    DirectAnswerTrainingExampleV01,
)
import eval.live.run_phase17_3_ks_e_pairwise_direct_answer_benchmark_v0_9 as base

DATASET_ID = "phase17.3-ks-f-direct-answer-v0.1"
EVENT_GROUP = "jev-model-launch-early-validation-2026-09-16_20"
DOMAIN_GROUP = "ai-model-launch-and-agent-evaluation"
SPLIT_GROUP = f"event:{EVENT_GROUP}"


def build_reviewed_example(data, spec):
    ordinal, pkey, skey, expected, note = spec
    proposition = base.propositions_for(data, ordinal)[pkey]
    slot = base.previous_slots_for(data, ordinal)[skey]
    return DirectAnswerTrainingExampleV01(
        event_group=EVENT_GROUP,
        domain_group=DOMAIN_GROUP,
        split_group=SPLIT_GROUP,
        ordinal=ordinal,
        proposition_key=pkey,
        slot_key=skey,
        proposition=proposition["statement"],
        primitive_family=proposition["primitive_family"],
        referent_scope=proposition["referent_scope"],
        state_question=slot["state_question"],
        slot_label=slot.get("slot_label"),
        label=expected,
        label_authority="HUMAN_REVIEWED",
        hard_negative=expected == "NOT_DIRECT",
        note=note,
        provenance_artifact=str(base.ARTIFACT.relative_to(ROOT)),
        source_contract=(
            data["trajectory"][ordinal - 1]["proposition_flatmap"].get(
                "contract"
            )
        ),
    )


def build_review_item(data, spec):
    ordinal, pkey, skey, _expected, note = spec
    proposition = base.propositions_for(data, ordinal)[pkey]
    slot = base.previous_slots_for(data, ordinal)[skey]
    return {
        "event_group": EVENT_GROUP,
        "domain_group": DOMAIN_GROUP,
        "split_group": SPLIT_GROUP,
        "ordinal": ordinal,
        "proposition_key": pkey,
        "slot_key": skey,
        "proposition": proposition["statement"],
        "primitive_family": proposition["primitive_family"],
        "referent_scope": proposition["referent_scope"],
        "state_question": slot["state_question"],
        "slot_label": slot.get("slot_label"),
        "note": note,
        "provenance_artifact": str(base.ARTIFACT.relative_to(ROOT)),
        "review_status": "UNREVIEWED",
    }


def main():
    data = json.loads(base.ARTIFACT.read_text(encoding="utf-8"))
    examples = tuple(
        build_reviewed_example(data, spec)
        for spec in base.STRICT_CASES
    )
    review_queue = tuple(
        build_review_item(data, spec)
        for spec in base.EXPLORATORY_CASES
    )
    dataset = DirectAnswerDatasetV01(
        dataset_id=DATASET_ID,
        status="DEVELOPMENT_ONLY",
        examples=examples,
        review_queue=review_queue,
    )

    fixture = (
        ROOT
        / "eval/live/fixtures/phase17_3_ks_f_direct_answer_dataset_v0_1.json"
    )
    fixture.write_text(
        json.dumps(
            dataset.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    jsonl = (
        ROOT
        / "eval/live/fixtures/phase17_3_ks_f_direct_answer_dataset_v0_1.jsonl"
    )
    with jsonl.open("w", encoding="utf-8") as handle:
        for row in dataset.examples:
            handle.write(
                json.dumps(
                    row.model_dump(mode="json"),
                    ensure_ascii=False,
                )
                + "\n"
            )

    result = {
        "dataset_id": dataset.dataset_id,
        "status": dataset.status,
        "example_count": len(dataset.examples),
        "label_counts": dataset.label_counts(),
        "authority_counts": dataset.authority_counts(),
        "hard_negative_count": sum(
            row.hard_negative for row in dataset.examples
        ),
        "event_groups": dataset.event_groups(),
        "review_queue_count": len(dataset.review_queue),
        "fixture": str(fixture.relative_to(ROOT)),
        "jsonl": str(jsonl.relative_to(ROOT)),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
