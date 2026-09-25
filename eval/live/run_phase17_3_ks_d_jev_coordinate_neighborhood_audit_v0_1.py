"""Phase17.3-KS-D Jev semantic-coordinate neighborhood audit v0.1.

Uses frozen historical Jev EventState artifacts. The audit asks whether the
retrieval layer surfaces historically duplicated or near-duplicate coordinates
before any schema mutation is considered.
"""
from pathlib import Path
import json
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.semantic_coordinate.models import SemanticCoordinate
from app.services.semantic_coordinate.retrieval import InMemoryCoordinateIndex


ARTIFACTS = {
    "keyby_n8": ROOT / (
        "eval/live/results/phase17_jev_proposition_keyby_replay_v0_1/"
        "phase17_jev_proposition_keyby_replay_v0.1_n8_20260922T080713Z.json"
    ),
    "longitudinal_v07_n8": ROOT / (
        "eval/live/results/phase17_jev_longitudinal_state_replay_v0_7/"
        "phase17_jev_longitudinal_state_replay_v0.7_n8_20260922T122031Z.json"
    ),
}

EXPECTED_NEIGHBORS = {
    "keyby_n8": [
        ("Open-source release status", "Release status"),
    ],
    "longitudinal_v07_n8": [
        ("Task completion time", "Operational performance characteristics"),
        ("Intended deployment context", "Real-time suitability"),
    ],
}
def load_coordinates(path: Path):
    obj = json.loads(path.read_text(encoding="utf-8"))
    slots = (
        (obj.get("summary") or {})
        .get("final_slot_state", {})
        .get("slots", [])
    )
    coordinates = []
    slot_by_coordinate = {}
    for slot in slots:
        coordinate = SemanticCoordinate(
            primitive_family=slot["primitive_family"],
            state_question=slot["state_question"],
            coordinate_label=slot.get("slot_label"),
            domain_hints=("Jev",),
        )
        coordinates.append(coordinate)
        slot_by_coordinate[coordinate.coordinate_id] = {
            "slot_id": slot.get("slot_id"),
            "slot_label": slot.get("slot_label"),
            "primitive_family": slot.get("primitive_family"),
            "state_question": slot.get("state_question"),
        }
    return coordinates, slot_by_coordinate


def pair_key(a: str, b: str):
    return tuple(sorted((a, b)))


def audit_artifact(name: str, path: Path):
    coordinates, slot_by_coordinate = load_coordinates(path)
    index = InMemoryCoordinateIndex()
    index.rebuild(coordinates)

    directional = {}
    neighbor_rows = []
    max_k = max(len(coordinates) - 1, 1)
    for query in coordinates:
        rows = index.retrieve(query, top_k=max_k)
        same_family = [
            row for row in rows
            if row.coordinate.primitive_family == query.primitive_family
        ]
        for rank, row in enumerate(same_family, start=1):
            key = pair_key(query.coordinate_id, row.coordinate.coordinate_id)
            directional.setdefault(key, []).append(row.semantic_similarity)
            neighbor_rows.append({
                "query_label": query.coordinate_label,
                "query_family": query.primitive_family,
                "candidate_label": row.coordinate.coordinate_label,
                "rank_within_family": rank,
                "similarity": row.semantic_similarity,
            })
    pairs = []
    for (left_id, right_id), scores in directional.items():
        left = slot_by_coordinate[left_id]
        right = slot_by_coordinate[right_id]
        pairs.append({
            "family": left["primitive_family"],
            "left_label": left["slot_label"],
            "right_label": right["slot_label"],
            "left_question": left["state_question"],
            "right_question": right["state_question"],
            "directional_scores": scores,
            "mean_similarity": sum(scores) / len(scores),
            "min_similarity": min(scores),
        })
    pairs.sort(
        key=lambda row: (
            -row["mean_similarity"],
            row["family"],
            row["left_label"] or "",
            row["right_label"] or "",
        )
    )

    expected = []
    for left_label, right_label in EXPECTED_NEIGHBORS.get(name, []):
        matching = next(
            (
                row for row in pairs
                if {row["left_label"], row["right_label"]}
                == {left_label, right_label}
            ),
            None,
        )
        family_rows = [
            row for row in pairs
            if matching is not None and row["family"] == matching["family"]
        ]
        rank = (
            family_rows.index(matching) + 1
            if matching is not None and matching in family_rows
            else None
        )
        expected.append({
            "labels": [left_label, right_label],
            "found": matching is not None,
            "family_rank": rank,
            "mean_similarity": (
                matching["mean_similarity"] if matching else None
            ),
        })

    return {
        "artifact": str(path.relative_to(ROOT)),
        "slot_count": len(coordinates),
        "embedding_model": index.embedding_model,
        "expected_neighbor_checks": expected,
        "top_pairs": pairs[:20],
        "neighbors": neighbor_rows,
    }
def main():
    audits = [
        audit_artifact(name, path)
        for name, path in ARTIFACTS.items()
    ]
    checks = [
        check
        for audit in audits
        for check in audit["expected_neighbor_checks"]
    ]
    result = {
        "benchmark": "phase17.3-ks-d-jev-coordinate-neighborhood-audit-v0.1",
        "status": "PASS" if all(
            check["found"] and check["family_rank"] <= 2
            for check in checks
        ) else "REVIEW",
        "schema_mutation_performed": False,
        "expected_check_count": len(checks),
        "expected_top1_count": sum(
            bool(check["found"] and check["family_rank"] == 1)
            for check in checks
        ),
        "expected_recall_at_2_count": sum(
            bool(check["found"] and check["family_rank"] <= 2)
            for check in checks
        ),
        "audits": audits,
    }

    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_d_jev_coordinate_neighborhood_audit_v0_1"
        / "phase17_3_ks_d_jev_coordinate_neighborhood_audit_v0_1.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    compact = {
        "benchmark": result["benchmark"],
        "status": result["status"],
        "expected_check_count": result["expected_check_count"],
        "expected_top1_count": result["expected_top1_count"],
        "expected_recall_at_2_count": result["expected_recall_at_2_count"],
        "audits": [
            {
                "artifact": audit["artifact"],
                "slot_count": audit["slot_count"],
                "embedding_model": audit["embedding_model"],
                "expected": audit["expected_neighbor_checks"],
                "top5_pairs": [
                    {
                        "family": row["family"],
                        "left": row["left_label"],
                        "right": row["right_label"],
                        "mean_similarity": round(row["mean_similarity"], 4),
                    }
                    for row in audit["top_pairs"][:5]
                ],
            }
            for audit in audits
        ],
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
