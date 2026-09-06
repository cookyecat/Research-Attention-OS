"""Run Collective Attention Salience (P) estimator v1 final fresh eval.

Not part of ordinary CI. Joins the frozen fresh Evidence Packet template with the
separately frozen Human Gold manifest by case id, validates provenance, then runs
P estimator v1 exactly as frozen.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_standing_radar_fit_eval import git_head, load_repo_env
from eval.live.collective_attention_v1 import (
    ESTIMATOR_VERSION,
    EVIDENCE_INTERFACE_VERSION,
    PROFILE_ID,
    PROMPT_VERSION,
    build_messages,
    compute_collective_attention_metrics,
    estimate_collective_attention_v1,
    invocation_record,
    load_collective_attention_profile,
    prompt_sha256,
    validate_evidence_packet,
)

DEFAULT_TEMPLATE = ROOT / "eval" / "live" / "manifest.collective_attention_final_fresh_validation.v1.template.yaml"
DEFAULT_GOLD = ROOT / "eval" / "live" / "manifest.collective_attention_final_fresh_human_gold.v1.yaml"
DEFAULT_OUT = ROOT / "eval" / "live" / "results" / "collective_attention_v1_final_fresh_first_run.json"

ESTIMATOR_FREEZE_DECLARATION_COMMIT = "5a08a0d8ab2700a56d91437797b664a53f842ea0"
FRESH_TEMPLATE_COMMIT = "e57b403fcacb1ff8f49aad23fe78a7266859c06a"
HUMAN_GOLD_COMMIT = "1b6bfb23a84411701cbee84caecf271e672e807b"
EXPECTED_PROMPT_SHA256 = "0fbc1c9c935e5cf31a98b77a0a6a9f5b99ff7473906a7e438e834f278d193b67"
EXPECTED_CASE_IDS = tuple(f"PF{i}" for i in range(1, 13))


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"manifest must be a mapping: {path}")
    return data


def load_fresh_template(path: Path = DEFAULT_TEMPLATE) -> dict[str, Any]:
    data = _load_yaml(path)
    cases = data.get("cases") or []
    if not isinstance(cases, list):
        raise ValueError("fresh template cases must be a list")
    normalized: list[dict[str, Any]] = []
    for raw in cases:
        if not isinstance(raw, dict):
            raise ValueError("fresh template case must be a mapping")
        case_id = str(raw.get("id") or "").strip()
        if not case_id:
            raise ValueError("fresh template case id is required")
        packet = raw.get("packet")
        validate_evidence_packet(packet)
        forbidden = {"collective_attention_salience", "gold", "label", "prediction"}
        leaked = forbidden.intersection(raw)
        if leaked:
            raise ValueError(f"fresh template case {case_id} leaks label/prediction fields: {sorted(leaked)}")
        normalized.append({"id": case_id, "packet": packet})
    out = dict(data)
    out["cases"] = normalized
    return out


def load_human_gold(path: Path = DEFAULT_GOLD) -> dict[str, Any]:
    data = _load_yaml(path)
    cases = data.get("cases") or []
    if not isinstance(cases, list):
        raise ValueError("Human Gold cases must be a list")
    normalized: list[dict[str, Any]] = []
    for raw in cases:
        if not isinstance(raw, dict):
            raise ValueError("Human Gold case must be a mapping")
        case_id = str(raw.get("id") or "").strip()
        label = raw.get("collective_attention_salience")
        if not case_id:
            raise ValueError("Human Gold case id is required")
        if label not in {"SALIENT", "NOT_SALIENT"}:
            raise ValueError(f"invalid Human Gold label for {case_id}: {label!r}")
        if "packet" in raw:
            raise ValueError(f"Human Gold case {case_id} must not redefine frozen packet")
        normalized.append(
            {
                "id": case_id,
                "gold_status": raw.get("gold_status"),
                "label_provenance": raw.get("label_provenance") or data.get("label_provenance"),
                "collective_attention_salience": label,
            }
        )
    out = dict(data)
    out["cases"] = normalized
    return out


def validate_manifest_provenance(template: dict[str, Any], gold: dict[str, Any]) -> None:
    runtime_expected = {
        "estimator_version": ESTIMATOR_VERSION,
        "prompt_version": PROMPT_VERSION,
        "profile_id": PROFILE_ID,
        "evidence_interface_version": EVIDENCE_INTERFACE_VERSION,
        "prompt_sha256": prompt_sha256(),
    }
    frozen_expected = {
        "estimator_freeze_declaration_commit": ESTIMATOR_FREEZE_DECLARATION_COMMIT,
        "fresh_template_commit": FRESH_TEMPLATE_COMMIT,
        "prompt_sha256": EXPECTED_PROMPT_SHA256,
    }

    mismatches: dict[str, Any] = {}
    for manifest_name, manifest in (("template", template), ("gold", gold)):
        for key, expected in runtime_expected.items():
            actual = manifest.get(key)
            if actual != expected:
                mismatches[f"{manifest_name}.{key}"] = {"manifest": actual, "expected": expected}

    # The template predates its own commit, so its identity is validated by the
    # runner constant plus the Human Gold's explicit fresh_template_commit.
    if template.get("estimator_freeze_declaration_commit") != ESTIMATOR_FREEZE_DECLARATION_COMMIT:
        mismatches["template.estimator_freeze_declaration_commit"] = {
            "manifest": template.get("estimator_freeze_declaration_commit"),
            "expected": ESTIMATOR_FREEZE_DECLARATION_COMMIT,
        }
    for key, expected in frozen_expected.items():
        actual = gold.get(key)
        if actual != expected:
            mismatches[f"gold.{key}"] = {"manifest": actual, "expected": expected}

    if prompt_sha256() != EXPECTED_PROMPT_SHA256:
        mismatches["runtime.prompt_sha256"] = {
            "runtime": prompt_sha256(),
            "expected": EXPECTED_PROMPT_SHA256,
        }
    if mismatches:
        raise ValueError(f"collective attention manifest provenance mismatch: {mismatches}")


def join_template_and_gold(template: dict[str, Any], gold: dict[str, Any]) -> list[dict[str, Any]]:
    template_by_id = {case["id"]: case for case in template["cases"]}
    gold_by_id = {case["id"]: case for case in gold["cases"]}

    if len(template_by_id) != len(template["cases"]):
        raise ValueError("duplicate case id in fresh template")
    if len(gold_by_id) != len(gold["cases"]):
        raise ValueError("duplicate case id in Human Gold")

    expected = set(EXPECTED_CASE_IDS)
    if set(template_by_id) != expected:
        raise ValueError(f"fresh template case ids mismatch: {sorted(template_by_id)}")
    if set(gold_by_id) != expected:
        raise ValueError(f"Human Gold case ids mismatch: {sorted(gold_by_id)}")

    joined: list[dict[str, Any]] = []
    for case_id in EXPECTED_CASE_IDS:
        t = template_by_id[case_id]
        g = gold_by_id[case_id]
        joined.append(
            {
                "id": case_id,
                "packet": t["packet"],
                "gold": g["collective_attention_salience"],
                "gold_status": g.get("gold_status"),
                "label_provenance": g.get("label_provenance"),
            }
        )
    return joined


def run_final_fresh_v1(
    template_path: Path = DEFAULT_TEMPLATE,
    gold_path: Path = DEFAULT_GOLD,
    *,
    score: bool = True,
    dry_run: bool = False,
    chat_fn=None,
) -> dict[str, Any]:
    load_repo_env()
    from app.config import settings

    profile = load_collective_attention_profile()
    template = load_fresh_template(template_path)
    gold = load_human_gold(gold_path)
    validate_manifest_provenance(template, gold)
    cases = join_template_and_gold(template, gold)

    rows: list[dict[str, Any]] = []
    technical_failures: list[dict[str, Any]] = []
    insufficient_evidence: list[str] = []

    for case in cases:
        packet = case["packet"]
        gold_label = case["gold"] if score else None
        row: dict[str, Any] = {
            "case_id": case["id"],
            "gold": gold_label,
            "gold_status": case.get("gold_status"),
            "label_provenance": case.get("label_provenance"),
            "prediction": None,
            "correct": None,
            "scorable": False,
            "measurement_status": None,
            "objective_constituency": "",
            "attention_state_summary": "",
            "inertia_summary": "",
            "reason": None,
            "failure_kind": None,
            "error": None,
            "transport_retries": 0,
            "model_meta": None,
        }

        if dry_run:
            messages = build_messages(packet, profile)
            row["dry_run"] = True
            row["prompt_chars"] = sum(len(m["content"]) for m in messages)
            rows.append(row)
            continue

        estimate = estimate_collective_attention_v1(packet, profile=profile, chat_fn=chat_fn)
        row["scorable"] = bool(estimate["scorable"])
        row["measurement_status"] = estimate["measurement_status"]
        row["prediction"] = estimate["collective_attention_salience"]
        row["objective_constituency"] = estimate["objective_constituency"]
        row["attention_state_summary"] = estimate["attention_state_summary"]
        row["inertia_summary"] = estimate["inertia_summary"]
        row["reason"] = estimate["reason"]
        row["failure_kind"] = estimate["failure_kind"]
        row["error"] = estimate["error"]
        row["transport_retries"] = estimate["transport_retries"]
        row["model_meta"] = estimate["model_meta"]

        if row["scorable"] and gold_label in {"SALIENT", "NOT_SALIENT"}:
            row["correct"] = row["prediction"] == gold_label
        elif estimate["measurement_status"] == "insufficient_evidence":
            insufficient_evidence.append(case["id"])
        elif estimate["failure_kind"]:
            technical_failures.append(
                {
                    "case_id": case["id"],
                    "failure_kind": estimate["failure_kind"],
                    "error": estimate["error"],
                    "transport_retries": estimate["transport_retries"],
                }
            )
        rows.append(row)

    metrics = compute_collective_attention_metrics(rows) if score and not dry_run else None
    models = sorted(
        {
            str((row.get("model_meta") or {}).get("model"))
            for row in rows
            if (row.get("model_meta") or {}).get("model")
        }
    )

    return {
        "name": gold.get("name"),
        "validation_type": gold.get("validation_type"),
        "estimator_version": ESTIMATOR_VERSION,
        "prompt_version": PROMPT_VERSION,
        "profile_id": PROFILE_ID,
        "evidence_interface_version": EVIDENCE_INTERFACE_VERSION,
        "prompt_sha256": prompt_sha256(),
        "estimator_freeze_declaration_commit": ESTIMATOR_FREEZE_DECLARATION_COMMIT,
        "fresh_template_commit": FRESH_TEMPLATE_COMMIT,
        "human_gold_commit": HUMAN_GOLD_COMMIT,
        "measurement_git_head": git_head(),
        "measurement_timestamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "template_manifest": str(template_path),
        "human_gold_manifest": str(gold_path),
        "dry_run": dry_run,
        "scored": bool(score and not dry_run),
        "invocation": invocation_record(
            requested_model=settings.llm_model,
            provider_base_url=settings.llm_base_url,
            thinking_protocol=settings.llm_thinking_protocol,
        ),
        "actual_models": models,
        "cases": rows,
        "metrics": metrics,
        "technical_failures": technical_failures,
        "insufficient_evidence_cases": insufficient_evidence,
        "n_cases": len(rows),
        "n_technical_failures": len(technical_failures),
        "n_insufficient_evidence": len(insufficient_evidence),
        "pre_registered_criterion": gold.get("pre_registered_criterion"),
    }


def write_artifact(payload: dict[str, Any], path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing first-run artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collective Attention Salience (P) estimator v1 final fresh eval")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-score", action="store_true", help="Predict without reading gold labels")
    args = parser.parse_args(argv)

    payload = run_final_fresh_v1(
        args.template,
        args.gold,
        score=not args.no_score,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        print(
            json.dumps(
                {
                    "n_cases": payload["n_cases"],
                    "prompt_sha256": payload["prompt_sha256"],
                    "estimator_freeze_declaration_commit": payload["estimator_freeze_declaration_commit"],
                    "fresh_template_commit": payload["fresh_template_commit"],
                    "human_gold_commit": payload["human_gold_commit"],
                },
                indent=2,
            )
        )
        return 0

    write_artifact(payload, args.out)
    print(f"wrote {args.out}")
    if payload.get("metrics"):
        print(json.dumps(payload["metrics"], indent=2))
    print(
        json.dumps(
            {
                "n_insufficient_evidence": payload["n_insufficient_evidence"],
                "n_technical_failures": payload["n_technical_failures"],
                "actual_models": payload["actual_models"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
