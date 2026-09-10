from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
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
from app.cognitive.schemas import KernelMatchItem
from app.services.cognitive_impact import legal_public_effects, normalize_frozen_transition
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.phase8c3_native_cognitive_interface_v0_1 import native_assess, native_locate
from eval.live.run_phase8c7_real_web_magnitude_free_validation_v0_1 import _assessment, _features, _matches
from eval.live.run_phase8c8_semantic_topology_stability_v0_1 import (
    CRITICAL,
    _code_maps,
    _forced_chat,
    _nodes,
    effect_key,
    load_units,
    serialize_effect,
    serialize_native_matches,
)
from eval.live.topology_stability_metrics_v0_1 import (
    canonical_topology,
    jaccard,
    summarize_topology_stability,
)

RUN_VERSION = "phase8c12-locate-relation-longitudinal-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase8c12_locate_relation_longitudinal_v0_1"
CASES = ("RS05", "RS15", "RS11", "RS12")
HIST8C8 = ROOT / "eval/live/results/phase8c8_semantic_topology_stability_v0_1/phase8c8_semantic_topology_stability_v0.1_20260909T195553Z.json"
HIST8C8_SHA = "f1d41669867e8cdddd5d8beb62b65348b24e42facbd783d031844297f60f8216"
HIST8C9 = ROOT / "eval/live/results/phase8c9_anchored_open_new_admission_v0_1/phase8c9_anchored_open_new_admission_v0.1_20260909T200448Z.json"
HIST8C9_SHA = "01e74482a1883b234f9446efd2cfd7ce6af2d23930c09a303460c5a58ade8efe"
STRATEGY_ID = "pareto-multidelta-magnitude-free-anchored-open-new"


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_verified(path: Path, expected: str) -> dict:
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f"artifact SHA mismatch {path}: {actual} != {expected}")
    return json.loads(path.read_text(encoding="utf-8"))


def as_topology(value) -> tuple:
    return canonical_topology(tuple(tuple(x) if isinstance(x, list) else x for x in (value or [])))


def modal(topologies: list[tuple]) -> tuple:
    counts = Counter(topologies)
    if not counts:
        return tuple()
    best = max(counts.values())
    return sorted((k for k, v in counts.items() if v == best), key=repr)[0]


def report(topologies, critical=()):
    return summarize_topology_stability(topologies, critical_relations=critical).as_dict()


def reconstruct_historical_modal_matches(case_row: dict, nodes) -> list[KernelMatchItem]:
    locate = case_row["locate"]
    rep = int(locate["modal_representative_repeat"])
    run = next(r for r in locate["runs"] if int(r["repeat"]) == rep and r["status"] == "OK")
    by_code = {str((n.payload or {}).get("phase6b_fixture_code") or n.title): n for n in nodes}
    out = []
    for item in run["matches"]:
        node = by_code[str(item["target"])]
        out.append(KernelMatchItem(
            kernel_node_id=node.id,
            relevance_type=str(item["relevance_type"]),
            score=float(item["score"]),
            reason=str(item["reason"]),
        ))
    return out


def current_attention(parsed, native_matches, nodes):
    prod_matches = _matches(native_matches, nodes)
    assessment = _assessment(parsed, nodes)
    normalized = normalize_frozen_transition(assessment, prod_matches).assessment
    legal = legal_public_effects(normalized)
    plan = route(
        _features(parsed), RuntimeView(), assessment=normalized, matches=prod_matches,
        decision_strategy=get_decision_strategy(STRATEGY_ID),
    )
    return plan.disposition.value, legal


def run_case(case_id: str, hist_case: dict, hist9: dict, repeats: int) -> dict:
    units, source_meta = load_units(case_id)
    nodes = _nodes(case_id)
    code_by_uuid, code_by_str = _code_maps(nodes)

    hist_locate_ok = [r for r in hist_case["locate"]["runs"] if r["status"] == "OK"]
    hist_target = [as_topology(r["target_key"]) for r in hist_locate_ok]
    hist_detail = [as_topology(r["detail_key"]) for r in hist_locate_ok]

    current_locate_rows = []
    current_target = []
    current_detail = []
    for repeat in range(1, repeats + 1):
        try:
            matches, meta, events = native_locate(units, nodes, chat_fn=_forced_chat)
            target = canonical_topology(code_by_uuid[m.kernel_node_id] for m in matches)
            detail = canonical_topology((code_by_uuid[m.kernel_node_id], str(m.relevance_type)) for m in matches)
            row = {
                "repeat": repeat, "status": "OK", "target_key": target, "detail_key": detail,
                "matches": serialize_native_matches(matches, code_by_uuid), "meta": meta, "schema_events": events,
            }
            current_target.append(target); current_detail.append(detail)
        except Exception as exc:
            row = {"repeat": repeat, "status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:3000]}
        current_locate_rows.append(row)
        print(json.dumps({"case": case_id, "gate": "12A_LOCATE", "repeat": repeat, "status": row["status"], "target": row.get("target_key"), "detail": row.get("detail_key"), "error": row.get("error")}, ensure_ascii=False), flush=True)

    frozen_hist_matches = reconstruct_historical_modal_matches(hist_case, nodes)
    impact_rows = []
    current_topologies = []
    attention = []
    for repeat in range(1, repeats + 1):
        try:
            parsed, meta, events = native_assess(units, nodes, frozen_hist_matches, chat_fn=_forced_chat)
            disposition, legal = current_attention(parsed, frozen_hist_matches, nodes)
            topology = canonical_topology(effect_key(e, code_by_str) for e in legal)
            row = {
                "repeat": repeat, "status": "OK", "topology_key": topology,
                "effects": [serialize_effect(e, code_by_str) for e in legal],
                "attention": disposition, "meta": meta, "schema_events": events,
            }
            current_topologies.append(topology); attention.append(disposition)
        except Exception as exc:
            row = {"repeat": repeat, "status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:3000]}
        impact_rows.append(row)
        print(json.dumps({"case": case_id, "gate": "12B_RELATION", "repeat": repeat, "status": row["status"], "topology": row.get("topology_key"), "attention": row.get("attention"), "error": row.get("error")}, ensure_ascii=False), flush=True)

    hist_impact_ok = [r for r in hist_case["impact"]["runs"] if r["status"] == "OK"]
    hist_topologies = [as_topology(r["topology_key"]) for r in hist_impact_ok]
    critical = CRITICAL.get(case_id, set())
    hist_attn = dict(hist9["replay_summary"][case_id]["candidate_attention"])
    current_attn = dict(sorted(Counter(attention).items()))

    return {
        "case": case_id,
        "source": source_meta,
        "n_units": len(units),
        "gate12a_locate": {
            "historical": {
                "target": report(hist_target), "detail": report(hist_detail),
                "modal_target": modal(hist_target), "modal_detail": modal(hist_detail),
            },
            "current": {
                "target": report(current_target), "detail": report(current_detail),
                "modal_target": modal(current_target), "modal_detail": modal(current_detail),
                "runs": current_locate_rows,
            },
            "modal_target_jaccard": jaccard(modal(hist_target), modal(current_target)),
            "modal_detail_jaccard": jaccard(modal(hist_detail), modal(current_detail)),
        },
        "gate12b_relation": {
            "historical_frozen_locate": serialize_native_matches(frozen_hist_matches, code_by_uuid),
            "historical": {
                "topology": report(hist_topologies, critical),
                "attention_anchored_magnitude_free_pareto": hist_attn,
            },
            "current": {
                "topology": report(current_topologies, critical),
                "attention_anchored_magnitude_free_pareto": current_attn,
                "attention_stability": (max(current_attn.values()) / len(attention)) if attention else 0.0,
                "runs": impact_rows,
            },
            "modal_topology_jaccard": jaccard(modal(hist_topologies), modal(current_topologies)),
            "historical_modal_topology": modal(hist_topologies),
            "current_modal_topology": modal(current_topologies),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=6)
    args = parser.parse_args()
    hist8 = load_verified(HIST8C8, HIST8C8_SHA)
    hist9 = load_verified(HIST8C9, HIST8C9_SHA)
    hist_by_case = {r["case"]: r for r in hist8["cases"]}

    rows = [run_case(case, hist_by_case[case], hist9, args.repeats) for case in CASES]
    summary = {}
    for row in rows:
        a = row["gate12a_locate"]
        b = row["gate12b_relation"]
        summary[row["case"]] = {
            "locate_modal_target_jaccard": a["modal_target_jaccard"],
            "locate_modal_detail_jaccard": a["modal_detail_jaccard"],
            "historical_locate_target_exact_mode": a["historical"]["target"]["exact_mode_rate"],
            "current_locate_target_exact_mode": a["current"]["target"]["exact_mode_rate"],
            "relation_modal_topology_jaccard": b["modal_topology_jaccard"],
            "historical_relation_exact_mode": b["historical"]["topology"]["exact_mode_rate"],
            "current_relation_exact_mode": b["current"]["topology"]["exact_mode_rate"],
            "historical_attention": b["historical"]["attention_anchored_magnitude_free_pareto"],
            "current_attention": b["current"]["attention_anchored_magnitude_free_pareto"],
            "current_attention_stability": b["current"]["attention_stability"],
            "critical_recall_historical": b["historical"]["topology"]["critical_relation_recall"],
            "critical_recall_current": b["current"]["topology"]["critical_relation_recall"],
        }

    output = {
        "run_version": RUN_VERSION,
        "status": "DEVELOPMENT_CAUSAL_ATTRIBUTION_ONLY",
        "measurement_sha": git_head(),
        "repeats": args.repeats,
        "historical_phase8c8": str(HIST8C8.relative_to(ROOT)),
        "historical_phase8c8_sha256": HIST8C8_SHA,
        "historical_phase8c9": str(HIST8C9.relative_to(ROOT)),
        "historical_phase8c9_sha256": HIST8C9_SHA,
        "decision_strategy": get_decision_strategy(STRATEGY_ID).execution_snapshot(),
        "summary": summary,
        "cases": rows,
        "guardrails": [
            "No Sensor or Auditor calls are made.",
            "Gate 12A changes execution epoch only on exact historical audited worlds and frozen Kernel fixtures.",
            "Gate 12B reconstructs exact historical modal Locate fields required by native_assess and changes Relation Mapping execution epoch only.",
            "Historical Attention is replayed under the same anchored-open-new plus magnitude-free Pareto strategy used for current Attention.",
            "A longitudinal distribution difference is not by itself proof of model-weight or provider-serving drift.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    digest = sha256(path)
    print(f"RESULT_PATH={path.relative_to(ROOT)}", flush=True)
    print(f"RESULT_SHA256={digest}", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
