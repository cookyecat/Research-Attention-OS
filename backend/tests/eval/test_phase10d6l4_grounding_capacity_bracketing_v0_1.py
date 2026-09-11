from eval.live.run_phase10d6l4_grounding_capacity_bracketing_v0_1 import (
    GroundingItem, GroundingResponse, SYSTEM_PROMPT, build_user_prompt,
    is_critical, prompt_items, validate_response,
)


def _item():
    return {
        "relation_id": "r1", "operation": "REINFORCE", "target_code": "M1",
        "target_proposition": "p", "relation_reason": "rr",
        "support_texts": [{"unit_id": "u1", "text": "evidence"}],
        "jurisdiction_anchor_codes": [], "strong_class": "DIRECT", "strong_reason": "SECRET",
    }


def test_grounding_schema_cannot_modify_relation_or_support():
    assert set(GroundingItem.model_fields) == {"relation_id", "grounding_class", "reason"}
    assert "Do not add, remove, retarget" in SYSTEM_PROMPT


def test_flash_prompt_excludes_strong_reference_labels_and_reasons():
    payload = prompt_items([_item()])
    assert "strong_class" not in payload[0]
    assert "strong_reason" not in payload[0]
    text = build_user_prompt([_item()])
    assert "SECRET" not in text
    assert '"strong_class"' not in text


def test_response_validation_requires_exact_relation_id_set():
    good = GroundingResponse(items=[GroundingItem(relation_id="r1", grounding_class="DIRECT")])
    assert validate_response(good, [_item()]) == (True, [])
    bad = GroundingResponse(items=[GroundingItem(relation_id="other", grounding_class="DIRECT")])
    ok, errors = validate_response(bad, [_item()])
    assert not ok and "RELATION_ID_SET_MISMATCH" in errors


def test_critical_error_definition_is_directionally_conservative():
    assert is_critical("DIRECT", "INSUFFICIENT")
    assert is_critical("INSUFFICIENT", "DIRECT")
    assert not is_critical("PARTIAL", "DIRECT")
    assert not is_critical("DIRECT", "PARTIAL")
