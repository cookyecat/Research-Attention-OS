from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.event import Event, EventMembershipAssertion
from app.models.source import Source
from app.services.event_observation import EventObservationV01
from app.services.event_state_slot_delta import (
    CurrentSlotV01,
    SlotDeltaV01,
    SlotMutationV01,
    apply_slot_delta,
)


def _event(db):
    row = Event(
        title="Jev model launch / emergence and early validation episode",
        event_type="MODEL_LAUNCH_EARLY_VALIDATION",
        actors=["Jev authors"],
        action="launch, explain, test, and early-validate Jev",
        object="Jev model",
        summary="Jev episode",
        confidence=0.5,
        status="CANDIDATE",
    )
    db.add(row)
    db.flush()
    return row


def _source(db, label):
    row = Source(
        source_type="TEXT",
        title=label,
        content_text=label,
        fingerprint=f"slot-delta-{uuid4()}",
        ingestion_method="TEST",
        raw_metadata={},
    )
    db.add(row)
    db.flush()
    return row
def _member(db, event, source, local=False):
    db.add(
        EventMembershipAssertion(
            workspace_id="local-default",
            event_id=event.id,
            source_id=source.id,
            frame_ids=[],
            action="ASSERT",
            membership="REPORTS_EVENT",
            contextual_role_fields={},
            audit_run_id=None,
            authority_policy_version="slot-delta-test",
            authority_epoch=1,
            authority_status="AUTHORIZED_SOURCE_LOCAL" if local else "AUTHORIZED",
            supersedes_assertion_id=None,
        )
    )
    db.flush()


def _obs(event, source, key, refs, day):
    return EventObservationV01(
        event_id=event.id,
        observation_key=key * 64,
        source_id=source.id,
        semantic_input_digests=(f"sem-{key}",),
        evidence_time=datetime(2026, 9, day, 12, 0, tzinfo=timezone.utc),
        ingest_time=datetime(2026, 9, day, 12, 1, tzinfo=timezone.utc),
        provenance_digest=f"prov-{key}",
        audited_semantic_unit_refs=refs,
    )


def _infer_family(label, question=""):
    text=f"{label} {question}".lower()
    if any(token in text for token in ("release","availability","lifecycle","phase","status")):
        return "STATE"
    if any(token in text for token in ("mechanism","architecture","process","transform")):
        return "PROCESS"
    if any(token in text for token in ("output form","interface","representation","typed structured")):
        return "FORM"
    if any(token in text for token in ("capability","demonstrat","behavior","function")):
        return "DISPOSITION"
    if any(token in text for token in ("application","affordance","suitab","role","context")):
        return "RELATION"
    if any(token in text for token in ("performance","latency","speed","cost","reliab","valid","correct","quality","validation")):
        return "QUALITY"
    if any(token in text for token in ("structure","composition","topology")):
        return "STRUCTURE"
    return "OTHER"


def _slot(slot_id, label, question, value, refs, primitive_family=None):
    return CurrentSlotV01(
        slot_id=slot_id,
        primitive_family=primitive_family or _infer_family(label, question),
        slot_label=label,
        state_question=question,
        value=value,
        support_refs=refs,
    )
def test_create_initial_slot(db):
    event = _event(db)
    a = _source(db, "launch")
    _member(db, event, a, local=True)
    result = apply_slot_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uLaunch",), 16),
        delta=SlotDeltaV01(
            mutations=(
                SlotMutationV01(
                    mode="CREATE",
                    slot=_slot(
                        "slot0001",
                        "identity_release",
                        "What is Jev and what is its release status?",
                        "Jev has been publicly released.",
                        ("uLaunch",),
                    ),
                ),
            ),
        ),
        supporting_source_ids=[a.id],
    )
    assert result.slot_state.status == "EMERGING"
    assert len(result.slot_state.slots) == 1
    assert result.slot_state.slots[0].slot_id == "slot0001"


def test_existing_key_upsert_reuses_slot_id(db):
    event = _event(db)
    a = _source(db, "launch")
    b = _source(db, "release detail")
    _member(db, event, a, local=True)
    _member(db, event, b)
    first = apply_slot_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uLaunch",), 16),
        delta=SlotDeltaV01(
            mutations=(SlotMutationV01(
                mode="CREATE",
                slot=_slot("slot0001","identity_release","What is Jev and what is its release status?","Jev has been released.",("uLaunch",)),
            ),),
        ),
        supporting_source_ids=[a.id],
    )
    second = apply_slot_delta(
        db,
        event_id=event.id,
        previous=first.slot_state,
        observation=_obs(event, b, "b", ("uHF",), 17),
        delta=SlotDeltaV01(
            mutations=(SlotMutationV01(
                mode="UPSERT",
                slot=_slot(
                    "slot0001",
                    "identity_release",
                    "What is Jev and what is its release status?",
                    "Jev has been released on Hugging Face.",
                    ("uHF",),
                ),
            ),),
        ),
        supporting_source_ids=[a.id, b.id],
    )
    assert len(second.slot_state.slots) == 1
    assert second.slot_state.slots[0].slot_id == "slot0001"
    assert "Hugging Face" in second.slot_state.slots[0].value
    assert second.slot_state.status == "ACTIVE"


def test_new_dimension_creates_second_slot(db):
    event = _event(db)
    a = _source(db, "launch")
    b = _source(db, "performance")
    _member(db, event, a, local=True)
    _member(db, event, b)
    first = apply_slot_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uLaunch",), 16),
        delta=SlotDeltaV01(
            mutations=(SlotMutationV01(
                mode="CREATE",
                slot=_slot("slot0001","identity_release","What is Jev and what is its release status?","Jev has been released.",("uLaunch",)),
            ),),
        ),
        supporting_source_ids=[a.id],
    )
    second = apply_slot_delta(
        db,
        event_id=event.id,
        previous=first.slot_state,
        observation=_obs(event, b, "b", ("uPerf",), 17),
        delta=SlotDeltaV01(
            mutations=(SlotMutationV01(
                mode="CREATE",
                slot=_slot("slot0002","performance","What are Jev's performance characteristics?","Jev is claimed to be much faster and cheaper.",("uPerf",)),
            ),),
        ),
        supporting_source_ids=[a.id, b.id],
    )
    assert {s.slot_id for s in second.slot_state.slots} == {"slot0001","slot0002"}
def test_one_observation_can_update_multiple_slots(db):
    event = _event(db)
    a = _source(db, "initial")
    b = _source(db, "benchmark")
    _member(db, event, a, local=True)
    _member(db, event, b)
    first = apply_slot_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uA",), 16),
        delta=SlotDeltaV01(
            mutations=(
                SlotMutationV01(
                    mode="CREATE",
                    slot=_slot("slot0001","performance","How fast is Jev?","Jev is claimed fast.",("uA",)),
                ),
                SlotMutationV01(
                    mode="CREATE",
                    slot=_slot("slot0002","validation","How well validated is Jev?","Validation is limited.",("uA",)),
                ),
            ),
        ),
        supporting_source_ids=[a.id],
    )
    second = apply_slot_delta(
        db,
        event_id=event.id,
        previous=first.slot_state,
        observation=_obs(event, b, "b", ("uBench",), 17),
        delta=SlotDeltaV01(
            mutations=(
                SlotMutationV01(
                    mode="UPSERT",
                    slot=_slot("slot0001","performance","How fast is Jev?","A benchmark reports faster per-move latency.",("uBench",)),
                ),
                SlotMutationV01(
                    mode="UPSERT",
                    slot=_slot("slot0002","validation","How well validated is Jev?","At least one benchmark now exists, but broader validation remains limited.",("uBench",)),
                ),
            ),
        ),
        supporting_source_ids=[a.id,b.id],
    )
    assert len(second.slot_state.slots) == 2
    assert {s.support_refs for s in second.slot_state.slots} == {("uBench",)}
def test_none_preserves_slots_but_evidence_advances(db):
    event = _event(db)
    a = _source(db, "launch")
    b = _source(db, "reaction")
    _member(db, event, a, local=True)
    _member(db, event, b)
    first = apply_slot_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uLaunch",), 16),
        delta=SlotDeltaV01(
            mutations=(SlotMutationV01(
                mode="CREATE",
                slot=_slot("slot0001","identity_release","What is Jev and what is its release status?","Jev was released.",("uLaunch",)),
            ),),
        ),
        supporting_source_ids=[a.id],
    )
    second = apply_slot_delta(
        db,
        event_id=event.id,
        previous=first.slot_state,
        observation=_obs(event, b, "b", (), 17),
        delta=None,
        supporting_source_ids=[a.id,b.id],
    )
    assert second.slot_state == first.slot_state
    assert second.event_state.world_state == first.event_state.world_state
    assert second.event_state.evidence_state.member_source_count == 2


def test_correction_upserts_same_slot_identity(db):
    event = _event(db)
    a = _source(db, "old")
    b = _source(db, "correction")
    _member(db,event,a,local=True)
    _member(db,event,b)
    first = apply_slot_delta(
        db,event_id=event.id,previous=None,
        observation=_obs(event,a,"a",("uOld",),16),
        delta=SlotDeltaV01(mutations=(SlotMutationV01(
            mode="CREATE",
            slot=_slot("slot0001","architecture","What architecture does Jev use?","Jev uses architecture A.",("uOld",)),
        ),)),
        supporting_source_ids=[a.id],
    )
    second = apply_slot_delta(
        db,event_id=event.id,previous=first.slot_state,
        observation=_obs(event,b,"b",("uNew",),17),
        delta=SlotDeltaV01(mutations=(SlotMutationV01(
            mode="UPSERT",
            slot=_slot("slot0001","architecture","What architecture does Jev use?","The authors corrected the description: Jev uses architecture B.",("uNew",)),
        ),)),
        supporting_source_ids=[a.id,b.id],
    )
    assert len(second.slot_state.slots) == 1
    assert second.slot_state.slots[0].slot_id == "slot0001"
    assert second.slot_state.slots[0].support_refs == ("uNew",)
def test_contest_stays_on_same_slot(db):
    event = _event(db)
    a = _source(db, "positive")
    b = _source(db, "negative")
    _member(db,event,a,local=True)
    _member(db,event,b)
    first = apply_slot_delta(
        db,event_id=event.id,previous=None,
        observation=_obs(event,a,"a",("uPos",),16),
        delta=SlotDeltaV01(mutations=(SlotMutationV01(
            mode="CREATE",
            slot=_slot("slot0001","validation","What is the validation status?","A reproduction reports a strong gain.",("uPos",)),
        ),)),
        supporting_source_ids=[a.id],
    )
    second = apply_slot_delta(
        db,event_id=event.id,previous=first.slot_state,
        observation=_obs(event,b,"b",("uNeg",),17),
        delta=SlotDeltaV01(mutations=(SlotMutationV01(
            mode="CONTEST",
            slot=_slot(
                "slot0001",
                "validation",
                "What is the validation status?",
                "Validation is contested: one reproduction reports a strong gain while another fails under comparable conditions.",
                ("uPos","uNeg"),
            ),
        ),)),
        supporting_source_ids=[a.id,b.id],
    )
    assert len(second.slot_state.slots) == 1
    assert second.slot_state.status == "CONTESTED"
    assert second.slot_state.slots[0].support_refs == ("uNeg","uPos")


def test_persisted_slot_delta_replays_identically(db):
    event = _event(db)
    a = _source(db,"launch")
    b = _source(db,"perf")
    _member(db,event,a,local=True)
    _member(db,event,b)
    obs_a=_obs(event,a,"a",("uA",),16)
    obs_b=_obs(event,b,"b",("uB",),17)
    d1=SlotDeltaV01(mutations=(SlotMutationV01(
        mode="CREATE",
        slot=_slot("slot0001","identity","What is Jev?","Jev launched.",("uA",)),
    ),))
    d2=SlotDeltaV01(mutations=(SlotMutationV01(
        mode="CREATE",
        slot=_slot("slot0002","performance","How does Jev perform?","Jev is claimed fast.",("uB",)),
    ),))
    o1=apply_slot_delta(db,event_id=event.id,previous=None,observation=obs_a,delta=d1,supporting_source_ids=[a.id])
    o2=apply_slot_delta(db,event_id=event.id,previous=o1.slot_state,observation=obs_b,delta=d2,supporting_source_ids=[a.id,b.id])
    r1=apply_slot_delta(db,event_id=event.id,previous=None,observation=obs_a,delta=SlotDeltaV01.model_validate(d1.model_dump(mode="json")),supporting_source_ids=[a.id])
    r2=apply_slot_delta(db,event_id=event.id,previous=r1.slot_state,observation=obs_b,delta=SlotDeltaV01.model_validate(d2.model_dump(mode="json")),supporting_source_ids=[a.id,b.id])
    assert r2.slot_state.state_digest == o2.slot_state.state_digest
    assert r2.event_state.state_digest == o2.event_state.state_digest
    assert r2 == o2


def test_rejects_unknown_upsert_slot(db):
    event=_event(db)
    a=_source(db,"x")
    _member(db,event,a,local=True)
    with pytest.raises(ValueError,match="First slot transition may contain only CREATE"):
        apply_slot_delta(
            db,event_id=event.id,previous=None,
            observation=_obs(event,a,"a",("uA",),16),
            delta=SlotDeltaV01(mutations=(SlotMutationV01(
                mode="UPSERT",
                slot=_slot("slot9999","x","x?","x",("uA",)),
            ),)),
            supporting_source_ids=[a.id],
        )


def test_existing_slot_question_is_immutable(db):
    event=_event(db)
    a=_source(db,"a")
    b=_source(db,"b")
    _member(db,event,a,local=True)
    _member(db,event,b)
    first=apply_slot_delta(
        db,event_id=event.id,previous=None,
        observation=_obs(event,a,"a",("uA",),16),
        delta=SlotDeltaV01(mutations=(SlotMutationV01(
            mode="CREATE",
            slot=_slot("slot0001","release","What is Jev's release status?","Jev released.",("uA",)),
        ),)),
        supporting_source_ids=[a.id],
    )
    with pytest.raises(ValueError,match="state_question is immutable"):
        apply_slot_delta(
            db,event_id=event.id,previous=first.slot_state,
            observation=_obs(event,b,"b",("uB",),17),
            delta=SlotDeltaV01(mutations=(SlotMutationV01(
                mode="UPSERT",
                slot=_slot(
                    "slot0001",
                    "release and performance",
                    "What is Jev's release status and performance?",
                    "Jev released and is fast.",
                    ("uA","uB"),
                ),
            ),)),
            supporting_source_ids=[a.id,b.id],
        )


def _draft_mutation(
    *,
    label="performance",
    support_keys=("N001",),
    primitive_family=None,
):
    from app.services.event_state_slot_delta import DraftSlotMutationV01
    return DraftSlotMutationV01(
        target="CREATE",
        primitive_family=primitive_family or _infer_family(label),
        slot_label=label,
        state_question=f"What are the {label} characteristics of this system?",
        value=f"Reported {label} value.",
        support_keys=support_keys,
    )


def _ledger(
    *,
    key,
    proposition=None,
    disposition="WORLD_MUTATION",
    primitive_family="QUALITY",
    indices=(0,),
):
    from app.services.event_state_slot_delta import NewEvidencePropositionV01
    return NewEvidencePropositionV01(
        support_key=key,
        proposition=proposition or f"Atomic proposition from {key}.",
        disposition=disposition,
        primitive_family=(
            primitive_family if disposition == "WORLD_MUTATION" else None
        ),
        mutation_indices=indices,
    )


def test_evidence_projection_allows_one_unit_to_update_multiple_world_axes():
    from app.services.event_state_slot_delta import (
        SlotDeltaDraftV01,
        _normalize_mutation_support_by_projection,
        _validate_evidence_projection,
    )
    draft=SlotDeltaDraftV01(
        mutations=(
            _draft_mutation(
                label="capability",
                support_keys=(),
                primitive_family="DISPOSITION",
            ),
            _draft_mutation(
                label="performance",
                support_keys=(),
                primitive_family="QUALITY",
            ),
        ),
        evidence_projection=(
            _ledger(
                key="N001",
                proposition="The system demonstrated a capability.",
                primitive_family="DISPOSITION",
                indices=(0,),
            ),
            _ledger(
                key="N001",
                proposition="The system achieved a performance result.",
                primitive_family="QUALITY",
                indices=(1,),
            ),
        ),
    )
    normalized=_normalize_mutation_support_by_projection(
        draft=draft,
        expected_new_keys={"N001"},
    )
    _validate_evidence_projection(
        draft=normalized,
        expected_new_keys={"N001"},
    )


def test_evidence_projection_rejects_missing_new_key():
    from app.services.event_state_slot_delta import (
        SlotDeltaDraftV01,
        _validate_evidence_projection,
    )
    draft=SlotDeltaDraftV01(
        mutations=(_draft_mutation(),),
        evidence_projection=(_ledger(key="N001"),),
    )
    with pytest.raises(ValueError,match="cover every NEW support key"):
        _validate_evidence_projection(
            draft=draft,
            expected_new_keys={"N001","N002"},
        )


def test_evidence_projection_allows_one_unit_to_split_into_multiple_propositions():
    from app.services.event_state_slot_delta import (
        SlotDeltaDraftV01,
        _normalize_mutation_support_by_projection,
        _validate_evidence_projection,
    )
    draft=SlotDeltaDraftV01(
        mutations=(
            _draft_mutation(label="output form",support_keys=()),
            _draft_mutation(label="reliability",support_keys=()),
        ),
        evidence_projection=(
            _ledger(
                key="N001",
                proposition="The system returns typed judgments.",
                primitive_family="FORM",
                indices=(0,),
            ),
            _ledger(
                key="N001",
                proposition="The system is claimed to resist hallucination.",
                primitive_family="QUALITY",
                indices=(1,),
            ),
        ),
    )
    normalized=_normalize_mutation_support_by_projection(
        draft=draft,
        expected_new_keys={"N001"},
    )
    assert normalized.mutations[0].support_keys == ("N001",)
    assert normalized.mutations[1].support_keys == ("N001",)
    _validate_evidence_projection(
        draft=normalized,
        expected_new_keys={"N001"},
    )


def test_evidence_projection_rejects_exact_duplicate_proposition_row():
    from app.services.event_state_slot_delta import (
        SlotDeltaDraftV01,
        _validate_evidence_projection,
    )
    row=_ledger(key="N001",proposition="Same atomic proposition.")
    draft=SlotDeltaDraftV01(
        mutations=(_draft_mutation(),),
        evidence_projection=(row,row),
    )
    with pytest.raises(ValueError,match="exact duplicate row"):
        _validate_evidence_projection(draft=draft,expected_new_keys={"N001"})


def test_evidence_projection_rejects_unknown_mutation_index():
    from app.services.event_state_slot_delta import (
        SlotDeltaDraftV01,
        _validate_evidence_projection,
    )
    draft=SlotDeltaDraftV01(
        mutations=(_draft_mutation(),),
        evidence_projection=(_ledger(key="N001",indices=(1,)),),
    )
    with pytest.raises(ValueError,match="unknown mutation index"):
        _validate_evidence_projection(draft=draft,expected_new_keys={"N001"})


def test_evidence_projection_rejects_nonworld_key_used_by_world_mutation():
    from app.services.event_state_slot_delta import (
        NewEvidenceDispositionV01,
        SlotDeltaDraftV01,
        _validate_evidence_projection,
    )
    draft=SlotDeltaDraftV01(
        mutations=(_draft_mutation(),),
        evidence_projection=(
            NewEvidenceDispositionV01(
                support_key="N001",
                proposition="Evidence-only qualifier.",
                disposition="EVIDENCE",
                mutation_indices=(),
            ),
        ),
    )
    with pytest.raises(ValueError,match="routing union must exactly match"):
        _validate_evidence_projection(draft=draft,expected_new_keys={"N001"})


def test_evidence_projection_rejects_world_routing_not_matching_support():
    from app.services.event_state_slot_delta import (
        SlotDeltaDraftV01,
        _validate_evidence_projection,
    )
    draft=SlotDeltaDraftV01(
        mutations=(
            _draft_mutation(
                label="performance",
                support_keys=("N001",),
                primitive_family="QUALITY",
            ),
            _draft_mutation(
                label="reliability",
                support_keys=("N002",),
                primitive_family="QUALITY",
            ),
        ),
        evidence_projection=(
            _ledger(
                key="N001",
                primitive_family="QUALITY",
                indices=(0,1),
            ),
            _ledger(
                key="N002",
                primitive_family="QUALITY",
                indices=(1,),
            ),
        ),
    )
    with pytest.raises(ValueError,match="routing union must exactly match"):
        _validate_evidence_projection(
            draft=draft,
            expected_new_keys={"N001","N002"},
        )


def test_projection_normalization_prunes_nonworld_new_support_but_keeps_world_support():
    from app.services.event_state_slot_delta import (
        NewEvidenceDispositionV01,
        SlotDeltaDraftV01,
        _normalize_mutation_support_by_projection,
        _validate_evidence_projection,
    )
    draft=SlotDeltaDraftV01(
        mutations=(
            _draft_mutation(
                label="performance",
                support_keys=("P001","N001","N002"),
            ),
        ),
        evidence_projection=(
            NewEvidenceDispositionV01(
                support_key="N001",
                proposition="World proposition N001.",
                disposition="WORLD_MUTATION",
                primitive_family="QUALITY",
                mutation_indices=(0,),
            ),
            NewEvidenceDispositionV01(
                support_key="N002",
                proposition="Evidence-only qualifier N002.",
                disposition="EVIDENCE",
                mutation_indices=(),
            ),
        ),
    )
    normalized=_normalize_mutation_support_by_projection(
        draft=draft,
        expected_new_keys={"N001","N002"},
    )
    assert normalized.mutations[0].support_keys == ("P001","N001")
    _validate_evidence_projection(
        draft=normalized,
        expected_new_keys={"N001","N002"},
    )


def test_projection_normalization_derives_missing_new_world_support_from_ledger():
    from app.services.event_state_slot_delta import (
        NewEvidenceDispositionV01,
        SlotDeltaDraftV01,
        _normalize_mutation_support_by_projection,
        _validate_evidence_projection,
    )
    draft=SlotDeltaDraftV01(
        mutations=(
            _draft_mutation(
                label="mechanism",
                support_keys=("P001",),
            ),
        ),
        evidence_projection=(
            NewEvidenceDispositionV01(
                support_key="N001",
                proposition="World proposition N001.",
                disposition="WORLD_MUTATION",
                primitive_family="PROCESS",
                mutation_indices=(0,),
            ),
            NewEvidenceDispositionV01(
                support_key="N002",
                proposition="Evidence-only qualifier N002.",
                disposition="EVIDENCE",
                mutation_indices=(),
            ),
        ),
    )
    normalized=_normalize_mutation_support_by_projection(
        draft=draft,
        expected_new_keys={"N001","N002"},
    )
    assert normalized.mutations[0].support_keys == ("P001","N001")
    _validate_evidence_projection(
        draft=normalized,
        expected_new_keys={"N001","N002"},
    )


def test_evidence_projection_rejects_cross_family_route():
    from app.services.event_state_slot_delta import (
        SlotDeltaDraftV01,
        _normalize_mutation_support_by_projection,
        _validate_evidence_projection,
    )
    draft=SlotDeltaDraftV01(
        mutations=(
            _draft_mutation(
                label="output form",
                support_keys=(),
                primitive_family="FORM",
            ),
        ),
        evidence_projection=(
            _ledger(
                key="N001",
                proposition="The system uses KV-cache reuse.",
                primitive_family="PROCESS",
                indices=(0,),
            ),
        ),
    )
    normalized=_normalize_mutation_support_by_projection(
        draft=draft,
        expected_new_keys={"N001"},
    )
    with pytest.raises(ValueError,match="primitive_family must match"):
        _validate_evidence_projection(
            draft=normalized,
            expected_new_keys={"N001"},
        )


def test_prune_unreferenced_mutations_remaps_projection_indices():
    from app.services.event_state_slot_delta import (
        SlotDeltaDraftV01,
        _prune_unreferenced_mutations,
    )
    draft=SlotDeltaDraftV01(
        mutations=(
            _draft_mutation(label="stale snapshot",support_keys=("P001",)),
            _draft_mutation(label="mechanism",support_keys=("N001",)),
        ),
        evidence_projection=(
            _ledger(
                key="N001",
                proposition="The system uses a new internal mechanism.",
                indices=(1,),
            ),
        ),
    )
    pruned=_prune_unreferenced_mutations(draft)
    assert len(pruned.mutations) == 1
    assert pruned.mutations[0].slot_label == "mechanism"
    assert pruned.evidence_projection[0].mutation_indices == (0,)
