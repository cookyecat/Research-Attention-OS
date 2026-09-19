from __future__ import annotations

import math
from typing import Iterable, Mapping

CONTRACT_VERSION = "representation-cognition-marginalization-v0.1"
WEIGHT_SEMANTICS = {"CALIBRATED_POSTERIOR", "OPERATIONAL_PROXY"}


def _normalize_distribution(values: Mapping[str, float]) -> dict[str, float]:
    cleaned: dict[str, float] = {}
    for key, raw in values.items():
        value = float(raw)
        if value < 0:
            raise ValueError(f"negative probability for {key}: {value}")
        if value > 0:
            cleaned[str(key)] = value
    total = sum(cleaned.values())
    if total <= 0:
        raise ValueError("categorical distribution must contain positive mass")
    return {key: value / total for key, value in sorted(cleaned.items())}


def entropy_bits(values: Mapping[str, float]) -> float:
    distribution = _normalize_distribution(values)
    return -sum(p * math.log2(p) for p in distribution.values() if p > 0)


def compose_attention_marginal(
    components: Iterable[Mapping],
    *,
    weight_semantics: str = "OPERATIONAL_PROXY",
) -> dict:
    semantics = str(weight_semantics).upper()
    if semantics not in WEIGHT_SEMANTICS:
        raise ValueError(f"unsupported weight_semantics: {weight_semantics}")

    raw_components = list(components)
    if not raw_components:
        raise ValueError("at least one representation component is required")

    weights: list[float] = []
    normalized_components: list[dict] = []
    for index, row in enumerate(raw_components):
        weight = float(row.get("weight", 0.0))
        if weight < 0:
            raise ValueError(f"negative representation weight at index {index}: {weight}")
        distribution = _normalize_distribution(row.get("attention_distribution") or {})
        weights.append(weight)
        normalized_components.append(
            {
                "representation_id": str(row.get("representation_id") or f"R{index}"),
                "raw_weight": weight,
                "attention_distribution": distribution,
                "conditional_entropy_bits": entropy_bits(distribution),
            }
        )

    total_weight = sum(weights)
    if total_weight <= 0:
        raise ValueError("representation weights must contain positive mass")

    for row, weight in zip(normalized_components, weights):
        row["weight"] = weight / total_weight

    labels = sorted(
        {
            label
            for row in normalized_components
            for label in row["attention_distribution"]
        }
    )
    marginal = {
        label: sum(
            row["weight"] * row["attention_distribution"].get(label, 0.0)
            for row in normalized_components
        )
        for label in labels
    }
    marginal = _normalize_distribution(marginal)

    marginal_entropy = entropy_bits(marginal)
    expected_conditional_entropy = sum(
        row["weight"] * row["conditional_entropy_bits"]
        for row in normalized_components
    )
    representation_induced_information = max(
        0.0,
        marginal_entropy - expected_conditional_entropy,
    )
    residual = marginal_entropy - (
        expected_conditional_entropy + representation_induced_information
    )

    calibrated = semantics == "CALIBRATED_POSTERIOR"
    return {
        "contract_version": CONTRACT_VERSION,
        "weight_semantics": semantics,
        "components": normalized_components,
        "marginal_attention_distribution": {
            key: round(value, 12) for key, value in marginal.items()
        },
        "marginal_attention_entropy_bits": round(marginal_entropy, 12),
        "expected_conditional_cognitive_entropy_bits": round(
            expected_conditional_entropy, 12
        ),
        "representation_induced_information_bits": round(
            representation_induced_information, 12
        ),
        "entropy_decomposition_residual_bits": round(residual, 12),
        "mutual_information_interpretation_valid": calibrated,
        "calibrated_representation_posterior": calibrated,
        "decision_authority": "NONE",
        "mutates_attention": False,
        "mutates_representation": False,
        "semantics": {
            "expected_conditional_cognitive_entropy_bits":
                "expected cognitive stochasticity conditional on representation",
            "representation_induced_information_bits": (
                "I(A;R|E) only when weights are calibrated posterior representation probabilities; "
                "otherwise an information-form diagnostic"
            ),
        },
    }


def demo() -> dict:
    return compose_attention_marginal(
        [
            {
                "representation_id": "R_keep_separate",
                "weight": 0.5,
                "attention_distribution": {"DROP": 1.0},
            },
            {
                "representation_id": "R_same_event",
                "weight": 0.5,
                "attention_distribution": {"ENGAGE": 1.0},
            },
        ],
        weight_semantics="OPERATIONAL_PROXY",
    )


if __name__ == "__main__":
    import json

    print(json.dumps(demo(), ensure_ascii=False, indent=2))
