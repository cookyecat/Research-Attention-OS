from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for p in (ROOT, BACKEND):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app.cognitive.client import chat_json
from app.services.cognitive_impact import legal_public_effects, normalize_frozen_transition
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.phase6b_cognitive_semantics_v0_1 import (
    admitted_epistemic_units,
    build_phase6b_mvp_kernel_nodes,
    build_phase6b_perf_challenge_nodes,
)
from eval.live.phase8c3_native_cognitive_interface_v0_1 import native_assess, native_locate
from eval.live.run_phase8c7_real_web_magnitude_free_validation_v0_1 import (
    _assessment,
    _features,
    _matches,
)

RUN_VERSION = "phase8c8-semantic-topology-stability-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase8c8_semantic_topology_stability_v0_1"
CASES = ("RS05", "RS15", "RS11", "RS12", "A", "C", "D", "X")

HIST_AUDIT = ROOT / "eval/live/results/phase7a_v0_2_6_epistemic_audit_v0_1/phase6b_epistemic_unit_audit_v0_1_20260908T090628Z.json"
HIST_AUDIT_SHA = "aa594aab2b7b2f0e252dbf3ed8978865e03d9ddd1b905c8f38db0ae60ea5711f"
REG_AUDIT = ROOT / "eval/live/results/phase7a_v0_2_6_regression_audit_v0_1/phase6b_epistemic_unit_audit_v0_1_20260908T094903Z.json"
REG_AUDIT_SHA = "c90883c2786995423d72c823247f0289cdc7e473b353f1bc83dd473b5fa6739f"
REAL_WEB = ROOT / "eval/live/results/phase8c7_real_web_magnitude_free_validation_v0_1/phase8c7_real_web_magnitude_free_validation_v0.1_20260909T185631Z.json"
REAL_WEB_SHA = "db24df43e836f91cd76767b838e21af67a377b61d69a5801bbb5c6695a135ae1"

CRITICAL = {
    "RS05": {("CHALLENGE", "CF-B-PERF")},
    "RS15": {("REINFORCE", "Q2"), ("REINFORCE", "B2")},
}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "but", "by", "for", "from",
    "has", "have", "if", "in", "into", "is", "it", "its", "may", "of", "on", "or", "that",
    "the", "their", "this", "to", "was", "were", "which", "with", "would", "could", "should",
}


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(path: Path, expected: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f"artifact SHA mismatch for {path}: {actual}")


def _forced_chat(messages, **kwargs):
    return chat_json(
        messages,
        timeout=float(kwargs.get("timeout") or 60.0),
        thinking=kwargs.get("thinking"),
        reasoning_effort=kwargs.get("reasoning_effort"),
        temperature=0.1,
    )


def _nodes(case_id: str):
    if case_id == "RS05":
        return build_phase6b_perf_challenge_nodes()
    return build_phase6b_mvp_kernel_nodes()


def _code_maps(nodes):
    code_by_uuid = {}
    code_by_str = {}
    for n in nodes:
        code = str((n.payload or {}).get("phase6b_fixture_code") or n.title)
        code_by_uuid[n.id] = code
        code_by_str[str(n.id)] = code
    return code_by_uuid, code_by_str


def _load_rs_units(case_id: str):
    path = HIST_AUDIT if case_id in {"RS05", "RS15"} else REG_AUDIT
    expected = HIST_AUDIT_SHA if path == HIST_AUDIT else REG_AUDIT_SHA
    verify(path, expected)
    data = json.loads(path.read_text())
    row = next(x for x in data["sources"] if x.get("source_id") == case_id)
    return admitted_epistemic_units(list(row.get("audits") or [])), {
        "artifact": str(path.relative_to(ROOT)), "sha256": expected,
        "representation": "full admitted epistemic units from frozen Auditor artifact",
    }


def _load_real_web_units(label: str):
    verify(REAL_WEB, REAL_WEB_SHA)
    data = json.loads(REAL_WEB.read_text())
    row = next(x for x in data["rows"] if x.get("label") == label and x.get("status") == "OK")
    units = []
    for idx, item in enumerate(row.get("semantic_units") or [], start=1):
        statement, status, confidence = item
        units.append({
            "unit_id": f"phase8c7-{label}-{idx}",
            "statement": str(statement),
            "epistemic_status": str(status),
            "confidence": str(confidence),
            "supports": [],
        })
    return units, {
        "artifact": str(REAL_WEB.relative_to(ROOT)), "sha256": REAL_WEB_SHA,
        "representation": "exact stored canonical tuples; support snippets were not retained in Phase 8C.7 and are empty here",
    }


def load_units(case_id: str):
    return _load_rs_units(case_id) if case_id.startswith("RS") else _load_real_web_units(case_id)


def match_target_key(matches, code_by_uuid):
    return tuple(sorted(code_by_uuid[m.kernel_node_id] for m in matches))


def match_detail_key(matches, code_by_uuid):
    return tuple(sorted((code_by_uuid[m.kernel_node_id], str(m.relevance_type)) for m in matches))


def serialize_native_matches(matches, code_by_uuid):
    return [{
        "target": code_by_uuid[m.kernel_node_id],
        "relevance_type": str(m.relevance_type),
        "score": float(m.score),
        "reason": str(m.reason or ""),
    } for m in matches]


def open_new_reason_signature(reason: str) -> dict:
    normalized = " ".join(re.findall(r"[a-z0-9]+", str(reason).lower()))
    tokens = [t for t in normalized.split() if t not in STOPWORDS][:14]
    label = " ".join(tokens)
    return {
        "label": label,
        "sha1": hashlib.sha1(normalized.encode()).hexdigest(),
    }


def effect_key(effect, code_by_str):
    op = effect.operation.value if hasattr(effect.operation, "value") else str(effect.operation)
    target = code_by_str.get(str(effect.target_kernel_node_id)) if effect.target_kernel_node_id else None
    return (op, target)


def serialize_effect(effect, code_by_str):
    op, target = effect_key(effect, code_by_str)
    row = {
        "operation": op,
        "target": target,
        "change_magnitude_debug_only": float(effect.change_magnitude),
        "epistemic_strength": float(effect.epistemic_strength),
        "target_importance": float(effect.target_importance),
        "reason": str(effect.reason or ""),
    }
    if op == "OPEN_NEW":
        row["open_new_reason_signature"] = open_new_reason_signature(effect.reason)
    return row


def topology_key(effects, code_by_str):
    return tuple(sorted(effect_key(e, code_by_str) for e in effects))


def jaccard(a, b) -> float:
    aa, bb = set(a), set(b)
    if not aa and not bb:
        return 1.0
    return len(aa & bb) / len(aa | bb)


def mean_pairwise_jaccard(keys) -> float:
    if len(keys) < 2:
        return 1.0 if keys else 0.0
    vals = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            vals.append(jaccard(keys[i], keys[j]))
    return sum(vals) / len(vals)


def distribution_metrics(keys) -> dict:
    if not keys:
        return {"n": 0, "n_unique": 0, "mode_rate": 0.0, "entropy_bits": 0.0, "mean_pairwise_jaccard": 0.0}
    counts = Counter(keys)
    n = len(keys)
    entropy = -sum((c / n) * math.log2(c / n) for c in counts.values())
    return {
        "n": n,
        "n_unique": len(counts),
        "mode_rate": max(counts.values()) / n,
        "entropy_bits": entropy,
        "mean_pairwise_jaccard": mean_pairwise_jaccard(keys),
        "counts": {str(k): v for k, v in counts.items()},
    }


def choose_modal_locate(ok_runs):
    if not ok_runs:
        return None, None
    counts = Counter(r["detail_key"] for r in ok_runs)
    best_count = max(counts.values())
    modal_keys = sorted(k for k, v in counts.items() if v == best_count)
    chosen_key = modal_keys[0]
    chosen = next(r for r in ok_runs if r["detail_key"] == chosen_key)
    return chosen_key, chosen


def magnitude_free_attention(parsed, native_matches, nodes):
    prod_matches = _matches(native_matches, nodes)
    assessment = _assessment(parsed, nodes)
    normalized = normalize_frozen_transition(assessment, prod_matches).assessment
    legal = legal_public_effects(normalized)
    strategy = get_decision_strategy("pareto-multidelta-magnitude-free")
    plan = route(
        _features(parsed), RuntimeView(), assessment=normalized, matches=prod_matches,
        decision_strategy=strategy,
    )
    return plan.disposition.value, legal


def run_case(case_id: str, repeats: int):
    units, source_meta = load_units(case_id)
    nodes = _nodes(case_id)
    code_by_uuid, code_by_str = _code_maps(nodes)

    locate_runs = []
    locate_objects = {}
    for repeat in range(1, repeats + 1):
        try:
            matches, meta, events = native_locate(units, nodes, chat_fn=_forced_chat)
            tkey = match_target_key(matches, code_by_uuid)
            dkey = match_detail_key(matches, code_by_uuid)
            row = {
                "repeat": repeat, "status": "OK",
                "target_key": tkey, "detail_key": dkey,
                "matches": serialize_native_matches(matches, code_by_uuid),
                "meta": meta, "schema_events": events,
            }
            locate_objects[repeat] = matches
        except Exception as exc:
            row = {"repeat": repeat, "status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:3000]}
        locate_runs.append(row)
        print(json.dumps({"case": case_id, "gate": "1A_LOCATE", "repeat": repeat, "status": row["status"], "targets": row.get("target_key"), "detail": row.get("detail_key"), "error": row.get("error")}, ensure_ascii=False), flush=True)

    locate_ok = [r for r in locate_runs if r["status"] == "OK"]
    modal_key, modal_row = choose_modal_locate(locate_ok)
    if modal_row is None:
        return {
            "case": case_id, "source": source_meta, "n_units": len(units),
            "locate_runs": locate_runs, "impact_runs": [],
            "error": "No valid Locate realization; Gate 1B skipped.",
        }
    frozen_matches = locate_objects[modal_row["repeat"]]

    impact_runs = []
    for repeat in range(1, repeats + 1):
        try:
            parsed, meta, events = native_assess(units, nodes, frozen_matches, chat_fn=_forced_chat)
            attention, legal = magnitude_free_attention(parsed, frozen_matches, nodes)
            tkey = topology_key(legal, code_by_str)
            row = {
                "repeat": repeat, "status": "OK",
                "topology_key": tkey,
                "effects": [serialize_effect(e, code_by_str) for e in legal],
                "magnitude_free_attention": attention,
                "meta": meta, "schema_events": events,
            }
        except Exception as exc:
            row = {"repeat": repeat, "status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:3000]}
        impact_runs.append(row)
        print(json.dumps({"case": case_id, "gate": "1B_IMPACT", "repeat": repeat, "status": row["status"], "topology": row.get("topology_key"), "attention": row.get("magnitude_free_attention"), "error": row.get("error")}, ensure_ascii=False), flush=True)

    target_keys = [r["target_key"] for r in locate_ok]
    detail_keys = [r["detail_key"] for r in locate_ok]
    impact_ok = [r for r in impact_runs if r["status"] == "OK"]
    topology_keys = [r["topology_key"] for r in impact_ok]
    attention_counts = Counter(r["magnitude_free_attention"] for r in impact_ok)
    edge_counts = Counter(edge for key in topology_keys for edge in set(key))
    critical = sorted(CRITICAL.get(case_id, set()))
    critical_recall = {
        str(edge): (edge_counts[edge] / len(impact_ok) if impact_ok else 0.0)
        for edge in critical
    }

    return {
        "case": case_id,
        "source": source_meta,
        "n_units": len(units),
        "locate": {
            "target_metrics": distribution_metrics(target_keys),
            "detail_metrics": distribution_metrics(detail_keys),
            "modal_detail_key": modal_key,
            "modal_representative_repeat": modal_row["repeat"],
            "runs": locate_runs,
        },
        "impact": {
            "topology_metrics": distribution_metrics(topology_keys),
            "edge_frequency": {str(k): v / len(impact_ok) for k, v in sorted(edge_counts.items())} if impact_ok else {},
            "critical_relations": critical,
            "critical_recall": critical_recall,
            "empty_topology_rate": sum(not k for k in topology_keys) / len(topology_keys) if topology_keys else 0.0,
            "magnitude_free_attention": dict(attention_counts),
            "attention_stability": max(attention_counts.values()) / len(impact_ok) if impact_ok else 0.0,
            "runs": impact_runs,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=6)
    args = parser.parse_args()

    results = []
    for case_id in CASES:
        results.append(run_case(case_id, args.repeats))

    summary = {}
    for row in results:
        case_id = row["case"]
        if "error" in row:
            summary[case_id] = {"error": row["error"]}
            continue
        summary[case_id] = {
            "n_units": row["n_units"],
            "locate_target_mode_rate": row["locate"]["target_metrics"]["mode_rate"],
            "locate_target_jaccard": row["locate"]["target_metrics"]["mean_pairwise_jaccard"],
            "locate_detail_mode_rate": row["locate"]["detail_metrics"]["mode_rate"],
            "impact_topology_mode_rate": row["impact"]["topology_metrics"]["mode_rate"],
            "impact_topology_jaccard": row["impact"]["topology_metrics"]["mean_pairwise_jaccard"],
            "impact_topology_entropy_bits": row["impact"]["topology_metrics"]["entropy_bits"],
            "critical_recall": row["impact"]["critical_recall"],
            "magnitude_free_attention": row["impact"]["magnitude_free_attention"],
            "attention_stability": row["impact"]["attention_stability"],
        }

    output = {
        "run_version": RUN_VERSION,
        "status": "CONTROLLED_FROZEN_AUDITED_WORLD_TOPOLOGY_ATTRIBUTION",
        "measurement_sha": git_head(),
        "repeats": args.repeats,
        "temperature": 0.1,
        "frozen_downstream": ["pareto-multidelta-v0.1", "magnitude-free-v0.1"],
        "open_new_identity_note": "Primary topology collapses OPEN_NEW target to null; strict normalized-reason signature is diagnostic only.",
        "real_web_limitation": "Phase 8C.7 stored canonical statement/status/confidence tuples but not support snippets; real-web Gate 1 replays those exact stored tuples with supports empty.",
        "summary": summary,
        "cases": results,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"RESULT_PATH={path.relative_to(ROOT)}")
    print(f"RESULT_SHA256={sha256(path)}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
