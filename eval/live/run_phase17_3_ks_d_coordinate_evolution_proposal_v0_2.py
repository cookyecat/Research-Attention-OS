"""Phase17.3-KS coordinate evolution proposal verification v0.2."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.semantic_coordinate.evolution import CoordinateEvolutionEngine
from app.services.semantic_coordinate.models import SemanticCoordinate
from app.services.semantic_coordinate.registry import SemanticCoordinateRegistry


def main():
    registry = SemanticCoordinateRegistry()
    latency = SemanticCoordinate(
        primitive_family="QUALITY",
        state_question="What is the inference latency?",
        coordinate_label="inference latency",
    )
    speed = SemanticCoordinate(
        primitive_family="QUALITY",
        state_question="How fast does inference execute?",
        coordinate_label="inference speed",
    )
    registry.register(latency)
    registry.register(speed)
    engine = CoordinateEvolutionEngine(registry)
    relation = engine.propose_merge(
        speed.coordinate_id,
        latency.coordinate_id,
        confidence=0.92,
        rationale="candidate semantic equivalence; migration not applied",
    )

    assert relation.relation == "MERGE"
    assert len(engine.history) == 1
    assert len(registry) == 2
    assert registry.get(speed.coordinate_id) is not None
    assert registry.get(latency.coordinate_id) is not None

    result = {
        "status": "PASS",
        "relation": relation.model_dump(mode="json"),
        "registry_size_before_and_after": [2, len(registry)],
        "schema_mutation_performed": False,
    }
    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_d_semantic_coordinate"
        / "phase17_3_ks_d_coordinate_evolution_proposal_v0_2.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
