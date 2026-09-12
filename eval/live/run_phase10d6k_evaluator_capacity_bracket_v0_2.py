from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for p in (ROOT, BACKEND):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment, node_proposition
from app.services.scheduler import get_decision_strategy
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
from eval.live.phase10d6k_evaluator_authority_v0_2 import (
    VERSION as AUTHORITY_VERSION,
    enrich_for_arm,
    strong_jurisdiction,
    strong_target_fit,
)
from eval.live.run_phase10d6l4_grounding_capacity_bracketing_v0_1 import run_batch as run_grounding_batch
from eval.live.run_phase10d6l4j_open_new_jurisdiction_capacity_v0_1 import run_batch as run_jurisdiction_batch
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import selected_cases
from eval.live.run_phase10d3_real_web_static_cognitive_map_v0_1 import branch_relation_key
from eval.live.run_phase10d6b_prompt_reconciliation_shadow_v0_1 import reconstruct_prod_matches
from eval.live.run_phase8c13_decision_causal_core_v0_1 import features

RUN_VERSION = "phase10d6k-evaluator-capacity-bracket-v0.2"
SOURCE = ROOT / "eval/live/results/phase10d6h_cardinal_field_removal_parity_v0_1/phase10d6h_cardinal_field_removal_parity_v0.1_20260911T071632Z.json"
SOURCE_SHA = "86e1dc644aa0b7a8e6f559b2fd674357268ba12ecd82b586ed626b655965e29c"
HIST = ROOT / "eval/live/results/phase10d4_real_web_basin_persistence_v0_1/phase10d4_real_web_basin_persistence_v0.1_20260910T160403Z.json"
HIST_SHA = "5299cab0607779989b896148765f5c6ef9873b001449b73f51cba6b67e7438a7"
OUT_DIR = ROOT / "eval/live/results/phase10d6k_evaluator_capacity_bracket_v0_2"
CASES = ("A", "D", "X", "N4")
REPEATS = 3
ARMS = (
    "K0_ALL_SUPPORT_SUFFICIENT",
    "K1_SINGLE_SOURCE_WEAK",
    "K2_WEAK_EVALUATOR_AUTHORITY",
    "K3_STRONG_EVALUATOR_AUTHORITY",
)
PROVENANCE = {"A": "PRIMARY_SOURCE", "D": "SECONDARY_REPORT", "X": "PRIMARY_SOURCE", "N4": "PRIMARY_SOURCE"}
FIT_SEVERITY = {"DIRECT": 0, "PARTIAL": 1, "INSUFFICIENT": 2, "CONTRADICTS_OPERATION": 3}
JURISDICTION_SEVERITY = {"SUPPORTED_JURISDICTION": 0, "INSUFFICIENT_JURISDICTION": 1}
STRATEGY_ID = "pareto-multidelta-cardinal-free-anchored-open-new"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def row_signature(row: dict) -> tuple:
    return (
        row["operation"],
        row.get("target"),
        tuple(sorted(row.get("support_unit_ids") or [])),
        tuple(sorted(row.get("jurisdiction_anchor_ids") or [])),
        row.get("reason") or "",
    )


def relation_id(label: str, sig: tuple) -> str:
    raw = json.dumps([label, sig[0], sig[1], list(sig[2]), list(sig[3]), sig[4]], ensure_ascii=False)
    return f"{label}::" + hashlib.sha256(raw.encode()).hexdigest()[:20]


def modal(values: list[str], severity: dict[str, int]) -> tuple[str, dict]:
    counts = Counter(values)
    top = max(counts.values())
    tied = [k for k, v in counts.items() if v == top]
    return max(tied, key=lambda x: severity[x]), dict(counts)


def unit_text(unit: dict) -> str:
    return str(unit.get("statement") or unit.get("content") or unit.get("text") or "")


def node_code(node) -> str:
    payload = node.payload or {}
    if isinstance(payload, dict) and payload.get("phase6b_fixture_code"):
        return str(payload["phase6b_fixture_code"])
    metadata = node.metadata or {}
    if isinstance(metadata, dict) and metadata.get("fixture_code"):
        return str(metadata["fixture_code"])
    return str(node.title)


def unique_rows(hcase: dict) -> dict[tuple, dict]:
    rows: dict[tuple, dict] = {}
    for sample in hcase["samples"]:
        for row in sample["normalized_effects"]:
            rows.setdefault(row_signature(row), row)
    return rows


def build_evaluator_items(label: str, case: dict, hcase: dict, nodes) -> tuple[list[dict], list[dict], dict[str, tuple]]:
    units = {str(u.get("unit_id")): u for u in case["frozen_units"]}
    by_code = {node_code(n): n for n in nodes}
    by_id = {str(n.id): n for n in nodes}
    targeted: list[dict] = []
    open_new: list[dict] = []
    sig_by_id: dict[str, tuple] = {}
    for sig, row in unique_rows(hcase).items():
        rid = relation_id(label, sig)
        sig_by_id[rid] = sig
        supports = [{"unit_id": uid, "text": unit_text(units[uid])} for uid in row.get("support_unit_ids") or []]
        if row["operation"] != "OPEN_NEW":
            node = by_code[row["target"]]
            targeted.append({
                "relation_id": rid,
                "operation": row["operation"],
                "target_code": row["target"],
                "target_proposition": node_proposition(node),
                "relation_reason": row.get("reason") or "",
                "support_texts": supports,
                "jurisdiction_anchor_codes": [],
            })
            continue
        anchors = []
        anchor_codes = []
        for anchor_id in row.get("jurisdiction_anchor_ids") or []:
            node = by_id[str(anchor_id)]
            anchors.append(str(anchor_id))
            anchor_codes.append(node_code(node))
        open_new.append({
            "relation_id": rid,
            "operation": "OPEN_NEW",
            "relation_reason": row.get("reason") or "",
            "support_texts": supports,
            "jurisdiction_anchor_ids": anchors,
            "jurisdiction_anchor_codes": anchor_codes,
        })
    return targeted, open_new, sig_by_id


def weak_evaluate_case(label: str, case: dict, hcase: dict, nodes) -> tuple[dict[tuple, str], dict[tuple, str], dict]:
    targeted, open_new, sig_by_id = build_evaluator_items(label, case, hcase, nodes)
    fit_votes = {x["relation_id"]: Counter() for x in targeted}
    jurisdiction_votes = {x["relation_id"]: Counter() for x in open_new}
    runs = {"targeted": [], "open_new": []}

    for repeat in range(1, REPEATS + 1):
        if targeted:
            run = run_grounding_batch(targeted)
            run["repeat"] = repeat
            runs["targeted"].append(run)
            if run.get("status") != "OK":
                raise RuntimeError(f"WEAK_GROUNDING_INVALID {label} repeat={repeat}: {run.get('errors')}")
            for item in run["items"]:
                fit_votes[item["relation_id"]][item["grounding_class"]] += 1
        if open_new:
            run = run_jurisdiction_batch(open_new)
            run["repeat"] = repeat
            runs["open_new"].append(run)
            if run.get("status") != "OK":
                raise RuntimeError(f"WEAK_JURISDICTION_INVALID {label} repeat={repeat}: {run.get('errors')}")
            for item in run["items"]:
                jurisdiction_votes[item["relation_id"]][item["jurisdiction_class"]] += 1
    fit_map: dict[tuple, str] = {}
    jurisdiction_map: dict[tuple, str] = {}
    fit_details = {}
    jurisdiction_details = {}
    for rid, counts in fit_votes.items():
        choice, raw = modal(list(counts.elements()), FIT_SEVERITY)
        sig = sig_by_id[rid]
        fit_map[sig] = choice
        fit_details[rid] = {
            "signature": [sig[0], sig[1], list(sig[2]), list(sig[3]), sig[4]],
            "modal": choice,
            "counts": raw,
        }
    for rid, counts in jurisdiction_votes.items():
        choice, raw = modal(list(counts.elements()), JURISDICTION_SEVERITY)
        sig = sig_by_id[rid]
        jurisdiction_map[sig] = choice
        jurisdiction_details[rid] = {
            "signature": [sig[0], sig[1], list(sig[2]), list(sig[3]), sig[4]],
            "modal": choice,
            "counts": raw,
        }
    return fit_map, jurisdiction_map, {
        "targeted": fit_details,
        "open_new": jurisdiction_details,
        "runs": runs,
    }


def make_base(row: dict) -> CognitiveEffect:
    target_id = UUID(row["target_kernel_node_id"]) if row.get("target_kernel_node_id") else None
    return CognitiveEffect(
        target_kernel_node_id=target_id,
        operation=CognitiveEffectKind(row["operation"]),
        change_magnitude=0.0,
        epistemic_strength=0.0,
        target_importance=0.0,
        reason=row.get("reason") or "",
    )


def authority_for_row(label: str, row: dict, arm: str, weak_fit: dict, weak_jurisdiction: dict) -> tuple[str | None, str | None]:
    sig = row_signature(row)
    if arm == "K2_WEAK_EVALUATOR_AUTHORITY":
        if row["operation"] == "OPEN_NEW":
            return None, weak_jurisdiction[sig]
        return weak_fit[sig], None
    if arm == "K3_STRONG_EVALUATOR_AUTHORITY":
        if row["operation"] == "OPEN_NEW":
            return None, strong_jurisdiction(label)
        return strong_target_fit(label, row["operation"], row.get("target")), None
    return None, None


def project_sample(
    label: str,
    sample: dict,
    arm: str,
    *,
    nodes,
    matches,
    weak_fit,
    weak_jurisdiction,
    relation_key,
    strategy,
) -> dict:
    effects = []
    traces = []
    rejected = []
    for row in sample["normalized_effects"]:
        fit, jurisdiction = authority_for_row(label, row, arm, weak_fit, weak_jurisdiction)
        enriched, trace = enrich_for_arm(
            make_base(row),
            arm=arm,
            nodes=nodes,
            matches=matches,
            fit=fit,
            jurisdiction=jurisdiction,
            provenance_role=PROVENANCE[label],
            support_bound=bool(row.get("support_unit_ids")),
        )
        trace = {
            **trace,
            "operation": row["operation"],
            "target": row.get("target"),
            "support_unit_ids": row.get("support_unit_ids") or [],
            "jurisdiction_anchor_ids": row.get("jurisdiction_anchor_ids") or [],
        }
        traces.append(trace)
        if enriched is None:
            rejected.append(trace)
        else:
            effects.append(enriched)
    assessment = CognitiveImpactAssessment(effects=effects)
    report = analyze_decision_causal_core(
        assessment=assessment,
        matches=matches,
        features=features(),
        decision_strategy=strategy,
        relation_key=relation_key,
    )
    return {
        "sample_id": sample["sample_id"],
        "attention": report.baseline_decision,
        "necessary_core": list(report.necessary_core),
        "sufficient_supports": list(report.sufficient_supports),
        "n_pre_grounding": len(sample["normalized_effects"]),
        "n_grounded": len(effects),
        "n_rejected": len(rejected),
        "rejected": rejected,
        "authority_trace": traces,
    }


def hist_counts(hist: dict, label: str) -> dict:
    row = hist["cases"][label]
    return {
        key: dict(Counter(x["attention"] for x in row[key]))
        for key in ("t1_samples", "t2_samples")
    }


def paired_counts(left: list[dict], right: list[dict], *, prefix: str) -> Counter:
    out = Counter()
    for a, b in zip(left, right):
        if a["attention"] != b["attention"]:
            out[f"{prefix}_changed"] += 1
        if b["attention"] == "ENGAGE" and a["attention"] != "ENGAGE":
            out[f"{prefix}_new_engage"] += 1
        if b["attention"] == "DROP" and a["attention"] != "DROP":
            out[f"{prefix}_new_drop"] += 1
    return out


def main() -> int:
    if sha256(SOURCE) != SOURCE_SHA:
        raise RuntimeError("SOURCE_SHA_MISMATCH")
    if sha256(HIST) != HIST_SHA:
        raise RuntimeError("HIST_SHA_MISMATCH")
    src = json.loads(SOURCE.read_text())
    hist = json.loads(HIST.read_text())
    selected = selected_cases()
    nodes = build_phase6b_mvp_kernel_nodes()
    strategy = get_decision_strategy(STRATEGY_ID)
    out_cases = {}
    paired = Counter()

    for label in CASES:
        case = selected[label]["case"]
        hcase = src["results"][label]
        matches = reconstruct_prod_matches(case, nodes)
        relation_key = branch_relation_key(nodes, case["frozen_units"])
        weak_fit, weak_jurisdiction, weak_details = weak_evaluate_case(label, case, hcase, nodes)
        arm_samples = {arm: [] for arm in ARMS}
        for sample in hcase["samples"]:
            for arm in ARMS:
                arm_samples[arm].append(project_sample(
                    label,
                    sample,
                    arm,
                    nodes=nodes,
                    matches=matches,
                    weak_fit=weak_fit,
                    weak_jurisdiction=weak_jurisdiction,
                    relation_key=relation_key,
                    strategy=strategy,
                ))

        summaries = {}
        for arm, rows in arm_samples.items():
            summaries[arm] = {
                "attention": dict(Counter(x["attention"] for x in rows)),
                "grounded_effects": sum(x["n_grounded"] for x in rows),
                "rejected_effects": sum(x["n_rejected"] for x in rows),
                "samples": rows,
            }
        paired.update(paired_counts(
            arm_samples["K2_WEAK_EVALUATOR_AUTHORITY"],
            arm_samples["K3_STRONG_EVALUATOR_AUTHORITY"],
            prefix="K3_vs_K2",
        ))
        paired.update(paired_counts(
            arm_samples["K1_SINGLE_SOURCE_WEAK"],
            arm_samples["K3_STRONG_EVALUATOR_AUTHORITY"],
            prefix="K3_vs_K1",
        ))
        out_cases[label] = {
            "provenance_role": PROVENANCE[label],
            "weak_evaluator": weak_details,
            "strong_policy": {
                "targeted": "case-level frozen policy from 175 amendment",
                "open_new_jurisdiction": strong_jurisdiction(label),
            },
            "arms": summaries,
            "historical_10d4_attention_context": hist_counts(hist, label),
        }
        print(json.dumps({
            "label": label,
            "attention": {arm: summaries[arm]["attention"] for arm in ARMS},
            "rejected": {arm: summaries[arm]["rejected_effects"] for arm in ARMS},
        }, ensure_ascii=False), flush=True)

    payload = {
        "run_version": RUN_VERSION,
        "status": "EVALUATOR_CAPACITY_BRACKETED_AUTHORITATIVE_ATTENTION_SHADOW",
        "measurement_sha": git_head(),
        "source_phase10d6h": str(SOURCE.relative_to(ROOT)),
        "source_sha256": SOURCE_SHA,
        "historical_context_phase10d4": str(HIST.relative_to(ROOT)),
        "historical_context_sha256": HIST_SHA,
        "authority_version": AUTHORITY_VERSION,
        "decision_strategy": strategy.execution_snapshot(),
        "weak_repeats_per_case": REPEATS,
        "arms": list(ARMS),
        "cases": out_cases,
        "paired_sensitivity": dict(paired),
        "guardrails": [
            "No acquisition, Sensor, Auditor, Locate or Relation-Mapping call occurs.",
            "Frozen 10D.6H relation topology/support/jurisdiction is reused exactly.",
            "Weak Grounding and jurisdiction evaluators see no strong labels.",
            "Strong evaluator is frozen case-level policy, not per-realization tuning.",
            "Grounding owns targeted relation-support fit; Anchored owns OPEN_NEW jurisdiction fit.",
            "All arms share C1 importance, cardinal-free effect existence, Magnitude-Free, Pareto and Attention.",
            "Production defaults remain unchanged; Phase 9A remains paused.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = OUT_DIR / f"phase10d6k_evaluator_capacity_bracket_v0.2_{stamp}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n")
    print("PAIRED=" + json.dumps(dict(paired), ensure_ascii=False, sort_keys=True))
    print("RESULT_PATH=" + str(out.relative_to(ROOT)))
    print("RESULT_SHA256=" + sha256(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
