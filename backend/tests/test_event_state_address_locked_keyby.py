from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.services.event_observation import EventObservationV01
from app.services.event_state_address_locked_keyby import (
    AddressLockedSynthesisDraftV01,
    LockedCreateGroupV01,
    LockedExistingUpdateV01,
    _locked_to_semantic_draft,
    semantic_keyby_address_locked,
    validate_create_groups_semantically,
)
from app.services.event_state_proposition_keyby import (
    KeyByAddressPolicyV01,
    PropositionFlatMapResultV01,
    WorldPropositionV01,
)
from app.services.event_state_slot_delta import (
    CurrentSlotV01,
    SemanticSlotStateV01,
    slot_state_digest,
)


def _fixture():
    event_id = UUID("11111111-1111-1111-1111-111111111111")
    source_id = UUID("22222222-2222-2222-2222-222222222222")
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    slots = (
        CurrentSlotV01(
            slot_id="slot-performance",
            primitive_family="QUALITY",
            slot_label="Operational performance",
            state_question=(
                "What are this system's operational performance characteristics?"
            ),
            value="Existing performance.",
            support_refs=("old-performance",),
        ),
        CurrentSlotV01(
            slot_id="slot-reliability",
            primitive_family="QUALITY",
            slot_label="Reliability",
            state_question="What are this system's reliability characteristics?",
            value="Existing reliability.",
            support_refs=("old-reliability",),
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
        observation_key="obs-address-locked-001",
        source_id=source_id,
        evidence_time=now,
        ingest_time=now,
        provenance_digest="prov-address-locked",
        audited_semantic_unit_refs=("new-performance", "new-capability"),
    )
    flatmap = PropositionFlatMapResultV01(
        unit_routes=(),
        world_propositions=(
            WorldPropositionV01(
                proposition_id="prop-performance-0001",
                statement="The system now completes decisions in about 300 ms.",
                support_refs=("new-performance",),
                primitive_family="QUALITY",
                referent_scope="TARGET_INTRINSIC",
            ),
            WorldPropositionV01(
                proposition_id="prop-capability-0002",
                statement="The system is designed for a new decision role.",
                support_refs=("new-capability",),
                primitive_family="DISPOSITION",
                referent_scope="TARGET_INTRINSIC",
            ),
        ),
    )
    policy = KeyByAddressPolicyV01(
        authorized_existing_slot_ids_by_proposition={
            "prop-performance-0001": ("slot-performance",),
        },
        create_eligible_proposition_keys=("prop-capability-0002",),
    )
    return previous, observation, flatmap, policy


def _locked_chat(messages, **_kwargs):
    import json

    payload = json.loads(messages[-1]["content"].split("\n\n", 1)[1])
    assert {
        row["slot_key"]
        for row in payload["authorized_existing_groups"]
    } == {"S001"}
    assert payload["create_eligible_proposition_keys"] == ["P002"]
    return {
        "existing_updates": [
            {
                "slot_key": "S001",
                "proposition_keys": ["P001"],
                "value": "The system completes decisions in about 300 ms.",
                "retain_previous_support_keys": [],
                "contest": False,
                "rationale": "new performance measurement",
            }
        ],
        "create_groups": [
            {
                "proposition_keys": ["P002"],
                "primitive_family": "DISPOSITION",
                "slot_label": "Intended role",
                "state_question": (
                    "What roles or functions is this system designed to perform?"
                ),
                "value": "The system is designed for a new decision role.",
                "rationale": "new disposition coordinate",
            }
        ],
        "no_change_proposition_keys": [],
        "phase_change": None,
        "rationale": "address-locked synthesis",
    }, {}


def test_address_locked_synthesis_preserves_existing_identity_and_creates_only_create_group():
    previous, observation, flatmap, policy = _fixture()
    delta, draft, locked = semantic_keyby_address_locked(
        event_identity={"object": "system"},
        previous=previous,
        observation=observation,
        flatmap=flatmap,
        address_policy=policy,
        chat_fn=_locked_chat,
    )

    assert locked.existing_updates[0].slot_key == "S001"
    assert draft.mutations[0].target == "EXISTING"
    assert draft.mutations[0].existing_slot_key == "S001"
    assert draft.mutations[0].state_question == (
        "What are this system's operational performance characteristics?"
    )
    assert draft.mutations[1].target == "CREATE"
    assert delta is not None
    assert delta.mutations[0].slot.slot_id == "slot-performance"
    assert delta.mutations[0].slot.state_question == (
        "What are this system's operational performance characteristics?"
    )
    assert delta.mutations[1].mode == "CREATE"


def test_locked_draft_rejects_unauthorized_existing_slot():
    previous, _observation, flatmap, policy = _fixture()
    locked = AddressLockedSynthesisDraftV01(
        existing_updates=(
            LockedExistingUpdateV01(
                slot_key="S002",
                proposition_keys=("P001",),
                value="wrong address",
            ),
        ),
        create_groups=(
            LockedCreateGroupV01(
                proposition_keys=("P002",),
                primitive_family="DISPOSITION",
                slot_label="Intended role",
                state_question=(
                    "What roles or functions is this system designed to perform?"
                ),
                value="new role",
            ),
        ),
    )
    with pytest.raises(ValueError, match="unauthorized existing slot"):
        _locked_to_semantic_draft(
            locked=locked,
            previous=previous,
            flatmap=flatmap,
            address_policy=policy,
        )


def test_locked_draft_requires_every_create_proposition():
    previous, _observation, flatmap, policy = _fixture()
    locked = AddressLockedSynthesisDraftV01(
        existing_updates=(
            LockedExistingUpdateV01(
                slot_key="S001",
                proposition_keys=("P001",),
                value="updated performance",
            ),
        ),
        create_groups=(),
    )
    with pytest.raises(ValueError, match="every CREATE-eligible proposition"):
        _locked_to_semantic_draft(
            locked=locked,
            previous=previous,
            flatmap=flatmap,
            address_policy=policy,
        )


def test_locked_draft_rejects_create_family_mismatch():
    previous, _observation, flatmap, policy = _fixture()
    locked = AddressLockedSynthesisDraftV01(
        existing_updates=(
            LockedExistingUpdateV01(
                slot_key="S001",
                proposition_keys=("P001",),
                value="updated performance",
            ),
        ),
        create_groups=(
            LockedCreateGroupV01(
                proposition_keys=("P002",),
                primitive_family="STATE",
                slot_label="Wrong family",
                state_question="What is this system's current state?",
                value="wrong",
            ),
        ),
    )
    with pytest.raises(ValueError, match="primitive_family mismatch"):
        _locked_to_semantic_draft(
            locked=locked,
            previous=previous,
            flatmap=flatmap,
            address_policy=policy,
        )


def _group_validation_chat(messages, **_kwargs):
    import json

    payload = json.loads(messages[-1]["content"].split("\n\n", 1)[1])
    statement = payload["proposition"]["statement"].lower()
    question = payload["current_slot"]["state_question"].lower()
    if "integrated" in statement and "external systems" in question:
        decision = "DIRECT"
    elif "resembles" in statement and "broader system pattern" in question:
        decision = "DIRECT"
    else:
        decision = "NOT_DIRECT"
    return {
        "decision": decision,
        "rationale": "synthetic orthogonality check",
    }, {}


def test_create_group_semantic_validation_accepts_orthogonal_same_family_groups():
    flatmap = PropositionFlatMapResultV01(
        unit_routes=(),
        world_propositions=(
            WorldPropositionV01(
                proposition_id="prop-integration-0001",
                statement="The system is integrated into an external workflow.",
                support_refs=("r1",),
                primitive_family="RELATION",
                referent_scope="TARGET_RELATION",
            ),
            WorldPropositionV01(
                proposition_id="prop-resemblance-0002",
                statement="The combined system resembles a broader AI-native pattern.",
                support_refs=("r2",),
                primitive_family="RELATION",
                referent_scope="TARGET_RELATION",
            ),
        ),
    )
    locked = AddressLockedSynthesisDraftV01(
        create_groups=(
            LockedCreateGroupV01(
                proposition_keys=("P001",),
                primitive_family="RELATION",
                slot_label="External integration",
                state_question=(
                    "In what external systems or workflows is this system integrated?"
                ),
                value="external workflow",
            ),
            LockedCreateGroupV01(
                proposition_keys=("P002",),
                primitive_family="RELATION",
                slot_label="System resemblance",
                state_question=(
                    "What broader system pattern does this system resemble?"
                ),
                value="AI-native pattern",
            ),
        ),
    )
    result = validate_create_groups_semantically(
        event_identity={"object": "system"},
        flatmap=flatmap,
        locked=locked,
        chat_fn=_group_validation_chat,
        repeats=2,
        max_workers=4,
    )
    assert result.valid is True
    assert result.membership_failures == ()
    assert result.cross_overlap_findings == ()


def test_create_group_semantic_validation_rejects_unrouted_cross_direct():
    def overlap_chat(messages, **_kwargs):
        import json

        payload = json.loads(messages[-1]["content"].split("\n\n", 1)[1])
        statement = payload["proposition"]["statement"].lower()
        question = payload["current_slot"]["state_question"].lower()
        if "integrated" in statement and "external systems" in question:
            decision = "DIRECT"
        elif "resembles" in statement and "broader system pattern" in question:
            decision = "DIRECT"
        elif "resembles" in statement and "external systems" in question:
            decision = "DIRECT"
        else:
            decision = "NOT_DIRECT"
        return {
            "decision": decision,
            "rationale": "synthetic overlap check",
        }, {}

    flatmap = PropositionFlatMapResultV01(
        unit_routes=(),
        world_propositions=(
            WorldPropositionV01(
                proposition_id="prop-integration-0001",
                statement="The system is integrated into an external workflow.",
                support_refs=("r1",),
                primitive_family="RELATION",
                referent_scope="TARGET_RELATION",
            ),
            WorldPropositionV01(
                proposition_id="prop-resemblance-0002",
                statement="The combined system resembles a broader AI-native pattern.",
                support_refs=("r2",),
                primitive_family="RELATION",
                referent_scope="TARGET_RELATION",
            ),
        ),
    )
    locked = AddressLockedSynthesisDraftV01(
        create_groups=(
            LockedCreateGroupV01(
                proposition_keys=("P001",),
                primitive_family="RELATION",
                slot_label="External integration",
                state_question=(
                    "In what external systems or workflows is this system integrated?"
                ),
                value="external workflow",
            ),
            LockedCreateGroupV01(
                proposition_keys=("P002",),
                primitive_family="RELATION",
                slot_label="System resemblance",
                state_question=(
                    "What broader system pattern does this system resemble?"
                ),
                value="AI-native pattern",
            ),
        ),
    )
    result = validate_create_groups_semantically(
        event_identity={"object": "system"},
        flatmap=flatmap,
        locked=locked,
        chat_fn=overlap_chat,
        repeats=2,
        max_workers=4,
    )
    assert result.valid is False
    assert result.cross_overlap_findings == ("P002->C001",)
