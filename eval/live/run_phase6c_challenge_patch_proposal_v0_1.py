from __future__ import annotations

import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_standing_radar_fit_eval import git_head, load_repo_env

AUDIT_ARTIFACT = ROOT / "eval/live/results/phase6b_epistemic_unit_audit_v0_1/phase6b_epistemic_unit_audit_v0_1_20260908T041732Z.json"
OUT_DIR = ROOT / "eval/live/results/phase6c_challenge_patch_proposal_v0_1"
RUN_VERSION = "phase6c-challenge-patch-proposal-v0.1"


def _value(value):
    return value.value if hasattr(value, "value") else value


def _snapshot(nodes):
    return [(str(n.id), n.node_type, n.title, n.status, deepcopy(n.payload), n.current_version) for n in nodes]


def _draft_row(draft):
    return {
        "target_object_type": _value(draft.target_object_type),
        "target_object_id": str(draft.target_object_id) if draft.target_object_id else None,
        "change_type": _value(draft.change_type),
        "current_state": draft.current_state,
        "proposed_state": draft.proposed_state,
        "reasoning": draft.reasoning,
        "suggested_confidence_change": draft.suggested_confidence_change,
        "evidence_link_ids": list(draft.evidence_link_ids),
    }


def run() -> dict:
    load_repo_env()
    from app.cognitive.factory import get_provider
    from app.services.cognitive_impact import canonical_delta_content, primary_update
    from app.services.scheduler import RuntimeView, route, validate_plan
    from eval.live.phase6b_cognitive_semantics_v0_1 import (
        audited_units_to_extraction,
        build_phase6b_perf_challenge_nodes,
        fixture_code_by_id,
        render_audited_cognitive_context,
    )

    audit = json.loads(AUDIT_ARTIFACT.read_text(encoding="utf-8"))
    source = next(row for row in audit["sources"] if row["source_id"] == "RS05")
    units = source.get("admitted_units") or []
    extraction = audited_units_to_extraction(units)
    context = render_audited_cognitive_context(units)
    nodes = build_phase6b_perf_challenge_nodes()
    before = _snapshot(nodes)
    code_by_id = fixture_code_by_id(nodes)
    provider = get_provider()
    matches = provider.match_kernel(extraction, nodes, extra_text=context)
    assessment = provider.assess_cognitive_impact(
        context,
        extraction,
        matches,
        independent_source_count=1,
        nodes=nodes,
    )
    update = primary_update(assessment)
    operation = _value(update.get("operation"))
    target_id = update.get("target_node_id")

    plan = route(
        assessment.features,
        RuntimeView(),
        assessment=assessment,
        matches=matches,
    )
    validate_plan(plan)

    delta = provider.propose_model_delta(
        context,
        extraction,
        matches,
        assessment.features,
        nodes,
        assessment=assessment,
    )
    evidence_ids = [
        f"{source['source_id']}:{unit['unit_id']}:{support['support_pointer']}"
        for unit in units
        for support in unit.get("supports") or []
    ]
    drafts = provider.propose_patches(
        context,
        delta,
        matches,
        assessment.features,
        nodes,
        evidence_ids,
        assessment=assessment,
        extraction=extraction,
    )
    after = _snapshot(nodes)

    return {
        "name": "raos-phase6c-challenge-patch-proposal-v0.1",
        "status": "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION",
        "run_version": RUN_VERSION,
        "measurement_timestamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "measurement_git_head": git_head(),
        "source_id": "RS05",
        "kernel_fixture": "PERF_CHALLENGE",
        "n_admitted_units": len(units),
        "primary_delta": {
            "operation": operation,
            "target_node_id": str(target_id) if target_id else None,
            "target_fixture_code": code_by_id.get(str(target_id)) if target_id else None,
            "delta_content": canonical_delta_content(assessment),
        },
        "attention_policy": {
            "disposition": plan.disposition.value,
            "expected_output": plan.expected_output.value,
            "reason": plan.reason,
        },
        "model_delta": {
            "summary": delta.summary,
            "what_could_change": list(delta.what_could_change),
            "distinctions": list(delta.distinctions),
            "questions": list(delta.questions),
            "admission_allowed": delta.admission_allowed,
            "epistemic_risk": delta.epistemic_risk,
            "evidence_maturity": delta.evidence_maturity,
            "rationale": delta.rationale,
        },
        "patch_drafts": [_draft_row(draft) for draft in drafts],
        "n_patch_drafts": len(drafts),
        "kernel_unchanged_after_proposal": before == after,
        "persisted_kernel_patch_count": 0,
        "stage_provenance": getattr(provider, "stage_provenance", {}),
        "methodology_note": (
            "PatchDraft generation is proposal-only. This runner never opens a DB session and therefore "
            "cannot commit cognition. Human accept/modify/reject is tested separately in an isolated test DB."
        ),
    }


def main() -> int:
    payload = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"phase6c_challenge_patch_proposal_v0_1_{payload['measurement_timestamp']}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps({
        "measurement_git_head": payload["measurement_git_head"],
        "primary_delta": payload["primary_delta"],
        "attention_policy": payload["attention_policy"],
        "n_patch_drafts": payload["n_patch_drafts"],
        "kernel_unchanged_after_proposal": payload["kernel_unchanged_after_proposal"],
        "patch_drafts": payload["patch_drafts"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
