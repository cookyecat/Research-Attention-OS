from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from eval.live.representation_cognition_marginalization_v0_1 import (
    compose_attention_marginal,
)


def test_deterministic_distinct_representations_create_representation_uncertainty():
    result = compose_attention_marginal(
        [
            {
                "representation_id": "R0",
                "weight": 0.5,
                "attention_distribution": {"DROP": 1.0},
            },
            {
                "representation_id": "R1",
                "weight": 0.5,
                "attention_distribution": {"ENGAGE": 1.0},
            },
        ],
        weight_semantics="CALIBRATED_POSTERIOR",
    )
    assert result["marginal_attention_distribution"] == {"DROP": 0.5, "ENGAGE": 0.5}
    assert result["marginal_attention_entropy_bits"] == 1.0
    assert result["expected_conditional_cognitive_entropy_bits"] == 0.0
    assert result["representation_induced_information_bits"] == 1.0
    assert result["entropy_decomposition_residual_bits"] == 0.0
    assert result["mutual_information_interpretation_valid"] is True


def test_identical_cognitive_distributions_have_zero_representation_contribution():
    result = compose_attention_marginal(
        [
            {
                "representation_id": "R0",
                "weight": 0.3,
                "attention_distribution": {"AWARE": 0.5, "ENGAGE": 0.5},
            },
            {
                "representation_id": "R1",
                "weight": 0.7,
                "attention_distribution": {"AWARE": 0.5, "ENGAGE": 0.5},
            },
        ],
        weight_semantics="CALIBRATED_POSTERIOR",
    )
    assert result["marginal_attention_distribution"] == {"AWARE": 0.5, "ENGAGE": 0.5}
    assert result["marginal_attention_entropy_bits"] == 1.0
    assert result["expected_conditional_cognitive_entropy_bits"] == 1.0
    assert result["representation_induced_information_bits"] == 0.0


def test_operational_proxy_is_diagnostic_not_bayesian_claim():
    result = compose_attention_marginal(
        [
            {
                "representation_id": "R0",
                "weight": 2.0,
                "attention_distribution": {"DROP": 1.0},
            },
            {
                "representation_id": "R1",
                "weight": 1.0,
                "attention_distribution": {"ENGAGE": 1.0},
            },
        ],
        weight_semantics="OPERATIONAL_PROXY",
    )
    assert result["components"][0]["weight"] == pytest.approx(2 / 3)
    assert result["components"][1]["weight"] == pytest.approx(1 / 3)
    assert result["marginal_attention_distribution"]["DROP"] == pytest.approx(2 / 3)
    assert result["marginal_attention_distribution"]["ENGAGE"] == pytest.approx(1 / 3)
    assert result["mutual_information_interpretation_valid"] is False
    assert result["calibrated_representation_posterior"] is False
    assert result["decision_authority"] == "NONE"
    assert result["mutates_attention"] is False
    assert result["mutates_representation"] is False


def test_mixed_internal_and_representation_uncertainty_decompose_exactly():
    result = compose_attention_marginal(
        [
            {
                "representation_id": "R0",
                "weight": 0.5,
                "attention_distribution": {"DROP": 0.5, "AWARE": 0.5},
            },
            {
                "representation_id": "R1",
                "weight": 0.5,
                "attention_distribution": {"AWARE": 0.5, "ENGAGE": 0.5},
            },
        ],
        weight_semantics="CALIBRATED_POSTERIOR",
    )
    assert result["marginal_attention_distribution"] == {
        "AWARE": 0.5,
        "DROP": 0.25,
        "ENGAGE": 0.25,
    }
    assert result["entropy_decomposition_residual_bits"] == pytest.approx(0.0, abs=1e-12)
    assert result["representation_induced_information_bits"] > 0
    assert result["expected_conditional_cognitive_entropy_bits"] > 0


def test_invalid_mass_fails_closed():
    with pytest.raises(ValueError, match="negative representation weight"):
        compose_attention_marginal(
            [
                {
                    "representation_id": "R0",
                    "weight": -1,
                    "attention_distribution": {"DROP": 1},
                }
            ]
        )

    with pytest.raises(ValueError, match="positive mass"):
        compose_attention_marginal(
            [
                {
                    "representation_id": "R0",
                    "weight": 0,
                    "attention_distribution": {"DROP": 1},
                }
            ]
        )

    with pytest.raises(ValueError, match="negative probability"):
        compose_attention_marginal(
            [
                {
                    "representation_id": "R0",
                    "weight": 1,
                    "attention_distribution": {"DROP": -0.1, "AWARE": 1.1},
                }
            ]
        )
