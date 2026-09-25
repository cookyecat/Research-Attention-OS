"""Export LLM-consensus Direct-Answer teacher pairs for KS-F distillation."""
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

GOLD_FIXTURE = (
    ROOT
    / "eval/live/fixtures/phase17_3_ks_f_direct_answer_dataset_v0_1.json"
)
LOCKED_RESULT = (
    ROOT
    / "eval/live/results/phase17_3_ks_e_address_locked_comparison_v0_6/"
    / "phase17_3_ks_e_address_locked_comparison_v0_6.json"
)
JEV_ARTIFACT = (
    ROOT
    / "eval/live/results/phase17_jev_longitudinal_state_replay_v0_7/"
    / "phase17_jev_longitudinal_state_replay_v0.7_n8_20260922T122031Z.json"
)

EVENT_GROUP = "jev-model-launch-early-validation-2026-09-16_20"
DOMAIN_GROUP = "ai-model-launch-and-agent-evaluation"
SPLIT_GROUP = f"event:{EVENT_GROUP}"


def previous_slot_maps(trajectory, step_index):
    if step_index == 0:
        return {}, {}
    slots = sorted(
        trajectory[step_index - 1]["slot_state"]["slots"],
        key=lambda row: row["slot_id"],
    )
    by_id = {row["slot_id"]: row for row in slots}
    key_by_id = {
        row["slot_id"]: f"S{i:03d}"
        for i, row in enumerate(slots, 1)
    }
    return by_id, key_by_id


def proposition_maps(step):
    props = step["proposition_flatmap"]["world_propositions"]
    by_id = {row["proposition_id"]: row for row in props}
    key_by_id = {
        row["proposition_id"]: f"P{i:03d}"
        for i, row in enumerate(props, 1)
    }
    return by_id, key_by_id


def main():
    gold = DirectAnswerDatasetV01.model_validate_json(
        GOLD_FIXTURE.read_text(encoding="utf-8")
    )
    gold_by_id = {row.example_id: row for row in gold.examples}

    locked = json.loads(LOCKED_RESULT.read_text(encoding="utf-8"))
    jev = json.loads(JEV_ARTIFACT.read_text(encoding="utf-8"))
    trajectory = jev["trajectory"]
    step_by_ordinal = {
        row["ordinal"]: (index, row)
        for index, row in enumerate(trajectory)
    }

    teacher_by_id = {}
    overlap = []

    for locked_row in locked["rows"]:
        if locked_row["status"] != "PASS":
            continue
        ordinal = locked_row["ordinal"]
        step_index, step = step_by_ordinal[ordinal]
        prop_by_id, prop_key_by_id = proposition_maps(step)
        slot_by_id, slot_key_by_id = previous_slot_maps(
            trajectory,
            step_index,
        )

        for proposition_plan in locked_row["pairwise_plan"]["propositions"]:
            proposition_id = proposition_plan["proposition_id"]
            proposition = prop_by_id[proposition_id]
            proposition_key = prop_key_by_id[proposition_id]

            for judgment in proposition_plan["consensus_judgments"]:
                decision = judgment["decision"]
                if decision not in {"DIRECT", "NOT_DIRECT"}:
                    continue
                slot_id = judgment["slot_id"]
                slot = slot_by_id[slot_id]
                slot_key = slot_key_by_id[slot_id]

                example = DirectAnswerTrainingExampleV01(
                    event_group=EVENT_GROUP,
                    domain_group=DOMAIN_GROUP,
                    split_group=SPLIT_GROUP,
                    ordinal=ordinal,
                    proposition_key=proposition_key,
                    slot_key=slot_key,
                    proposition=proposition["statement"],
                    primitive_family=proposition["primitive_family"],
                    referent_scope=proposition["referent_scope"],
                    state_question=slot["state_question"],
                    slot_label=slot.get("slot_label"),
                    label=decision,
                    label_authority="LLM_CONSENSUS",
                    hard_negative=decision == "NOT_DIRECT",
                    note=(
                        "two-judgment Direct-Answer consensus from "
                        "Address-Locked v0.6"
                    ),
                    provenance_artifact=str(
                        LOCKED_RESULT.relative_to(ROOT)
                    ),
                    source_contract=judgment.get("contract"),
                )
                teacher_by_id[example.example_id] = example

    for example_id, teacher in teacher_by_id.items():
        human = gold_by_id.get(example_id)
        if human is None:
            continue
        overlap.append({
            "example_id": example_id,
            "human_label": human.label,
            "teacher_label": teacher.label,
            "agree": human.label == teacher.label,
            "ordinal": human.ordinal,
            "proposition_key": human.proposition_key,
            "slot_key": human.slot_key,
            "note": human.note,
        })

    teacher_examples = tuple(
        sorted(
            teacher_by_id.values(),
            key=lambda row: row.example_id,
        )
    )
    novel_examples = tuple(
        row
        for row in teacher_examples
        if row.example_id not in gold_by_id
    )

    teacher_dataset = DirectAnswerDatasetV01(
        dataset_id="phase17.3-ks-f-teacher-pool-v0.1",
        status="DEVELOPMENT_ONLY",
        examples=teacher_examples,
    )

    output = (
        ROOT
        / "eval/live/fixtures/phase17_3_ks_f_teacher_pool_v0_1.json"
    )
    payload = {
        "dataset": teacher_dataset.model_dump(mode="json"),
        "novel_teacher_example_ids": [
            row.example_id for row in novel_examples
        ],
        "human_overlap": overlap,
        "source_address_locked_result": str(
            LOCKED_RESULT.relative_to(ROOT)
        ),
    }
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = {
        "teacher_example_count": len(teacher_examples),
        "novel_teacher_example_count": len(novel_examples),
        "label_counts": teacher_dataset.label_counts(),
        "human_overlap_count": len(overlap),
        "human_overlap_agreement_count": sum(
            row["agree"] for row in overlap
        ),
        "human_overlap_accuracy": (
            sum(row["agree"] for row in overlap) / len(overlap)
            if overlap else None
        ),
        "fixture": str(output.relative_to(ROOT)),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
