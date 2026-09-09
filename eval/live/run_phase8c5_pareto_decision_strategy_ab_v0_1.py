from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import (
    CognitiveEffect,
    CognitiveImpactAssessment,
    legal_public_effects,
    normalize_frozen_transition,
    select_primary_effect,
)
from app.services.matching import KernelMatch
from app.services.pareto_decision_strategy import decision_vector, pareto_frontier
from app.services.scheduler import (
    RuntimeView,
    SchedulerFeatures,
    decision_strategy_snapshot,
    get_decision_strategy,
    route,
)
from eval.live.run_phase8c2_production_sensor_bridge_ab_v0_1 import _base_world, _load_manifest

RUN_VERSION = "phase8c5-pareto-decision-strategy-ab-v0.1"
STEP2 = ROOT / (
    "eval/live/results/phase8c3_native_interface_probe_v0_1/"
    "phase8c3_native_interface_probe_v0.1_20260909T135412Z.json"
)
STEP2_SHA256 = "3f68c034b55fd8a132c282027f87fe3665a388ed94e8be2e653bfba6aaf55d9e"
OUT_DIR = ROOT / "eval/live/results/phase8c5_pareto_decision_strategy_ab_v0_1"
CASES = ("RS05", "RS15", "RS11", "RS12")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _features() -> SchedulerFeatures:
    return SchedulerFeatures(
        topic_relevance=0.5,
        structural_relevance=0.2,
        decision_relevance=0.2,
        novelty=0.5,
        credibility=0.6,
        kernel_delta=0.2,
        bottleneck_alignment=0.1,
        disagreement=0.0,
        actionability=0.3,
        temporal_value=0.3,
        cognitive_cost=2.0,
        evidence_maturity=0.6,
        threatens_active_work=False,
        marketing_heavy=False,
        sources_conflict=False,
        high_quality_technical=False,
        foundational_paper=False,
    )


def _load_frozen() -> dict:
    raw = STEP2.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != STEP2_SHA256:
        raise RuntimeError(f"Step2 artifact SHA mismatch: {actual}")
    return json.loads(raw)


def _reconstruct_matches(run: dict, nodes) -> list[KernelMatch]:
    by_id = {str(node.id): node for node in nodes}
    out: list[KernelMatch] = []
    for item in run.get("matches") or []:
        raw = str(item.get("target") or "")
        node = by_id.get(raw)
        if node is None:
            continue
        rel = str(item.get("relevance_type") or "TOPIC")
        out.append(
            KernelMatch(
                node_id=node.id,
                node_type=node.node_type,
                title=node.title,
                score=float(item.get("score") or 0.0),
                reason=str(item.get("reason") or ""),
                structural=rel.upper() == "STRUCTURAL",
                relevance_type=rel,
            )
        )
    return out


def _reconstruct_effects(run: dict, nodes) -> list[CognitiveEffect]:
    by_id = {str(node.id): node for node in nodes}
    out: list[CognitiveEffect] = []
    for item in run.get("effects") or []:
        op = CognitiveEffectKind(str(item["operation"]))
        raw = item.get("target")
        target = None if op == CognitiveEffectKind.OPEN_NEW else (UUID(str(raw)) if raw else None)
        node = by_id.get(str(raw)) if raw and target is not None else None
        out.append(
            CognitiveEffect(
                target_kernel_node_id=target,
                operation=op,
                change_magnitude=float(item["change_magnitude"]),
                epistemic_strength=float(item["epistemic_strength"]),
                target_importance=float(item["target_importance"]),
                reason=str(item.get("reason") or ""),
                exploration_candidate=bool(item.get("exploration_candidate")),
                target_node_type=node.node_type if node is not None else None,
            )
        )
    return out


def _effect_row(effect: CognitiveEffect) -> dict:
    return {
        "operation": effect.operation.value,
        "target": str(effect.target_kernel_node_id) if effect.target_kernel_node_id else None,
        "change_magnitude": float(effect.change_magnitude),
        "epistemic_strength": float(effect.epistemic_strength),
        "target_importance": float(effect.target_importance),
    }


def _strategy_result(strategy, assessment, matches) -> dict:
    plan = route(
        _features(),
        RuntimeView(),
        assessment=assessment,
        matches=matches,
        decision_strategy=strategy,
    )
    return {
        "strategy": decision_strategy_snapshot(strategy),
        "disposition": plan.disposition.value,
        "expected_output": plan.expected_output.value,
        "reason": plan.reason,
    }


def _run_one(case_id: str, run: dict, manifest: dict) -> dict:
    engine, db, _source, _code_by_id = _base_world(case_id, dict(manifest["cases"][case_id]))
    try:
        from app.services.pipeline import _active_kernel

        nodes = _active_kernel(db)
        matches = _reconstruct_matches(run, nodes)
        effects = _reconstruct_effects(run, nodes)
        assessment = CognitiveImpactAssessment(effects=effects, attention_cost=2.0)
        normalized = normalize_frozen_transition(assessment, matches).assessment
        legal = legal_public_effects(normalized)
        primary = select_primary_effect(normalized)
        frontier = pareto_frontier(legal)
        return {
            "case": case_id,
            "repeat": int(run["repeat"]),
            "source_effect_count": len(effects),
            "legal_effect_count": len(legal),
            "primary_effect": _effect_row(primary) if primary is not None else None,
            "pareto_frontier": [
                {**_effect_row(effect), "decision_vector": list(decision_vector(effect))}
                for effect in frontier
            ],
            "one_delta": _strategy_result(get_decision_strategy("one-delta"), normalized, matches),
            "pareto": _strategy_result(get_decision_strategy("pareto-multidelta"), normalized, matches),
        }
    finally:
        db.close()
        engine.dispose()


def _summary(rows: list[dict]) -> dict:
    out = {}
    for case_id in CASES:
        case_rows = [row for row in rows if row["case"] == case_id]
        one = Counter(row["one_delta"]["disposition"] for row in case_rows)
        pareto = Counter(row["pareto"]["disposition"] for row in case_rows)
        changed = [
            row["repeat"]
            for row in case_rows
            if row["one_delta"]["disposition"] != row["pareto"]["disposition"]
        ]
        primary = Counter(
            str((row["primary_effect"] or {}).get("operation")) + ":" + str((row["primary_effect"] or {}).get("target"))
            for row in case_rows
        )
        frontier_sets = Counter(
            str(tuple((e["operation"], e["target"]) for e in row["pareto_frontier"]))
            for row in case_rows
        )
        out[case_id] = {
            "one_delta_attention": dict(one),
            "pareto_attention": dict(pareto),
            "attention_changed_repeats": changed,
            "one_delta_primary_counts": dict(primary),
            "pareto_frontier_set_counts": dict(frontier_sets),
        }
    return out


def main() -> int:
    frozen = _load_frozen()
    manifest = _load_manifest()
    rows: list[dict] = []
    for case_id in CASES:
        for run in frozen.get("runs") or []:
            if run.get("case") != case_id or run.get("status") != "OK":
                continue
            row = _run_one(case_id, run, manifest)
            rows.append(row)
            print(
                json.dumps(
                    {
                        "case": case_id,
                        "repeat": row["repeat"],
                        "one_delta": row["one_delta"]["disposition"],
                        "pareto": row["pareto"]["disposition"],
                        "primary": row["primary_effect"],
                        "frontier": row["pareto_frontier"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    summary = _summary(rows)
    output = {
        "run_version": RUN_VERSION,
        "status": "CONTROLLED_FROZEN_DECISION_STRATEGY_AB",
        "measurement_sha": git_head(),
        "source_artifact": str(STEP2.relative_to(ROOT)),
        "source_artifact_sha256": STEP2_SHA256,
        "frozen_layers": ["native canonical CognitiveEffects", "Kernel fixture", "runtime", "policy thresholds"],
        "changed_variable": "decision_strategy",
        "normalization": "OPEN_NEW target is forced to null, matching canonical production semantics.",
        "limitations": [
            "Frozen effects come from the native Phase 8C.3 probe, not full production grounding.",
            "change_magnitude remains the frozen raw LLM pseudo-cardinal estimate.",
            "This A/B isolates decision geometry; it does not test calibration quality.",
        ],
        "summary": summary,
        "rows": rows,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"RESULT_PATH={path.relative_to(ROOT)}", flush=True)
    print(f"RESULT_SHA256={hashlib.sha256(path.read_bytes()).hexdigest()}", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
