from app.services.semantic_coordinate.adjudication import (
    CandidateAdjudicationPlan,
    CandidateSlotScore,
    PropositionCandidatePlan,
)
from app.services.semantic_coordinate.direct_answer import (
    DirectAnswerJudgmentV01,
    build_pairwise_authorization_plan_batched,
    build_pairwise_authorization_plan_proposition_batched,
    build_pairwise_authorization_plan_parallel,
    consensus_direct_answer,
    judge_direct_answer,
    judge_direct_answer_batch,
    judge_direct_answer_parallel_consensus,
    resolve_pairwise_address,
    verify_proposition_address,
)


def test_family_mismatch_is_not_direct_without_llm_call():
    def must_not_call(*_args, **_kwargs):
        raise AssertionError("LLM must not run across primitive families")

    result = judge_direct_answer(
        event_identity={"object": "Jev"},
        proposition={
            "proposition_id": "p1",
            "statement": "The system is fast.",
            "primitive_family": "QUALITY",
            "referent_scope": "TARGET_INTRINSIC",
        },
        slot={
            "slot_id": "s1",
            "primitive_family": "STRUCTURE",
            "state_question": "What architecture does this system use?",
            "value": "Transformer",
        },
        chat_fn=must_not_call,
    )
    assert result.decision == "NOT_DIRECT"
    assert "hard mismatch" in result.rationale


def test_pairwise_llm_result_is_bound_to_input_ids():
    def fake_chat(_messages, **_kwargs):
        return {
            "decision": "DIRECT",
            "rationale": "The proposition updates the exact performance answer.",
        }, {}

    result = judge_direct_answer(
        event_identity={"object": "Jev"},
        proposition={
            "proposition_id": "prop-performance",
            "statement": "The system now completes a decision in 300 ms.",
            "primitive_family": "QUALITY",
            "referent_scope": "TARGET_INTRINSIC",
        },
        slot={
            "slot_id": "slot-performance",
            "primitive_family": "QUALITY",
            "slot_label": "Operational performance",
            "state_question": "What are this system's operational performance characteristics?",
            "value": "Previously 500 ms.",
        },
        chat_fn=fake_chat,
    )
    assert result.proposition_id == "prop-performance"
    assert result.slot_id == "slot-performance"
    assert result.decision == "DIRECT"


def _judgment(slot_id, decision):
    return DirectAnswerJudgmentV01(
        proposition_id="p1",
        slot_id=slot_id,
        decision=decision,
        rationale="test",
    )


def test_exactly_one_direct_authorizes_reuse():
    result = resolve_pairwise_address(
        judgments=[
            _judgment("s1", "NOT_DIRECT"),
            _judgment("s2", "DIRECT"),
        ],
        full_same_family_verified=False,
    )
    assert result.status == "REUSE_AUTHORIZED"
    assert result.authorized_existing_slot_ids == ("s2",)
    assert result.authorized_existing_slot_id == "s2"


def test_zero_direct_requires_full_family_before_create():
    partial = resolve_pairwise_address(
        judgments=[_judgment("s1", "NOT_DIRECT")],
        full_same_family_verified=False,
    )
    assert partial.status == "UNRESOLVED"

    full = resolve_pairwise_address(
        judgments=[_judgment("s1", "NOT_DIRECT")],
        full_same_family_verified=True,
    )
    assert full.status == "CREATE_ELIGIBLE"


def test_multiple_direct_authorizes_existing_set():
    result = resolve_pairwise_address(
        judgments=[
            _judgment("s1", "DIRECT"),
            _judgment("s2", "DIRECT"),
        ],
        full_same_family_verified=True,
    )
    assert result.status == "REUSE_AUTHORIZED"
    assert result.authorized_existing_slot_ids == ("s1", "s2")
    assert result.authorized_existing_slot_id is None
    assert result.direct_slot_ids == ("s1", "s2")


def test_uncertain_fails_closed_even_if_one_direct_exists():
    result = resolve_pairwise_address(
        judgments=[
            _judgment("s1", "DIRECT"),
            _judgment("s2", "UNCERTAIN"),
        ],
        full_same_family_verified=True,
    )
    assert result.status == "UNRESOLVED"
    assert result.direct_slot_ids == ("s1",)
    assert result.uncertain_slot_ids == ("s2",)


def test_consensus_requires_agreement_and_fails_closed_on_disagreement():
    direct = consensus_direct_answer([
        _judgment("s1", "DIRECT"),
        _judgment("s1", "DIRECT"),
    ])
    assert direct.decision == "DIRECT"

    negative = consensus_direct_answer([
        _judgment("s1", "NOT_DIRECT"),
        _judgment("s1", "NOT_DIRECT"),
    ])
    assert negative.decision == "NOT_DIRECT"

    uncertain = consensus_direct_answer([
        _judgment("s1", "DIRECT"),
        _judgment("s1", "NOT_DIRECT"),
    ])
    assert uncertain.decision == "UNCERTAIN"


def test_consensus_rejects_mixed_pair_ids():
    import pytest

    with pytest.raises(ValueError, match="one proposition-slot pair"):
        consensus_direct_answer([
            _judgment("s1", "DIRECT"),
            _judgment("s2", "DIRECT"),
        ])


def test_verify_proposition_address_expands_after_zero_direct_and_finds_hidden_reuse():
    import json

    def fake_chat(messages, **_kwargs):
        payload = json.loads(messages[-1]["content"].split("\n\n", 1)[1])
        slot_id = payload["current_slot"]["slot_id"]
        return {
            "decision": "DIRECT" if slot_id == "s-hidden" else "NOT_DIRECT",
            "rationale": "test pair decision",
        }, {}

    result = verify_proposition_address(
        event_identity={"object": "Jev"},
        proposition={
            "proposition_id": "p1",
            "statement": "The system has a concrete performance measurement.",
            "primitive_family": "QUALITY",
            "referent_scope": "TARGET_INTRINSIC",
        },
        same_family_slots=[
            {
                "slot_id": "s-top",
                "primitive_family": "QUALITY",
                "state_question": "What are this system's reliability characteristics?",
                "value": "reliable",
            },
            {
                "slot_id": "s-hidden",
                "primitive_family": "QUALITY",
                "state_question": "What are this system's operational performance characteristics?",
                "value": "fast",
            },
        ],
        initial_candidate_slot_ids=("s-top",),
        chat_fn=fake_chat,
        repeats=2,
    )
    assert result.expansion_triggered is True
    assert result.expanded_slot_ids == ("s-hidden",)
    assert result.resolution.status == "REUSE_AUTHORIZED"
    assert result.resolution.authorized_existing_slot_ids == ("s-hidden",)
    assert result.resolution.authorized_existing_slot_id == "s-hidden"


def test_verify_proposition_address_full_scan_zero_direct_allows_create():
    def fake_chat(_messages, **_kwargs):
        return {
            "decision": "NOT_DIRECT",
            "rationale": "distinct same-family dimension",
        }, {}

    result = verify_proposition_address(
        event_identity={"object": "Jev"},
        proposition={
            "proposition_id": "p1",
            "statement": "A new same-family dimension is observed.",
            "primitive_family": "QUALITY",
            "referent_scope": "TARGET_INTRINSIC",
        },
        same_family_slots=[
            {
                "slot_id": "s1",
                "primitive_family": "QUALITY",
                "state_question": "What are this system's reliability characteristics?",
                "value": "reliable",
            },
            {
                "slot_id": "s2",
                "primitive_family": "QUALITY",
                "state_question": "What are this system's performance characteristics?",
                "value": "fast",
            },
        ],
        initial_candidate_slot_ids=("s1",),
        chat_fn=fake_chat,
        repeats=2,
    )
    assert result.expansion_triggered is True
    assert result.resolution.status == "CREATE_ELIGIBLE"
    assert result.resolution.full_same_family_verified is True


def test_verify_proposition_address_preserves_multiple_direct_existing_slots():
    import json

    def fake_chat(messages, **_kwargs):
        payload = json.loads(messages[-1]["content"].split("\n\n", 1)[1])
        slot_id = payload["current_slot"]["slot_id"]
        return {
            "decision": "DIRECT",
            "rationale": f"{slot_id} is directly updated by the proposition.",
        }, {}

    result = verify_proposition_address(
        event_identity={"object": "synthetic system"},
        proposition={
            "proposition_id": "p-multi",
            "statement": (
                "The system demonstrates a behavior that directly updates "
                "two orthogonal existing state questions."
            ),
            "primitive_family": "QUALITY",
            "referent_scope": "TARGET_INTRINSIC",
        },
        same_family_slots=[
            {
                "slot_id": "s1",
                "primitive_family": "QUALITY",
                "state_question": "What is quality dimension A?",
                "value": "old A",
            },
            {
                "slot_id": "s2",
                "primitive_family": "QUALITY",
                "state_question": "What is quality dimension B?",
                "value": "old B",
            },
        ],
        initial_candidate_slot_ids=("s1", "s2"),
        chat_fn=fake_chat,
        repeats=1,
    )

    assert result.resolution.status == "REUSE_AUTHORIZED"
    assert result.resolution.authorized_existing_slot_ids == ("s1", "s2")
    assert result.resolution.authorized_existing_slot_id is None


def test_batched_direct_answer_rejects_missing_pair_key():
    import json
    import pytest

    def incomplete_chat(messages, **_kwargs):
        payload = json.loads(messages[-1]["content"].split("\n\n", 1)[1])
        first = payload["pairs"][0]
        return {
            "judgments": [{
                "pair_key": first["pair_key"],
                "decision": "DIRECT",
                "rationale": "only one row returned",
            }]
        }, {}

    pairs = [
        (
            {
                "proposition_id": "p1",
                "statement": "The system is fast.",
                "primitive_family": "QUALITY",
                "referent_scope": "TARGET_INTRINSIC",
            },
            {
                "slot_id": "s1",
                "primitive_family": "QUALITY",
                "state_question": "What is system speed?",
            },
        ),
        (
            {
                "proposition_id": "p2",
                "statement": "The system is reliable.",
                "primitive_family": "QUALITY",
                "referent_scope": "TARGET_INTRINSIC",
            },
            {
                "slot_id": "s2",
                "primitive_family": "QUALITY",
                "state_question": "What is system reliability?",
            },
        ),
    ]
    with pytest.raises(ValueError, match="exactly cover pair keys"):
        judge_direct_answer_batch(
            event_identity={"object": "system"},
            pairs=pairs,
            chat_fn=incomplete_chat,
        )


def test_batched_family_mismatch_short_circuits_without_llm():
    def must_not_call(*_args, **_kwargs):
        raise AssertionError("LLM must not run for hard family mismatch")

    rows = judge_direct_answer_batch(
        event_identity={"object": "system"},
        pairs=[(
            {
                "proposition_id": "p1",
                "statement": "The system is fast.",
                "primitive_family": "QUALITY",
                "referent_scope": "TARGET_INTRINSIC",
            },
            {
                "slot_id": "s1",
                "primitive_family": "STRUCTURE",
                "state_question": "What architecture does it use?",
            },
        )],
        chat_fn=must_not_call,
    )
    assert len(rows) == 1
    assert rows[0].decision == "NOT_DIRECT"


def test_batched_authorization_preserves_pairwise_semantics_with_two_calls():
    import json

    calls = []

    def fake_batch_chat(messages, **_kwargs):
        payload = json.loads(messages[-1]["content"].split("\n\n", 1)[1])
        calls.append(payload)
        judgments = []
        for pair in payload["pairs"]:
            pid = pair["proposition"]["proposition_id"]
            sid = pair["current_slot"]["slot_id"]
            is_direct = (
                (pid == "p1" and sid == "s1")
                or (pid == "p2" and sid == "s2")
            )
            judgments.append({
                "pair_key": pair["pair_key"],
                "decision": "DIRECT" if is_direct else "NOT_DIRECT",
                "rationale": "synthetic independent pair decision",
            })
        return {"judgments": judgments}, {}

    propositions = [
        {
            "proposition_id": "p1",
            "statement": "Proposition one.",
            "primitive_family": "QUALITY",
            "referent_scope": "TARGET_INTRINSIC",
        },
        {
            "proposition_id": "p2",
            "statement": "Proposition two.",
            "primitive_family": "QUALITY",
            "referent_scope": "TARGET_INTRINSIC",
        },
    ]
    slots = [
        {
            "slot_id": "s1",
            "primitive_family": "QUALITY",
            "state_question": "What is dimension one?",
            "value": "old one",
        },
        {
            "slot_id": "s2",
            "primitive_family": "QUALITY",
            "state_question": "What is dimension two?",
            "value": "old two",
        },
    ]
    candidate_rows = (
        PropositionCandidatePlan(
            proposition_id="p1",
            primitive_family="QUALITY",
            candidate_slots=(
                CandidateSlotScore(slot_id="s1", semantic_similarity=0.9),
                CandidateSlotScore(slot_id="s2", semantic_similarity=0.8),
            ),
            same_family_slot_ids=("s1", "s2"),
            hidden_same_family_slot_ids=(),
        ),
        PropositionCandidatePlan(
            proposition_id="p2",
            primitive_family="QUALITY",
            candidate_slots=(
                CandidateSlotScore(slot_id="s1", semantic_similarity=0.8),
                CandidateSlotScore(slot_id="s2", semantic_similarity=0.9),
            ),
            same_family_slot_ids=("s1", "s2"),
            hidden_same_family_slot_ids=(),
        ),
    )
    plan = CandidateAdjudicationPlan(
        top_k=2,
        propositions=candidate_rows,
        visible_slot_ids=("s1", "s2"),
        total_slot_count=2,
        visible_slot_count=2,
    )

    result = build_pairwise_authorization_plan_batched(
        event_identity={"object": "system"},
        propositions=propositions,
        current_slots=slots,
        candidate_plan=plan,
        chat_fn=fake_batch_chat,
        repeats=2,
    )

    assert len(calls) == 2
    by_prop = {
        row.proposition_id: row.resolution
        for row in result.propositions
    }
    assert by_prop["p1"].authorized_existing_slot_ids == ("s1",)
    assert by_prop["p2"].authorized_existing_slot_ids == ("s2",)


def test_proposition_scoped_batch_uses_two_calls_per_proposition_and_keeps_results():
    import json

    calls = []

    def fake_batch_chat(messages, **_kwargs):
        payload = json.loads(messages[-1]["content"].split("\n\n", 1)[1])
        proposition_ids = {
            pair["proposition"]["proposition_id"]
            for pair in payload["pairs"]
        }
        assert len(proposition_ids) == 1
        calls.append(next(iter(proposition_ids)))
        judgments = []
        for pair in payload["pairs"]:
            pid = pair["proposition"]["proposition_id"]
            sid = pair["current_slot"]["slot_id"]
            direct = (
                (pid == "p1" and sid == "s1")
                or (pid == "p2" and sid == "s2")
            )
            judgments.append({
                "pair_key": pair["pair_key"],
                "decision": "DIRECT" if direct else "NOT_DIRECT",
                "rationale": "proposition-scoped synthetic decision",
            })
        return {"judgments": judgments}, {}

    propositions = [
        {
            "proposition_id": "p1",
            "statement": "Proposition one.",
            "primitive_family": "QUALITY",
            "referent_scope": "TARGET_INTRINSIC",
        },
        {
            "proposition_id": "p2",
            "statement": "Proposition two.",
            "primitive_family": "QUALITY",
            "referent_scope": "TARGET_INTRINSIC",
        },
    ]
    slots = [
        {
            "slot_id": "s1",
            "primitive_family": "QUALITY",
            "state_question": "What is dimension one?",
            "value": "old one",
        },
        {
            "slot_id": "s2",
            "primitive_family": "QUALITY",
            "state_question": "What is dimension two?",
            "value": "old two",
        },
    ]
    candidate_rows = (
        PropositionCandidatePlan(
            proposition_id="p1",
            primitive_family="QUALITY",
            candidate_slots=(
                CandidateSlotScore(slot_id="s1", semantic_similarity=0.9),
                CandidateSlotScore(slot_id="s2", semantic_similarity=0.8),
            ),
            same_family_slot_ids=("s1", "s2"),
            hidden_same_family_slot_ids=(),
        ),
        PropositionCandidatePlan(
            proposition_id="p2",
            primitive_family="QUALITY",
            candidate_slots=(
                CandidateSlotScore(slot_id="s1", semantic_similarity=0.8),
                CandidateSlotScore(slot_id="s2", semantic_similarity=0.9),
            ),
            same_family_slot_ids=("s1", "s2"),
            hidden_same_family_slot_ids=(),
        ),
    )
    plan = CandidateAdjudicationPlan(
        top_k=2,
        propositions=candidate_rows,
        visible_slot_ids=("s1", "s2"),
        total_slot_count=2,
        visible_slot_count=2,
    )

    result = build_pairwise_authorization_plan_proposition_batched(
        event_identity={"object": "system"},
        propositions=propositions,
        current_slots=slots,
        candidate_plan=plan,
        chat_fn=fake_batch_chat,
        repeats=2,
    )

    assert calls == ["p1", "p1", "p2", "p2"]
    by_prop = {
        row.proposition_id: row.resolution
        for row in result.propositions
    }
    assert by_prop["p1"].authorized_existing_slot_ids == ("s1",)
    assert by_prop["p2"].authorized_existing_slot_ids == ("s2",)


def test_parallel_consensus_preserves_single_pair_prompt_and_order():
    import json
    import threading

    calls = []
    lock = threading.Lock()

    def fake_single_chat(messages, **_kwargs):
        system = messages[0]["content"]
        assert "batched pairwise" not in system
        payload = json.loads(messages[-1]["content"].split("\n\n", 1)[1])
        pid = payload["proposition"]["proposition_id"]
        sid = payload["current_slot"]["slot_id"]
        with lock:
            calls.append((pid, sid))
        direct = (
            (pid == "p1" and sid == "s1")
            or (pid == "p2" and sid == "s2")
        )
        return {
            "decision": "DIRECT" if direct else "NOT_DIRECT",
            "rationale": "independent single-pair decision",
        }, {}

    pairs = [
        (
            {
                "proposition_id": "p1",
                "statement": "P1",
                "primitive_family": "QUALITY",
                "referent_scope": "TARGET_INTRINSIC",
            },
            {
                "slot_id": "s1",
                "primitive_family": "QUALITY",
                "state_question": "Q1?",
            },
        ),
        (
            {
                "proposition_id": "p2",
                "statement": "P2",
                "primitive_family": "QUALITY",
                "referent_scope": "TARGET_INTRINSIC",
            },
            {
                "slot_id": "s2",
                "primitive_family": "QUALITY",
                "state_question": "Q2?",
            },
        ),
    ]
    rows = judge_direct_answer_parallel_consensus(
        event_identity={"object": "system"},
        pairs=pairs,
        chat_fn=fake_single_chat,
        repeats=2,
        max_workers=4,
    )
    assert len(calls) == 4
    assert rows[0].proposition_id == "p1"
    assert rows[0].slot_id == "s1"
    assert rows[0].decision == "DIRECT"
    assert rows[1].proposition_id == "p2"
    assert rows[1].slot_id == "s2"
    assert rows[1].decision == "DIRECT"


def test_parallel_authorization_plan_matches_expected_addresses():
    import json

    def fake_single_chat(messages, **_kwargs):
        payload = json.loads(messages[-1]["content"].split("\n\n", 1)[1])
        pid = payload["proposition"]["proposition_id"]
        sid = payload["current_slot"]["slot_id"]
        direct = (
            (pid == "p1" and sid == "s1")
            or (pid == "p2" and sid == "s2")
        )
        return {
            "decision": "DIRECT" if direct else "NOT_DIRECT",
            "rationale": "parallel synthetic decision",
        }, {}

    propositions = [
        {
            "proposition_id": "p1",
            "statement": "P1",
            "primitive_family": "QUALITY",
            "referent_scope": "TARGET_INTRINSIC",
        },
        {
            "proposition_id": "p2",
            "statement": "P2",
            "primitive_family": "QUALITY",
            "referent_scope": "TARGET_INTRINSIC",
        },
    ]
    slots = [
        {
            "slot_id": "s1",
            "primitive_family": "QUALITY",
            "state_question": "Q1?",
        },
        {
            "slot_id": "s2",
            "primitive_family": "QUALITY",
            "state_question": "Q2?",
        },
    ]
    rows = (
        PropositionCandidatePlan(
            proposition_id="p1",
            primitive_family="QUALITY",
            candidate_slots=(
                CandidateSlotScore(slot_id="s1", semantic_similarity=0.9),
                CandidateSlotScore(slot_id="s2", semantic_similarity=0.8),
            ),
            same_family_slot_ids=("s1", "s2"),
            hidden_same_family_slot_ids=(),
        ),
        PropositionCandidatePlan(
            proposition_id="p2",
            primitive_family="QUALITY",
            candidate_slots=(
                CandidateSlotScore(slot_id="s1", semantic_similarity=0.8),
                CandidateSlotScore(slot_id="s2", semantic_similarity=0.9),
            ),
            same_family_slot_ids=("s1", "s2"),
            hidden_same_family_slot_ids=(),
        ),
    )
    plan = CandidateAdjudicationPlan(
        top_k=2,
        propositions=rows,
        visible_slot_ids=("s1", "s2"),
        total_slot_count=2,
        visible_slot_count=2,
    )
    result = build_pairwise_authorization_plan_parallel(
        event_identity={"object": "system"},
        propositions=propositions,
        current_slots=slots,
        candidate_plan=plan,
        chat_fn=fake_single_chat,
        repeats=2,
        max_workers=4,
    )
    by_prop = {
        row.proposition_id: row.resolution.authorized_existing_slot_ids
        for row in result.propositions
    }
    assert by_prop == {
        "p1": ("s1",),
        "p2": ("s2",),
    }
