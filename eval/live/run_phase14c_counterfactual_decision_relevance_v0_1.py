from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db import Base
from app.enums import CognitiveEffectKind, DetectedBy, SourceEdgeRelationship
from app.models.event import RepresentationAuditRun
from app.services.cognitive_impact import (
    CognitiveEffect,
    CognitiveImpactAssessment,
    features_from_impact,
    ground_effects,
)
from app.services.event_evidence_frames import _persist_payload
from app.services.extraction import ExtractionResult
from app.services.ingestion import ingest_text
from app.services.representation_auditor import REPRESENTATION_AUDITOR_CONTRACT
from app.services.representation_belief import belief_history_from_audits
from app.services.representation_snapshot import freeze_representation_snapshot
from app.services.scheduler import route
from app.services.source_graph import persist_source_edge

RUN_VERSION = "phase14c-counterfactual-decision-relevance-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase14c_counterfactual_decision_relevance_v0_1"


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _payload(side: str) -> dict:
    wording = (
        "Acme launched the Nimbus API public beta at AtlasConf on September 19."
        if side == "A"
        else "Acme debuted the Nimbus API public beta at AtlasConf on September 19."
    )
    return {
        "event_key": f"phase14c-nimbus-{side}",
        "event_title": "Acme Nimbus API public beta launch",
        "event_summary": wording,
        "semantic_provenance": {
            "mode": "AUDITED_BRIDGE",
            "authority": "SEMANTIC_AUDITED",
            "controlled_counterfactual": True,
        },
        "source": {},
        "actors": [{"name": "Acme", "role": "actor"}],
        "actions": [
            {
                "description": wording,
                "temporal_status": "ENACTED",
            }
        ],
        "affected_systems_populations": [{"name": "software developers"}],
        "uncertainties": [],
        "rejected_or_unscorable_objects": [],
        "rendered_event_text": wording,
        "claim_evidence": [],
        "observation_evidence": [],
        "audit_summary": {"controlled": True},
    }


def _make_world(db: Session):
    a = ingest_text(
        db,
        "Acme launched the Nimbus API public beta at AtlasConf on September 19.",
        title="Acme launches Nimbus API public beta",
    )
    b = ingest_text(
        db,
        "Independent Publisher Beta reports that Acme debuted the Nimbus API public beta at AtlasConf on September 19.",
        title="Nimbus API public beta debuts at AtlasConf",
    )
    a.publisher = "Publisher Alpha"
    b.publisher = "Publisher Beta"
    a.canonical_url = "https://alpha.example.test/nimbus-launch"
    b.canonical_url = "https://beta.example.test/nimbus-launch"
    a.published_at = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
    b.published_at = datetime(2026, 9, 19, 13, 0, tzinfo=timezone.utc)
    db.flush()

    fa = _persist_payload(
        db,
        source=a,
        payload=_payload("A"),
        analysis_run_id=None,
        frame_ordinal=0,
        workspace_id="phase14c-controlled",
    )
    fb = _persist_payload(
        db,
        source=b,
        payload=_payload("B"),
        analysis_run_id=None,
        frame_ordinal=0,
        workspace_id="phase14c-controlled",
    )
    return a, b, fa, fb


def _insert_same_event_belief(db: Session, fa, fb) -> RepresentationAuditRun:
    row = RepresentationAuditRun(
        identity_key="phase14c-controlled-same-event",
        workspace_id="phase14c-controlled",
        audit_type="FRAME_PAIR",
        subject_type="EVENT_FRAME",
        subject_id=fa.id,
        object_type="EVENT_FRAME",
        object_id=fb.id,
        input_evidence_digest="phase14c-controlled-evidence",
        input_frame_ids=[str(fa.id), str(fb.id)],
        evidence_bundle_refs={"controlled": True},
        auditor_contract_version=REPRESENTATION_AUDITOR_CONTRACT,
        provider="controlled-intervention",
        model="none",
        judgments={
            "event_identity": {
                "value": "SAME_EVENT",
                "support_ids": ["FRAME_A", "FRAME_B"],
                "conflict_ids": [],
                "rationale": "Controlled epistemic intervention for decision-relevance testing.",
                "missing_evidence": [],
            },
            "provenance_dependency": {
                "value": "INDEPENDENT",
                "direction": "NOT_APPLICABLE",
                "support_ids": ["CONTROLLED_INDEPENDENCE"],
                "conflict_ids": [],
                "rationale": "The intervention holds provenance independence fixed.",
                "missing_evidence": [],
            },
            "relation_context": {
                "value": "RELATED",
                "support_ids": ["FRAME_A", "FRAME_B"],
                "conflict_ids": [],
                "rationale": "Same occurrence is concretely related.",
                "missing_evidence": [],
            },
        },
        supporting_evidence=[],
        conflicting_evidence=[],
        uncertainty={},
        proposed_transition={},
        authority_policy_version="shadow-none-v0.1",
        authority_result="SHADOW_ONLY",
    )
    db.add(row)
    db.flush()
    return row


def _cognitive_probe(relational_context) -> dict:
    extraction = ExtractionResult(evidence_maturity=0.8)
    raw = [
        CognitiveEffect(
            target_kernel_node_id=None,
            operation=CognitiveEffectKind.OPEN_NEW,
            change_magnitude=0.75,
            epistemic_strength=0.90,
            target_importance=0.80,
            reason="Controlled high-value new cognitive branch.",
            exploration_candidate=True,
        )
    ]
    grounded = ground_effects(
        raw,
        [],
        extraction,
        independent_source_count=relational_context.independent_sources,
    )
    assessment = CognitiveImpactAssessment(
        effects=grounded,
        attention_cost=2.0,
        exploration_candidate=True,
    )
    features = features_from_impact(
        assessment,
        [],
        extraction,
        is_duplicate=relational_context.is_duplicate,
        independent_source_count=relational_context.independent_sources,
        secondary_report_count=relational_context.secondary_reports,
        evidence_maturity=0.8,
    )
    plan = route(features, assessment=assessment, matches=[])
    effect = grounded[0] if grounded else None
    return {
        "independent_source_count": relational_context.independent_sources,
        "secondary_report_count": relational_context.secondary_reports,
        "is_duplicate": relational_context.is_duplicate,
        "grounded_epistemic_strength": (
            float(effect.epistemic_strength) if effect is not None else None
        ),
        "change_magnitude": float(effect.change_magnitude) if effect is not None else None,
        "target_importance": float(effect.target_importance) if effect is not None else None,
        "disposition": str(getattr(plan.disposition, "value", plan.disposition)),
        "expected_output": str(getattr(plan.expected_output, "value", plan.expected_output)),
        "reason": plan.reason,
    }


def _snapshot_state(snapshot) -> dict:
    return {
        "graph_digest": snapshot.graph_digest,
        "decision_representation_digest": snapshot.decision_representation_digest,
        "independent_source_count": snapshot.relational_context.independent_sources,
        "secondary_report_count": snapshot.relational_context.secondary_reports,
        "is_duplicate": snapshot.relational_context.is_duplicate,
        "relational_facts": [list(row) for row in snapshot.relational_context.facts],
    }


def run() -> dict:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        a, b, fa, fb = _make_world(db)

        base_snapshot = freeze_representation_snapshot(db, a, [b])
        base_probe = _cognitive_probe(base_snapshot.relational_context)

        audit = _insert_same_event_belief(db, fa, fb)
        same_belief = belief_history_from_audits([audit])
        same_snapshot = freeze_representation_snapshot(db, a, [b])
        same_probe = _cognitive_probe(same_snapshot.relational_context)

        persist_source_edge(
            db,
            b.id,
            a.id,
            SourceEdgeRelationship.REPOSTS,
            confidence=1.0,
            detected_by=DetectedBy.USER,
            evidence="Controlled positive-control secondary relation.",
        )
        secondary_snapshot = freeze_representation_snapshot(db, a, [b])
        secondary_probe = _cognitive_probe(secondary_snapshot.relational_context)

        base = _snapshot_state(base_snapshot)
        same = _snapshot_state(same_snapshot)
        secondary = _snapshot_state(secondary_snapshot)

    diagnostics = {
        "same_event_belief_exists": same_belief["latest_epoch"]["counts"]["SAME_EVENT"] == 1,
        "same_event_keeps_provenance_independence_fixed": (
            same["independent_source_count"] == base["independent_source_count"] == 2
            and same["secondary_report_count"] == base["secondary_report_count"] == 0
            and same["is_duplicate"] is False
        ),
        "same_event_does_not_change_graph_digest": same["graph_digest"] == base["graph_digest"],
        "same_event_does_not_change_decision_digest": (
            same["decision_representation_digest"] == base["decision_representation_digest"]
        ),
        "same_event_does_not_change_current_probe_attention": (
            same_probe["disposition"] == base_probe["disposition"]
        ),
        "positive_control_changes_decision_digest": (
            secondary["decision_representation_digest"] != base["decision_representation_digest"]
        ),
        "positive_control_changes_attention": (
            secondary_probe["disposition"] != base_probe["disposition"]
        ),
    }

    if diagnostics["positive_control_changes_attention"] and diagnostics[
        "same_event_does_not_change_decision_digest"
    ]:
        interpretation = {
            "current_direct_same_event_decision_influence": "ZERO_BY_CURRENT_CONTRACT",
            "potential_counterfactual_same_event_decision_relevance": "UNKNOWN",
            "reason": (
                "The harness is decision-sensitive under the provenance positive control, "
                "but SAME_EVENT belief has no current decision-input projection."
            ),
        }
    else:
        interpretation = {
            "current_direct_same_event_decision_influence": "UNRESOLVED",
            "potential_counterfactual_same_event_decision_relevance": "UNKNOWN",
            "reason": "Preregistered positive-control or expressibility condition did not hold.",
        }

    return {
        "run_version": RUN_VERSION,
        "status": "COUNTERFACTUAL_CURRENT_CONTRACT_PROBE_COMPLETE",
        "measurement_git_head": git_head(),
        "states": {
            "R_BASE": {"representation": base, "cognitive_probe": base_probe},
            "R_SAME": {
                "representation": same,
                "cognitive_probe": same_probe,
                "belief_view": same_belief,
            },
            "R_SECONDARY_POSITIVE_CONTROL": {
                "representation": secondary,
                "cognitive_probe": secondary_probe,
            },
        },
        "diagnostics": diagnostics,
        "interpretation": interpretation,
        "guardrails": [
            "SAME_EVENT is not mapped to REPOSTS, DERIVED_FROM, or non-independence.",
            "No production DB or AttentionPlan persistence.",
            "Positive control uses current production epistemic cap and Attention policy.",
            "A null SAME_EVENT result is interpreted as current-contract blindness, not intrinsic irrelevance.",
            "No calibrated mutual-information claim.",
        ],
    }


def main() -> None:
    report = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    for name, state in report["states"].items():
        rep = state["representation"]
        probe = state["cognitive_probe"]
        print(
            name,
            "decision_digest", rep["decision_representation_digest"][:12],
            "independent", rep["independent_source_count"],
            "secondary", rep["secondary_report_count"],
            "epi", probe["grounded_epistemic_strength"],
            "attention", probe["disposition"],
        )
    print("DIAGNOSTICS", json.dumps(report["diagnostics"], ensure_ascii=False))
    print("INTERPRETATION", json.dumps(report["interpretation"], ensure_ascii=False))


if __name__ == "__main__":
    main()
