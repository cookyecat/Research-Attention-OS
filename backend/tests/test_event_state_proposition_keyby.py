from app.services.event_state_proposition_keyby import (
    KeyByMutationDraftV01,
    PropositionRouteV01,
    SemanticKeyByDraftV01,
    _create_expansion_proposition_keys,
    _normalize_keyby_draft,
    _validate_address_policy,
    _validate_candidate_authorization,
    PropositionFlatMapResultV01,
    WorldPropositionV01,
    semantic_keyby_candidate_aware,
    semantic_keyby_pairwise_guarded,
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


def _existing_mutation(slot_key: str) -> KeyByMutationDraftV01:
    return KeyByMutationDraftV01(
        target="EXISTING",
        existing_slot_key=slot_key,
        primitive_family="QUALITY",
        slot_label="Operational performance",
        state_question="What are this system's operational performance characteristics?",
        value="updated performance",
    )


def test_candidate_authorization_rejects_existing_target_outside_topk():
    import pytest

    draft = SemanticKeyByDraftV01(
        mutations=(_existing_mutation("S002"),),
        proposition_routes=(
            PropositionRouteV01(
                proposition_key="P001",
                disposition="WORLD_MUTATION",
                mutation_indices=(0,),
            ),
        ),
    )
    with pytest.raises(ValueError, match="outside candidate authorization"):
        _validate_candidate_authorization(
            draft=draft,
            candidate_slot_keys_by_proposition={
                "P001": {"S001"},
            },
        )


def test_shared_existing_mutation_requires_authorization_from_every_proposition():
    import pytest

    draft = SemanticKeyByDraftV01(
        mutations=(_existing_mutation("S002"),),
        proposition_routes=(
            PropositionRouteV01(
                proposition_key="P001",
                disposition="WORLD_MUTATION",
                mutation_indices=(0,),
            ),
            PropositionRouteV01(
                proposition_key="P002",
                disposition="WORLD_MUTATION",
                mutation_indices=(0,),
            ),
        ),
    )
    with pytest.raises(ValueError, match="P002"):
        _validate_candidate_authorization(
            draft=draft,
            candidate_slot_keys_by_proposition={
                "P001": {"S002"},
                "P002": {"S003"},
            },
        )

    _validate_candidate_authorization(
        draft=draft,
        candidate_slot_keys_by_proposition={
            "P001": {"S002"},
            "P002": {"S002", "S003"},
        },
    )


def test_create_with_hidden_same_family_slot_is_provisional():
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
    assert _create_expansion_proposition_keys(
        draft=draft,
        hidden_same_family_slot_keys_by_proposition={
            "P001": {"S003"},
        },
    ) == ("P001",)

    assert _create_expansion_proposition_keys(
        draft=draft,
        hidden_same_family_slot_keys_by_proposition={
            "P001": set(),
        },
    ) == ()


def _ks_e_fixture():
    from datetime import datetime, timezone
    from uuid import UUID

    from app.services.event_observation import EventObservationV01
    from app.services.event_state_slot_delta import (
        CurrentSlotV01,
        SemanticSlotStateV01,
        slot_state_digest,
    )

    event_id = UUID("11111111-1111-1111-1111-111111111111")
    source_id = UUID("22222222-2222-2222-2222-222222222222")
    now = datetime(2026, 9, 23, tzinfo=timezone.utc)
    slots = (
        CurrentSlotV01(
            slot_id="slot-0001-performance",
            primitive_family="QUALITY",
            slot_label="Operational performance",
            state_question="What are this system's operational performance characteristics?",
            value="Existing performance.",
            support_refs=("old-performance",),
        ),
        CurrentSlotV01(
            slot_id="slot-0002-reliability",
            primitive_family="QUALITY",
            slot_label="Reliability",
            state_question="What are this system's reliability characteristics?",
            value="Existing reliability.",
            support_refs=("old-reliability",),
        ),
        CurrentSlotV01(
            slot_id="slot-0003-correctness",
            primitive_family="QUALITY",
            slot_label="Correctness",
            state_question="How correct and valid are this system's outputs?",
            value="Existing correctness.",
            support_refs=("old-correctness",),
        ),
    )
    previous = SemanticSlotStateV01(
        event_id=event_id,
        slots=slots,
        status="ACTIVE",
        effective_at=now,
        state_digest=slot_state_digest(
            event_id=event_id,
            slots=slots,
            status="ACTIVE",
            effective_at=now,
        ),
    )
    observation = EventObservationV01(
        event_id=event_id,
        observation_key="observation-key-0001",
        source_id=source_id,
        evidence_time=now,
        ingest_time=now,
        provenance_digest="provenance-test",
        audited_semantic_unit_refs=("new-performance",),
    )
    flatmap = PropositionFlatMapResultV01(
        unit_routes=(),
        world_propositions=(
            WorldPropositionV01(
                proposition_id="proposition-performance-0001",
                statement="The system now completes decisions in about 300 ms.",
                support_refs=("new-performance",),
                primitive_family="QUALITY",
                referent_scope="TARGET_INTRINSIC",
            ),
        ),
    )
    return previous, observation, flatmap


def _ks_e_retriever():
    from app.services.semantic_coordinate.retrieval import CoordinateCandidateRetriever

    def fake_embed(texts):
        vectors = []
        for text in texts:
            low = text.lower()
            if "reliability" in low:
                vectors.append([1.0, 0.0])
            elif "operational performance" in low:
                vectors.append([0.9, 0.1])
            elif "correct" in low:
                vectors.append([0.0, 1.0])
            else:
                vectors.append([1.0, 0.0])
        return vectors, "fake-embedding"

    return CoordinateCandidateRetriever(fake_embed)


def _ks_e_chat(messages, **_kwargs):
    import json

    payload = json.loads(messages[-1]["content"].split("\n\n", 1)[1])
    visible = {row["slot_key"] for row in payload["previous_slots"]}
    if "S001" in visible:
        mutation = {
            "target": "EXISTING",
            "existing_slot_key": "S001",
            "primitive_family": "QUALITY",
            "slot_label": "Operational performance",
            "state_question": "What are this system's operational performance characteristics?",
            "value": "The system now completes decisions in about 300 ms.",
            "retain_previous_support_keys": [],
            "contest": False,
            "rationale": "Directly updates operational performance.",
        }
    else:
        mutation = {
            "target": "CREATE",
            "existing_slot_key": None,
            "primitive_family": "QUALITY",
            "slot_label": "Task completion time",
            "state_question": "How quickly can this system complete a task?",
            "value": "The system now completes decisions in about 300 ms.",
            "retain_previous_support_keys": [],
            "contest": False,
            "rationale": "No visible candidate directly answers the proposition.",
        }
    return {
        "contract": "event-semantic-keyby-v0.6",
        "mutations": [mutation],
        "proposition_routes": [{
            "proposition_key": "P001",
            "disposition": "WORLD_MUTATION",
            "mutation_indices": [0],
            "rationale": "Routes the proposition.",
        }],
        "phase_change": None,
        "rationale": "test",
    }, {}


def test_candidate_aware_shadow_records_topk_miss_without_changing_full_keyby():
    previous, observation, flatmap = _ks_e_fixture()
    result = semantic_keyby_candidate_aware(
        event_identity={"object": "Jev"},
        previous=previous,
        observation=observation,
        flatmap=flatmap,
        chat_fn=_ks_e_chat,
        mode="SHADOW",
        candidate_top_k=1,
        candidate_retriever=_ks_e_retriever(),
    )

    assert result.expansion_triggered is False
    assert result.draft.mutations[0].target == "EXISTING"
    assert result.draft.mutations[0].existing_slot_key == "S001"
    assert result.shadow_unauthorized_existing_routes == ("P001:S001",)
    assert result.initial_context.visible_slot_keys == ("S002",)


def test_candidate_aware_constrained_create_is_expanded_then_reused():
    previous, observation, flatmap = _ks_e_fixture()
    result = semantic_keyby_candidate_aware(
        event_identity={"object": "Jev"},
        previous=previous,
        observation=observation,
        flatmap=flatmap,
        chat_fn=_ks_e_chat,
        mode="CONSTRAINED",
        candidate_top_k=1,
        candidate_retriever=_ks_e_retriever(),
    )

    assert result.expansion_triggered is True
    assert result.expanded_proposition_keys == ("P001",)
    assert result.initial_context.visible_slot_keys == ("S002",)
    assert result.final_context.visible_slot_keys == ("S001", "S002", "S003")
    assert result.draft.mutations[0].target == "EXISTING"
    assert result.draft.mutations[0].existing_slot_key == "S001"
    assert result.delta is not None
    assert result.delta.mutations[0].mode == "UPSERT"


def test_address_policy_rejects_changed_existing_address():
    import pytest

    draft = SemanticKeyByDraftV01(
        mutations=(_existing_mutation("S002"),),
        proposition_routes=(
            PropositionRouteV01(
                proposition_key="P001",
                disposition="WORLD_MUTATION",
                mutation_indices=(0,),
            ),
        ),
    )
    with pytest.raises(ValueError, match="changed pairwise-authorized address"):
        _validate_address_policy(
            draft=draft,
            authorized_existing_slot_keys_by_proposition={"P001": ("S001",)},
            create_eligible_proposition_keys=set(),
        )


def test_address_policy_rejects_create_for_reuse_authorized_proposition():
    import pytest

    draft = SemanticKeyByDraftV01(
        mutations=(_mutation("new-performance"),),
        proposition_routes=(
            PropositionRouteV01(
                proposition_key="P001",
                disposition="WORLD_MUTATION",
                mutation_indices=(0,),
            ),
        ),
    )
    with pytest.raises(ValueError, match="CREATE for REUSE-authorized"):
        _validate_address_policy(
            draft=draft,
            authorized_existing_slot_keys_by_proposition={"P001": ("S001",)},
            create_eligible_proposition_keys=set(),
        )


def test_address_policy_rejects_existing_for_create_only_proposition():
    import pytest

    draft = SemanticKeyByDraftV01(
        mutations=(_existing_mutation("S001"),),
        proposition_routes=(
            PropositionRouteV01(
                proposition_key="P001",
                disposition="WORLD_MUTATION",
                mutation_indices=(0,),
            ),
        ),
    )
    with pytest.raises(ValueError, match="EXISTING for CREATE-only"):
        _validate_address_policy(
            draft=draft,
            authorized_existing_slot_keys_by_proposition={},
            create_eligible_proposition_keys={"P001"},
        )


def test_address_policy_rejects_no_change_for_create_eligible_proposition():
    import pytest

    draft = SemanticKeyByDraftV01(
        mutations=(),
        proposition_routes=(
            PropositionRouteV01(
                proposition_key="P001",
                disposition="NO_WORLD_VALUE_CHANGE",
            ),
        ),
    )
    with pytest.raises(ValueError, match="cannot be dropped"):
        _validate_address_policy(
            draft=draft,
            authorized_existing_slot_keys_by_proposition={},
            create_eligible_proposition_keys={"P001"},
        )


def test_address_policy_allows_no_change_on_authorized_existing_coordinate():
    draft = SemanticKeyByDraftV01(
        mutations=(),
        proposition_routes=(
            PropositionRouteV01(
                proposition_key="P001",
                disposition="NO_WORLD_VALUE_CHANGE",
            ),
        ),
    )
    _validate_address_policy(
        draft=draft,
        authorized_existing_slot_keys_by_proposition={"P001": ("S001",)},
        create_eligible_proposition_keys=set(),
    )


def _ks_e_pairwise_chat(messages, **kwargs):
    import json

    system = messages[0]["content"]
    if "batched pairwise Direct-Answer Gate" in system:
        payload = json.loads(
            messages[-1]["content"].split("\n\n", 1)[1]
        )
        judgments = []
        for pair in payload["pairs"]:
            question = (
                pair["current_slot"]["state_question"].lower()
            )
            if "operational performance" in question:
                decision = "DIRECT"
                rationale = (
                    "300 ms is a concrete operational-performance value."
                )
            else:
                decision = "NOT_DIRECT"
                rationale = "This slot asks a different QUALITY question."
            judgments.append({
                "pair_key": pair["pair_key"],
                "decision": decision,
                "rationale": rationale,
            })
        return {"judgments": judgments}, {}

    if "pairwise Direct-Answer Gate" in system:
        payload = json.loads(
            messages[-1]["content"].split("\n\n", 1)[1]
        )
        question = payload["current_slot"]["state_question"].lower()
        if "operational performance" in question:
            decision = "DIRECT"
            rationale = "300 ms is a concrete operational-performance value."
        else:
            decision = "NOT_DIRECT"
            rationale = "This slot asks a different QUALITY question."
        return {
            "decision": decision,
            "rationale": rationale,
        }, {}
    return _ks_e_chat(messages, **kwargs)


def test_pairwise_guarded_keyby_recovers_from_wrong_top1_and_binds_address():
    previous, observation, flatmap = _ks_e_fixture()
    result = semantic_keyby_pairwise_guarded(
        event_identity={"object": "Jev"},
        previous=previous,
        observation=observation,
        flatmap=flatmap,
        chat_fn=_ks_e_pairwise_chat,
        pairwise_chat_fn=_ks_e_pairwise_chat,
        candidate_top_k=1,
        candidate_retriever=_ks_e_retriever(),
        pairwise_repeats=2,
    )

    proposition_id = "proposition-performance-0001"
    assert result.candidate_context.visible_slot_keys == ("S002",)
    pair = result.pairwise_plan.propositions[0]
    assert pair.proposition_id == proposition_id
    assert pair.initial_candidate_slot_ids == ("slot-0002-reliability",)
    assert pair.expansion_triggered is True
    assert pair.resolution.status == "REUSE_AUTHORIZED"
    assert (
        pair.resolution.authorized_existing_slot_id
        == "slot-0001-performance"
    )
    assert result.address_policy.authorized_existing_slot_key_by_proposition == {
        proposition_id: "slot-0001-performance"
    }
    assert result.address_policy.create_eligible_proposition_keys == ()
    assert result.draft.mutations[0].target == "EXISTING"
    assert result.draft.mutations[0].existing_slot_key == "S001"
    assert result.delta is not None
    assert result.delta.mutations[0].mode == "UPSERT"
    assert (
        result.delta.mutations[0].slot.slot_id
        == "slot-0001-performance"
    )


def test_address_policy_allows_multiple_authorized_existing_targets():
    draft = SemanticKeyByDraftV01(
        mutations=(
            _existing_mutation("S001"),
            _existing_mutation("S002"),
        ),
        proposition_routes=(
            PropositionRouteV01(
                proposition_key="P001",
                disposition="WORLD_MUTATION",
                mutation_indices=(0, 1),
            ),
        ),
    )
    _validate_address_policy(
        draft=draft,
        authorized_existing_slot_keys_by_proposition={
            "P001": ("S001", "S002"),
        },
        create_eligible_proposition_keys=set(),
    )


def test_address_policy_rejects_existing_target_outside_authorized_set():
    import pytest

    draft = SemanticKeyByDraftV01(
        mutations=(
            _existing_mutation("S001"),
            _existing_mutation("S003"),
        ),
        proposition_routes=(
            PropositionRouteV01(
                proposition_key="P001",
                disposition="WORLD_MUTATION",
                mutation_indices=(0, 1),
            ),
        ),
    )
    with pytest.raises(ValueError, match="authorized address set"):
        _validate_address_policy(
            draft=draft,
            authorized_existing_slot_keys_by_proposition={
                "P001": ("S001", "S002"),
            },
            create_eligible_proposition_keys=set(),
        )


def test_pairwise_guarded_parallel_transport_matches_serial_fixture():
    previous, observation, flatmap = _ks_e_fixture()
    result = semantic_keyby_pairwise_guarded(
        event_identity={"object": "Jev"},
        previous=previous,
        observation=observation,
        flatmap=flatmap,
        chat_fn=_ks_e_pairwise_chat,
        pairwise_chat_fn=_ks_e_pairwise_chat,
        candidate_top_k=1,
        candidate_retriever=_ks_e_retriever(),
        pairwise_repeats=2,
        pairwise_transport="PARALLEL",
        pairwise_max_workers=4,
    )

    proposition_id = "proposition-performance-0001"
    assert result.pairwise_transport == "PARALLEL"
    assert result.candidate_context.visible_slot_keys == ("S002",)
    pair = result.pairwise_plan.propositions[0]
    assert pair.expansion_triggered is True
    assert pair.resolution.status == "REUSE_AUTHORIZED"
    assert pair.resolution.authorized_existing_slot_ids == (
        "slot-0001-performance",
    )
    assert (
        result.address_policy
        .authorized_existing_slot_ids_by_proposition
        == {
            proposition_id: ("slot-0001-performance",),
        }
    )
    assert result.draft.mutations[0].target == "EXISTING"
    assert result.draft.mutations[0].existing_slot_key == "S001"
    assert result.delta is not None
    assert result.delta.mutations[0].mode == "UPSERT"


def test_pairwise_guarded_batch_transport_matches_serial_fixture():
    previous, observation, flatmap = _ks_e_fixture()
    result = semantic_keyby_pairwise_guarded(
        event_identity={"object": "Jev"},
        previous=previous,
        observation=observation,
        flatmap=flatmap,
        chat_fn=_ks_e_pairwise_chat,
        pairwise_chat_fn=_ks_e_pairwise_chat,
        candidate_top_k=1,
        candidate_retriever=_ks_e_retriever(),
        pairwise_repeats=2,
        pairwise_transport="BATCH",
    )

    proposition_id = "proposition-performance-0001"
    assert result.pairwise_transport == "BATCH"
    assert result.candidate_context.visible_slot_keys == ("S002",)
    pair = result.pairwise_plan.propositions[0]
    assert pair.expansion_triggered is True
    assert pair.resolution.status == "REUSE_AUTHORIZED"
    assert pair.resolution.authorized_existing_slot_ids == (
        "slot-0001-performance",
    )
    assert (
        result.address_policy
        .authorized_existing_slot_ids_by_proposition
        == {
            proposition_id: ("slot-0001-performance",),
        }
    )
    assert result.draft.mutations[0].target == "EXISTING"
    assert result.draft.mutations[0].existing_slot_key == "S001"
    assert result.delta is not None
    assert result.delta.mutations[0].mode == "UPSERT"
