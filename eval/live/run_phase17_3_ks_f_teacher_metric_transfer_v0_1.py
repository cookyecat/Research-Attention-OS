"""KS-F teacher-only metric transfer diagnostic v0.1.

Fit scalar cosine policies on teacher-only pairs, evaluate on human-reviewed
pairs. Same Event: this is a leakage-reduced development diagnostic, not a
generalization claim.
"""
from pathlib import Path
import json
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from app.cognitive.client import embed_texts
from app.cognitive.embedding_math import cosine_similarity
from app.services.semantic_coordinate.models import (
    CoordinateRetrievalQuery,
    SemanticCoordinate,
)
from app.services.semantic_coordinate.retrieval import (
    format_coordinate_query_for_embedding,
)
from app.services.semantic_coordinate.training_data import (
    DirectAnswerDatasetV01,
)
from eval.live.run_phase17_3_ks_f_embedding_direct_answer_baseline_v0_1 import (
    candidate_thresholds,
    zero_error_selective_frontier,
)

GOLD = (
    ROOT
    / "eval/live/fixtures/phase17_3_ks_f_direct_answer_dataset_v0_1.json"
)
TEACHER = (
    ROOT
    / "eval/live/fixtures/phase17_3_ks_f_teacher_pool_v0_2.json"
)


def encode_rows(examples):
    query_texts = []
    coordinate_texts = []
    for row in examples:
        query = CoordinateRetrievalQuery(
            primitive_family=row.primitive_family,
            text=row.proposition,
            query_kind="PROPOSITION",
        )
        query_texts.append(
            format_coordinate_query_for_embedding(
                query.embedding_text(),
                query_kind=query.query_kind,
            )
        )
        coordinate = SemanticCoordinate(
            primitive_family=row.primitive_family,
            state_question=row.state_question,
            coordinate_label=row.slot_label,
        )
        coordinate_texts.append(coordinate.embedding_text())

    vectors, model = embed_texts(query_texts + coordinate_texts)
    count = len(examples)
    queries = vectors[:count]
    coordinates = vectors[count:]
    rows = []
    for example, query_vector, coordinate_vector in zip(
        examples,
        queries,
        coordinates,
    ):
        rows.append({
            "example_id": example.example_id,
            "label": example.label,
            "ordinal": example.ordinal,
            "proposition_key": example.proposition_key,
            "slot_key": example.slot_key,
            "score": cosine_similarity(
                query_vector,
                coordinate_vector,
            ),
        })
    return rows, model


def balanced_stats(rows, threshold):
    tp = tn = fp = fn = 0
    for row in rows:
        pred = (
            "DIRECT"
            if row["score"] >= threshold
            else "NOT_DIRECT"
        )
        if row["label"] == "DIRECT":
            tp += pred == "DIRECT"
            fn += pred == "NOT_DIRECT"
        else:
            tn += pred == "NOT_DIRECT"
            fp += pred == "DIRECT"

    tpr = tp / (tp + fn) if tp + fn else 0.0
    tnr = tn / (tn + fp) if tn + fp else 0.0
    return {
        "threshold": threshold,
        "balanced_accuracy": (tpr + tnr) / 2.0,
        "accuracy": (tp + tn) / len(rows),
        "direct_recall": tpr,
        "not_direct_recall": tnr,
        "false_direct": fp,
        "false_not_direct": fn,
    }


def fit_balanced_threshold(rows):
    candidates = [
        balanced_stats(rows, threshold)
        for threshold in candidate_thresholds(
            [row["score"] for row in rows]
        )
    ]
    candidates.sort(
        key=lambda row: (
            -row["balanced_accuracy"],
            -(row["direct_recall"] + row["not_direct_recall"]),
            row["false_direct"],
            row["false_not_direct"],
        )
    )
    return candidates[0]


def evaluate_threshold(rows, threshold):
    predictions = []
    for row in rows:
        predicted = (
            "DIRECT"
            if row["score"] >= threshold
            else "NOT_DIRECT"
        )
        predictions.append({
            **row,
            "predicted": predicted,
            "correct": predicted == row["label"],
        })

    direct_predictions = [
        row for row in predictions
        if row["predicted"] == "DIRECT"
    ]
    direct_gold = [
        row for row in predictions
        if row["label"] == "DIRECT"
    ]
    not_gold = [
        row for row in predictions
        if row["label"] == "NOT_DIRECT"
    ]
    return {
        "accuracy": sum(row["correct"] for row in predictions)
        / len(predictions),
        "direct_precision": (
            sum(
                row["label"] == "DIRECT"
                for row in direct_predictions
            ) / len(direct_predictions)
            if direct_predictions else None
        ),
        "direct_recall": sum(
            row["predicted"] == "DIRECT"
            for row in direct_gold
        ) / len(direct_gold),
        "not_direct_recall": sum(
            row["predicted"] == "NOT_DIRECT"
            for row in not_gold
        ) / len(not_gold),
        "false_direct": sum(
            row["predicted"] == "DIRECT"
            and row["label"] == "NOT_DIRECT"
            for row in predictions
        ),
        "false_not_direct": sum(
            row["predicted"] == "NOT_DIRECT"
            and row["label"] == "DIRECT"
            for row in predictions
        ),
        "predictions": predictions,
    }


def evaluate_selective(rows, policy):
    predictions = []
    for row in rows:
        if row["score"] <= policy["theta_not_direct"]:
            predicted = "NOT_DIRECT"
        elif row["score"] >= policy["theta_direct"]:
            predicted = "DIRECT"
        else:
            predicted = "ABSTAIN"
        predictions.append({
            **row,
            "predicted": predicted,
            "correct": (
                None
                if predicted == "ABSTAIN"
                else predicted == row["label"]
            ),
        })
    covered = [
        row for row in predictions
        if row["predicted"] != "ABSTAIN"
    ]
    return {
        "coverage": len(covered) / len(rows),
        "covered_count": len(covered),
        "abstain_count": len(rows) - len(covered),
        "covered_accuracy": (
            sum(bool(row["correct"]) for row in covered) / len(covered)
            if covered else None
        ),
        "false_direct": sum(
            row["predicted"] == "DIRECT"
            and row["label"] == "NOT_DIRECT"
            for row in covered
        ),
        "false_not_direct": sum(
            row["predicted"] == "NOT_DIRECT"
            and row["label"] == "DIRECT"
            for row in covered
        ),
        "predictions": predictions,
    }


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
    train_examples = tuple(
        row for row in teacher.examples
        if row.example_id not in gold_ids
    )

    if {row.label for row in train_examples} != {
        "DIRECT",
        "NOT_DIRECT",
    }:
        raise RuntimeError(
            "teacher-only diagnostic requires both labels"
        )

    train_rows, train_model = encode_rows(train_examples)
    test_rows, test_model = encode_rows(gold.examples)
    if train_model != test_model:
        raise RuntimeError("embedding model changed between train/test")

    fitted = fit_balanced_threshold(train_rows)
    test_eval = evaluate_threshold(
        test_rows,
        fitted["threshold"],
    )

    selective_policy = zero_error_selective_frontier(
        train_rows
    )
    selective_eval = (
        evaluate_selective(test_rows, selective_policy)
        if selective_policy is not None
        else None
    )

    result = {
        "benchmark": (
            "phase17.3-ks-f-teacher-metric-transfer-v0.1"
        ),
        "embedding_model": train_model,
        "train_source": "teacher-only exact-pair non-overlap",
        "train_example_count": len(train_rows),
        "train_label_counts": {
            label: sum(
                row["label"] == label for row in train_rows
            )
            for label in ("DIRECT", "NOT_DIRECT")
        },
        "test_source": "human-reviewed gold",
        "test_example_count": len(test_rows),
        "same_event_warning": (
            "train/test share the Jev Event; no cross-event "
            "generalization claim"
        ),
        "fitted_balanced_threshold": fitted,
        "human_gold_test": test_eval,
        "teacher_zero_error_selective_policy": selective_policy,
        "human_gold_selective_test": selective_eval,
    }

    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_f_teacher_metric_transfer_v0_1"
        / "phase17_3_ks_f_teacher_metric_transfer_v0_1.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps({
        "benchmark": result["benchmark"],
        "embedding_model": result["embedding_model"],
        "train_example_count": result["train_example_count"],
        "train_label_counts": result["train_label_counts"],
        "fitted_threshold": round(
            fitted["threshold"], 4
        ),
        "train_balanced_accuracy": round(
            fitted["balanced_accuracy"], 4
        ),
        "human_gold_accuracy": round(
            test_eval["accuracy"], 4
        ),
        "human_gold_direct_precision": (
            round(test_eval["direct_precision"], 4)
            if test_eval["direct_precision"] is not None
            else None
        ),
        "human_gold_direct_recall": round(
            test_eval["direct_recall"], 4
        ),
        "human_gold_not_direct_recall": round(
            test_eval["not_direct_recall"], 4
        ),
        "human_gold_false_direct": test_eval["false_direct"],
        "human_gold_false_not_direct": (
            test_eval["false_not_direct"]
        ),
        "selective_policy": selective_policy,
        "selective_human_gold": (
            {
                "coverage": round(
                    selective_eval["coverage"], 4
                ),
                "covered_accuracy": (
                    round(
                        selective_eval["covered_accuracy"],
                        4,
                    )
                    if selective_eval[
                        "covered_accuracy"
                    ] is not None
                    else None
                ),
                "false_direct": selective_eval[
                    "false_direct"
                ],
                "false_not_direct": selective_eval[
                    "false_not_direct"
                ],
            }
            if selective_eval is not None
            else None
        ),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
