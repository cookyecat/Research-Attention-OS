"""Phase17.3-KS-E deterministic shadow audit on frozen Jev v0.7."""
from pathlib import Path
import json
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.event_state_proposition_keyby import (
    PropositionFlatMapResultV01,
    SemanticKeyByDraftV01,
    _candidate_authorization_violations,
    _candidate_context_from_plan,
    _create_expansion_proposition_keys,
)
from app.services.semantic_coordinate.adjudication import (
    build_candidate_adjudication_plan,
)

ARTIFACT = ROOT / (
    "eval/live/results/phase17_jev_longitudinal_state_replay_v0_7/"
    "phase17_jev_longitudinal_state_replay_v0.7_n8_20260922T122031Z.json"
)


def slot_aliases(slots):
    ordered = sorted(slots, key=lambda row: row["slot_id"])
    return {
        row["slot_id"]: f"S{i:03d}"
        for i, row in enumerate(ordered, 1)
    }
def main():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    previous_slots = []
    rows = []

    for step in data["trajectory"]:
        flatmap = PropositionFlatMapResultV01.model_validate(
            step["proposition_flatmap"]
        )
        draft = SemanticKeyByDraftV01.model_validate(
            step["semantic_keyby"]
        )
        plan = build_candidate_adjudication_plan(
            propositions=flatmap.world_propositions,
            current_slots=previous_slots,
            top_k=2,
        )
        prop_key_by_id = {
            row.proposition_id: f"P{i:03d}"
            for i, row in enumerate(flatmap.world_propositions, 1)
        }
        context = _candidate_context_from_plan(
            plan=plan,
            proposition_key_by_id=prop_key_by_id,
            slot_key_by_id=slot_aliases(previous_slots),
            mode="SHADOW",
        )
        violations = _candidate_authorization_violations(
            draft=draft,
            candidate_slot_keys_by_proposition={
                key: set(value)
                for key, value in (
                    context.candidate_slot_keys_by_proposition.items()
                )
            },
        )
        provisional = _create_expansion_proposition_keys(
            draft=draft,
            hidden_same_family_slot_keys_by_proposition={
                key: set(value)
                for key, value in (
                    context.hidden_same_family_slot_keys_by_proposition.items()
                )
            },
        )
        existing_targets = [
            {
                "mutation_index": index,
                "slot_key": mutation.existing_slot_key,
            }
            for index, mutation in enumerate(draft.mutations)
            if mutation.target == "EXISTING"
        ]
        create_targets = [
            {
                "mutation_index": index,
                "slot_label": mutation.slot_label,
                "state_question": mutation.state_question,
            }
            for index, mutation in enumerate(draft.mutations)
            if mutation.target == "CREATE"
        ]
        rows.append({
            "ordinal": step["ordinal"],
            "title": step["title"],
            "previous_slot_count": len(previous_slots),
            "world_proposition_count": len(flatmap.world_propositions),
            "visible_candidate_slot_count": context.visible_slot_count,
            "compression_ratio": context.compression_ratio,
            "authorization_violations": list(violations),
            "provisional_create_proposition_keys": list(provisional),
            "existing_targets": existing_targets,
            "create_targets": create_targets,
            "candidate_slot_keys_by_proposition": {
                key: list(value)
                for key, value in (
                    context.candidate_slot_keys_by_proposition.items()
                )
            },
        })
        previous_slots = step["slot_state"]["slots"]

    nonzero = [row for row in rows if row["previous_slot_count"] > 0]
    result = {
        "benchmark": "phase17.3-ks-e-shadow-audit-v0.1",
        "artifact": str(ARTIFACT.relative_to(ROOT)),
        "top_k": 2,
        "observation_count": len(rows),
        "authorization_violation_count": sum(
            len(row["authorization_violations"]) for row in rows
        ),
        "observations_with_provisional_create": sum(
            bool(row["provisional_create_proposition_keys"])
            for row in rows
        ),
        "provisional_create_proposition_count": sum(
            len(row["provisional_create_proposition_keys"])
            for row in rows
        ),
        "mean_visible_slot_ratio": (
            sum(row["compression_ratio"] for row in nonzero) / len(nonzero)
            if nonzero else 1.0
        ),
        "mean_slot_count": (
            sum(row["previous_slot_count"] for row in nonzero) / len(nonzero)
            if nonzero else 0.0
        ),
        "mean_visible_candidate_slot_count": (
            sum(row["visible_candidate_slot_count"] for row in nonzero)
            / len(nonzero)
            if nonzero else 0.0
        ),
        "rows": rows,
    }
    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_e_shadow_audit_v0_1"
        / "phase17_3_ks_e_shadow_audit_v0_1.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "benchmark": result["benchmark"],
        "observation_count": result["observation_count"],
        "authorization_violation_count": result[
            "authorization_violation_count"
        ],
        "observations_with_provisional_create": result[
            "observations_with_provisional_create"
        ],
        "provisional_create_proposition_count": result[
            "provisional_create_proposition_count"
        ],
        "mean_visible_slot_ratio": round(
            result["mean_visible_slot_ratio"], 4
        ),
        "mean_slot_count": round(result["mean_slot_count"], 2),
        "mean_visible_candidate_slot_count": round(
            result["mean_visible_candidate_slot_count"], 2
        ),
        "observation_summary": [
            {
                "ordinal": row["ordinal"],
                "previous": row["previous_slot_count"],
                "visible": row["visible_candidate_slot_count"],
                "ratio": round(row["compression_ratio"], 3),
                "violations": row["authorization_violations"],
                "provisional_create": row[
                    "provisional_create_proposition_keys"
                ],
            }
            for row in rows
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
