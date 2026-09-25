"""Phase17.3-KS-D proposition -> coordinate retrieval benchmark v0.3.

This benchmark matches the real KeyBy boundary:
typed World proposition + primitive family -> existing semantic coordinates.
The retriever is judged primarily by Recall@K, not by final REUSE/CREATE.
"""
from pathlib import Path
import json
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
from app.services.semantic_coordinate.retrieval import CoordinateCandidateRetriever


def c(family, question, label):
    return SemanticCoordinate(
        primitive_family=family,
        state_question=question,
        coordinate_label=label,
    )


def q(family, proposition):
    return CoordinateRetrievalQuery(
        primitive_family=family,
        text=proposition,
        query_kind="PROPOSITION",
    )
CASES = [
    {
        "id": "P17D-P001",
        "query": q(
            "QUALITY",
            "The system completes decisions in about 300 ms and handles 10 calls per second.",
        ),
        "gold": c(
            "QUALITY",
            "What are this system's operational performance characteristics?",
            "operational performance",
        ),
        "distractors": [
            c("QUALITY", "How correct and valid are this system's outputs?", "output correctness"),
            c("QUALITY", "How reliable is this system under repeated operation?", "operational reliability"),
        ],
    },
    {
        "id": "P17D-P002",
        "query": q(
            "QUALITY",
            "The system returns valid structured outputs and is claimed to avoid hallucinated values.",
        ),
        "gold": c(
            "QUALITY",
            "What are this system's output correctness and validity characteristics?",
            "output correctness",
        ),
        "distractors": [
            c("QUALITY", "What are this system's operational performance characteristics?", "operational performance"),
            c("QUALITY", "How reliable is this system under repeated operation?", "operational reliability"),
        ],
    },
    {
        "id": "P17D-P003",
        "query": q(
            "QUALITY",
            "Repeated runs occasionally fail after long contexts but usually recover without restart.",
        ),
        "gold": c(
            "QUALITY",
            "What are this system's reliability or failure-mode characteristics?",
            "operational reliability",
        ),
        "distractors": [
            c("QUALITY", "How correct and valid are this system's outputs?", "output correctness"),
            c("QUALITY", "What are this system's operational performance characteristics?", "operational performance"),
        ],
    },
    {
        "id": "P17D-P004",
        "query": q(
            "RELATION",
            "The authors propose using the system for browser automation, teaching assistants, and real-time agents.",
        ),
        "gold": c(
            "RELATION",
            "For what roles, uses, or application contexts is this system suitable?",
            "application affordance",
        ),
        "distractors": [
            c("RELATION", "What external systems does this system depend on?", "external dependency"),
            c("RELATION", "On what environment or platform is this system demonstrated?", "demonstration environment"),
        ],
    },
    {
        "id": "P17D-P005",
        "query": q(
            "STRUCTURE",
            "The system contains a decoder, a planner, and a memory component arranged as separate modules.",
        ),
        "gold": c(
            "STRUCTURE",
            "What components and organization make up this system?",
            "structural composition",
        ),
        "distractors": [
            c("STRUCTURE", "How is this system's memory or storage organized?", "memory structure"),
            c("STRUCTURE", "What hardware module hierarchy does this system contain?", "hardware hierarchy"),
        ],
    },
    {
        "id": "P17D-P006",
        "query": q(
            "QUALITY",
            "Inference is reported to be 20 to 200 times faster and 40 to 400 times cheaper.",
        ),
        "gold": c(
            "QUALITY",
            "What are this system's operational performance characteristics?",
            "operational performance",
        ),
        "distractors": [
            c("QUALITY", "How correct and valid are this system's outputs?", "output correctness"),
            c("QUALITY", "What are this system's reliability or failure-mode characteristics?", "operational reliability"),
        ],
    },
    {
        "id": "P17D-P007",
        "query": q(
            "STATE",
            "The model weights and code are now publicly released and available for download.",
        ),
        "gold": c(
            "STATE",
            "What is this system's current release or availability status?",
            "release availability",
        ),
        "distractors": [
            c("STATE", "Is this system currently running, paused, or stopped?", "execution state"),
            c("STATE", "Is this system currently under maintenance?", "maintenance state"),
        ],
    },
    {
        "id": "P17D-P008",
        "query": q(
            "PROCESS",
            "A single decoder processes the context and schema once, reuses a KV cache, and scores field tokens.",
        ),
        "gold": c(
            "PROCESS",
            "What mechanism does this system use to produce its outputs?",
            "generation mechanism",
        ),
        "distractors": [
            c("PROCESS", "How is this system trained from data?", "training process"),
            c("PROCESS", "How does this system update or adapt its parameters?", "adaptation process"),
        ],
    },
    {
        "id": "P17D-P009",
        "query": q(
            "FORM",
            "The system returns typed structured judgments rather than free-form strings.",
        ),
        "gold": c(
            "FORM",
            "What form or representation does this system's output take?",
            "output form",
        ),
        "distractors": [
            c("FORM", "Through what interface does a user interact with this system?", "interaction interface"),
            c("FORM", "In what physical action form does this system act on the world?", "action form"),
        ],
    },
    {
        "id": "P17D-P010",
        "query": q(
            "RELATION",
            "The system connects to a browser API, a market simulator, and an external tool runtime.",
        ),
        "gold": c(
            "RELATION",
            "What external systems, services, or integrations does this system depend on?",
            "external integration dependency",
        ),
        "distractors": [
            c("RELATION", "For what applications or roles is this system suitable?", "application affordance"),
            c("RELATION", "In what deployment environments is this system typically used?", "deployment context"),
        ],
    },
    {
        "id": "P17D-P011",
        "query": q(
            "STRUCTURE",
            "The agent keeps a short-term KV cache plus a separate episodic memory store.",
        ),
        "gold": c(
            "STRUCTURE",
            "How is this system's memory or storage structurally organized?",
            "memory organization",
        ),
        "distractors": [
            c("STRUCTURE", "What is this system's overall architecture and component composition?", "overall architecture"),
            c("STRUCTURE", "What hardware module hierarchy does this system contain?", "hardware hierarchy"),
        ],
    },
    {
        "id": "P17D-P012",
        "query": q(
            "FORM",
            "Users operate the system through a conversational web interface.",
        ),
        "gold": c(
            "FORM",
            "What user-facing interface or interaction form does this system expose?",
            "interaction interface",
        ),
        "distractors": [
            c("FORM", "What representation or schema do this system's outputs take?", "output representation"),
            c("FORM", "In what physical action form does this system act on the world?", "action form"),
        ],
    },
]
def main():
    retriever = CoordinateCandidateRetriever()
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

        serialized = [
            {
                "label": row.coordinate.coordinate_label,
                "state_question": row.coordinate.state_question,
                "similarity": row.semantic_similarity,
                "is_gold": row.coordinate.coordinate_id == gold_id,
            }
            for row in ranked
        ]
        gold_score = next(
            item["similarity"] for item in serialized if item["is_gold"]
        )
        negative_scores = [
            item["similarity"] for item in serialized if not item["is_gold"]
        ]
        rows.append({
            "id": case["id"],
            "family": case["query"].primitive_family,
            "proposition": case["query"].text,
            "gold_rank": rank,
            "gold_margin": gold_score - max(negative_scores),
            "ranked": serialized,
        })

    result = {
        "benchmark": "phase17.3-ks-d-proposition-retrieval-v0.3",
        "case_count": len(rows),
        "recall_at_1": sum(r["gold_rank"] <= 1 for r in rows) / len(rows),
        "recall_at_2": sum(r["gold_rank"] <= 2 for r in rows) / len(rows),
        "recall_at_3": sum(r["gold_rank"] <= 3 for r in rows) / len(rows),
        "mean_reciprocal_rank": sum(reciprocal_ranks) / len(reciprocal_ranks),
        "mean_gold_margin": sum(r["gold_margin"] for r in rows) / len(rows),
        "min_gold_margin": min(r["gold_margin"] for r in rows),
        "schema_mutation_performed": False,
        "results": rows,
    }
    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_d_proposition_retrieval_benchmark_v0_3"
        / "phase17_3_ks_d_proposition_retrieval_benchmark_v0_3.json"
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
        "mean_reciprocal_rank": round(result["mean_reciprocal_rank"], 4),
        "mean_gold_margin": round(result["mean_gold_margin"], 4),
        "min_gold_margin": round(result["min_gold_margin"], 4),
        "case_summary": [
            {
                "id": row["id"],
                "rank": row["gold_rank"],
                "margin": round(row["gold_margin"], 4),
                "top": row["ranked"][0]["label"],
                "gold": next(
                    item["label"]
                    for item in row["ranked"]
                    if item["is_gold"]
                ),
            }
            for row in rows
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
