"""Build a human-review pack for expanding KS-F semantic-address gold."""
from pathlib import Path
import json
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.semantic_coordinate.training_data import DirectAnswerDatasetV01

GOLD = (
    ROOT
    / "eval/live/fixtures/phase17_3_ks_f_direct_answer_dataset_v0_1.json"
)
TEACHER = (
    ROOT
    / "eval/live/fixtures/phase17_3_ks_f_teacher_pool_v0_2.json"
)


def review_identity(row):
    return (
        row["event_group"],
        row["primitive_family"],
        row["referent_scope"],
        row["proposition"],
        row["state_question"],
    )


def main():
    gold = DirectAnswerDatasetV01.model_validate_json(
        GOLD.read_text(encoding="utf-8")
    )
    teacher_payload = json.loads(
        TEACHER.read_text(encoding="utf-8")
    )
    teacher = DirectAnswerDatasetV01.model_validate(
        teacher_payload["dataset"]
    )
    gold_ids = {row.example_id for row in gold.examples}
    novel = [
        row for row in teacher.examples
        if row.example_id not in gold_ids
    ]

    exploratory_by_identity = {
        review_identity(row): row
        for row in gold.review_queue
    }

    items = []
    for row in novel:
        identity = (
            row.event_group,
            row.primitive_family,
            row.referent_scope,
            row.proposition,
            row.state_question,
        )
        exploratory = exploratory_by_identity.get(identity)
        boundary_case = exploratory is not None

        priority = (
            "HIGH"
            if boundary_case or row.label == "DIRECT"
            else "MEDIUM"
        )
        items.append({
            "review_id": row.example_id,
            "priority": priority,
            "event_group": row.event_group,
            "domain_group": row.domain_group,
            "ordinal": row.ordinal,
            "proposition_key": row.proposition_key,
            "slot_key": row.slot_key,
            "primitive_family": row.primitive_family,
            "referent_scope": row.referent_scope,
            "proposition": row.proposition,
            "state_question": row.state_question,
            "slot_label": row.slot_label,
            "teacher_suggestion": row.label,
            "teacher_authority": row.label_authority,
            "previously_exploratory": boundary_case,
            "boundary_note": (
                exploratory.get("note")
                if exploratory is not None
                else row.note
            ),
            "human_label": None,
            "human_rationale": None,
            "review_status": "PENDING",
        })

    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    items.sort(
        key=lambda row: (
            priority_order[row["priority"]],
            row["ordinal"] or 0,
            row["proposition_key"] or "",
            row["slot_key"] or "",
        )
    )

    json_output = (
        ROOT
        / "eval/live/fixtures/phase17_3_ks_f_human_review_pack_v0_1.json"
    )
    payload = {
        "contract": "phase17.3-ks-f-human-review-pack-v0.1",
        "status": "PENDING_REVIEW",
        "authority_rule": (
            "teacher_suggestion is advisory; only completed human_label "
            "may be promoted to HUMAN_REVIEWED gold"
        ),
        "item_count": len(items),
        "high_priority_count": sum(
            row["priority"] == "HIGH" for row in items
        ),
        "items": items,
    }
    json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md_output = (
        ROOT
        / "eval/live/fixtures/phase17_3_ks_f_human_review_pack_v0_1.md"
    )
    lines = [
        "# Phase17.3-KS-F Human Review Pack v0.1",
        "",
        "Teacher suggestions are advisory only.",
        "For each case, decide whether the proposition directly changes the exact state_question.",
        "",
    ]
    for index, row in enumerate(items, 1):
        lines.extend([
            f"## {index}. {row['priority']} — {row['review_id']}",
            "",
            f"- Event ordinal: {row['ordinal']}",
            f"- Pair: {row['proposition_key']} → {row['slot_key']}",
            f"- Primitive: {row['primitive_family']} / {row['referent_scope']}",
            f"- Teacher suggestion: **{row['teacher_suggestion']}**",
            f"- Previously exploratory: {row['previously_exploratory']}",
            f"- Boundary note: {row['boundary_note']}",
            "",
            "**Proposition**",
            "",
            f"> {row['proposition']}",
            "",
            "**State question**",
            "",
            f"> {row['state_question']}",
            "",
            "**Human review**",
            "",
            "- Label: DIRECT | NOT_DIRECT",
            "- Rationale:",
            "",
        ])
    md_output.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "review_item_count": len(items),
        "high_priority_count": payload["high_priority_count"],
        "teacher_direct_count": sum(
            row["teacher_suggestion"] == "DIRECT"
            for row in items
        ),
        "teacher_not_direct_count": sum(
            row["teacher_suggestion"] == "NOT_DIRECT"
            for row in items
        ),
        "previously_exploratory_count": sum(
            row["previously_exploratory"] for row in items
        ),
        "json": str(json_output.relative_to(ROOT)),
        "markdown": str(md_output.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
