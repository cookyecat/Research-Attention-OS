"""Phase17.3-KS-D controlled candidate-retrieval benchmark v0.1.

Gold tests paraphrase retrieval inside one primitive family. Embedding is
candidate evidence only; this benchmark does not authorize schema mutation.
"""
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


def c(family, question, label):
    return SemanticCoordinate(
        primitive_family=family,
        state_question=question,
        coordinate_label=label,
    )


CASES = [
    {
        "id": "P17D-001",
        "family": "QUALITY",
        "query": c(
            "QUALITY",
            "What are this system's operational performance characteristics?",
            "operational performance",
        ),
        "gold": c(
            "QUALITY",
            "How does this system perform in latency, speed, throughput, call rate, and operating efficiency?",
            "runtime performance",
        ),
        "distractors": [
            c(
                "QUALITY",
                "How correct and valid are this system's outputs?",
                "output correctness",
            ),
            c(
                "QUALITY",
                "How reliable is this system under failures and repeated operation?",
                "operational reliability",
            ),
        ],
    },
    {
        "id": "P17D-002",
        "family": "QUALITY",
        "query": c(
            "QUALITY",
            "What is the correctness and validity behavior of this system's outputs?",
            "output correctness",
        ),
        "gold": c(
            "QUALITY",
            "How often are the system's outputs valid, correct, or hallucination-free?",
            "output validity",
        ),
        "distractors": [
            c(
                "QUALITY",
                "How does this system perform in latency, speed, throughput, and operating efficiency?",
                "runtime performance",
            ),
            c(
                "QUALITY",
                "How reliable is this system under failures and repeated operation?",
                "operational reliability",
            ),
        ],
    },
    {
        "id": "P17D-003",
        "family": "QUALITY",
        "query": c(
            "QUALITY",
            "How reliable and robust is this system during operation?",
            "operational reliability",
        ),
        "gold": c(
            "QUALITY",
            "What failure and stability behavior does this system exhibit under repeated operation?",
            "runtime robustness",
        ),
        "distractors": [
            c(
                "QUALITY",
                "How correct and valid are this system's outputs?",
                "output correctness",
            ),
            c(
                "QUALITY",
                "How does this system perform in latency, speed, throughput, and operating efficiency?",
                "runtime performance",
            ),
        ],
    },
    {
        "id": "P17D-004",
        "family": "RELATION",
        "query": c(
            "RELATION",
            "What application contexts or affordances characterize this system?",
            "application affordance",
        ),
        "gold": c(
            "RELATION",
            "For what roles, uses, or external contexts is this system suitable?",
            "role and suitability",
        ),
        "distractors": [
            c(
                "RELATION",
                "What external systems does this system depend on?",
                "external dependency",
            ),
            c(
                "RELATION",
                "What organizations or actors is this system related to?",
                "actor relation",
            ),
        ],
    },
    {
        "id": "P17D-005",
        "family": "STRUCTURE",
        "query": c(
            "STRUCTURE",
            "What is this system's architecture and structural composition?",
            "architecture",
        ),
        "gold": c(
            "STRUCTURE",
            "What components and organization make up this system?",
            "composition",
        ),
        "distractors": [
            c(
                "STRUCTURE",
                "What storage layout and memory organization does this system use?",
                "storage structure",
            ),
            c(
                "STRUCTURE",
                "What hardware module hierarchy does this system contain?",
                "hardware hierarchy",
            ),
        ],
    },
]


def main():
    retriever = CoordinateCandidateRetriever()
    matcher = CoordinateSimilarityEngine()
    rows = []
    reciprocal_ranks = []
    for case in CASES:
        candidates = [case["gold"], *case["distractors"]]
        ranked = retriever.retrieve(
            case["query"],
            candidates,
            top_k=len(candidates),
        )
        ids = [row.coordinate.coordinate_id for row in ranked]
        gold_id = case["gold"].coordinate_id
        rank = ids.index(gold_id) + 1
        reciprocal_ranks.append(1.0 / rank)

        serialized = []
        for row in ranked:
            match = matcher.compare(
                case["query"],
                row.coordinate,
                semantic_similarity=row.semantic_similarity,
            )
            serialized.append({
                "coordinate_id": row.coordinate.coordinate_id,
                "label": row.coordinate.coordinate_label,
                "state_question": row.coordinate.state_question,
                "similarity": row.semantic_similarity,
                "compatibility": match.compatibility,
                "score": match.score,
                "is_gold": row.coordinate.coordinate_id == gold_id,
            })
        gold_score = next(
            item["similarity"] for item in serialized if item["is_gold"]
        )
        best_negative = max(
            item["similarity"] for item in serialized if not item["is_gold"]
        )
        rows.append({
            "id": case["id"],
            "family": case["family"],
            "gold_rank": rank,
            "top1_correct": rank == 1,
            "gold_margin": gold_score - best_negative,
            "ranked": serialized,
        })

    result = {
        "benchmark": "phase17.3-ks-d-candidate-retrieval-v0.1",
        "case_count": len(rows),
        "top1_accuracy": sum(r["top1_correct"] for r in rows) / len(rows),
        "mean_reciprocal_rank": sum(reciprocal_ranks) / len(reciprocal_ranks),
        "positive_margin_count": sum(r["gold_margin"] > 0 for r in rows),
        "schema_mutation_performed": False,
        "results": rows,
    }
    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_d_candidate_retrieval_benchmark_v0_1"
        / "phase17_3_ks_d_candidate_retrieval_benchmark_v0_1.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "benchmark": result["benchmark"],
        "case_count": result["case_count"],
        "top1_accuracy": result["top1_accuracy"],
        "mean_reciprocal_rank": result["mean_reciprocal_rank"],
        "positive_margin_count": result["positive_margin_count"],
        "case_summary": [
            {
                "id": row["id"],
                "gold_rank": row["gold_rank"],
                "gold_margin": round(row["gold_margin"], 4),
                "top": row["ranked"][0]["label"],
                "gold": next(
                    item["label"] for item in row["ranked"] if item["is_gold"]
                ),
            }
            for row in rows
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
