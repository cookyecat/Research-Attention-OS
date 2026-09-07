"""Run the first fresh integrated no-Delta AWARE attribution measurement.

This runner joins:
- frozen IA1-IA12 template (event + P Evidence Packet)
- frozen Human D/S/P + Final Gold
- frozen D/S/P estimators
- frozen Boolean integration harness / production Scheduler wiring

It is an attribution runner, not a new semantic judge.
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
from eval.live.no_delta_awareness_integration_v1 import (
    INTEGRATION_VERSION,
    POLICY_GATE_VERSION,
    estimate_integrated_no_delta_awareness_v1,
    expected_gate_disposition,
)
from eval.live.standing_radar_fit_v3 import (
    ESTIMATOR_VERSION as D_ESTIMATOR_VERSION,
    PROFILE_ID as D_PROFILE_ID,
    PROMPT_VERSION as D_PROMPT_VERSION,
    build_messages as build_d_messages,
    load_standing_radar_profile,
    prompt_sha256 as d_prompt_sha256,
)
from eval.live.material_consequence_v1 import (
    ESTIMATOR_VERSION as S_ESTIMATOR_VERSION,
    PROFILE_ID as S_PROFILE_ID,
    PROMPT_VERSION as S_PROMPT_VERSION,
    build_messages as build_s_messages,
    load_material_consequence_profile,
    prompt_sha256 as s_prompt_sha256,
)
from eval.live.collective_attention_v1 import (
    ESTIMATOR_VERSION as P_ESTIMATOR_VERSION,
    EVIDENCE_INTERFACE_VERSION as P_EVIDENCE_INTERFACE_VERSION,
    PROFILE_ID as P_PROFILE_ID,
    PROMPT_VERSION as P_PROMPT_VERSION,
    build_messages as build_p_messages,
    load_collective_attention_profile,
    prompt_sha256 as p_prompt_sha256,
)

DEFAULT_TEMPLATE = ROOT / "eval" / "live" / "manifest.no_delta_awareness_integrated_fresh.v1.template.yaml"
DEFAULT_GOLD = ROOT / "eval" / "live" / "manifest.no_delta_aware_integrated_human_gold.v1.yaml"
DEFAULT_OUT = ROOT / "eval" / "live" / "results" / "no_delta_awareness_integration_v1_fresh_first_run.json"

FRESH_TEMPLATE_COMMIT = "20bf62d173790692acdbeeb1d29a5575d85f79e6"
INTEGRATION_FREEZE_COMMIT = "c39292be9b4d782391c845368efa7346502be7ec"
HUMAN_GOLD_COMMIT = "964ef46e9ee54caa7d1957160053f6560cd5476b"


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"manifest must be a mapping: {path}")
    return data


def load_joined_cases(template_path: Path = DEFAULT_TEMPLATE, gold_path: Path = DEFAULT_GOLD) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    template = _load_yaml(template_path)
    gold = _load_yaml(gold_path)

    template_cases = template.get("cases") or []
    gold_cases = gold.get("cases") or []
    by_gold = {str(c.get("id")): c for c in gold_cases}
    if len(by_gold) != len(gold_cases):
        raise ValueError("duplicate Human Gold case id")

    joined: list[dict[str, Any]] = []
    for case in template_cases:
        cid = str(case.get("id"))
        if cid not in by_gold:
            raise ValueError(f"missing Human Gold for {cid}")
        joined.append({"template": case, "gold": by_gold[cid]})

    template_ids = [str(c.get("id")) for c in template_cases]
    gold_ids = [str(c.get("id")) for c in gold_cases]
    if set(template_ids) != set(gold_ids):
        raise ValueError(f"template/gold id mismatch: template={template_ids}, gold={gold_ids}")
    if len(joined) != 12:
        raise ValueError(f"expected 12 integrated cases, got {len(joined)}")
    return template, gold, joined


def validate_provenance(template: dict[str, Any], gold: dict[str, Any]) -> None:
    expected_template = {
        "integration_version": INTEGRATION_VERSION,
        "policy_gate_version": POLICY_GATE_VERSION,
        "integration_freeze_commit": INTEGRATION_FREEZE_COMMIT,
        "standing_radar_estimator_version": D_ESTIMATOR_VERSION,
        "standing_radar_profile_id": D_PROFILE_ID,
        "material_consequence_estimator_version": S_ESTIMATOR_VERSION,
        "collective_attention_estimator_version": P_ESTIMATOR_VERSION,
        "collective_attention_evidence_interface_version": P_EVIDENCE_INTERFACE_VERSION,
    }
    template_mismatch = {
        k: {"manifest": template.get(k), "runtime": v}
        for k, v in expected_template.items()
        if template.get(k) != v
    }
    if template_mismatch:
        raise ValueError(f"integrated template provenance mismatch: {template_mismatch}")

    expected_gold = {
        "fresh_template_commit": FRESH_TEMPLATE_COMMIT,
        "integration_freeze_commit": INTEGRATION_FREEZE_COMMIT,
    }
    gold_mismatch = {
        k: {"manifest": gold.get(k), "expected": v}
        for k, v in expected_gold.items()
        if gold.get(k) != v
    }
    if gold_mismatch:
        raise ValueError(f"integrated Human Gold provenance mismatch: {gold_mismatch}")


def _binary_metrics(rows: list[dict[str, Any]], *, gold_key: str, pred_key: str, positive: str, negative: str) -> dict[str, Any]:
    scored = [r for r in rows if r.get(gold_key) in {positive, negative} and r.get(pred_key) in {positive, negative}]
    n = len(scored)
    gp = sum(r[gold_key] == positive for r in scored)
    gn = sum(r[gold_key] == negative for r in scored)
    tp = sum(r[gold_key] == positive and r[pred_key] == positive for r in scored)
    tn = sum(r[gold_key] == negative and r[pred_key] == negative for r in scored)
    fp = sum(r[gold_key] == negative and r[pred_key] == positive for r in scored)
    fn = sum(r[gold_key] == positive and r[pred_key] == negative for r in scored)
    return {
        "n_scored": n,
        "n_gold_positive": gp,
        "n_gold_negative": gn,
        "exact_accuracy": (tp + tn) / n if n else None,
        "positive_recall": tp / gp if gp else None,
        "negative_recall": tn / gn if gn else None,
        "false_positive_count": fp,
        "false_negative_count": fn,
    }


def compute_integrated_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    d = _binary_metrics(rows, gold_key="gold_D", pred_key="pred_D", positive="IN", negative="OUT")
    s = _binary_metrics(rows, gold_key="gold_S", pred_key="pred_S", positive="MATERIAL", negative="NOT_MATERIAL")
    p = _binary_metrics(rows, gold_key="gold_P", pred_key="pred_P", positive="SALIENT", negative="NOT_SALIENT")
    final = _binary_metrics(rows, gold_key="gold_final", pred_key="pred_final", positive="AWARE", negative="DROP")

    oracle_rows = [r for r in rows if r.get("human_gate_final") in {"AWARE", "DROP"}]
    oracle_exact = sum(r["human_gate_final"] == r["gold_final"] for r in oracle_rows)

    return {
        "D": d,
        "S": s,
        "P": p,
        "final": {
            **final,
            "aware_recall": final["positive_recall"],
            "drop_recall": final["negative_recall"],
            "false_aware_count": final["false_positive_count"],
            "false_drop_count": final["false_negative_count"],
        },
        "human_gate_consistency": {
            "n": len(oracle_rows),
            "exact": oracle_exact,
            "accuracy": oracle_exact / len(oracle_rows) if oracle_rows else None,
            "mismatch_cases": [r["case_id"] for r in oracle_rows if r["human_gate_final"] != r["gold_final"]],
        },
        "masked_component_error_cases": [r["case_id"] for r in rows if r.get("any_component_error") and r.get("final_correct") is True],
        "causal_final_error_cases": [r["case_id"] for r in rows if r.get("final_correct") is False],
        "wiring_mismatch_cases": [r["case_id"] for r in rows if r.get("gate_wiring_matches") is False],
    }


def run_integrated_v1(
    template_path: Path,
    gold_path: Path,
    *,
    dry_run: bool,
    d_chat_fn=None,
    s_chat_fn=None,
    p_chat_fn=None,
) -> dict[str, Any]:
    load_repo_env()
    template, gold, joined = load_joined_cases(template_path, gold_path)
    validate_provenance(template, gold)

    d_profile = load_standing_radar_profile()
    s_profile = load_material_consequence_profile()
    p_profile = load_collective_attention_profile()

    rows: list[dict[str, Any]] = []
    component_failures: list[dict[str, Any]] = []
    actual_models = {"D": set(), "S": set(), "P": set()}

    for item in joined:
        case = item["template"]
        g = item["gold"]
        cid = str(case["id"])
        event = str(case["event"])
        p_packet = case["p_packet"]

        gold_d = str(g["D"])
        gold_s = str(g["S"])
        gold_p = str(g["P"])
        gold_final = str(g["final"])
        human_gate_final = expected_gate_disposition(gold_d, gold_s, gold_p).value

        row: dict[str, Any] = {
            "case_id": cid,
            "gold_D": gold_d,
            "gold_S": gold_s,
            "gold_P": gold_p,
            "gold_final": gold_final,
            "human_gate_final": human_gate_final,
            "human_gate_matches_final": human_gate_final == gold_final,
            "pred_D": None,
            "pred_S": None,
            "pred_P": None,
            "pred_final": None,
            "D_correct": None,
            "S_correct": None,
            "P_correct": None,
            "final_correct": None,
            "any_component_error": None,
            "gate_wiring_matches": None,
            "scorable": False,
            "D": None,
            "S": None,
            "P": None,
        }

        if dry_run:
            d_messages = build_d_messages(event, d_profile)
            s_messages = build_s_messages(event, s_profile)
            p_messages = build_p_messages(p_packet, p_profile)
            row.update({
                "dry_run": True,
                "D_prompt_chars": sum(len(m["content"]) for m in d_messages),
                "S_prompt_chars": sum(len(m["content"]) for m in s_messages),
                "P_prompt_chars": sum(len(m["content"]) for m in p_messages),
            })
            rows.append(row)
            continue

        out = estimate_integrated_no_delta_awareness_v1(
            event,
            p_packet,
            d_profile=d_profile,
            s_profile=s_profile,
            p_profile=p_profile,
            d_chat_fn=d_chat_fn,
            s_chat_fn=s_chat_fn,
            p_chat_fn=p_chat_fn,
        )
        row["scorable"] = bool(out.get("scorable"))
        row["gate_wiring_matches"] = out.get("gate_wiring_matches")
        row["D"] = out.get("D")
        row["S"] = out.get("S")
        row["P"] = out.get("P")

        for component in ("D", "S", "P"):
            meta = ((out.get(component) or {}).get("model_meta") or {})
            if meta.get("model"):
                actual_models[component].add(str(meta["model"]))

        if not row["scorable"]:
            component_failures.append({
                "case_id": cid,
                "component_scorable": out.get("component_scorable"),
                "D_failure": (out.get("D") or {}).get("failure_kind"),
                "S_failure": (out.get("S") or {}).get("failure_kind"),
                "P_failure": (out.get("P") or {}).get("failure_kind"),
            })
            rows.append(row)
            continue

        labels = out["labels"]
        row["pred_D"] = labels["D"]
        row["pred_S"] = labels["S"]
        row["pred_P"] = labels["P"]
        row["pred_final"] = str(out["disposition"])
        row["D_correct"] = row["pred_D"] == gold_d
        row["S_correct"] = row["pred_S"] == gold_s
        row["P_correct"] = row["pred_P"] == gold_p
        row["final_correct"] = row["pred_final"] == gold_final
        row["any_component_error"] = not (row["D_correct"] and row["S_correct"] and row["P_correct"])
        rows.append(row)

    metrics = None if dry_run else compute_integrated_metrics(rows)
    p_insufficient = [
        r["case_id"] for r in rows
        if ((r.get("P") or {}).get("failure_kind") == "insufficient_evidence")
    ]

    return {
        "name": gold.get("name"),
        "validation_type": gold.get("validation_type"),
        "integration_version": INTEGRATION_VERSION,
        "policy_gate_version": POLICY_GATE_VERSION,
        "integration_freeze_commit": INTEGRATION_FREEZE_COMMIT,
        "fresh_template_commit": FRESH_TEMPLATE_COMMIT,
        "human_gold_commit": HUMAN_GOLD_COMMIT,
        "measurement_git_head": git_head(),
        "measurement_timestamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "template_manifest": str(template_path),
        "human_gold_manifest": str(gold_path),
        "dry_run": dry_run,
        "scored": not dry_run,
        "component_identity": {
            "D": {"estimator_version": D_ESTIMATOR_VERSION, "prompt_version": D_PROMPT_VERSION, "profile_id": D_PROFILE_ID, "prompt_sha256": d_prompt_sha256()},
            "S": {"estimator_version": S_ESTIMATOR_VERSION, "prompt_version": S_PROMPT_VERSION, "profile_id": S_PROFILE_ID, "prompt_sha256": s_prompt_sha256()},
            "P": {"estimator_version": P_ESTIMATOR_VERSION, "prompt_version": P_PROMPT_VERSION, "profile_id": P_PROFILE_ID, "evidence_interface_version": P_EVIDENCE_INTERFACE_VERSION, "prompt_sha256": p_prompt_sha256()},
        },
        "actual_models": {k: sorted(v) for k, v in actual_models.items()},
        "cases": rows,
        "metrics": metrics,
        "component_failures": component_failures,
        "p_insufficient_evidence_cases": p_insufficient,
        "n_cases": len(rows),
        "n_component_failures": len(component_failures),
    }


def write_artifact(payload: dict[str, Any], path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing integrated first-run artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Integrated no-Delta AWARE fresh attribution run")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    payload = run_integrated_v1(args.template, args.gold, dry_run=args.dry_run)
    if args.dry_run:
        print(json.dumps({
            "n_cases": payload["n_cases"],
            "integration_version": payload["integration_version"],
            "integration_freeze_commit": payload["integration_freeze_commit"],
            "fresh_template_commit": payload["fresh_template_commit"],
            "human_gold_commit": payload["human_gold_commit"],
            "component_identity": payload["component_identity"],
        }, indent=2, ensure_ascii=False))
        return 0

    write_artifact(payload, args.out)
    print(f"wrote {args.out}")
    print(json.dumps(payload["metrics"], indent=2, ensure_ascii=False))
    print(json.dumps({
        "n_component_failures": payload["n_component_failures"],
        "p_insufficient_evidence_cases": payload["p_insufficient_evidence_cases"],
        "actual_models": payload["actual_models"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
