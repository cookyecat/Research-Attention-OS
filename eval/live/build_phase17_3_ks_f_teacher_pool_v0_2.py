"""Extend KS-F teacher pool with CREATE-group semantic cross-check pairs."""
from pathlib import Path
import json
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.semantic_coordinate.training_data import (
    DirectAnswerDatasetV01,
    DirectAnswerTrainingExampleV01,
)

V01 = (
    ROOT
    / "eval/live/fixtures/phase17_3_ks_f_teacher_pool_v0_1.json"
)
GOLD = (
    ROOT
    / "eval/live/fixtures/phase17_3_ks_f_direct_answer_dataset_v0_1.json"
)
JEV = (
    ROOT
    / "eval/live/results/phase17_jev_longitudinal_state_replay_v0_7/"
    / "phase17_jev_longitudinal_state_replay_v0.7_n8_20260922T122031Z.json"
)
CROSSCHECK = (
    ROOT
    / "eval/live/results/phase17_3_ks_e_create_group_crosscheck_v0_1/"
    / "phase17_3_ks_e_create_group_crosscheck_v0_1.json"
)

EVENT_GROUP = "jev-model-launch-early-validation-2026-09-16_20"
DOMAIN_GROUP = "ai-model-launch-and-agent-evaluation"
SPLIT_GROUP = f"event:{EVENT_GROUP}"

CREATE_GROUPS = {
    "NEW_RELATION_INTEGRATION": {
        "slot_label": "External integration and deployment context",
        "state_question": (
            "In what external systems or workflows is this system "
            "integrated or deployed?"
        ),
    },
    "NEW_RELATION_RESEMBLANCE": {
        "slot_label": "System composition resemblance",
        "state_question": (
            "What broader system pattern does this system's "
            "composition resemble?"
        ),
    },
}


def main():
    existing_payload = json.loads(V01.read_text(encoding="utf-8"))
    existing = DirectAnswerDatasetV01.model_validate(
        existing_payload["dataset"]
    )
    gold = DirectAnswerDatasetV01.model_validate_json(
        GOLD.read_text(encoding="utf-8")
    )
    gold_by_id = {row.example_id: row for row in gold.examples}

    jev = json.loads(JEV.read_text(encoding="utf-8"))
    step = next(
        row for row in jev["trajectory"]
        if row["ordinal"] == 8
    )
    propositions = {
        f"P{i:03d}": row
        for i, row in enumerate(
            step["proposition_flatmap"]["world_propositions"],
            1,
        )
    }

    crosscheck = json.loads(CROSSCHECK.read_text(encoding="utf-8"))
    by_id = {row.example_id: row for row in existing.examples}

    added = []
    for item in crosscheck["results"]:
        pkey, synthetic_slot_key = item["pair"].split("->", 1)
        decision = item["decision"]
        if decision not in {"DIRECT", "NOT_DIRECT"}:
            continue

        proposition = propositions[pkey]
        group = CREATE_GROUPS[synthetic_slot_key]
        example = DirectAnswerTrainingExampleV01(
            event_group=EVENT_GROUP,
            domain_group=DOMAIN_GROUP,
            split_group=SPLIT_GROUP,
            ordinal=8,
            proposition_key=pkey,
            slot_key=synthetic_slot_key,
            proposition=proposition["statement"],
            primitive_family=proposition["primitive_family"],
            referent_scope=proposition["referent_scope"],
            state_question=group["state_question"],
            slot_label=group["slot_label"],
            label=decision,
            label_authority="LLM_CONSENSUS",
            hard_negative=decision == "NOT_DIRECT",
            note=(
                "CREATE-group two-judgment Direct-Answer cross-check "
                "from KS-E"
            ),
            provenance_artifact=str(
                CROSSCHECK.relative_to(ROOT)
            ),
            source_contract="semantic-coordinate-direct-answer-v0.1",
        )
        if example.example_id not in by_id:
            by_id[example.example_id] = example
            added.append(example)

    teacher_examples = tuple(
        sorted(by_id.values(), key=lambda row: row.example_id)
    )
    dataset = DirectAnswerDatasetV01(
        dataset_id="phase17.3-ks-f-teacher-pool-v0.2",
        status="DEVELOPMENT_ONLY",
        examples=teacher_examples,
    )

    overlap = []
    for row in dataset.examples:
        human = gold_by_id.get(row.example_id)
        if human is not None:
            overlap.append({
                "example_id": row.example_id,
                "teacher_label": row.label,
                "human_label": human.label,
                "agree": row.label == human.label,
            })

    novel = [
        row for row in dataset.examples
        if row.example_id not in gold_by_id
    ]
    output = (
        ROOT
        / "eval/live/fixtures/phase17_3_ks_f_teacher_pool_v0_2.json"
    )
    output.write_text(
        json.dumps(
            {
                "dataset": dataset.model_dump(mode="json"),
                "novel_teacher_example_ids": [
                    row.example_id for row in novel
                ],
                "human_overlap": overlap,
                "added_from_create_group_crosscheck": [
                    row.example_id for row in added
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    def counts(rows):
        result = {"DIRECT": 0, "NOT_DIRECT": 0}
        for row in rows:
            result[row.label] += 1
        return result

    print(json.dumps({
        "teacher_example_count": len(dataset.examples),
        "teacher_label_counts": dataset.label_counts(),
        "novel_teacher_example_count": len(novel),
        "novel_teacher_label_counts": counts(novel),
        "added_crosscheck_count": len(added),
        "added_crosscheck_label_counts": counts(added),
        "human_overlap_count": len(overlap),
        "human_overlap_agreement_count": sum(
            row["agree"] for row in overlap
        ),
        "fixture": str(output.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
