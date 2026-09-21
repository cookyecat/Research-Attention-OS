from __future__ import annotations

from uuid import uuid4

from sqlalchemy import func, select

from app.models.event import Event, EventEvidenceFrame, EventMembershipAssertion, EventRevision, EventSource
from app.services.event_processor import process_event
from app.services.extraction import ExtractionResult
from app.services.ingestion import ingest_text


def _source(db, title: str, text: str):
    return ingest_text(db, text, title=title)


def _chat(candidate_payload: dict, resolver_payload: dict | None = None):
    def call(messages, **_kwargs):
        system = messages[0]["content"]
        if "Event Processor V1" in system:
            return candidate_payload, {"model": "fake-event-v1"}
        if "coarse Event Resolver V1" in system:
            assert resolver_payload is not None
            payload = dict(resolver_payload)
            if payload.get("matched_event_id") == "__FIRST__":
                import json
                user = json.loads(messages[-1]["content"].split("\n\n", 1)[1])
                payload["matched_event_id"] = user["existing_event_candidates"][0]["event_id"]
            return payload, {"model": "fake-event-v1"}
        raise AssertionError(system[:80])
    return call


def _candidate(title: str, *, state: str | None = None):
    return {
        "title": title,
        "event_type": "PRODUCT_RELEASE",
        "actors": ["Acme"],
        "action": "release Nimbus API",
        "object": "Nimbus API",
        "occurred_at": None,
        "time_context": "2026-09-20",
        "location": None,
        "description": title,
        "current_state": state,
        "attributes": {},
        "support_unit_ids": [],
        "missing_fields": [],
    }


def test_same_event_merges_two_sources_and_appends_revision(db):
    a = _source(db, "Acme launches Nimbus API", "Acme launches Nimbus API.")
    ra = process_event(db, a, ExtractionResult(event_title=a.title, event_summary=a.content_text), chat_fn=_chat(_candidate(a.title)))
    assert ra.created is True

    b = _source(db, "Reuters: Acme Nimbus API launch", "Reuters reports the same Nimbus API launch.")
    rb = process_event(
        db,
        b,
        ExtractionResult(event_title=b.title, event_summary=b.content_text),
        chat_fn=_chat(
            _candidate("Acme Nimbus API launch confirmed", state="launched"),
            {"decision": "SAME_EVENT", "matched_event_id": "__FIRST__", "rationale": "Same release story.", "missing_evidence": []},
        ),
    )

    assert rb.created is False
    assert rb.event.id == ra.event.id
    assert db.scalar(select(func.count()).select_from(Event)) == 1
    assert db.scalar(select(func.count()).select_from(EventSource)) == 2
    assert db.scalar(select(func.count()).select_from(EventRevision)) == 2
    revisions = db.execute(
        select(EventRevision).where(EventRevision.event_id == rb.event.id)
    ).scalars().all()
    by_kind = {row.revision_payload["kind"]: row for row in revisions}
    first_state = by_kind["CREATE"].revision_payload["event_state"]
    latest_state = by_kind["UPDATE"].revision_payload["event_state"]
    assert first_state["contract"] == "event-state-v0.1"
    assert first_state["evidence_state"]["member_source_count"] == 1
    assert latest_state["evidence_state"]["member_source_count"] == 2
    assert latest_state["evidence_state"]["independent_source_count"] == 2
    assert latest_state["evidence_state"]["arrival_momentum"] is None
    assert latest_state["world_state"]["current_state"] == "launched"

    assertion = db.execute(
        select(EventMembershipAssertion).where(EventMembershipAssertion.source_id == b.id)
    ).scalar_one()
    assert assertion.authority_status == "AUTHORIZED"
    assert assertion.contextual_role_fields["cross_source_commitment"] is True
    assert rb.event.current_state == "launched"


def test_different_event_creates_new_event(db):
    a = _source(db, "Acme launches Nimbus API", "Acme launches Nimbus API.")
    process_event(db, a, ExtractionResult(event_title=a.title, event_summary=a.content_text), chat_fn=_chat(_candidate(a.title)))

    b = _source(db, "Acme opens Nimbus grants", "Acme opens a separate university grant program.")
    rb = process_event(
        db,
        b,
        ExtractionResult(event_title=b.title, event_summary=b.content_text),
        chat_fn=_chat(
            {
                **_candidate("Acme opens Nimbus grants"),
                "action": "open grant program",
                "object": "Nimbus university grants",
            },
            {"decision": "DIFFERENT_EVENT", "matched_event_id": None, "rationale": "Separate story.", "missing_evidence": []},
        ),
    )
    assert rb.created is True
    assert db.scalar(select(func.count()).select_from(Event)) == 2


def test_uncertain_never_merges(db):
    a = _source(db, "Acme launches Nimbus API", "Acme launches Nimbus API.")
    ra = process_event(db, a, ExtractionResult(event_title=a.title, event_summary=a.content_text), chat_fn=_chat(_candidate(a.title)))

    b = _source(db, "Nimbus update", "An unclear Nimbus update is reported.")
    rb = process_event(
        db,
        b,
        ExtractionResult(event_title=b.title, event_summary=b.content_text),
        chat_fn=_chat(
            _candidate("Nimbus update"),
            {"decision": "UNCERTAIN", "matched_event_id": str(ra.event.id), "rationale": "Insufficient identity evidence.", "missing_evidence": ["exact episode"]},
        ),
    )
    assert rb.created is True
    assert rb.event.id != ra.event.id
    assert db.scalar(select(func.count()).select_from(Event)) == 2


def test_reprocess_same_observation_is_exactly_once_noop(db):
    a = _source(db, "Acme launches Nimbus API", "Acme launches Nimbus API.")
    first = process_event(
        db,
        a,
        ExtractionResult(event_title=a.title, event_summary=a.content_text),
        chat_fn=_chat(_candidate(a.title)),
    )
    second = process_event(
        db,
        a,
        ExtractionResult(event_title=a.title, event_summary="Updated details about the same launch."),
        chat_fn=_chat(_candidate(a.title, state="completed")),
    )
    assert second.reused_existing_membership is True
    assert second.event.id == first.event.id
    assert db.scalar(select(func.count()).select_from(Event)) == 1
    assert db.scalar(select(func.count()).select_from(EventRevision)) == 1
    assert second.event.current_state is None
    assert second.execution["observation"]["already_applied"] is True


def test_reprocess_changed_admitted_semantics_creates_new_observation_revision(db):
    a = _source(db, "Acme launches Nimbus API", "Acme launches Nimbus API.")
    first = process_event(
        db,
        a,
        ExtractionResult(event_title=a.title, event_summary=a.content_text),
        chat_fn=_chat(_candidate(a.title)),
    )
    db.add(
        EventEvidenceFrame(
            identity_key=f"changed-semantic-{uuid4()}",
            workspace_id="local-default",
            source_id=a.id,
            source_snapshot_id=None,
            analysis_run_id=None,
            frame_contract_version="event-evidence-frame-v0.3",
            semantic_input_digest="semantic-change-v1",
            frame_payload={"audited_semantic_units": [{"unit_id": "unit-change"}]},
            frame_digest=f"frame-{uuid4()}",
        )
    )
    db.flush()

    second = process_event(
        db,
        a,
        ExtractionResult(event_title=a.title, event_summary="Updated admitted semantics."),
        chat_fn=_chat(_candidate(a.title, state="completed")),
    )

    assert second.event.id == first.event.id
    assert second.event.current_state == "completed"
    assert second.execution["observation"]["already_applied"] is False
    revisions = db.execute(
        select(EventRevision).where(EventRevision.event_id == first.event.id)
    ).scalars().all()
    assert len(revisions) == 2
    assert len({row.observation_key for row in revisions}) == 2



def test_event_candidate_accepts_date_only_and_fills_audited_support_ids(db):
    from app.services.event_processor import extract_event_candidate
    from app.services.extraction import ExtractedClaim
    from app.enums import AttributionType, ClaimType

    source = _source(db, "Dated event", "Acme released Nimbus.")
    extraction = ExtractionResult(
        event_title="Dated event",
        event_summary="Acme released Nimbus.",
        claims=[
            ExtractedClaim(
                text="Acme released Nimbus.",
                claim_type=ClaimType.FACTUAL,
                attributed_to="Acme",
                attribution_type=AttributionType.COMPANY,
                semantic_unit_id="unit-1",
                semantic_supports=[
                    {
                        "source_id": str(source.id),
                        "support_pointer": "PARA 0001",
                        "support_excerpt": "Acme released Nimbus.",
                    }
                ],
            )
        ],
    )
    payload = _candidate("Acme released Nimbus")
    payload["occurred_at"] = "2026-09-20"
    payload["support_unit_ids"] = []
    candidate, meta = extract_event_candidate(
        source,
        extraction,
        chat_fn=_chat(payload),
    )
    assert candidate.occurred_at is not None
    assert candidate.occurred_at.date().isoformat() == "2026-09-20"
    assert candidate.support_unit_ids == [f"{source.id}:unit-1"]
    assert meta["support_ids_filled_from_audited_units"] is True



def test_pipeline_two_sources_same_event_share_one_current_attention_candidate(db, monkeypatch):
    import app.services.event_processor as event_processor
    from app.services.current_attention import current_attention_plans
    from app.services.pipeline import run_pipeline
    from app.testing.kernel_fixture import seed_mvp_kernel

    seed_mvp_kernel(db)
    a = _source(
        db,
        "Acme launches Nimbus API public beta",
        "Acme launched the Nimbus API public beta at AtlasConf.",
    )
    first = run_pipeline(db, a.id, reprocess=True)
    event_id = first["attention_plan"]["candidate_id"]

    def force_same(candidate, candidate_rows, **_kwargs):
        assert candidate_rows
        return (
            event_processor.EventResolutionV1(
                decision="SAME_EVENT",
                matched_event_id=candidate_rows[0]["event_id"],
                rationale="Controlled same coarse story.",
                missing_evidence=[],
            ),
            {"mode": "CONTROLLED_TEST"},
        )

    monkeypatch.setattr(event_processor, "resolve_event_candidate", force_same)
    b = _source(
        db,
        "Reuters reports Acme Nimbus API public beta launch",
        "Reuters independently reports Acme launched the Nimbus API public beta at AtlasConf.",
    )
    second = run_pipeline(db, b.id, reprocess=True)

    assert second["attention_plan"]["candidate_type"] == "EVENT"
    assert second["attention_plan"]["candidate_id"] == event_id
    assert second["event_processor"]["resolution"]["decision"] == "SAME_EVENT"
    assert db.scalar(select(func.count()).select_from(Event)) == 1
    assert db.scalar(select(func.count()).select_from(EventSource)) == 2

    current = [
        plan
        for plan in current_attention_plans(db)
        if str(plan.candidate_type) == "EVENT" and str(plan.candidate_id) == event_id
    ]
    assert len(current) == 1


def test_event_revision_chain_is_linear_under_rapid_distinct_observations(db):
    a = _source(db, "Acme launches Nimbus API", "Acme launches Nimbus API.")
    first = process_event(
        db,
        a,
        ExtractionResult(event_title=a.title, event_summary=a.content_text),
        chat_fn=_chat(_candidate(a.title, state="announced")),
    )

    b = _source(db, "Reuters confirms Nimbus launch", "Reuters confirms the Nimbus launch.")
    process_event(
        db,
        b,
        ExtractionResult(event_title=b.title, event_summary=b.content_text),
        chat_fn=_chat(
            _candidate("Nimbus launched", state="launched"),
            {
                "decision": "SAME_EVENT",
                "matched_event_id": "__FIRST__",
                "rationale": "Same Nimbus release episode.",
                "missing_evidence": [],
            },
        ),
    )

    c = _source(db, "Acme says Nimbus rollout completed", "Acme says the rollout completed.")
    process_event(
        db,
        c,
        ExtractionResult(event_title=c.title, event_summary=c.content_text),
        chat_fn=_chat(
            _candidate("Nimbus rollout completed", state="completed"),
            {
                "decision": "SAME_EVENT",
                "matched_event_id": "__FIRST__",
                "rationale": "Same Nimbus release episode.",
                "missing_evidence": [],
            },
        ),
    )

    rows = db.execute(
        select(EventRevision).where(EventRevision.event_id == first.event.id)
    ).scalars().all()
    assert len(rows) == 3
    assert len({row.observation_key for row in rows}) == 3

    by_id = {row.id: row for row in rows}
    children = {}
    for row in rows:
        if row.parent_revision_id is not None:
            children.setdefault(row.parent_revision_id, []).append(row.id)

    roots = [row for row in rows if row.parent_revision_id is None]
    heads = [row for row in rows if row.id not in children]
    assert len(roots) == 1
    assert len(heads) == 1

    cursor = roots[0]
    visited = [cursor.id]
    while cursor.id in children:
        assert len(children[cursor.id]) == 1
        cursor = by_id[children[cursor.id][0]]
        visited.append(cursor.id)
    assert len(visited) == 3
    assert heads[0].id == visited[-1]
