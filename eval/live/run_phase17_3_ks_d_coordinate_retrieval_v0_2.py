"""Phase17.3-KS-D live coordinate retrieval + matcher verification v0.2."""
from pathlib import Path
import json
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.semantic_coordinate.matcher import CoordinateSimilarityEngine
from app.services.semantic_coordinate.models import SemanticCoordinate
from app.services.semantic_coordinate.retrieval import CoordinateCandidateRetriever


def coordinate(family, question, label, aliases=()):
    return SemanticCoordinate(
        primitive_family=family,
        state_question=question,
        coordinate_label=label,
        aliases=aliases,
    )


def main():
    query = coordinate(
        "QUALITY",
        "What is the inference latency?",
        "inference latency",
        ("response time",),
    )
    candidates = [
        coordinate(
            "QUALITY",
            "How fast does inference execute?",
            "inference speed",
            ("latency", "response time"),
        ),
        coordinate(
            "QUALITY",
            "What is the operational cost?",
            "operational cost",
            ("price", "expense"),
        ),
        coordinate(
            "STRUCTURE",
            "What architecture does the system use?",
            "architecture",
        ),
        coordinate(
            "DISPOSITION",
            "What tasks can the system perform?",
            "demonstrated capability",
        ),
    ]

    retriever = CoordinateCandidateRetriever()
    rows = retriever.retrieve(query, candidates, top_k=5)
    matcher = CoordinateSimilarityEngine()

    ranked = []
    for row in rows:
        match = matcher.compare(
            query,
            row.coordinate,
            semantic_similarity=row.semantic_similarity,
        )
        ranked.append({
            "coordinate_id": row.coordinate.coordinate_id,
            "primitive_family": row.coordinate.primitive_family,
            "state_question": row.coordinate.state_question,
            "semantic_similarity": row.semantic_similarity,
            "compatibility": match.compatibility,
            "requires_semantic_resolution": match.requires_semantic_resolution,
            "match_score": match.score,
            "embedding_model": row.embedding_model,
        })

    assert ranked
    assert all(row["primitive_family"] == "QUALITY" for row in ranked)
    assert "fast" in ranked[0]["state_question"].lower()

    result = {
        "status": "PASS",
        "query": query.model_dump(mode="json"),
        "ranked_candidates": ranked,
        "hard_family_prefilter": True,
        "schema_mutation_performed": False,
    }
    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_d_coordinate_retrieval_v0_2"
        / "phase17_3_ks_d_coordinate_retrieval_v0_2.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
