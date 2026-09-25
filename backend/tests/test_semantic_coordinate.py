from app.services.event_state_semantic_key_resolver import (
    resolve_key,
    retrieve_key_candidates,
)
from app.services.semantic_coordinate.adjudication import (
    build_candidate_adjudication_plan,
)
from app.services.semantic_coordinate.matcher import CoordinateSimilarityEngine
from app.services.semantic_coordinate.models import (
    CoordinateRetrievalQuery,
    SemanticCoordinate,
)
from app.services.semantic_coordinate.registry import SemanticCoordinateRegistry
from app.services.semantic_coordinate.retrieval import (
    CoordinateCandidateRetriever,
    InMemoryCoordinateIndex,
    format_coordinate_query_for_embedding,
)
from app.config import settings


def _coordinate(
    family="QUALITY",
    question="What is the operational latency?",
    **kwargs,
):
    return SemanticCoordinate(
        primitive_family=family,
        state_question=question,
        **kwargs,
    )


def test_coordinate_identity_ignores_contextual_hints_and_aliases():
    a = _coordinate(
        aliases=("latency",),
        domain_hints=("models",),
        entity_type_hints=("AI system",),
    )
    b = _coordinate(
        coordinate_label="runtime performance",
        aliases=("response time",),
        domain_hints=("robotics",),
        entity_type_hints=("controller",),
    )
    assert a.coordinate_id == b.coordinate_id
def test_coordinate_identity_changes_across_primitive_family():
    quality = _coordinate(family="QUALITY")
    relation = _coordinate(family="RELATION")
    assert quality.coordinate_id != relation.coordinate_id
    assert quality.referent_scope == "TARGET_INTRINSIC"
    assert relation.referent_scope == "TARGET_RELATION"


def test_registry_merges_non_identity_metadata_for_same_coordinate():
    registry = SemanticCoordinateRegistry()
    registry.register(_coordinate(
        coordinate_label="operational latency",
        aliases=("latency",),
        domain_hints=("models",),
        confidence=0.4,
    ))
    merged = registry.register(_coordinate(
        coordinate_label="response latency",
        aliases=("response time",),
        domain_hints=("robotics",),
        confidence=0.8,
    ))
    assert len(registry) == 1
    assert merged.coordinate_label == "operational latency"
    assert merged.aliases == (
        "latency",
        "response latency",
        "response time",
    )
    assert merged.domain_hints == ("models", "robotics")
    assert merged.confidence == 0.8


def test_retrieval_prefilters_family_and_batches_embedding_once():
    calls = []

    def fake_embed(texts):
        calls.append(list(texts))
        vectors = []
        for text in texts:
            lowered = text.lower()
            if "latency" in lowered or "speed" in lowered:
                vectors.append([1.0, 0.0])
            else:
                vectors.append([0.0, 1.0])
        return vectors, "fake-embedding"
    query = _coordinate(question="What is the inference latency?")
    speed = _coordinate(
        question="How fast does the system execute?",
        coordinate_label="speed",
    )
    cost = _coordinate(
        question="What is the operating cost?",
        coordinate_label="cost",
    )
    wrong_family = _coordinate(
        family="STRUCTURE",
        question="What architecture does the system use?",
    )

    rows = CoordinateCandidateRetriever(fake_embed).retrieve(
        query,
        [speed, cost, wrong_family],
        top_k=5,
    )
    assert len(calls) == 1
    assert len(calls[0]) == 3  # query + two QUALITY candidates
    assert [row.coordinate.coordinate_id for row in rows] == [
        speed.coordinate_id,
        cost.coordinate_id,
    ]
    assert all(
        row.coordinate.primitive_family == "QUALITY"
        for row in rows
    )
def test_matcher_family_guard_does_not_call_embedding():
    def must_not_run(_texts):
        raise AssertionError("embedding should not run across primitive families")

    engine = CoordinateSimilarityEngine(must_not_run)
    result = engine.compare(
        _coordinate(family="QUALITY"),
        _coordinate(
            family="STRUCTURE",
            question="What architecture does the system use?",
        ),
    )
    assert result.compatibility == "TYPE_MISMATCH"
    assert result.requires_semantic_resolution is False
    assert result.rationale == "primitive-family hard guard mismatch"


def test_matcher_similarity_is_advisory_not_auto_merge():
    engine = CoordinateSimilarityEngine()
    a = _coordinate(question="What is the inference latency?")
    b = _coordinate(question="How fast does inference execute?")
    result = engine.compare(a, b, semantic_similarity=0.95)
    assert result.compatibility == "CANDIDATE"
    assert result.score == 0.95
    assert result.value_type_compatible is None
    assert result.temporal_behavior_compatible is True
    assert result.requires_semantic_resolution is True
    assert "cannot decide REUSE/CREATE" in result.rationale
def test_resolver_reuses_only_same_family_and_canonical_question():
    existing = [{
        "slot_key": "slot-1",
        "primitive_family": "QUALITY",
        "state_question": "What is the inference latency?",
    }]
    reused = resolve_key(
        event_identity={"object": "Jev"},
        current_slots=existing,
        proposition={
            "primitive_family": "QUALITY",
            "state_question": "  What is the inference latency?  ",
        },
    )
    assert reused.decision == "REUSE"
    assert reused.slot_key == "slot-1"

    created = resolve_key(
        event_identity={"object": "Jev"},
        current_slots=existing,
        proposition={
            "primitive_family": "QUALITY",
            "state_question": "What is the operating cost?",
        },
    )
    assert created.decision == "CREATE"
    assert created.slot_key is None


def test_in_memory_index_reuses_candidate_vectors_across_queries():
    calls = []

    def fake_embed(texts):
        calls.append(list(texts))
        vectors = []
        for text in texts:
            lowered = text.lower()
            if (
                "latency" in lowered
                or "speed" in lowered
                or "response time" in lowered
            ):
                vectors.append([1.0, 0.0])
            elif "cost" in lowered:
                vectors.append([0.7, 0.3])
            else:
                vectors.append([0.0, 1.0])
        return vectors, "fake-embedding"

    speed = _coordinate(
        question="How fast does the system execute?",
        coordinate_label="speed",
    )
    cost = _coordinate(
        question="What is the operating cost?",
        coordinate_label="cost",
    )
    structure = _coordinate(
        family="STRUCTURE",
        question="What architecture does the system use?",
    )
    index = InMemoryCoordinateIndex(fake_embed)
    index.rebuild([speed, cost, structure])

    first = index.retrieve(
        _coordinate(question="What is the inference latency?"),
        top_k=5,
    )
    second = index.retrieve(
        _coordinate(question="What is the response time?"),
        top_k=5,
    )

    assert len(index) == 3
    assert len(calls) == 3  # one build + one embedding per query
    assert len(calls[0]) == 3
    assert len(calls[1]) == 1
    assert len(calls[2]) == 1
    assert first[0].coordinate.coordinate_id == speed.coordinate_id
    assert second[0].coordinate.coordinate_id == speed.coordinate_id
    assert all(
        row.coordinate.primitive_family == "QUALITY"
        for row in first + second
    )


def test_coordinate_query_uses_task_instruction_for_qwen(monkeypatch):
    monkeypatch.setattr(settings, "embedding_query_protocol", "qwen")
    formatted = format_coordinate_query_for_embedding("state question text")
    assert formatted.startswith(
        "Instruct: Given a semantic state question, retrieve existing state dimensions"
    )
    assert formatted.endswith("Query: state question text")


def test_coordinate_query_stays_raw_when_instruct_disabled(monkeypatch):
    monkeypatch.setattr(settings, "embedding_query_protocol", "none")
    assert (
        format_coordinate_query_for_embedding("state question text")
        == "state question text"
    )


def test_proposition_query_uses_proposition_task_instruction(monkeypatch):
    monkeypatch.setattr(settings, "embedding_query_protocol", "qwen")
    query = CoordinateRetrievalQuery(
        primitive_family="QUALITY",
        text="The system completes a decision in 300 ms.",
    )
    formatted = format_coordinate_query_for_embedding(
        query.embedding_text(),
        query_kind=query.query_kind,
    )
    assert formatted.startswith(
        "Instruct: Given a typed semantic proposition about the world"
    )
    assert "proposition: The system completes a decision in 300 ms." in formatted


def test_retriever_accepts_typed_proposition_query():
    calls = []

    def fake_embed(texts):
        calls.append(list(texts))
        vectors = []
        for text in texts:
            lowered = text.lower()
            if "300 ms" in lowered or "performance" in lowered:
                vectors.append([1.0, 0.0])
            else:
                vectors.append([0.0, 1.0])
        return vectors, "fake-embedding"

    query = CoordinateRetrievalQuery(
        primitive_family="QUALITY",
        text="The system completes a decision in 300 ms.",
    )
    performance = _coordinate(
        question="What are this system's operational performance characteristics?",
        coordinate_label="performance",
    )
    reliability = _coordinate(
        question="What are this system's reliability characteristics?",
        coordinate_label="reliability",
    )
    structure = _coordinate(
        family="STRUCTURE",
        question="What architecture does this system use?",
        coordinate_label="architecture",
    )

    rows = CoordinateCandidateRetriever(fake_embed).retrieve(
        query,
        [performance, reliability, structure],
        top_k=3,
    )
    assert len(calls) == 1
    assert [row.coordinate.coordinate_label for row in rows] == [
        "performance",
        "reliability",
    ]


def test_coordinate_query_from_coordinate_preserves_clean_state_question():
    coordinate = _coordinate(
        question="What is the operational latency?",
        coordinate_label="latency",
    )
    query = CoordinateRetrievalQuery.from_coordinate(coordinate)
    assert query.text == "What is the operational latency?"
    assert query.exclude_coordinate_id == coordinate.coordinate_id
    assert query.query_kind == "STATE_QUESTION"


def test_raw_world_proposition_must_not_use_exact_resolver():
    import pytest

    with pytest.raises(ValueError, match="raw WorldProposition"):
        resolve_key(
            event_identity={"object": "Jev"},
            current_slots=[],
            proposition={
                "primitive_family": "QUALITY",
                "statement": "Jev completes a decision in 300 ms.",
            },
        )


def test_event_slot_candidate_retrieval_preserves_local_slot_identity():
    def fake_embed(texts):
        vectors = []
        for text in texts:
            lowered = text.lower()
            if "300 ms" in lowered or "performance" in lowered:
                vectors.append([1.0, 0.0])
            else:
                vectors.append([0.0, 1.0])
        return vectors, "fake-embedding"

    result = retrieve_key_candidates(
        event_identity={"object": "Jev"},
        current_slots=[
            {
                "slot_id": "event-slot-performance",
                "slot_label": "Operational performance",
                "primitive_family": "QUALITY",
                "state_question": "What are this system's operational performance characteristics?",
            },
            {
                "slot_id": "event-slot-reliability",
                "slot_label": "Reliability",
                "primitive_family": "QUALITY",
                "state_question": "What are this system's reliability characteristics?",
            },
            {
                "slot_id": "event-slot-structure",
                "slot_label": "Architecture",
                "primitive_family": "STRUCTURE",
                "state_question": "What architecture does this system use?",
            },
        ],
        proposition={
            "primitive_family": "QUALITY",
            "statement": "Jev completes a decision in 300 ms.",
        },
        top_k=2,
        retriever=CoordinateCandidateRetriever(fake_embed),
    )

    assert result.same_family_slot_count == 2
    assert result.total_current_slots == 3
    assert [row.slot_key for row in result.candidates] == [
        "event-slot-performance",
        "event-slot-reliability",
    ]
    assert result.query.query_kind == "PROPOSITION"
    assert "does not decide REUSE/CREATE" in result.rationale


def test_candidate_adjudication_plan_is_family_scoped_and_tracks_hidden_slots():
    def fake_embed(texts):
        vectors = []
        for text in texts:
            low = text.lower()
            if "300 ms" in low or "performance" in low:
                vectors.append([1.0, 0.0])
            elif "reliability" in low:
                vectors.append([0.7, 0.3])
            else:
                vectors.append([0.0, 1.0])
        return vectors, "fake-embedding"

    slots = [
        {
            "slot_id": "quality-performance",
            "primitive_family": "QUALITY",
            "slot_label": "Performance",
            "state_question": "What are this system's operational performance characteristics?",
        },
        {
            "slot_id": "quality-reliability",
            "primitive_family": "QUALITY",
            "slot_label": "Reliability",
            "state_question": "What are this system's reliability characteristics?",
        },
        {
            "slot_id": "quality-correctness",
            "primitive_family": "QUALITY",
            "slot_label": "Correctness",
            "state_question": "How correct and valid are this system's outputs?",
        },
        {
            "slot_id": "structure-architecture",
            "primitive_family": "STRUCTURE",
            "slot_label": "Architecture",
            "state_question": "What architecture does this system use?",
        },
    ]
    propositions = [{
        "proposition_id": "prop-performance",
        "primitive_family": "QUALITY",
        "statement": "The system completes a decision in 300 ms.",
    }]
    plan = build_candidate_adjudication_plan(
        propositions=propositions,
        current_slots=slots,
        top_k=2,
        retriever=CoordinateCandidateRetriever(fake_embed),
    )

    assert plan.total_slot_count == 4
    assert plan.visible_slot_count == 2
    assert plan.compression_ratio == 0.5
    row = plan.propositions[0]
    assert row.primitive_family == "QUALITY"
    assert "structure-architecture" not in row.same_family_slot_ids
    assert row.candidate_slot_ids[0] == "quality-performance"
    assert len(row.hidden_same_family_slot_ids) == 1
    assert row.create_requires_expansion is True


def test_candidate_adjudication_plan_no_hidden_family_means_create_needs_no_expansion():
    def fake_embed(texts):
        return [[1.0, 0.0] for _ in texts], "fake-embedding"

    plan = build_candidate_adjudication_plan(
        propositions=[{
            "proposition_id": "p1",
            "primitive_family": "STATE",
            "statement": "The model is released.",
        }],
        current_slots=[{
            "slot_id": "state-release",
            "primitive_family": "STATE",
            "slot_label": "Release",
            "state_question": "What is this system's release status?",
        }],
        top_k=2,
        retriever=CoordinateCandidateRetriever(fake_embed),
    )
    row = plan.propositions[0]
    assert row.candidate_slot_ids == ("state-release",)
    assert row.hidden_same_family_slot_ids == ()
    assert row.create_requires_expansion is False
