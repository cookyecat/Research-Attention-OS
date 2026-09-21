from __future__ import annotations

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
from app.db import Base
from app.cognitive.prompts import MATCH_SYSTEM
from app.cognitive.research_aligned_contract import (
    GROUNDING_SYSTEM,
    RELATION_MAPPING_SYSTEM,
    SUPPORT_BINDING_SYSTEM,
    canonical_semantic_units,
)
from app.cognitive.research_aligned_provider import ResearchAlignedCognitiveProvider
from app.enums import SourceEdgeRelationship
from app.models.event import Event, EventEvidenceFrame, EventMembershipAssertion, EventSource
from app.models.kernel import KernelNode
from app.models.source import Source, SourceEdge
from app.services.event_cognition_input import build_event_cognition_input
from app.services.frame_conditioned_cognition import event_frame_to_extraction
from app.services.scheduler import RuntimeView, get_decision_strategy, route

RUN_VERSION = "phase17-event-state-cognition-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase17_event_state_cognition_v0_1"

CHALLENGE_STATEMENT = (
    "Profiler evidence shows kernel launch overhead dominates runtime for a small "
    "64x64 bf16 matrix multiplication with bias."
)
CORRECTION_STATEMENT = (
    "The authors corrected the profiler interpretation: the earlier launch-overhead "
    "conclusion applied only to setup-heavy measurements; in the steady-state 64x64 "
    "bf16 matmul run, computation remains dominant."
)


def _meta() -> dict:
    return {
        "latency_ms": 1,
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "model": "phase17-controlled-transport",
    }


def _belief_node() -> KernelNode:
    statement = (
        "For a small 64x64 bf16 matrix multiplication with bias, computation dominates "
        "runtime rather than kernel preparation and launch overhead."
    )
    return KernelNode(
        id=uuid4(),
        node_type="BELIEF",
        title="Computation dominates runtime.",
        status="ACTIVE",
        payload={"proposition": statement, "importance": 0.9},
        current_version=1,
    )


def _source(db: Session, title: str) -> Source:
    source = Source(
        source_type="TEXT",
        title=title,
        content_text=title,
        fingerprint=f"phase17-{uuid4()}",
        ingestion_method="CONTROLLED_EVAL",
        raw_metadata={},
    )
    db.add(source)
    db.flush()
    return source


def _event(db: Session) -> Event:
    event = Event(
        title="64x64 bf16 matmul profiler result",
        event_type="RESEARCH_RESULT",
        actors=["Acme Research"],
        action="report and correct profiler interpretation",
        object="64x64 bf16 matrix multiplication with bias",
        time_context="2026-09-21",
        summary="Acme Research reports profiler evidence and subsequent interpretation updates.",
        current_state="updated",
        confidence=0.8,
        status="CANDIDATE",
    )
    db.add(event)
    db.flush()
    return event


def _member(db: Session, event: Event, source: Source, *, local: bool) -> None:
    db.add(
        EventSource(
            event_id=event.id,
            source_id=source.id,
            relationship="REPORTS",
            confidence=0.9,
        )
    )
    db.add(
        EventMembershipAssertion(
            workspace_id="local-default",
            event_id=event.id,
            source_id=source.id,
            frame_ids=[],
            action="ASSERT",
            membership="REPORTS_EVENT",
            contextual_role_fields={
                "origin": "PHASE17_CONTROLLED",
                "cross_source_commitment": not local,
            },
            audit_run_id=None,
            authority_policy_version="phase17-controlled",
            authority_epoch=1,
            authority_status="AUTHORIZED_SOURCE_LOCAL" if local else "AUTHORIZED",
            supersedes_assertion_id=None,
        )
    )
    db.flush()


def _frame(db: Session, source: Source, statement: str, label: str) -> EventEvidenceFrame:
    unit_id = f"{source.id}:action_change:{label}"
    support = {
        "source_id": str(source.id),
        "support_pointer": f"PARA {label}",
        "support_excerpt": statement,
    }
    payload = {
        "event_key": "phase17-profiler-event",
        "event_summary": statement,
        "rendered_event_text": statement,
        "audited_semantic_units": [
            {
                "unit_id": unit_id,
                "statement": statement,
                "epistemic_status": "SOURCE_CLAIM",
                "confidence": "HIGH",
                "supports": [support],
            }
        ],
    }
    row = EventEvidenceFrame(
        identity_key=f"phase17-{uuid4()}",
        workspace_id="local-default",
        source_id=source.id,
        source_snapshot_id=None,
        analysis_run_id=None,
        frame_contract_version="event-evidence-frame-v0.3",
        semantic_input_digest=f"semantic-{label}-{uuid4()}",
        frame_payload=payload,
        frame_digest=f"frame-{label}-{uuid4()}",
    )
    db.add(row)
    db.flush()
    return row


def _classify_units(extraction) -> dict:
    units = canonical_semantic_units(extraction)
    challenge = [
        row for row in units
        if "launch overhead dominates runtime" in row["statement"].lower()
    ]
    correction = [
        row for row in units
        if "computation remains dominant" in row["statement"].lower()
    ]
    return {
        "units": units,
        "challenge": challenge,
        "correction": correction,
    }


def _run_cognition(
    extraction,
    node: KernelNode,
    *,
    independent_source_count: int,
    secondary_report_count: int,
) -> dict:
    classified = _classify_units(extraction)
    challenge_ids = [row["unit_id"] for row in classified["challenge"]]
    correction_ids = [row["unit_id"] for row in classified["correction"]]

    def fake_chat(messages, **_kwargs):
        system = messages[0]["content"]
        if system == MATCH_SYSTEM:
            if challenge_ids or correction_ids:
                return {
                    "matches": [
                        {
                            "kernel_node_id": str(node.id),
                            "relevance_type": "EVIDENCE",
                            "score": 0.99,
                            "reason": "Directly addresses the frozen profiler belief.",
                        }
                    ]
                }, _meta()
            return {"matches": []}, _meta()

        if system == RELATION_MAPPING_SYSTEM:
            effects = []
            if challenge_ids:
                effects.append(
                    {
                        "operation": "CHALLENGE",
                        "target_kernel_node_id": str(node.id),
                        "reason": "Audited profiler evidence says launch overhead dominates.",
                    }
                )
            if correction_ids:
                effects.append(
                    {
                        "operation": "REINFORCE",
                        "target_kernel_node_id": str(node.id),
                        "reason": "Audited correction says steady-state computation remains dominant.",
                    }
                )
            return {"effects": effects}, _meta()

        if system == SUPPORT_BINDING_SYSTEM:
            bindings = []
            relation_index = 1
            if challenge_ids:
                bindings.append(
                    {
                        "relation_id": f"R{relation_index:03d}",
                        "support_unit_ids": challenge_ids,
                        "jurisdiction_anchor_ids": [],
                        "reason": "All audited challenge units support this relation.",
                    }
                )
                relation_index += 1
            if correction_ids:
                bindings.append(
                    {
                        "relation_id": f"R{relation_index:03d}",
                        "support_unit_ids": correction_ids,
                        "jurisdiction_anchor_ids": [],
                        "reason": "All audited correction units support this relation.",
                    }
                )
            return {"bindings": bindings}, _meta()

        if system == GROUNDING_SYSTEM:
            items = []
            relation_index = 1
            if challenge_ids:
                items.append(
                    {
                        "relation_id": f"R{relation_index:03d}",
                        "grounding_class": "DIRECT",
                        "reason": "The profiler statement directly bears on the belief.",
                    }
                )
                relation_index += 1
            if correction_ids:
                items.append(
                    {
                        "relation_id": f"R{relation_index:03d}",
                        "grounding_class": "DIRECT",
                        "reason": "The correction directly bears on the same belief.",
                    }
                )
            return {"items": items}, _meta()

        raise AssertionError(f"unexpected system prompt: {system[:80]}")

    provider = ResearchAlignedCognitiveProvider(chat_fn=fake_chat)
    matches = provider.match_kernel(
        extraction,
        [node],
        query_embedding=[],
        node_embeddings=None,
        ranked_ids=None,
    )
    assessment = provider.assess_cognitive_impact(
        "",
        extraction,
        matches,
        independent_source_count=independent_source_count,
        secondary_report_count=secondary_report_count,
        nodes=[node],
    )
    strategy = get_decision_strategy(
        "pareto-multidelta-cardinal-free-effect-anchored-open-new"
    )
    draft = route(
        assessment.features,
        RuntimeView(),
        assessment=assessment,
        matches=matches,
        decision_strategy=strategy,
    )
    return {
        "semantic_units": classified["units"],
        "challenge_unit_ids": challenge_ids,
        "correction_unit_ids": correction_ids,
        "independent_source_count": independent_source_count,
        "secondary_report_count": secondary_report_count,
        "matches": [
            {
                "node_id": str(match.node_id),
                "relevance_type": match.relevance_type,
                "score": match.score,
            }
            for match in matches
        ],
        "authorized_effects": [effect.as_dict() for effect in assessment.effects],
        "disposition": draft.disposition.value,
        "urgency": draft.urgency,
        "decision_effect": (
            draft.decision_effect.as_dict() if draft.decision_effect is not None else None
        ),
    }


def _new_db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return Session(engine)


def _case_a(node: KernelNode) -> dict:
    db = _new_db()
    try:
        event = _event(db)
        a = _source(db, "Publisher A profiler report")
        b = _source(db, "Publisher B independent profiler report")
        _member(db, event, a, local=True)
        _member(db, event, b, local=False)
        _frame(db, a, CHALLENGE_STATEMENT, "A")
        frame_b = _frame(db, b, CHALLENGE_STATEMENT, "B")

        latest_ext = event_frame_to_extraction(frame_b)
        latest = _run_cognition(
            latest_ext,
            node,
            independent_source_count=1,
            secondary_report_count=0,
        )
        aggregated_input = build_event_cognition_input(db, event.id)
        aggregated = _run_cognition(
            aggregated_input.extraction,
            node,
            independent_source_count=aggregated_input.relational_context.independent_sources,
            secondary_report_count=aggregated_input.relational_context.secondary_reports,
        )
        return {
            "latest_source": latest,
            "event_aggregated": aggregated,
            "event_input": aggregated_input.as_dict(),
            "diagnostics": {
                "latest_unit_count": len(latest["semantic_units"]),
                "event_unit_count": len(aggregated["semantic_units"]),
                "preserves_two_support_units": len(aggregated["challenge_unit_ids"]) == 2,
                "event_independent_count_two": (
                    aggregated["independent_source_count"] == 2
                    and aggregated["secondary_report_count"] == 0
                ),
            },
        }
    finally:
        db.close()


def _case_b(node: KernelNode) -> dict:
    db = _new_db()
    try:
        event = _event(db)
        a = _source(db, "Initial profiler result")
        b = _source(db, "Profiler interpretation correction")
        _member(db, event, a, local=True)
        _member(db, event, b, local=False)
        _frame(db, a, CHALLENGE_STATEMENT, "A")
        frame_b = _frame(db, b, CORRECTION_STATEMENT, "B")

        latest_ext = event_frame_to_extraction(frame_b)
        latest = _run_cognition(
            latest_ext,
            node,
            independent_source_count=1,
            secondary_report_count=0,
        )
        aggregated_input = build_event_cognition_input(db, event.id)
        aggregated = _run_cognition(
            aggregated_input.extraction,
            node,
            independent_source_count=aggregated_input.relational_context.independent_sources,
            secondary_report_count=aggregated_input.relational_context.secondary_reports,
        )
        return {
            "latest_source": latest,
            "event_aggregated": aggregated,
            "event_input": aggregated_input.as_dict(),
            "diagnostics": {
                "latest_has_challenge": bool(latest["challenge_unit_ids"]),
                "latest_has_correction": bool(latest["correction_unit_ids"]),
                "aggregate_has_challenge": bool(aggregated["challenge_unit_ids"]),
                "aggregate_has_correction": bool(aggregated["correction_unit_ids"]),
                "aggregate_authorized_effect_kinds": sorted(
                    effect["operation"] for effect in aggregated["authorized_effects"]
                ),
                "latest_authorized_effect_kinds": sorted(
                    effect["operation"] for effect in latest["authorized_effects"]
                ),
            },
        }
    finally:
        db.close()


def _case_c(node: KernelNode) -> dict:
    db = _new_db()
    try:
        event = _event(db)
        a = _source(db, "Original profiler report")
        b = _source(db, "Repost of profiler report")
        _member(db, event, a, local=True)
        _member(db, event, b, local=False)
        _frame(db, a, CHALLENGE_STATEMENT, "A")
        _frame(db, b, CHALLENGE_STATEMENT, "B")
        db.add(
            SourceEdge(
                source_id=b.id,
                target_id=a.id,
                relationship=SourceEdgeRelationship.REPOSTS,
                confidence=1.0,
                detected_by="AI",
                evidence="controlled repost provenance",
            )
        )
        db.flush()

        aggregated_input = build_event_cognition_input(db, event.id)
        aggregated = _run_cognition(
            aggregated_input.extraction,
            node,
            independent_source_count=aggregated_input.relational_context.independent_sources,
            secondary_report_count=aggregated_input.relational_context.secondary_reports,
        )
        return {
            "event_aggregated": aggregated,
            "event_input": aggregated_input.as_dict(),
            "diagnostics": {
                "member_source_count": len(aggregated_input.member_source_ids),
                "independent_source_count": aggregated_input.relational_context.independent_sources,
                "secondary_report_count": aggregated_input.relational_context.secondary_reports,
                "repost_does_not_inflate_independence": (
                    len(aggregated_input.member_source_ids) == 2
                    and aggregated_input.relational_context.independent_sources == 1
                    and aggregated_input.relational_context.secondary_reports == 1
                ),
            },
        }
    finally:
        db.close()


def run() -> dict:
    node = _belief_node()
    case_a = _case_a(node)
    case_b = _case_b(node)
    case_c = _case_c(node)

    diagnostics = {
        "case_a_preserves_two_support_units": case_a["diagnostics"][
            "preserves_two_support_units"
        ],
        "case_a_independence_correct": case_a["diagnostics"][
            "event_independent_count_two"
        ],
        "case_b_latest_is_correction_only": (
            not case_b["diagnostics"]["latest_has_challenge"]
            and case_b["diagnostics"]["latest_has_correction"]
        ),
        "case_b_event_retains_prior_and_correction": (
            case_b["diagnostics"]["aggregate_has_challenge"]
            and case_b["diagnostics"]["aggregate_has_correction"]
        ),
        "case_b_event_effect_set_richer_than_latest": (
            set(case_b["diagnostics"]["aggregate_authorized_effect_kinds"])
            > set(case_b["diagnostics"]["latest_authorized_effect_kinds"])
        ),
        "case_c_repost_independence_guardrail": case_c["diagnostics"][
            "repost_does_not_inflate_independence"
        ],
    }
    diagnostics["all_preregistered_structural_gates_pass"] = all(
        diagnostics.values()
    )
    return {
        "run_version": RUN_VERSION,
        "status": "EVENT_STATE_COGNITION_CONTROLLED_COMPLETE",
        "kernel_target_id": str(node.id),
        "cases": {
            "A_INDEPENDENT_CORROBORATION": case_a,
            "B_MATERIAL_CORRECTION": case_b,
            "C_REPOST_PROVENANCE_CONTROL": case_c,
        },
        "diagnostics": diagnostics,
        "guardrails": [
            "In-memory databases only.",
            "No production Event/Attention/WATCH writes.",
            "Uses event-cognition-input-v0.1 and frozen ResearchAligned cognition.",
            "Controlled fake model transport varies only with visible semantic units.",
            "Cases were fixed in Phase17 preregistration before execution.",
        ],
    }


def main():
    report = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    for name, case in report["cases"].items():
        print("---", name)
        for view_name in ("latest_source", "event_aggregated"):
            row = case.get(view_name)
            if row is None:
                continue
            print(
                view_name,
                "units", len(row["semantic_units"]),
                "independent", row["independent_source_count"],
                "secondary", row["secondary_report_count"],
                "effects", [effect["operation"] for effect in row["authorized_effects"]],
                "disposition", row["disposition"],
            )
        print("diagnostics", json.dumps(case["diagnostics"], ensure_ascii=False))
    print("GLOBAL", json.dumps(report["diagnostics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
