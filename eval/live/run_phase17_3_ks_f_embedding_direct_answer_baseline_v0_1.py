"""Phase17.3-KS-F embedding-only Direct-Answer baseline v0.1."""
from pathlib import Path
import json
import math
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.cognitive.client import embed_texts
from app.cognitive.embedding_math import cosine_similarity
from app.services.semantic_coordinate.models import (
    CoordinateRetrievalQuery,
    SemanticCoordinate,
)
from app.services.semantic_coordinate.retrieval import (
    format_coordinate_query_for_embedding,
)
from app.services.semantic_coordinate.training_data import DirectAnswerDatasetV01

FIXTURE = (
    ROOT
    / "eval/live/fixtures/phase17_3_ks_f_direct_answer_dataset_v0_1.json"
)


def candidate_thresholds(scores):
    values = sorted(set(scores))
    if not values:
        return [0.0]
    thresholds = [values[0] - 1e-6]
    thresholds.extend(
        (left + right) / 2.0
        for left, right in zip(values, values[1:])
    )
    thresholds.append(values[-1] + 1e-6)
    return thresholds


def classify(score, threshold):
    return "DIRECT" if score >= threshold else "NOT_DIRECT"


def threshold_stats(rows, threshold):
    correct = 0
    false_direct = 0
    false_not_direct = 0
    for row in rows:
        predicted = classify(row["score"], threshold)
        correct += predicted == row["label"]
        false_direct += (
            predicted == "DIRECT" and row["label"] == "NOT_DIRECT"
        )
        false_not_direct += (
            predicted == "NOT_DIRECT" and row["label"] == "DIRECT"
        )
    return {
        "threshold": threshold,
        "accuracy": correct / len(rows),
        "correct": correct,
        "false_direct": false_direct,
        "false_not_direct": false_not_direct,
    }


def best_threshold(rows):
    candidates = [
        threshold_stats(rows, threshold)
        for threshold in candidate_thresholds(
            [row["score"] for row in rows]
        )
    ]
    candidates.sort(
        key=lambda row: (
            -row["accuracy"],
            row["false_direct"] + row["false_not_direct"],
            -row["threshold"],
        )
    )
    return candidates[0]


def leave_one_out(rows):
    predictions = []
    for index, row in enumerate(rows):
        train = rows[:index] + rows[index + 1 :]
        selected = best_threshold(train)
        predicted = classify(row["score"], selected["threshold"])
        predictions.append({
            "example_id": row["example_id"],
            "label": row["label"],
            "score": row["score"],
            "threshold": selected["threshold"],
            "predicted": predicted,
            "correct": predicted == row["label"],
        })
    return {
        "accuracy": sum(row["correct"] for row in predictions)
        / len(predictions),
        "predictions": predictions,
    }


def roc_auc(rows):
    positives = [
        row["score"] for row in rows if row["label"] == "DIRECT"
    ]
    negatives = [
        row["score"] for row in rows if row["label"] == "NOT_DIRECT"
    ]
    wins = 0.0
    total = len(positives) * len(negatives)
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return wins / total


def zero_error_selective_frontier(rows):
    thresholds = candidate_thresholds(
        [row["score"] for row in rows]
    )
    best = None
    for low in thresholds:
        for high in thresholds:
            if low >= high:
                continue
            covered = []
            errors = 0
            for row in rows:
                if row["score"] <= low:
                    predicted = "NOT_DIRECT"
                elif row["score"] >= high:
                    predicted = "DIRECT"
                else:
                    continue
                covered.append(row)
                errors += predicted != row["label"]
            if errors:
                continue
            candidate = {
                "theta_not_direct": low,
                "theta_direct": high,
                "covered_count": len(covered),
                "coverage": len(covered) / len(rows),
                "abstain_count": len(rows) - len(covered),
            }
            if best is None or (
                candidate["covered_count"] > best["covered_count"]
            ):
                best = candidate
    return best


def leave_one_out_selective(rows):
    predictions = []
    for index, row in enumerate(rows):
        train = rows[:index] + rows[index + 1 :]
        policy = zero_error_selective_frontier(train)
        if policy is None:
            predictions.append({
                "example_id": row["example_id"],
                "label": row["label"],
                "score": row["score"],
                "prediction": "ABSTAIN",
                "correct": None,
            })
            continue

        if row["score"] <= policy["theta_not_direct"]:
            predicted = "NOT_DIRECT"
        elif row["score"] >= policy["theta_direct"]:
            predicted = "DIRECT"
        else:
            predicted = "ABSTAIN"

        predictions.append({
            "example_id": row["example_id"],
            "label": row["label"],
            "score": row["score"],
            "theta_not_direct": policy["theta_not_direct"],
            "theta_direct": policy["theta_direct"],
            "prediction": predicted,
            "correct": (
                None
                if predicted == "ABSTAIN"
                else predicted == row["label"]
            ),
        })

    covered = [
        row for row in predictions
        if row["prediction"] != "ABSTAIN"
    ]
    return {
        "coverage": len(covered) / len(predictions),
        "covered_count": len(covered),
        "abstain_count": len(predictions) - len(covered),
        "covered_accuracy": (
            sum(bool(row["correct"]) for row in covered) / len(covered)
            if covered else None
        ),
        "false_direct": sum(
            row["prediction"] == "DIRECT"
            and row["label"] == "NOT_DIRECT"
            for row in covered
        ),
        "false_not_direct": sum(
            row["prediction"] == "NOT_DIRECT"
            and row["label"] == "DIRECT"
            for row in covered
        ),
        "predictions": predictions,
    }


def summarize_scores(rows):
    result = {}
    for label in ("DIRECT", "NOT_DIRECT"):
        scores = sorted(
            row["score"] for row in rows if row["label"] == label
        )
        result[label] = {
            "count": len(scores),
            "min": min(scores),
            "mean": sum(scores) / len(scores),
            "max": max(scores),
        }
    return result


def score_variant(dataset, variant):
    query_texts = []
    candidate_texts = []
    for row in dataset.examples:
        if variant == "raw":
            query_texts.append(row.proposition)
            candidate_texts.append(row.state_question)
        elif variant == "retrieval_protocol":
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
            candidate_texts.append(coordinate.embedding_text())
        else:
            raise ValueError(f"unknown variant: {variant}")

    vectors, model = embed_texts(query_texts + candidate_texts)
    count = len(dataset.examples)
    query_vectors = vectors[:count]
    candidate_vectors = vectors[count:]
    rows = []
    for example, query_vector, candidate_vector in zip(
        dataset.examples,
        query_vectors,
        candidate_vectors,
    ):
        rows.append({
            "example_id": example.example_id,
            "label": example.label,
            "hard_negative": example.hard_negative,
            "ordinal": example.ordinal,
            "proposition_key": example.proposition_key,
            "slot_key": example.slot_key,
            "note": example.note,
            "score": cosine_similarity(
                query_vector,
                candidate_vector,
            ),
        })

    selected = best_threshold(rows)
    loo = leave_one_out(rows)
    loo_selective = leave_one_out_selective(rows)
    return {
        "variant": variant,
        "embedding_model": model,
        "score_summary": summarize_scores(rows),
        "roc_auc": roc_auc(rows),
        "optimistic_best_threshold": selected,
        "leave_one_out": loo,
        "leave_one_out_selective": loo_selective,
        "zero_error_selective_same_set": (
            zero_error_selective_frontier(rows)
        ),
        "rows": sorted(
            rows,
            key=lambda row: row["score"],
            reverse=True,
        ),
    }


def main():
    dataset = DirectAnswerDatasetV01.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    variants = [
        score_variant(dataset, "raw"),
        score_variant(dataset, "retrieval_protocol"),
    ]
    result = {
        "benchmark": (
            "phase17.3-ks-f-embedding-direct-answer-baseline-v0.1"
        ),
        "dataset_id": dataset.dataset_id,
        "dataset_status": dataset.status,
        "example_count": len(dataset.examples),
        "event_group_count": len(dataset.event_groups()),
        "evaluation_warning": (
            "single-event development set; best-threshold and zero-error "
            "coverage are same-set optimistic diagnostics"
        ),
        "variants": variants,
    }

    output = (
        ROOT
        / "eval/live/results/phase17_3_ks_f_embedding_direct_answer_baseline_v0_1"
        / "phase17_3_ks_f_embedding_direct_answer_baseline_v0_1.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    compact = {
        "benchmark": result["benchmark"],
        "dataset_status": result["dataset_status"],
        "example_count": result["example_count"],
        "variants": [
            {
                "variant": row["variant"],
                "embedding_model": row["embedding_model"],
                "roc_auc": round(row["roc_auc"], 4),
                "optimistic_accuracy": round(
                    row["optimistic_best_threshold"]["accuracy"],
                    4,
                ),
                "optimistic_threshold": round(
                    row["optimistic_best_threshold"]["threshold"],
                    4,
                ),
                "false_direct": row[
                    "optimistic_best_threshold"
                ]["false_direct"],
                "false_not_direct": row[
                    "optimistic_best_threshold"
                ]["false_not_direct"],
                "loo_accuracy": round(
                    row["leave_one_out"]["accuracy"],
                    4,
                ),
                "loo_selective_coverage": round(
                    row["leave_one_out_selective"]["coverage"],
                    4,
                ),
                "loo_selective_covered_accuracy": (
                    round(
                        row["leave_one_out_selective"][
                            "covered_accuracy"
                        ],
                        4,
                    )
                    if row["leave_one_out_selective"][
                        "covered_accuracy"
                    ] is not None
                    else None
                ),
                "loo_selective_false_direct": row[
                    "leave_one_out_selective"
                ]["false_direct"],
                "loo_selective_false_not_direct": row[
                    "leave_one_out_selective"
                ]["false_not_direct"],
                "zero_error_coverage_same_set": round(
                    row["zero_error_selective_same_set"]["coverage"],
                    4,
                ),
                "score_summary": {
                    label: {
                        key: (
                            round(value, 4)
                            if isinstance(value, float)
                            else value
                        )
                        for key, value in values.items()
                    }
                    for label, values in row["score_summary"].items()
                },
            }
            for row in variants
        ],
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
