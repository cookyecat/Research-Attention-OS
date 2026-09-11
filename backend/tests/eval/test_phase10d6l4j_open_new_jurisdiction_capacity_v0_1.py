from eval.live.run_phase10d6l4j_open_new_jurisdiction_capacity_v0_1 import (
    SYSTEM_PROMPT,
    JurisdictionItem,
    JurisdictionResponse,
    build_user_prompt,
    load_open_new_items,
    prompt_items,
    validate_response,
)


def test_frozen_open_new_item_count_and_labels():
    items = load_open_new_items()
    assert len(items) == 2
    assert all(x["operation"] == "OPEN_NEW" for x in items)
    assert all(x["strong_class"] == "INSUFFICIENT" for x in items)


def test_prompt_includes_full_anchor_semantics_and_hides_strong_labels():
    items = load_open_new_items()
    rows = prompt_items(items)
    text = build_user_prompt(items)
    assert "strong_class" not in text
    assert "strong_reason" not in text
    assert "Collective Intelligence" in text
    assert "Build better embodied and multi-agent intelligence systems" in text
    assert rows[1]["proposed_jurisdiction_anchors"]

def test_prompt_contract_is_jurisdiction_only():
    low = SYSTEM_PROMPT.lower()
    assert "jurisdiction" in low
    assert "do not add, remove, retarget" in low
    for token in ("drop", "aware", "watch", "engage"):
        assert token not in low


def test_validation_requires_exact_relation_set():
    items = load_open_new_items()
    parsed = JurisdictionResponse(items=[
        JurisdictionItem(
            relation_id=items[0]["relation_id"],
            jurisdiction_class="INSUFFICIENT_JURISDICTION",
            reason="x",
        )
    ])
    ok, errors = validate_response(parsed, items)
    assert not ok
    assert "RELATION_ID_SET_MISMATCH" in errors
