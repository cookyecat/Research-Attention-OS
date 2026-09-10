from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app import models as _models  # noqa: F401
from app.db import Base
from app.enums import CognitiveEffectKind
from app.services.ingestion import ingest_url
from app.services.cognitive_impact import CognitiveImpactAssessment, legal_public_effects, normalize_frozen_transition
from app.services.pipeline import _active_kernel
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
from eval.live.phase8c3_native_cognitive_interface_v0_1 import NATIVE_IMPACT_SYSTEM, native_assess, native_locate
from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map, execution_snapshot as map_snapshot
from eval.live.run_phase8c7_real_web_magnitude_free_validation_v0_1 import _assessment, _features, _forced_chat, _matches, _perceive

RUN_VERSION = "phase10d2-real-web-source-diversity-broadening-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase10d2_real_web_source_diversity_broadening_v0_1"
MANIFEST = ROOT / "eval/live/manifest.phase10d2_real_web_broadening.v0.1.yaml"
LABELS = ("N1", "N2", "B1", "B2", "F1", "F2")
STRATEGY_ID = "pareto-multidelta-magnitude-free-anchored-open-new"
LOCATE_REPEATS = 3
INITIAL_N = 12
EXPANDED_N = 24
HALF_WIDTH_GATE = 0.20




def prepare_batch2_world():
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    if manifest.get("selection_status") != "preregistered_before_raos_outcomes":
        raise RuntimeError("batch2 selection status mismatch")
    specs = {str(row["label"]): row for row in manifest.get("sources") or []}
    if tuple(specs) != LABELS:
        raise RuntimeError(f"batch2 labels/order mismatch: {tuple(specs)}")
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    Base.metadata.create_all(engine)
    db = Session(engine, autoflush=False, expire_on_commit=False)
    sources = {}
    acquisition = {}
    try:
        for label in LABELS:
            spec = specs[label]
            source = ingest_url(db, str(spec["url"]))
            sources[label] = source
            acquisition[label] = {
                "label": label,
                "stratum": str(spec["stratum"]),
                "publisher_preregistered": str(spec["publisher"]),
                "title_preregistered": str(spec["title"]),
                "source_id": str(source.id),
                "title_fetched": source.title,
                "requested_url": str(spec["url"]),
                "canonical_url": source.canonical_url,
                "content_hash": source.content_hash,
                "content_chars": len(source.content_text or ""),
                "fingerprint": source.fingerprint,
                "ingestion_method": source.ingestion_method,
                "raw_metadata": source.raw_metadata,
            }
        return engine, db, sources, acquisition, manifest
    except Exception:
        db.close(); engine.dispose(); raise


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prompt_sha() -> str:
    return hashlib.sha256(NATIVE_IMPACT_SYSTEM.encode()).hexdigest()


def jsonable_unit(unit: dict) -> dict:
    # Exact replay contract for fields consumed by native canonical payload.
    return {
        "unit_id": str(unit.get("unit_id") or ""),
        "statement": str(unit.get("statement") or ""),
        "epistemic_status": str(unit.get("epistemic_status") or ""),
        "confidence": str(unit.get("confidence") or ""),
        "supports": list(unit.get("supports") or []),
    }


def unit_replay_hash(units: list[dict]) -> str:
    payload = [jsonable_unit(u) for u in units]
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def code_maps(nodes):
    code_by_id = {}
    for n in nodes:
        code = str((n.payload or {}).get("phase6b_fixture_code") or n.title)
        code_by_id[str(n.id)] = code
    return code_by_id


def serialize_match(item, nodes) -> dict:
    by_id = {n.id: n for n in nodes}
    node = by_id[item.kernel_node_id]
    code = str((node.payload or {}).get("phase6b_fixture_code") or node.title)
    return {
        "target": code,
        "kernel_node_id": str(item.kernel_node_id),
        "relevance_type": str(item.relevance_type or "TOPIC"),
        "score": float(item.score),
        "reason": str(item.reason or ""),
    }


def modal_locate(runs: list[dict]) -> dict:
    # Modal target set only; preserve the earliest complete realization for frozen replay.
    keys = [tuple(sorted(r["target_set"])) for r in runs]
    counts = Counter(keys)
    best_count = max(counts.values())
    winners = {k for k, v in counts.items() if v == best_count}
    selected = next(r for r, key in zip(runs, keys) if key in winners)
    return {
        "modal_target_set": list(tuple(sorted(selected["target_set"]))),
        "modal_count": best_count,
        "modal_rate": best_count / len(runs),
        "selected_repeat": selected["repeat"],
        "selected_matches": selected["native_matches"],
    }


def branch_relation_key(nodes, admitted_units):
    code_by_id = code_maps(nodes)
    known_unit_ids = sorted(
        {str(u.get("unit_id") or "").strip() for u in admitted_units if str(u.get("unit_id") or "").strip()},
        key=lambda x: (-len(x), x),
    )

    def key(effect):
        op = effect.operation.value if hasattr(effect.operation, "value") else str(effect.operation)
        if op == "OPEN_NEW":
            reason = str(effect.reason or "")
            refs = tuple(sorted(uid for uid in known_unit_ids if uid and uid in reason))
            return ("OPEN_NEW", refs if refs else ("UNRESOLVED",))
        target = code_by_id.get(str(effect.target_kernel_node_id)) if effect.target_kernel_node_id else None
        return (op, target)

    return key


def current_attention(parsed, native_matches, nodes, strategy):
    prod_matches = _matches(native_matches, nodes)
    assessment = _assessment(parsed, nodes)
    normalized = normalize_frozen_transition(assessment, prod_matches).assessment
    legal = legal_public_effects(normalized)
    legal_assessment = CognitiveImpactAssessment(
        effects=legal,
        attention_cost=float(parsed.attention_cost or 2.0),
        exploration_candidate=bool(parsed.exploration_candidate),
    )
    plan = route(
        _features(parsed), RuntimeView(), assessment=legal_assessment,
        matches=prod_matches, decision_strategy=strategy,
    )
    return plan.disposition.value, legal, prod_matches, legal_assessment


def collect_relation_sample(label, ordinal, units, nodes, native_matches, strategy):
    parsed, meta, events = native_assess(units, nodes, native_matches, chat_fn=_forced_chat)
    disposition, legal, prod_matches, assessment = current_attention(parsed, native_matches, nodes, strategy)
    relation_key = branch_relation_key(nodes, units)
    report = analyze_decision_causal_core(
        assessment=assessment,
        matches=prod_matches,
        features=_features(parsed),
        decision_strategy=strategy,
        relation_key=relation_key,
    )
    if report.baseline_decision != disposition:
        raise RuntimeError(f"causal baseline mismatch {label} sample {ordinal}: {report.baseline_decision}!={disposition}")
    present = sorted({relation_key(e) for e in legal}, key=repr)
    return {
        "sample_id": f"fresh-{ordinal}",
        "topology": present,
        "necessary_core": report.necessary_core,
        "sufficient_supports": report.sufficient_supports,
        "attention": disposition,
        "effects": [
            {
                "operation": e.operation.value if hasattr(e.operation, "value") else str(e.operation),
                "target_kernel_node_id": str(e.target_kernel_node_id) if e.target_kernel_node_id else None,
                "change_magnitude_debug_only": float(e.change_magnitude),
                "epistemic_strength": float(e.epistemic_strength),
                "target_importance": float(e.target_importance),
                "reason": str(e.reason or ""),
            }
            for e in legal
        ],
        "causal_profile": report.as_dict(),
        "meta": meta,
        "schema_events": events,
    }


def expansion_reasons(m: dict) -> list[dict]:
    reasons = []
    lo, hi = m["attention_distribution"]["dominant_wilson95"]
    if (hi - lo) / 2 > HALF_WIDTH_GATE:
        reasons.append({
            "kind": "dominant_attention_precision",
            "half_width": (hi - lo) / 2,
            "action": m["attention_distribution"]["dominant_action"],
        })
    for relation, row in m["relation_map"].items():
        p = row["load_bearing"]["p"]
        hw = row["load_bearing"]["half_width"]
        if 0.25 <= p <= 0.75 and hw > HALF_WIDTH_GATE:
            reasons.append({"kind": "load_bearing_precision", "relation": relation, "p": p, "half_width": hw})
    return reasons


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--initial-n", type=int, default=INITIAL_N)
    ap.add_argument("--expanded-n", type=int, default=EXPANDED_N)
    args = ap.parse_args()
    if args.initial_n < 1 or args.expanded_n < args.initial_n:
        raise ValueError("invalid sample targets")

    engine, db, sources, acquisition, manifest = prepare_batch2_world()
    try:
        acquisition_class = {label: "NEW_BATCH2_SNAPSHOT" for label in LABELS}
        if any(not str((sources[label].content_text or "")).strip() for label in LABELS):
            raise RuntimeError("blank real-web source before model calls")
        print(json.dumps({"stage": "ACQUISITION_CLASS", "classes": acquisition_class}, ensure_ascii=False), flush=True)
        for node in build_phase6b_mvp_kernel_nodes():
            db.add(node)
        db.flush()
        nodes = _active_kernel(db)
        strategy = get_decision_strategy(STRATEGY_ID)
        cases = {}

        for label in LABELS:
            print(json.dumps({"label": label, "stage": "PERCEPTION_START"}), flush=True)
            units, perception_diag = _perceive(sources[label])
            frozen_units = [jsonable_unit(u) for u in units]
            if any(not u["statement"] for u in frozen_units):
                raise RuntimeError(f"blank admitted unit in {label}")
            replay_hash = unit_replay_hash(frozen_units)
            print(json.dumps({"label": label, "stage": "PERCEPTION_DONE", "n_units": len(frozen_units), "replay_hash": replay_hash}), flush=True)

            locate_runs = []
            raw_native_runs = []
            for repeat in range(1, LOCATE_REPEATS + 1):
                native, meta, events = native_locate(frozen_units, nodes, chat_fn=_forced_chat)
                serialized = [serialize_match(x, nodes) for x in native]
                target_set = sorted({x["target"] for x in serialized})
                locate_runs.append({
                    "repeat": repeat, "target_set": target_set, "native_matches": serialized,
                    "meta": meta, "schema_events": events,
                })
                raw_native_runs.append(native)
                print(json.dumps({"label": label, "stage": "LOCATE", "repeat": repeat, "targets": target_set}), flush=True)
            modal = modal_locate(locate_runs)
            selected_native = raw_native_runs[int(modal["selected_repeat"]) - 1]

            samples = []
            for ordinal in range(1, args.initial_n + 1):
                sample = collect_relation_sample(label, ordinal, frozen_units, nodes, selected_native, strategy)
                samples.append(sample)
                print(json.dumps({
                    "label": label, "stage": "N12", "sample": ordinal,
                    "attention": sample["attention"], "topology": sample["topology"],
                    "necessary": sample["necessary_core"], "sufficient": sample["sufficient_supports"],
                }, ensure_ascii=False), flush=True)
            n12_map = summarize_static_cognitive_map(samples)
            reasons = expansion_reasons(n12_map)
            expansion = {"triggered": bool(reasons), "reasons": reasons}
            print(json.dumps({"label": label, "stage": "N12_MAP", "attention": n12_map["attention_distribution"], "expansion": expansion}), flush=True)
            if reasons:
                for ordinal in range(len(samples) + 1, args.expanded_n + 1):
                    sample = collect_relation_sample(label, ordinal, frozen_units, nodes, selected_native, strategy)
                    samples.append(sample)
                    print(json.dumps({
                        "label": label, "stage": "N24", "sample": ordinal,
                        "attention": sample["attention"], "topology": sample["topology"],
                        "necessary": sample["necessary_core"], "sufficient": sample["sufficient_supports"],
                    }, ensure_ascii=False), flush=True)
            final_map = summarize_static_cognitive_map(samples)
            cases[label] = {
                "perception": perception_diag,
                "frozen_units": frozen_units,
                "frozen_units_replay_sha256": replay_hash,
                "locate": {"runs": locate_runs, "modal": modal},
                "sampling": {"initial_n": args.initial_n, "expanded_n": args.expanded_n, "expansion": expansion},
                "map": final_map,
                "samples": samples,
            }

        model_pairs = sorted({
            (s["meta"].get("requested_model"), s["meta"].get("response_model"))
            for c in cases.values() for s in c["samples"] if s.get("meta")
        }, key=repr)
        out = {
            "run_version": RUN_VERSION,
            "status": "REAL_WEB_FROZEN_PERCEPTION_STATIC_EMPIRICAL_MAP",
            "measurement_sha": git_head(),
            "manifest": str(MANIFEST.relative_to(ROOT)),
            "selection_strata": {label: acquisition[label]["stratum"] for label in LABELS},
            "acquisition": acquisition,
            "acquisition_class": acquisition_class,
            "perception_contract": "one fresh Sensor v0.2.6 + Auditor v0.1.1 pass per source, then exact frozen replay",
            "locate_contract": f"{LOCATE_REPEATS} repeats; modal target-set; earliest representative tie-break; then frozen",
            "relation_mapping_prompt_sha256": prompt_sha(),
            "decision_strategy": strategy.execution_snapshot(),
            "map_chip": map_snapshot(),
            "model_pairs_seen": model_pairs,
            "cases": cases,
            "guardrails": [
                "Batch-2 source labels/strata/URLs were preregistered before any RAOS outcome was observed.",
                "Every Batch-2 URL is a new frozen snapshot; this phase makes no historical continuity claim for these sources.",
                "Perception is sampled once per source and then frozen; this phase does not estimate Sensor/Auditor variance.",
                "Complete native-consumed semantic unit fields are persisted for exact replay.",
                "Relation Mapping is the only repeatedly sampled cognitive stage after Locate freeze.",
                "Raw change_magnitude is debug-only under the selected decision strategy.",
                "OPEN_NEW branch identity uses only explicit references to frozen admitted unit ids; unresolved branches remain UNRESOLVED.",
                "No human-gold accuracy claim is made from Attention class alone.",
                "No temporal/stochastic-process model is fitted.",
                "Production default remains one-delta-v1.",
            ],
        }
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        print("RESULT_PATH=" + str(path.relative_to(ROOT)))
        print("RESULT_SHA256=" + sha256(path))
        for label, case in cases.items():
            m = case["map"]
            print("\n###", label, "N=", m["n"])
            print("ATTN", m["attention_distribution"])
            print("TOPO_H", m["topology_distribution"]["entropy_bits"], "CORE_H", m["load_bearing_distribution"]["entropy_bits"])
            for relation, row in sorted(m["relation_map"].items(), key=lambda kv: (-kv[1]["load_bearing"]["p"], -kv[1]["topology"]["p"], kv[0])):
                if row["load_bearing"]["p"] > 0:
                    print(relation, "P(T)=", row["topology"]["p"], "P(B)=", row["load_bearing"]["p"], "CI=", row["load_bearing"]["wilson95"])
        return 0
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
