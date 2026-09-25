"""Phase17.3-KS-D controlled candidate-retrieval benchmark v0.2.

Gold tests paraphrase retrieval inside one primitive family. Embedding is
candidate evidence only; this benchmark does not authorize schema mutation.
Retriever quality is evaluated primarily by Recall@K, with Top-1/MRR/margin
retained as diagnostic precision signals.
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

EXTRA_CASE_SPECS = [
    (
        "P17D-006", "QUALITY",
        ("What are this system's operating efficiency and cost characteristics?", "operating efficiency"),
        ("How does this system perform in speed, throughput, latency, call rate, and cost efficiency?", "runtime performance"),
        [
            ("How correct and valid are this system's outputs?", "output correctness"),
            ("How reliable is this system under repeated operation?", "operational reliability"),
        ],
    ),
    (
        "P17D-007", "STATE",
        ("What is the current release and availability status of this system?", "release availability"),
        ("Is this system released, accessible, or otherwise available for use?", "lifecycle availability"),
        [
            ("Is this system currently running, paused, or stopped?", "execution state"),
            ("Is this system currently in maintenance mode?", "maintenance state"),
        ],
    ),
    (
        "P17D-008", "PROCESS",
        ("How does this system generate or infer its outputs at runtime?", "runtime mechanism"),
        ("What internal procedure or mechanism produces this system's outputs?", "generation mechanism"),
        [
            ("How is this system trained from data?", "training procedure"),
            ("How does this system update or adapt its parameters?", "adaptation procedure"),
        ],
    ),
    (
        "P17D-009", "FORM",
        ("In what representation or structure does this system express outputs?", "output representation"),
        ("What form, schema, or representation do this system's outputs take?", "output form"),
        [
            ("Through what interface does a user interact with this system?", "interaction interface"),
            ("In what physical action form does this system act on the world?", "action form"),
        ],
    ),
    (
        "P17D-010", "RELATION",
        ("What external systems or services is this system integrated with or dependent on?", "integration dependency"),
        ("Which external systems participate in this system's integration or dependency context?", "external dependency"),
        [
            ("For what applications or roles is this system suitable?", "application affordance"),
            ("In what deployment environments is this system typically used?", "deployment context"),
        ],
    ),
    (
        "P17D-011", "STRUCTURE",
        ("How is this system's memory or storage structurally organized?", "memory organization"),
        ("What storage layout and memory organization make up this system?", "storage structure"),
        [
            ("What is this system's overall architecture and component composition?", "architecture"),
            ("What hardware module hierarchy does this system contain?", "hardware hierarchy"),
        ],
    ),
    (
        "P17D-012", "FORM",
        ("Through what interaction channel or interface does a user operate this system?", "interaction channel"),
        ("What user-facing interface or interaction form does this system expose?", "interaction interface"),
        [
            ("What representation or schema do this system's outputs take?", "output representation"),
            ("In what physical action form does this system act on the world?", "action form"),
        ],
    ),
]

for case_id, family, query, gold, negatives in EXTRA_CASE_SPECS:
    CASES.append({
        "id": case_id,
        "family": family,
        "query": c(family, query[0], query[1]),
        "gold": c(family, gold[0], gold[1]),
        "distractors": [c(family, text, label) for text, label in negatives],
    })


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

    margins = [row["gold_margin"] for row in rows]
    result = {
        "benchmark": "phase17.3-ks-d-candidate-retrieval-v0.2",
        "case_count": len(rows),
        "recall_at_1": sum(r["gold_rank"] <= 1 for r in rows) / len(rows),
        "recall_at_2": sum(r["gold_rank"] <= 2 for r in rows) / len(rows),
        "recall_at_3": sum(r["gold_rank"] <= 3 for r in rows) / len(rows),
        "top1_accuracy": sum(r["top1_correct"] for r in rows) / len(rows),
        "mean_reciprocal_rank": sum(reciprocal_ranks) / len(reciprocal_ranks),
        "positive_margin_count": sum(margin > 0 for margin in margins),
        "mean_gold_margin": sum(margins) / len(margins),
        "min_gold_margin": min(margins),
        "schema_mutation_performed": False,
        "results": rows,
    }
    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_d_candidate_retrieval_benchmark_v0_2"
        / "phase17_3_ks_d_candidate_retrieval_benchmark_v0_2.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "benchmark": result["benchmark"],
        "case_count": result["case_count"],
        "recall_at_1": result["recall_at_1"],
        "recall_at_2": result["recall_at_2"],
        "recall_at_3": result["recall_at_3"],
        "top1_accuracy": result["top1_accuracy"],
        "mean_reciprocal_rank": result["mean_reciprocal_rank"],
        "positive_margin_count": result["positive_margin_count"],
        "mean_gold_margin": round(result["mean_gold_margin"], 4),
        "min_gold_margin": round(result["min_gold_margin"], 4),
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
