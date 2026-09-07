"""Run Semantic Evidence Auditor v0.1 on a minimal RS02 controlled set.

Development-only. This evaluates whether already-cited evidence is semantically sufficient
for one semantic object. It does not reread/search the full source and does not repair the
extractor output.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_standing_radar_fit_eval import load_repo_env
from eval.live.semantic_evidence_auditor_v0_1 import (
    audit_semantic_evidence_v0_1,
    invocation_record,
)
from eval.live.semantic_source_loader_v0_1 import load_dev_manifest, load_manifest_source

DEFAULT_OUT_DIR = ROOT / "eval" / "live" / "results" / "semantic_evidence_auditor_v0_1"


def git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _rs02_source():
    manifest = load_dev_manifest()
    entry = next(item for item in manifest["sources"] if item["id"] == "RS02")
    return load_manifest_source(entry)


# Development labels only. They may be calibrated, but every post-run adjudication must
# remain explicit so a later report cannot silently reinterpret the initial controlled run.
CONTROLLED_CASES = [
    {
        "audit_id": "RS02-AUD-001-correct-codebase-support",
        "object_type": "affected_system_population",
        "semantic_object": "The affected system is the Cursor codebase.",
        "evidence": [
            {
                "source_id": "RS02",
                "support_pointer": "PARA 0005",
                "support_excerpt": "这不是 AI slop code，而是你每天都在使用的 Cursor 的代码。",
            }
        ],
        "human_gold": "SUFFICIENT",
        "gold_status": "PREDECLARED_INITIAL",
        "why": "The excerpt explicitly identifies the code as Cursor code.",
    },
    {
        "audit_id": "RS02-AUD-002-wrong-codebase-support",
        "object_type": "affected_system_population",
        "semantic_object": "The affected system is the Cursor codebase.",
        "evidence": [
            {
                "source_id": "RS02",
                "support_pointer": "PARA 0004",
                "support_excerpt": "上个月已经合入了 1000 个 PR。这个月才过去 12 天，她又合入了接近 800 个。",
            }
        ],
        "human_gold": "INSUFFICIENT",
        "gold_status": "PREDECLARED_INITIAL",
        "why": "The excerpt supports PR volume, but not the identity of the affected codebase.",
    },
    {
        "audit_id": "RS02-AUD-003-overstrong-efficiency-scope",
        "object_type": "epistemic_unit",
        "semantic_object": "Boris achieved approximately the same PR throughput as Lauren Tan.",
        "evidence": [
            {
                "source_id": "RS02",
                "support_pointer": "PARA 0006",
                "support_excerpt": "很多人，包括 Claude Code 的 Boris，都提过自己借助 coding agent 达到了类似的效率。",
            }
        ],
        "human_gold": "INSUFFICIENT",
        "gold_status": "POST_RUN_ADJUDICATED_20260907",
        "why": "The excerpt says similar efficiency, but PR throughput is a stronger material claim not stated or conservatively entailed by the cited evidence.",
    },
    {
        "audit_id": "RS02-AUD-004-ambiguous-efficiency-reference",
        "object_type": "epistemic_unit",
        "semantic_object": "Boris achieved efficiency similar to Lauren Tan's.",
        "evidence": [
            {
                "source_id": "RS02",
                "support_pointer": "PARA 0006",
                "support_excerpt": "很多人，包括 Claude Code 的 Boris，都提过自己借助 coding agent 达到了类似的效率。",
            }
        ],
        "human_gold": "UNCERTAIN",
        "gold_status": "PREDECLARED_CALIBRATION_AFTER_INITIAL_RUN",
        "why": "The excerpt is relevant and contains an explicit similarity relation, but the local excerpt does not resolve what the anaphoric '类似' refers to, so Lauren Tan as the comparison target remains ambiguous.",
    },
]


def _verify_case_supports_exist(source) -> None:
    if source.source_id != "RS02":
        raise ValueError("controlled auditor v0.1 cases are pinned to RS02")
    for case in CONTROLLED_CASES:
        for support in case["evidence"]:
            excerpt = support["support_excerpt"]
            if excerpt not in source.rendered_text:
                raise ValueError(
                    f"controlled support excerpt not found in pinned RS02 source: {case['audit_id']}"
                )


def main() -> None:
    source = _rs02_source()
    _verify_case_supports_exist(source)

    load_repo_env()
    from app.config import settings
    if not settings.llm_api_key:
        raise SystemExit("RAOS_LLM_API_KEY unavailable after repo .env bootstrap")

    rows = []
    for case in CONTROLLED_CASES:
        result = audit_semantic_evidence_v0_1(
            audit_id=case["audit_id"],
            object_type=case["object_type"],
            semantic_object=case["semantic_object"],
            evidence=case["evidence"],
        )
        audit_result = result.get("result") if result.get("scorable") else None
        predicted = audit_result.get("verdict") if audit_result else None
        rows.append(
            {
                "audit_id": case["audit_id"],
                "object_type": case["object_type"],
                "semantic_object": case["semantic_object"],
                "evidence": case["evidence"],
                "human_gold": case["human_gold"],
                "gold_status": case["gold_status"],
                "human_gold_rationale": case["why"],
                "scorable": bool(result.get("scorable")),
                "failure_kind": result.get("failure_kind"),
                "error": result.get("error"),
                "repair_used": bool(result.get("repair_used")),
                "schema_events": result.get("schema_events") or [],
                "invalid_raw": result.get("invalid_raw"),
                "model_meta": result.get("model_meta"),
                "audit_result": audit_result,
                "predicted_verdict": predicted,
                "verdict_match": predicted == case["human_gold"] if predicted else False,
            }
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact = {
        "name": "raos-semantic-evidence-auditor-development-v0.1",
        "status": "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION",
        "measurement_timestamp": timestamp,
        "measurement_git_head": git_head(),
        "source": {
            "source_id": source.source_id,
            "path": source.path,
            "git_blob_sha": source.git_blob_sha,
            "text_sha256": source.text_sha256,
        },
        "invocation": invocation_record(
            requested_model=settings.llm_model,
            provider_base_url=settings.llm_base_url,
        ),
        "n_cases": len(rows),
        "n_scorable": sum(1 for row in rows if row["scorable"]),
        "n_first_pass_valid": sum(1 for row in rows if row["scorable"] and not row["repair_used"]),
        "n_verdict_match": sum(1 for row in rows if row["verdict_match"]),
        "cases": rows,
        "methodology_note": "Development/calibration only. AUD-003 Gold was adjudicated after the first real run; do not reinterpret the original 2/3 predeclared result as fresh 3/3 evidence.",
    }

    DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DEFAULT_OUT_DIR / f"semantic_evidence_auditor_v0_1_{timestamp}.json"
    if out_path.exists():
        raise SystemExit(f"refusing to overwrite development artifact: {out_path}")
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {out_path}")
    print(
        json.dumps(
            {
                "n_cases": artifact["n_cases"],
                "n_scorable": artifact["n_scorable"],
                "n_first_pass_valid": artifact["n_first_pass_valid"],
                "n_verdict_match": artifact["n_verdict_match"],
                "results": [
                    {
                        "audit_id": row["audit_id"],
                        "gold": row["human_gold"],
                        "gold_status": row["gold_status"],
                        "predicted": row["predicted_verdict"],
                        "match": row["verdict_match"],
                        "repair_used": row["repair_used"],
                        "actual_model": (row.get("model_meta") or {}).get("model"),
                    }
                    for row in rows
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
