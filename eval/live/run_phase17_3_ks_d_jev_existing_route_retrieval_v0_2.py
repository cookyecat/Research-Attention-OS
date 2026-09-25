"""Phase17.3-KS-D Jev EXISTING-route retrieval benchmark v0.2.

Gold labels are recovered automatically from a frozen historical KeyBy run:
WorldProposition -> proposition_route -> EXISTING mutation -> previous slot.
No manual semantic gold is introduced.
"""
from pathlib import Path
import json
import re
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.semantic_coordinate.models import (
    CoordinateRetrievalQuery,
    SemanticCoordinate,
)
from app.services.semantic_coordinate.retrieval import InMemoryCoordinateIndex


ARTIFACT = ROOT / (
    "eval/live/results/phase17_jev_longitudinal_state_replay_v0_7/"
    "phase17_jev_longitudinal_state_replay_v0.7_n8_20260922T122031Z.json"
)


def coordinate_from_slot(slot):
    return SemanticCoordinate(
        primitive_family=slot["primitive_family"],
        state_question=slot["state_question"],
        coordinate_label=slot.get("slot_label"),
        domain_hints=("Jev",),
    )


def proposition_index(key: str) -> int:
    match = re.fullmatch(r"P(\d+)", key or "")
    if not match:
        raise ValueError(f"unexpected proposition key: {key}")
    return int(match.group(1)) - 1
def previous_slot_aliases(slots):
    ordered = sorted(slots, key=lambda row: row["slot_id"])
    return {
        f"S{i:03d}": slot
        for i, slot in enumerate(ordered, 1)
    }


def main():
    obj = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    trajectory = obj["trajectory"]
    cases = []
    create_routes = []

    previous_slots = []
    for step_index, step in enumerate(trajectory):
        alias_to_slot = previous_slot_aliases(previous_slots)
        coordinates = [coordinate_from_slot(slot) for slot in previous_slots]
        coordinate_to_slot = {
            coordinate.coordinate_id: slot
            for coordinate, slot in zip(coordinates, previous_slots)
        }

        index = InMemoryCoordinateIndex()
        index.rebuild(coordinates)

        propositions = (step.get("proposition_flatmap") or {}).get("world_propositions") or []
        draft = step.get("semantic_keyby") or {}
        mutations = draft.get("mutations") or []
        routes = draft.get("proposition_routes") or []

        for route in routes:
            if route.get("disposition") != "WORLD_MUTATION":
                continue
            pidx = proposition_index(route["proposition_key"])
            if pidx >= len(propositions):
                raise ValueError(
                    f"{route['proposition_key']} outside proposition list"
                )
            proposition = propositions[pidx]
            query = CoordinateRetrievalQuery(
                primitive_family=proposition["primitive_family"],
                text=proposition["statement"],
            )

            target_mutations = [
                mutations[idx]
                for idx in route.get("mutation_indices") or []
            ]
            existing_targets = [
                mutation
                for mutation in target_mutations
                if mutation.get("target") == "EXISTING"
            ]
            create_targets = [
                mutation
                for mutation in target_mutations
                if mutation.get("target") == "CREATE"
            ]

            same_family_count = sum(
                slot.get("primitive_family") == query.primitive_family
                for slot in previous_slots
            )
            ranked = index.retrieve(
                query,
                top_k=max(same_family_count, 1),
            ) if coordinates else []
            ranked_ids = [
                row.coordinate.coordinate_id
                for row in ranked
            ]

            for mutation in existing_targets:
                alias = mutation.get("existing_slot_key")
                gold_slot = alias_to_slot.get(alias)
                if gold_slot is None:
                    raise ValueError(
                        f"missing previous slot alias {alias} at step {step_index + 1}"
                    )
                gold_coordinate = coordinate_from_slot(gold_slot)
                try:
                    rank = ranked_ids.index(gold_coordinate.coordinate_id) + 1
                except ValueError:
                    rank = None
                cases.append({
                    "ordinal": step.get("ordinal"),
                    "title": step.get("title"),
                    "proposition_key": route["proposition_key"],
                    "proposition": proposition["statement"],
                    "primitive_family": proposition["primitive_family"],
                    "previous_slot_count": len(previous_slots),
                    "same_family_candidate_count": same_family_count,
                    "gold_slot_id": gold_slot["slot_id"],
                    "gold_slot_label": gold_slot.get("slot_label"),
                    "gold_state_question": gold_slot.get("state_question"),
                    "gold_rank": rank,
                    "top_candidates": [
                        {
                            "slot_id": coordinate_to_slot[
                                row.coordinate.coordinate_id
                            ]["slot_id"],
                            "slot_label": row.coordinate.coordinate_label,
                            "state_question": row.coordinate.state_question,
                            "similarity": row.semantic_similarity,
                        }
                        for row in ranked[:5]
                    ],
                })
            for mutation in create_targets:
                create_routes.append({
                    "ordinal": step.get("ordinal"),
                    "title": step.get("title"),
                    "proposition_key": route["proposition_key"],
                    "proposition": proposition["statement"],
                    "primitive_family": proposition["primitive_family"],
                    "created_slot_label": mutation.get("slot_label"),
                    "created_state_question": mutation.get("state_question"),
                    "same_family_candidate_count": same_family_count,
                    "nearest_existing": (
                        {
                            "slot_label": ranked[0].coordinate.coordinate_label,
                            "state_question": ranked[0].coordinate.state_question,
                            "similarity": ranked[0].semantic_similarity,
                        }
                        if ranked else None
                    ),
                })

        previous_slots = (
            (step.get("slot_state") or {}).get("slots") or previous_slots
        )

    if not cases:
        raise RuntimeError("benchmark recovered no EXISTING route cases")

    nontrivial = [
        case for case in cases
        if case["same_family_candidate_count"] >= 2
    ]

    def recall(rows, k):
        return (
            sum(
                case["gold_rank"] is not None
                and case["gold_rank"] <= k
                for case in rows
            ) / len(rows)
            if rows else None
        )

    result = {
        "benchmark": "phase17.3-ks-d-jev-existing-route-retrieval-v0.2",
        "artifact": str(ARTIFACT.relative_to(ROOT)),
        "existing_route_case_count": len(cases),
        "nontrivial_case_count": len(nontrivial),
        "recall_at_1": recall(cases, 1),
        "recall_at_2": recall(cases, 2),
        "recall_at_3": recall(cases, 3),
        "nontrivial_recall_at_1": recall(nontrivial, 1),
        "nontrivial_recall_at_2": recall(nontrivial, 2),
        "nontrivial_recall_at_3": recall(nontrivial, 3),
        "mean_reciprocal_rank": sum(
            1.0 / case["gold_rank"]
            for case in cases
            if case["gold_rank"] is not None
        ) / len(cases),
        "create_route_count": len(create_routes),
        "schema_mutation_performed": False,
        "cases": cases,
        "create_route_diagnostics": create_routes,
    }
    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_d_jev_existing_route_retrieval_v0_2"
        / "phase17_3_ks_d_jev_existing_route_retrieval_v0_2.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps({
        "benchmark": result["benchmark"],
        "existing_route_case_count": result["existing_route_case_count"],
        "nontrivial_case_count": result["nontrivial_case_count"],
        "recall_at_1": result["recall_at_1"],
        "recall_at_2": result["recall_at_2"],
        "recall_at_3": result["recall_at_3"],
        "nontrivial_recall_at_1": result["nontrivial_recall_at_1"],
        "nontrivial_recall_at_2": result["nontrivial_recall_at_2"],
        "nontrivial_recall_at_3": result["nontrivial_recall_at_3"],
        "mean_reciprocal_rank": round(result["mean_reciprocal_rank"], 4),
        "create_route_count": result["create_route_count"],
        "failures": [
            {
                "ordinal": case["ordinal"],
                "proposition_key": case["proposition_key"],
                "family": case["primitive_family"],
                "gold": case["gold_slot_label"],
                "rank": case["gold_rank"],
                "top": (
                    case["top_candidates"][0]["slot_label"]
                    if case["top_candidates"] else None
                ),
            }
            for case in cases
            if case["gold_rank"] != 1
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
