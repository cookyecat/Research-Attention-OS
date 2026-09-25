"""Phase17.3-KS coordinate proposal contract verification v0.2."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.semantic_coordinate.proposal import propose_coordinate
from app.services.semantic_coordinate.registry import SemanticCoordinateRegistry


def main():
    registry = SemanticCoordinateRegistry()
    samples = [
        dict(
            proposition="Jev inference latency improved.",
            primitive_family="QUALITY",
            state_question="What is the operational latency?",
            coordinate_label="operational latency",
            domain_hints=("AI models",),
        ),
        dict(
            proposition="A robot controller has lower response latency.",
            primitive_family="QUALITY",
            state_question="What is the operational latency?",
            coordinate_label="operational latency",
            domain_hints=("robotics",),
        ),
        dict(
            proposition="API usage cost fell.",
            primitive_family="QUALITY",
            state_question="What is the operational cost?",
            coordinate_label="operational cost",
            domain_hints=("AI models",),
        ),
    ]

    proposed = []
    for sample in samples:
        proposal = propose_coordinate(**sample)
        coordinate = proposal.candidates[0]
        registry.register(coordinate)
        proposed.append(coordinate.model_dump(mode="json"))

    registered = [
        coordinate.model_dump(mode="json")
        for coordinate in registry.all()
    ]
    latency_id = proposed[0]["coordinate_id"]
    merged_latency = registry.get(latency_id)
    result = {
        "status": "PASS",
        "proposal_count": len(proposed),
        "unique_coordinate_count": len(registry),
        "cross_domain_same_question_reused_id": (
            proposed[0]["coordinate_id"] == proposed[1]["coordinate_id"]
        ),
        "cross_domain_hints_merged": (
            merged_latency.domain_hints == ("AI models", "robotics")
        ),
        "proposals": proposed,
        "registered_coordinates": registered,
    }
    assert result["unique_coordinate_count"] == 2
    assert result["cross_domain_same_question_reused_id"] is True
    assert result["cross_domain_hints_merged"] is True
    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_d_semantic_coordinate"
        / "phase17_3_ks_d_coordinate_proposal_v0_2.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
