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
from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment, legal_public_effects, normalize_frozen_transition
from app.services.effect_calibration import MAGNITUDE_FREE_CALIBRATION, RAW_CARDINAL_CALIBRATION
from app.services.matching import KernelMatch
from app.services.pareto_decision_strategy import pareto_frontier
from app.services.pipeline import _active_kernel
from app.services.scheduler import RuntimeView, SchedulerFeatures, get_decision_strategy, route
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
from eval.live.phase8c2_production_sensor_bridge_v0_1 import (
    _admitted_event_units,
    _as_of,
    _audit_non_event_units,
    _fail_on_auditor_transport_error,
    production_source_to_sensor_source,
)
from eval.live.phase8c3_native_cognitive_interface_v0_1 import native_assess, native_locate
from eval.live.raw_source_attention_vertical_slice_v0_1 import audit_event_edges, project_event_audit_edges
from eval.live.run_phase8c2_real_world_continuity_ab_v0_1 import _prepare_base_world
from eval.live.semantic_evidence_extractor_v0_2_6 import estimate_semantic_evidence_v0_2_6

RUN_VERSION = "phase8c7-real-web-magnitude-free-validation-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase8c7_real_web_magnitude_free_validation_v0_1"
LABELS = ("A", "C", "D", "X")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _forced_chat(messages, **kwargs):
    return chat_json(
        messages,
        timeout=float(kwargs.get("timeout") or 60.0),
        thinking=kwargs.get("thinking"),
        reasoning_effort=kwargs.get("reasoning_effort"),
        temperature=0.1,
    )


def _features(impact) -> SchedulerFeatures:
    return SchedulerFeatures(
        topic_relevance=.5, structural_relevance=.2, decision_relevance=.2,
        novelty=.5, credibility=.6, kernel_delta=.2, bottleneck_alignment=.1,
        disagreement=0.0, actionability=.3, temporal_value=.3,
        cognitive_cost=float(getattr(impact, "attention_cost", 2.0) or 2.0),
        evidence_maturity=float(getattr(impact, "evidence_maturity", .6) or .0),
        threatens_active_work=bool(getattr(impact, "threatens_active_work", False)),
        marketing_heavy=bool(getattr(impact, "marketing_heavy", False)),
        sources_conflict=False,
        high_quality_technical=bool(getattr(impact, "high_quality_technical", False)),
        foundational_paper=bool(getattr(impact, "foundational_paper", False)),
    )


def _perceive(source):
    sensor_source = production_source_to_sensor_source(source)
    result = estimate_semantic_evidence_v0_2_6(sensor_source, as_of=_as_of(source), chat_fn=_forced_chat)
    if not result.get("scorable") or not result.get("batch"):
        raise RuntimeError(f"Sensor failure: {result.get('failure_kind')} {result.get('error')}")
    batch = result["batch"]
    source_id = str(source.id)
    non_rows, non_admitted = _audit_non_event_units(
        source_id, list(batch.get("non_event_units") or []), chat_fn=_forced_chat
    )
    event_units = []
    event_rows = []
    for frame in batch.get("event_frames") or []:
        rows = audit_event_edges(project_event_audit_edges(source_id, frame), chat_fn=_forced_chat)
        _fail_on_auditor_transport_error(rows, source_id=source_id)
        admitted, _projection = _admitted_event_units(frame, rows)
        event_units.extend(admitted)
        event_rows.extend(rows)
    units = [*event_units, *non_admitted]
    diag = {
        "sensor_non_event_units": len(batch.get("non_event_units") or []),
        "sensor_event_frames": len(batch.get("event_frames") or []),
        "audited_non_event_edges": len(non_rows),
        "audited_event_edges": len(event_rows),
        "admitted_non_event_units": len(non_admitted),
        "admitted_event_units": len(event_units),
        "repair_used": bool(result.get("repair_used")),
    }
    return units, diag


def _unit_signature(units):
    rows = sorted(
        (
            str(u.get("statement") or "").strip(),
            str(u.get("epistemic_status") or ""),
            str(u.get("confidence") or ""),
        )
        for u in units
        if str(u.get("statement") or "").strip()
    )
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest(), rows


def _matches(native_matches, nodes):
    by_id = {n.id: n for n in nodes}
    out = []
    for item in native_matches:
        node = by_id[item.kernel_node_id]
        rel = str(item.relevance_type or "TOPIC")
        out.append(KernelMatch(
            node_id=node.id, node_type=node.node_type, title=node.title,
            score=float(item.score), reason=str(item.reason or ""),
            structural=rel.upper() == "STRUCTURAL", relevance_type=rel,
        ))
    return out


def _assessment(parsed, nodes):
    by_id = {n.id: n for n in nodes}
    effects = []
    for item in parsed.effects:
        op = item.operation if isinstance(item.operation, CognitiveEffectKind) else CognitiveEffectKind(str(item.operation))
        target = item.target_kernel_node_id
        if op == CognitiveEffectKind.OPEN_NEW:
            target = None
        node = by_id.get(target) if target else None
        effects.append(CognitiveEffect(
            target_kernel_node_id=target,
            operation=op,
            change_magnitude=float(item.change_magnitude),
            epistemic_strength=float(item.epistemic_strength),
            target_importance=float(item.target_importance),
            reason=str(item.reason or ""),
            exploration_candidate=bool(item.exploration_candidate),
            target_node_type=node.node_type if node else None,
        ))
    return CognitiveImpactAssessment(
        effects=effects,
        attention_cost=float(parsed.attention_cost or 2.0),
        exploration_candidate=bool(parsed.exploration_candidate),
    )


def _effect_row(effect, code_by_id):
    return {
        "operation": effect.operation.value if hasattr(effect.operation, "value") else str(effect.operation),
        "target": code_by_id.get(str(effect.target_kernel_node_id)) if effect.target_kernel_node_id else None,
        "change_magnitude": float(effect.change_magnitude),
        "epistemic_strength": float(effect.epistemic_strength),
        "target_importance": float(effect.target_importance),
        "reason": effect.reason,
    }


def _strategy_result(strategy_id, assessment, matches, features):
    strategy = get_decision_strategy(strategy_id)
    plan = route(features, RuntimeView(), assessment=assessment, matches=matches, decision_strategy=strategy)
    return {
        "disposition": plan.disposition.value,
        "expected_output": plan.expected_output.value,
        "strategy": strategy.execution_snapshot(),
    }


def _one(label, source, nodes, code_by_id, repeat):
    units, perception_diag = _perceive(source)
    unit_hash, unit_rows = _unit_signature(units)
    native_matches, match_meta, match_events = native_locate(units, nodes, chat_fn=_forced_chat)
    parsed, impact_meta, impact_events = native_assess(units, nodes, native_matches, chat_fn=_forced_chat)
    matches = _matches(native_matches, nodes)
    assessment = _assessment(parsed, nodes)
    normalized = normalize_frozen_transition(assessment, matches).assessment
    legal = legal_public_effects(normalized)
    topology = sorted(
        (
            e.operation.value if hasattr(e.operation, "value") else str(e.operation),
            code_by_id.get(str(e.target_kernel_node_id)) if e.target_kernel_node_id else None,
        )
        for e in legal
    )
    topology_hash = hashlib.sha256(json.dumps(topology, sort_keys=True).encode()).hexdigest()
    features = _features(parsed)
    raw_frontier = pareto_frontier(legal, matches, calibration_strategy=RAW_CARDINAL_CALIBRATION)
    mf_frontier = pareto_frontier(legal, matches, calibration_strategy=MAGNITUDE_FREE_CALIBRATION)
    return {
        "label": label, "repeat": repeat, "status": "OK",
        "semantic_unit_hash": unit_hash,
        "semantic_units": unit_rows,
        "perception": perception_diag,
        "effect_topology_hash": topology_hash,
        "effect_topology": topology,
        "effects": [_effect_row(e, code_by_id) for e in legal],
        "raw_frontier": [_effect_row(e, code_by_id) for e in raw_frontier],
        "magnitude_free_frontier": [_effect_row(e, code_by_id) for e in mf_frontier],
        "raw_cardinal": _strategy_result("pareto-multidelta", normalized, matches, features),
        "magnitude_free": _strategy_result("pareto-multidelta-magnitude-free", normalized, matches, features),
        "match_meta": match_meta, "impact_meta": impact_meta,
        "schema_events": [*match_events, *impact_events],
    }


def _summary(rows):
    out = {}
    for label in LABELS:
        selected = [r for r in rows if r["label"] == label]
        ok = [r for r in selected if r["status"] == "OK"]
        raw = Counter(r["raw_cardinal"]["disposition"] for r in ok)
        mf = Counter(r["magnitude_free"]["disposition"] for r in ok)
        out[label] = {
            "n_runs": len(selected), "n_ok": len(ok), "n_errors": len(selected)-len(ok),
            "n_unique_semantic_unit_hashes": len({r["semantic_unit_hash"] for r in ok}),
            "n_unique_effect_topology_hashes": len({r["effect_topology_hash"] for r in ok}),
            "raw_cardinal_attention": dict(raw),
            "magnitude_free_attention": dict(mf),
            "raw_stability": (max(raw.values()) / len(ok)) if ok else 0.0,
            "magnitude_free_stability": (max(mf.values()) / len(ok)) if ok else 0.0,
            "attention_changed_repeats": [r["repeat"] for r in ok if r["raw_cardinal"]["disposition"] != r["magnitude_free"]["disposition"]],
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    engine, db, sources, acquisition, manifest = _prepare_base_world()
    try:
        if not all(x["hash_match"] and x["char_count_match"] for x in acquisition.values()):
            raise RuntimeError("real-web acquisition continuity gate failed before model calls")
        for node in build_phase6b_mvp_kernel_nodes():
            db.add(node)
        db.flush()
        nodes = _active_kernel(db)
        code_by_id = {str(n.id): str((n.payload or {}).get("phase6b_fixture_code") or n.title) for n in nodes}
        rows = []
        for label in LABELS:
            for repeat in range(1, args.repeats + 1):
                try:
                    row = _one(label, sources[label], nodes, code_by_id, repeat)
                except Exception as exc:
                    row = {"label": label, "repeat": repeat, "status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:3000]}
                rows.append(row)
                print(json.dumps({
                    "label": label, "repeat": repeat, "status": row["status"],
                    "n_units": len(row.get("semantic_units") or []),
                    "topology": row.get("effect_topology"),
                    "raw": (row.get("raw_cardinal") or {}).get("disposition"),
                    "magnitude_free": (row.get("magnitude_free") or {}).get("disposition"),
                    "error": row.get("error"),
                }, ensure_ascii=False), flush=True)
        summary = _summary(rows)
        output = {
            "run_version": RUN_VERSION,
            "status": "REAL_WEB_NATIVE_PERCEPTION_AND_CALIBRATION_VALIDATION",
            "measurement_sha": git_head(),
            "acquisition": acquisition,
            "kernel_fixture": "phase6b-mvp-in-memory-copy",
            "repeats": args.repeats,
            "sensor_temperature": 0.1,
            "changed_variable_within_each_realization": "effect_calibration only",
            "interpretation_note": "No new cognitive gold labels; report stability/behavior, not automatic correctness.",
            "summary": summary,
            "rows": rows,
        }
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
        path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str)+"\n", encoding="utf-8")
        print(f"RESULT_PATH={path.relative_to(ROOT)}")
        print(f"RESULT_SHA256={hashlib.sha256(path.read_bytes()).hexdigest()}")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close(); engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
