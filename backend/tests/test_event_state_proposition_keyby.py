from app.services.event_state_proposition_keyby import (
    KeyByMutationDraftV01,
    PropositionRouteV01,
    SemanticKeyByDraftV01,
    _normalize_keyby_draft,
)


def _mutation(label: str) -> KeyByMutationDraftV01:
    return KeyByMutationDraftV01(
        target="CREATE",
        primitive_family="QUALITY",
        slot_label=label,
        state_question=f"What is this system's {label}?",
        value=label,
    )


def test_keyby_normalizer_prunes_unreferenced_mutation_and_remaps_indices():
    draft = SemanticKeyByDraftV01(
        mutations=(
            _mutation("orphan"),
            _mutation("performance"),
            _mutation("correctness"),
        ),
        proposition_routes=(
            PropositionRouteV01(
                proposition_key="P001",
                disposition="WORLD_MUTATION",
                mutation_indices=(1,),
            ),
            PropositionRouteV01(
                proposition_key="P002",
                disposition="WORLD_MUTATION",
                mutation_indices=(2,),
            ),
        ),
    )
    normalized = _normalize_keyby_draft(draft)
    assert [row.slot_label for row in normalized.mutations] == [
        "performance",
        "correctness",
    ]
    assert normalized.proposition_routes[0].mutation_indices == (0,)
    assert normalized.proposition_routes[1].mutation_indices == (1,)


def test_keyby_normalizer_is_identity_when_all_mutations_are_referenced():
    draft = SemanticKeyByDraftV01(
        mutations=(_mutation("performance"),),
        proposition_routes=(
            PropositionRouteV01(
                proposition_key="P001",
                disposition="WORLD_MUTATION",
                mutation_indices=(0,),
            ),
        ),
    )
    assert _normalize_keyby_draft(draft) == draft


def test_flatmap_normalizer_makes_world_support_authoritative():
    from app.services.event_state_proposition_keyby import (
        PropositionFlatMapDraftV01,
        UnitPlaneRouteV01,
        WorldPropositionDraftV01,
        _normalize_flatmap_draft,
        _validate_flatmap_draft,
    )
    draft=PropositionFlatMapDraftV01(
        unit_routes=(
            UnitPlaneRouteV01(
                support_key="N001",
                disposition="IDENTITY",
            ),
        ),
        world_propositions=(
            WorldPropositionDraftV01(
                statement="The system demonstrated Tetris-playing behavior.",
                support_keys=("N001",),
                primitive_family="DISPOSITION",
                referent_scope="TARGET_INTRINSIC",
            ),
        ),
    )
    normalized=_normalize_flatmap_draft(draft)
    assert normalized.unit_routes[0].disposition == "WORLD"
    _validate_flatmap_draft(
        draft=normalized,
        expected_new_keys={"N001"},
    )


def test_flatmap_normalizer_does_not_hide_world_without_proposition():
    import pytest
    from app.services.event_state_proposition_keyby import (
        PropositionFlatMapDraftV01,
        UnitPlaneRouteV01,
        _normalize_flatmap_draft,
        _validate_flatmap_draft,
    )
    draft=PropositionFlatMapDraftV01(
        unit_routes=(
            UnitPlaneRouteV01(
                support_key="N001",
                disposition="WORLD",
            ),
        ),
        world_propositions=(),
    )
    normalized=_normalize_flatmap_draft(draft)
    with pytest.raises(ValueError,match="WORLD N-key must support"):
        _validate_flatmap_draft(
            draft=normalized,
            expected_new_keys={"N001"},
        )


def test_referent_scope_requires_relation_family_for_target_relation():
    import pytest
    from app.services.event_state_proposition_keyby import WorldPropositionDraftV01
    with pytest.raises(ValueError, match="TARGET_RELATION proposition must use RELATION"):
        WorldPropositionDraftV01(
            statement="The target is integrated into an external workflow.",
            support_keys=("N001",),
            primitive_family="PROCESS",
            referent_scope="TARGET_RELATION",
        )


def test_relation_family_requires_target_relation_scope():
    import pytest
    from app.services.event_state_proposition_keyby import WorldPropositionDraftV01
    with pytest.raises(ValueError, match="RELATION proposition must use TARGET_RELATION"):
        WorldPropositionDraftV01(
            statement="The target is integrated into an external workflow.",
            support_keys=("N001",),
            primitive_family="RELATION",
            referent_scope="TARGET_INTRINSIC",
        )
