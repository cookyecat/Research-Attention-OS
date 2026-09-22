from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

import app.models  # noqa: F401
from app.cognitive.client import chat_json
from app.db import Base
from app.models.event import Event, EventMembershipAssertion
from app.models.source import Source
from app.services.event_observation import EventObservationV01
from app.services.event_state_slot_delta import (
    CurrentSlotV01,
    SemanticSlotStateV01,
    apply_slot_delta,
    make_slot_state,
)
from app.services.event_state_proposition_keyby import decide_slot_delta_two_stage

RUN_VERSION = "phase17-state-slot-delta-two-stage-real-model-v0.8"
OUT_DIR = ROOT / "eval/live/results/phase17_state_slot_delta_two_stage_real_model_v0_8"
def _db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return Session(engine)


def _event(db):
    row = Event(
        title="Jev model launch / emergence and early validation episode",
        event_type="MODEL_LAUNCH_EARLY_VALIDATION",
        actors=["TypeSafe AI / Jev authors and ecosystem participants"],
        action="launch, explain, test, and early-validate Jev",
        object="Jev model",
        summary="controlled keyed-slot probe",
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
        fingerprint=f"slot-real-{uuid4()}",
        ingestion_method="CONTROLLED_EVAL",
        raw_metadata={},
    )
    db.add(row)
    db.flush()
    return row


def _member(db,event,source,local=False):
    db.add(EventMembershipAssertion(
        workspace_id="local-default",
        event_id=event.id,
        source_id=source.id,
        frame_ids=[],
        action="ASSERT",
        membership="REPORTS_EVENT",
        contextual_role_fields={},
        audit_run_id=None,
        authority_policy_version="slot-real",
        authority_epoch=1,
        authority_status="AUTHORIZED_SOURCE_LOCAL" if local else "AUTHORIZED",
        supersedes_assertion_id=None,
    ))
    db.flush()
def _obs(event,source,key,refs,day=18):
    return EventObservationV01(
        event_id=event.id,
        observation_key=(key*64)[:64],
        source_id=source.id,
        semantic_input_digests=(f"sem-{key}",),
        evidence_time=datetime(2026,9,day,12,0,tzinfo=timezone.utc),
        ingest_time=datetime(2026,9,day,12,1,tzinfo=timezone.utc),
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


def _slot(slot_id,label,question,value,refs,primitive_family=None):
    return CurrentSlotV01(
        slot_id=slot_id,
        primitive_family=primitive_family or _infer_family(label, question),
        slot_label=label,
        state_question=question,
        value=value,
        support_refs=refs,
    )
def _state(event, slots, status="ACTIVE"):
    return make_slot_state(
        event_id=event.id,
        slots=tuple(slots),
        status=status,
        effective_at=datetime(2026,9,16,12,0,tzinfo=timezone.utc),
    )


def _identity(event):
    return {
        "title": event.title,
        "event_type": event.event_type,
        "actors": list(event.actors or []),
        "action": event.action,
        "object": event.object,
    }
def _run_case(
    *,
    name,
    previous_slots,
    previous_units,
    new_units,
    expect_mutations,
    expect_create,
    expect_existing,
    expect_slot_count,
    expect_status="ACTIVE",
    previous_status="ACTIVE",
    forbid_created_question_terms=(),
    forbid_created_value_terms=(),
    expect_created_families=None,
):
    db=_db()
    try:
        event=_event(db)
        sources=[]
        previous=None
        if previous_slots:
            a=_source(db,"previous")
            _member(db,event,a,local=True)
            sources.append(a.id)
            previous=_state(event,previous_slots,status=previous_status)
        b=_source(db,"new")
        _member(db,event,b,local=previous is None)
        sources.append(b.id)
        refs=tuple(row["unit_id"] for row in new_units)
        obs=_obs(event,b,"b",refs)

        decision=decide_slot_delta_two_stage(
            event_identity=_identity(event),
            previous=previous,
            observation=obs,
            previous_support_units=previous_units,
            new_semantic_units=new_units,
            chat_fn=chat_json,
        )
        delta=decision.delta
        applied=apply_slot_delta(
            db,
            event_id=event.id,
            previous=previous,
            observation=obs,
            delta=delta,
            supporting_source_ids=sources,
        )
        mutations=list(delta.mutations) if delta is not None else []
        modes=[m.mode for m in mutations]
        created_questions=[
            m.slot.state_question for m in mutations if m.mode=="CREATE"
        ]
        created_values=[
            m.slot.value for m in mutations if m.mode=="CREATE"
        ]
        created_families=[
            m.slot.primitive_family for m in mutations if m.mode=="CREATE"
        ]
        lowered="\n".join(created_questions).lower()
        value_lowered="\n".join(created_values).lower()
        forbidden_hits=[
            term for term in forbid_created_question_terms
            if term.lower() in lowered
        ]
        forbidden_value_hits=[
            term for term in forbid_created_value_terms
            if term.lower() in value_lowered
        ]
        family_match=(
            True if expect_created_families is None
            else sorted(created_families)==sorted(expect_created_families)
        )
        return {
            "name": name,
            "mutation_count": len(mutations),
            "expect_mutations": expect_mutations,
            "mutation_count_match": len(mutations)==expect_mutations,
            "create_count": modes.count("CREATE"),
            "expect_create": expect_create,
            "create_match": modes.count("CREATE")==expect_create,
            "existing_count": sum(1 for m in mutations if m.mode in {"UPSERT","CONTEST"}),
            "expect_existing": expect_existing,
            "existing_match": sum(1 for m in mutations if m.mode in {"UPSERT","CONTEST"})==expect_existing,
            "slot_count": len(applied.slot_state.slots),
            "expect_slot_count": expect_slot_count,
            "slot_count_match": len(applied.slot_state.slots)==expect_slot_count,
            "status": applied.slot_state.status,
            "expect_status": expect_status,
            "status_match": applied.slot_state.status==expect_status,
            "created_questions": created_questions,
            "created_values": created_values,
            "created_families": created_families,
            "expect_created_families": expect_created_families,
            "created_family_match": family_match,
            "forbidden_question_hits": forbidden_hits,
            "forbidden_value_hits": forbidden_value_hits,
            "question_constraint_match": not forbidden_hits and not forbidden_value_hits,
            "technical_error": None,
            "flatmap": decision.flatmap.model_dump(mode="json"),
            "keyby_draft": decision.keyby_draft.model_dump(mode="json"),
            "delta": delta.model_dump(mode="json") if delta else None,
            "slot_state": applied.slot_state.model_dump(mode="json"),
        }
    except Exception as exc:
        return {
            "name": name,
            "mutation_count": -1,
            "expect_mutations": expect_mutations,
            "mutation_count_match": False,
            "create_count": -1,
            "expect_create": expect_create,
            "create_match": False,
            "existing_count": -1,
            "expect_existing": expect_existing,
            "existing_match": False,
            "slot_count": -1,
            "expect_slot_count": expect_slot_count,
            "slot_count_match": False,
            "status": "ERROR",
            "expect_status": expect_status,
            "status_match": False,
            "created_questions": [],
            "created_values": [],
            "created_families": [],
            "expect_created_families": expect_created_families,
            "created_family_match": False,
            "forbidden_question_hits": [],
            "forbidden_value_hits": [],
            "question_constraint_match": False,
            "technical_error": f"{type(exc).__name__}: {exc}",
            "flatmap": None,
            "keyby_draft": None,
            "delta": None,
            "slot_state": None,
        }
    finally:
        db.close()


def run():
    cases=[]

    cases.append(_run_case(
        name="EXISTING_KEY_REUSE",
        previous_slots=[
            _slot("slot-release","lifecycle","What is the current release/availability status?","The system has been released.",("uOld",))
        ],
        previous_units=[{"unit_id":"uOld","statement":"The system has been released."}],
        new_units=[{"unit_id":"uNew","statement":"Jev is now available on Hugging Face and training code is planned."}],
        expect_mutations=1, expect_create=0, expect_existing=1, expect_slot_count=1,
    ))

    cases.append(_run_case(
        name="NEW_DIMENSION_CREATE",
        previous_slots=[
            _slot("slot-release","lifecycle","What is the current release/availability status?","The system has been released.",("uOld",))
        ],
        previous_units=[{"unit_id":"uOld","statement":"The system has been released."}],
        new_units=[{"unit_id":"uPerf","statement":"The author claims Jev is 20-200x faster and 40-400x cheaper."}],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=2,
        forbid_created_question_terms=("jev","source","validation","evidence","confidence"),
    ))

    cases.append(_run_case(
        name="MULTI_SLOT_UPDATE_WORLD",
        previous_slots=[
            _slot("slot-performance","performance","What are the current performance characteristics?","Reported latency is about 500ms per move.",("uPerfOld",)),
            _slot("slot-capability","capability","What capabilities or behaviors has the system demonstrated?","The system has demonstrated game-playing.",("uCapOld",)),
        ],
        previous_units=[
            {"unit_id":"uPerfOld","statement":"Reported latency is about 500ms per move."},
            {"unit_id":"uCapOld","statement":"The system has demonstrated game-playing."},
        ],
        new_units=[{"unit_id":"uBench","statement":"A Tetris run reports Jev played 200 pieces in real time, scored 9200, and ran at 300ms per move."}],
        expect_mutations=2, expect_create=0, expect_existing=2, expect_slot_count=2,
    ))

    cases.append(_run_case(
        name="ACHIEVED_ACTION_SPLITS_CAPABILITY_AND_QUALITY",
        previous_slots=[
            _slot(
                "slot-capability",
                "capability",
                "What capabilities or behaviors has the system demonstrated?",
                "The system has demonstrated complex task execution.",
                ("uCapOld",),
                primitive_family="DISPOSITION",
            ),
            _slot(
                "slot-performance",
                "performance",
                "What are the current performance characteristics?",
                "No completion-time measurement is yet recorded.",
                ("uPerfOld",),
                primitive_family="QUALITY",
            ),
        ],
        previous_units=[
            {"unit_id":"uCapOld","statement":"The system has demonstrated complex task execution."},
            {"unit_id":"uPerfOld","statement":"No completion-time measurement is yet recorded."},
        ],
        new_units=[{
            "unit_id":"uAchievement",
            "statement":"The system rebuilt a complex subsystem in about one hour; the source does not describe the internal procedure used."
        }],
        expect_mutations=2, expect_create=0, expect_existing=2, expect_slot_count=2,
    ))

    cases.append(_run_case(
        name="PERIPHERAL_NONE",
        previous_slots=[
            _slot("slot-capability","capability","What capabilities or behaviors has the system demonstrated?","The system has demonstrated game-playing.",("uDemo",))
        ],
        previous_units=[{"unit_id":"uDemo","statement":"The system has demonstrated game-playing."}],
        new_units=[{"unit_id":"uReaction","statement":"The author says this feels like everything is about to change and people sent DMs asking if the demo is real."}],
        expect_mutations=0, expect_create=0, expect_existing=0, expect_slot_count=1,
    ))

    cases.append(_run_case(
        name="CORRECTION_SAME_KEY",
        previous_slots=[
            _slot("slot-mechanism","mechanism","How does the system work?","It uses mechanism A.",("uOld",))
        ],
        previous_units=[{"unit_id":"uOld","statement":"Jev uses mechanism A."}],
        new_units=[{"unit_id":"uCorrection","statement":"The authors explicitly correct the earlier description: Jev uses mechanism B, not A."}],
        expect_mutations=1, expect_create=0, expect_existing=1, expect_slot_count=1,
    ))

    cases.append(_run_case(
        name="CONTEST_SAME_WORLD_KEY",
        previous_slots=[
            _slot("slot-performance","performance","What are the current performance characteristics?","A benchmark reports about 300ms per move.",("uPos",))
        ],
        previous_units=[{"unit_id":"uPos","statement":"A benchmark reports Jev at about 300ms per move."}],
        new_units=[{"unit_id":"uNeg","statement":"A separate benchmark under comparable conditions reports about 1.5 seconds per move and explicitly disputes the earlier 300ms result; the conflict is unresolved."}],
        expect_mutations=1, expect_create=0, expect_existing=1, expect_slot_count=1,
        expect_status="CONTESTED",
    ))

    cases.append(_run_case(
        name="MECHANISM_CREATES_NEW_SLOT",
        previous_slots=[
            _slot("slot-capability","capability","What capabilities or behaviors has the system demonstrated?","The system has demonstrated game-playing.",("uGames",))
        ],
        previous_units=[{"unit_id":"uGames","statement":"The system has demonstrated game-playing."}],
        new_units=[{"unit_id":"uMechanism","statement":"Jev uses a single Transformer decoder with KV-cache reuse and field-relevant token scoring instead of autoregressive JSON generation."}],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=2,
        forbid_created_question_terms=("jev","game","mario","source","validation","evidence"),
    ))

    cases.append(_run_case(
        name="EVIDENCE_ONLY_REPRODUCTION_NONE",
        previous_slots=[
            _slot("slot-performance","performance","What are the current performance characteristics?","A run reports about 300ms per move.",("uPerf",))
        ],
        previous_units=[{"unit_id":"uPerf","statement":"A run reports about 300ms per move."}],
        new_units=[{"unit_id":"uRepro","statement":"An independent team repeated the same benchmark and reproduced the existing 300ms-per-move result; it reports no materially different performance value."}],
        expect_mutations=0, expect_create=0, expect_existing=0, expect_slot_count=1,
    ))

    cases.append(_run_case(
        name="SOURCE_OMISSION_NONE",
        previous_slots=[
            _slot("slot-release","lifecycle","What is the current release/availability status?","The system is available in beta.",("uAvail",))
        ],
        previous_units=[{"unit_id":"uAvail","statement":"Jev is available in beta."}],
        new_units=[{"unit_id":"uOmission","statement":"This Tetris report discusses scores and latency but does not state whether Jev is released, private, or in beta."}],
        expect_mutations=0, expect_create=0, expect_existing=0, expect_slot_count=1,
    ))

    cases.append(_run_case(
        name="IDENTITY_CONFLICT_OUTSIDE_WORLD_NONE",
        previous_slots=[
            _slot("slot-release","lifecycle","What is the current release/availability status?","The system is available in beta.",("uAvail",))
        ],
        previous_units=[{"unit_id":"uAvail","statement":"Jev is available in beta."}],
        new_units=[{"unit_id":"uIdentityConflict","statement":"A new source explicitly states Jev is not an AI model but a human-operated system; it gives no new information about release or availability."}],
        expect_mutations=0, expect_create=0, expect_existing=0, expect_slot_count=1,
    ))

    cases.append(_run_case(
        name="REPEATED_DEMO_UPSERT",
        previous_slots=[
            _slot("slot-capability","capability","What capabilities or behaviors has the system demonstrated?","It has demonstrated Mario and DOOM game-playing.",("uGames",))
        ],
        previous_units=[{"unit_id":"uGames","statement":"It has demonstrated Mario and DOOM game-playing."}],
        new_units=[{"unit_id":"uTetris","statement":"A later demo shows Jev playing Tetris in real time."}],
        expect_mutations=1, expect_create=0, expect_existing=1, expect_slot_count=1,
    ))

    cases.append(_run_case(
        name="GENERAL_CAPABILITY_CREATE",
        previous_slots=[],
        previous_units=[],
        new_units=[{"unit_id":"uMario","statement":"A live demo shows Jev playing Super Mario Bros. in real time."}],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=1,
        expect_status="EMERGING",
        forbid_created_question_terms=("jev","mario","game","source","validation","evidence"),
    ))

    cases.append(_run_case(
        name="LIFECYCLE_IDENTITY_SEPARATION_CREATE",
        previous_slots=[],
        previous_units=[],
        new_units=[{"unit_id":"uRelease","statement":"TypeSafe AI announced that Jev is released and available to selected beta users."}],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=1,
        expect_status="EMERGING",
        forbid_created_question_terms=("jev","typesafe","who","what is the model","creator","source","validation","evidence"),
    ))

    cases.append(_run_case(
        name="SINGLE_SOURCE_PERFORMANCE_WORLD_CREATE",
        previous_slots=[
            _slot("slot-release","lifecycle","What is the current release/availability status?","The system is in beta.",("uAvail",))
        ],
        previous_units=[{"unit_id":"uAvail","statement":"Jev is in beta."}],
        new_units=[{"unit_id":"uClaim","statement":"The author claims Jev is 20-200x faster and 40-400x cheaper; no independent benchmark is provided."}],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=2,
        forbid_created_question_terms=("jev","validation","evidence","confidence","source","independent"),
    ))

    cases.append(_run_case(
        name="MECHANISM_INDEPENDENT_OF_OUTPUT_FORM",
        previous_slots=[
            _slot(
                "slot-output",
                "output form",
                "What is the form, format, or structure of this system's output?",
                "The system returns typed structured judgments rather than free-form strings.",
                ("uOutput",),
            )
        ],
        previous_units=[
            {
                "unit_id":"uOutput",
                "statement":"The system returns typed structured judgments rather than free-form strings."
            }
        ],
        new_units=[
            {
                "unit_id":"uMechanism",
                "statement":"The system uses one Transformer decoder pass with KV-cache reuse and per-field token scoring; this evidence gives no new information about the output format itself."
            }
        ],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=2,
        forbid_created_question_terms=("output format","output structure","typed judgment","jev"),
    ))

    cases.append(_run_case(
        name="OUTPUT_FORM_INDEPENDENT_OF_MECHANISM",
        previous_slots=[
            _slot(
                "slot-mechanism",
                "mechanism",
                "What internal process or mechanism transforms inputs/state into outputs/actions?",
                "It uses one Transformer decoder pass with KV-cache reuse.",
                ("uMechanism",),
            )
        ],
        previous_units=[
            {
                "unit_id":"uMechanism",
                "statement":"It uses one Transformer decoder pass with KV-cache reuse."
            }
        ],
        new_units=[
            {
                "unit_id":"uOutput",
                "statement":"The system returns typed structured judgments rather than free-form strings; this source gives no new mechanism information."
            }
        ],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=2,
        forbid_created_question_terms=("mechanism","architecture","how does","jev"),
    ))

    cases.append(_run_case(
        name="MECHANISM_ONLY_INDEPENDENT_OF_PERFORMANCE",
        previous_slots=[
            _slot("slot-performance","performance","What are the current performance characteristics?","Reported latency is 300ms per move.",("uPerf",))
        ],
        previous_units=[{"unit_id":"uPerf","statement":"Reported latency is 300ms per move."}],
        new_units=[{"unit_id":"uMechanism","statement":"Jev uses KV-cache reuse and field-relevant token scoring rather than autoregressive JSON generation; this source gives no new performance measurement."}],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=2,
        forbid_created_question_terms=("jev","performance","speed","cost","latency"),
    ))

    cases.append(_run_case(
        name="PERFORMANCE_ONLY_INDEPENDENT_OF_MECHANISM",
        previous_slots=[
            _slot("slot-mechanism","mechanism","How does the system work?","It uses KV-cache reuse and field-relevant token scoring.",("uMech",))
        ],
        previous_units=[{"unit_id":"uMech","statement":"It uses KV-cache reuse and field-relevant token scoring."}],
        new_units=[{"unit_id":"uPerf","statement":"A benchmark reports Jev at 300ms per move and $0.001 per run; it provides no new architecture or mechanism information."}],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=2,
        forbid_created_question_terms=("jev","mechanism","architecture","how does"),
    ))

    cases.append(_run_case(
        name="CAPABILITY_VS_AFFORDANCE",
        previous_slots=[
            _slot("slot-capability","capability","What capabilities or behaviors has the system demonstrated?","It has demonstrated real-time game-playing.",("uCap",))
        ],
        previous_units=[{"unit_id":"uCap","statement":"It has demonstrated real-time game-playing."}],
        new_units=[{"unit_id":"uAfford","statement":"The author proposes using Jev as a teaching assistant and workflow router, but provides no demonstration of either application."}],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=2,
        forbid_created_question_terms=("jev","game","demonstrated capability","validation","evidence"),
    ))

    cases.append(_run_case(
        name="MULTI_PROPOSITION_BASIS_COMPLETENESS",
        previous_slots=[
            _slot(
                "slot-capability",
                "capability",
                "What capabilities or behaviors has the system demonstrated?",
                "It has demonstrated real-time game-playing.",
                ("uCapOld",),
            ),
            _slot(
                "slot-affordance",
                "applications",
                "What applications or roles has the system been proposed or intended for?",
                "It has been proposed for real-time game agents.",
                ("uAffOld",),
            ),
        ],
        previous_units=[
            {"unit_id":"uCapOld","statement":"It has demonstrated real-time game-playing."},
            {"unit_id":"uAffOld","statement":"It has been proposed for real-time game agents."},
        ],
        new_units=[
            {"unit_id":"uCapNew","statement":"A new live demo shows Jev playing Tetris over 200 pieces."},
            {"unit_id":"uPerfNew","statement":"The same run reports about 300ms per move and near-zero cost."},
            {"unit_id":"uAffNew","statement":"The author proposes using Jev as a workflow router for software agents."},
        ],
        expect_mutations=3,
        expect_create=1,
        expect_existing=2,
        expect_slot_count=3,
        forbid_created_question_terms=(
            "jev","tetris","workflow","source","validation","evidence","confidence"
        ),
    ))

    cases.append(_run_case(
        name="SAME_PRIMITIVE_METRICS_ONE_KEY",
        previous_slots=[],
        previous_units=[],
        new_units=[
            {"unit_id":"uLatency","statement":"A report gives latency of about 300ms per decision."},
            {"unit_id":"uThroughput","statement":"The same report gives throughput of about 10 decisions per second."},
            {"unit_id":"uRate","statement":"It also reports a sustained inference rate under the same workload."},
        ],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=1,
        expect_status="EMERGING",
        forbid_created_question_terms=("jev","source","validation","evidence"),
    ))

    cases.append(_run_case(
        name="SINGLE_UNIT_MULTI_AXIS_SPLIT",
        previous_slots=[],
        previous_units=[],
        new_units=[{
            "unit_id":"uMixed",
            "statement":"The system returns typed structured judgments rather than free-form strings, and the author claims it is structurally incapable of hallucination."
        }],
        expect_mutations=2, expect_create=2, expect_existing=0, expect_slot_count=2,
        expect_status="EMERGING",
        forbid_created_question_terms=("benefit","advantage","jev"),
    ))

    cases.append(_run_case(
        name="BENEFIT_WRAPPER_DECOMPOSES",
        previous_slots=[],
        previous_units=[],
        new_units=[{
            "unit_id":"uBenefit",
            "statement":"The stated benefits are lower-latency operation and 100% valid structured output."
        }],
        expect_mutations=2, expect_create=2, expect_existing=0, expect_slot_count=2,
        expect_status="EMERGING",
        forbid_created_question_terms=("benefit","advantage","strength","feature","jev"),
    ))

    cases.append(_run_case(
        name="CROSS_PRIMITIVE_CONJUNCTION_SPLITS_KEYS",
        previous_slots=[],
        previous_units=[],
        new_units=[
            {
                "unit_id":"uOutput",
                "statement":"Jev returns typed judgments rather than free-form strings."
            },
            {
                "unit_id":"uReliability",
                "statement":"The author separately claims Jev is structurally incapable of hallucination."
            },
        ],
        expect_mutations=2, expect_create=2, expect_existing=0, expect_slot_count=2,
        expect_status="EMERGING",
        forbid_created_question_terms=("jev","source","validation","evidence"),
    ))


    cases.append(_run_case(
        name="PRESENTATION_VISUALIZATION_NONE",
        previous_slots=[
            _slot(
                "slot-capability",
                "capability",
                "What capabilities or behaviors has the system demonstrated?",
                "It has demonstrated real-time game-playing.",
                ("uCap",),
            )
        ],
        previous_units=[{"unit_id":"uCap","statement":"It has demonstrated real-time game-playing."}],
        new_units=[{
            "unit_id":"uViz",
            "statement":"The author used Claude to create a visualization explaining how Jev works."
        }],
        expect_mutations=0, expect_create=0, expect_existing=0, expect_slot_count=1,
    ))

    cases.append(_run_case(
        name="INCIDENTAL_DEMO_HARDWARE_NONE",
        previous_slots=[
            _slot(
                "slot-capability",
                "capability",
                "What capabilities or behaviors has the system demonstrated?",
                "It has demonstrated real-time game-playing.",
                ("uCap",),
            )
        ],
        previous_units=[{"unit_id":"uCap","statement":"It has demonstrated real-time game-playing."}],
        new_units=[{
            "unit_id":"uHardware",
            "statement":"The explanatory demo is presented on an M4 MacBook; the source makes no compatibility or performance claim about that hardware."
        }],
        expect_mutations=0, expect_create=0, expect_existing=0, expect_slot_count=1,
    ))

    cases.append(_run_case(
        name="BASE_MODEL_LINEAGE_TARGET_STRUCTURE",
        previous_slots=[
            _slot(
                "slot-release",
                "lifecycle",
                "What is the current release/availability status?",
                "The system has been released.",
                ("uRelease",),
            )
        ],
        previous_units=[{"unit_id":"uRelease","statement":"The system has been released."}],
        new_units=[{
            "unit_id":"uLineage",
            "statement":"Jev is based on the Qwen2.5-RLCD model published by Harsha Gundal on Hugging Face."
        }],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=2,
        expect_created_families=("STRUCTURE",),
        forbid_created_question_terms=("harsha","hugging","publisher","provenance"),
        forbid_created_value_terms=("harsha","hugging face","published by"),
    ))

    cases.append(_run_case(
        name="RELATED_COMPONENT_RELEASE_NONE",
        previous_slots=[
            _slot(
                "slot-release",
                "lifecycle",
                "What is the current release/availability status?",
                "Jev has been released.",
                ("uRelease",),
            )
        ],
        previous_units=[{"unit_id":"uRelease","statement":"Jev has been released."}],
        new_units=[{
            "unit_id":"uComponent",
            "statement":"The separate Qwen2.5-RLCD base model is open-sourced and is reported as 5x faster on-device for type-safe JSON workloads; this says nothing new about Jev's own release status."
        }],
        expect_mutations=0, expect_create=0, expect_existing=0, expect_slot_count=1,
    ))

    cases.append(_run_case(
        name="APPLICATION_INFRA_NORMALIZES_TO_RELATION",
        previous_slots=[
            _slot(
                "slot-capability",
                "capability",
                "What capabilities or behaviors has the system demonstrated?",
                "Jev has demonstrated decision-making.",
                ("uCap",),
            )
        ],
        previous_units=[{"unit_id":"uCap","statement":"Jev has demonstrated decision-making."}],
        new_units=[{
            "unit_id":"uTrading",
            "statement":"Jev is integrated into an automated trading workflow that uses Monad for execution and Kuru as the on-chain order book."
        }],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=2,
        expect_created_families=("RELATION",),
        forbid_created_question_terms=("monad","kuru","block","order book"),
    ))

    cases.append(_run_case(
        name="COMPOSITE_WORKFLOW_NOT_TARGET_PROCESS",
        previous_slots=[
            _slot(
                "slot-capability",
                "capability",
                "What capabilities or behaviors has the system demonstrated?",
                "Jev has demonstrated browser decision-making.",
                ("uCap",),
            )
        ],
        previous_units=[{"unit_id":"uCap","statement":"Jev has demonstrated browser decision-making."}],
        new_units=[{
            "unit_id":"uWorkflow",
            "statement":"A browser agent surrounding Jev uses a DOM state space, a new action space each step, and a small LLM fallback; Jev is integrated into that workflow for decisions."
        }],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=2,
        expect_created_families=("RELATION",),
        forbid_created_question_terms=("dom","fallback","action space"),
    ))

    cases.append(_run_case(
        name="TARGET_RELEASE_STRIPS_IDENTITY_PROVENANCE",
        previous_slots=[
            _slot(
                "slot-capability",
                "capability",
                "What capabilities or behaviors has the system demonstrated?",
                "Jev has demonstrated game-playing.",
                ("uCap",),
            )
        ],
        previous_units=[{"unit_id":"uCap","statement":"Jev has demonstrated game-playing."}],
        new_units=[{
            "unit_id":"uRelease",
            "statement":"After two years of secret R&D, a ChatGPT co-inventor announced and released the new AI model Jev."
        }],
        expect_mutations=1, expect_create=1, expect_existing=0, expect_slot_count=2,
        expect_created_families=("STATE",),
        forbid_created_question_terms=("chatgpt","inventor","ai model","two years","creator"),
        forbid_created_value_terms=("chatgpt","inventor","two years","secret r&d"),
    ))

    diagnostics={
        "mutation_count_matches":sum(r["mutation_count_match"] for r in cases),
        "create_matches":sum(r["create_match"] for r in cases),
        "existing_matches":sum(r["existing_match"] for r in cases),
        "slot_count_matches":sum(r["slot_count_match"] for r in cases),
        "status_matches":sum(r["status_match"] for r in cases),
        "question_constraint_matches":sum(r["question_constraint_match"] for r in cases),
        "created_family_matches":sum(r["created_family_match"] for r in cases),
    }
    diagnostics["all_pass"]=all(
        r["mutation_count_match"] and r["create_match"] and r["existing_match"]
        and r["slot_count_match"] and r["status_match"]
        and r["question_constraint_match"] and r["created_family_match"]
        for r in cases
    )
    return {"run_version":RUN_VERSION,"cases":cases,"diagnostics":diagnostics}
def main():
    report=run()
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path=OUT_DIR/f"{RUN_VERSION.replace('-','_')}_{stamp}.json"
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("RESULT_PATH="+str(path.relative_to(ROOT)))
    for row in report["cases"]:
        print(
            row["name"],
            "mut",row["mutation_count"],"/",row["expect_mutations"],
            "create",row["create_count"],
            "existing",row["existing_count"],
            "slots",row["slot_count"],
            "status",row["status"],
        )
        print(" ",json.dumps(row["delta"],ensure_ascii=False))
    print("DIAGNOSTICS",json.dumps(report["diagnostics"],ensure_ascii=False))

if __name__=="__main__":
    main()
