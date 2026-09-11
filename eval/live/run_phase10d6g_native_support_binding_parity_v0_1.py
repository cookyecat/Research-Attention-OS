from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for p in (ROOT, BACKEND):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app.cognitive.client import chat_json, chat_json_schema
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
from eval.live.phase10d6g_native_support_binding_v0_1 import (
    CONTRACT_VERSION,
    NativeSupportBoundResponse,
    SYSTEM_PROMPT,
    normalize_effects,
    relation_family,
    relation_identity,
    user_prompt,
    validate_effect,
)
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import selected_cases
from eval.live.run_phase10d6b_prompt_reconciliation_shadow_v0_1 import reconstruct_prod_matches

RUN_VERSION = "phase10d6g-native-support-binding-parity-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase10d6g_native_support_binding_parity_v0_1"
CASES = ("A", "D", "X", "N4")
REPEATS = 6
HISTORICAL_SENTINELS = {
    "A": [("CHALLENGE", "B1"), ("REINFORCE", "M1"), ("OPEN_NEW", "OPEN_NEW"), ("CHALLENGE", "Q1")],
    "D": [("CHALLENGE", "B2"), ("REINFORCE", "B1"), ("REINFORCE", "Q1"), ("REINFORCE", "BT1"), ("OPEN_NEW", "OPEN_NEW"), ("REINFORCE", "Q2"), ("REINFORCE", "M1")],
    "X": [("OPEN_NEW", "OPEN_NEW"), ("REINFORCE", "M1"), ("CHALLENGE", "BT1"), ("REINFORCE", "B1"), ("REINFORCE", "Q1")],
    "N4": [("OPEN_NEW", "OPEN_NEW"), ("REINFORCE", "B1"), ("REINFORCE", "BT1"), ("REINFORCE", "M1"), ("REINFORCE", "Q1"), ("CHALLENGE", "BT1"), ("CHALLENGE", "B1")],
}


def git_head():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def forced_chat(messages, **kwargs):
    return chat_json(
        messages,
        timeout=float(kwargs.get("timeout") or 60.0),
        thinking=kwargs.get("thinking"),
        reasoning_effort=kwargs.get("reasoning_effort"),
        temperature=0.1,
    )


def serialize(effect, nodes):
    by_id = {node.id: str((node.payload or {}).get("phase6b_fixture_code") or node.title) for node in nodes}
    return {
        "operation": effect.operation,
        "target_kernel_node_id": str(effect.target_kernel_node_id) if effect.target_kernel_node_id else None,
        "target": by_id.get(effect.target_kernel_node_id) if effect.target_kernel_node_id else None,
        "change_magnitude_debug_only": float(effect.change_magnitude),
        "epistemic_strength_debug_only": float(effect.epistemic_strength),
        "target_importance_debug_only": float(effect.target_importance),
        "support_unit_ids": list(effect.support_unit_ids),
        "jurisdiction_anchor_ids": [str(x) for x in effect.jurisdiction_anchor_ids],
        "jurisdiction_anchors": [by_id.get(x, str(x)) for x in effect.jurisdiction_anchor_ids],
        "reason": effect.reason,
    }


def run_one(label, ordinal, case, nodes, matches):
    parsed, meta, events = chat_json_schema(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt(case["frozen_units"], matches, nodes)}],
        NativeSupportBoundResponse,
        chat_fn=forced_chat,
        thinking="disabled",
        timeout=60.0,
    )
    raw = []
    valid_effects = []
    invalid = []
    for effect in parsed.effects:
        row = serialize(effect, nodes)
        raw.append(row)
        ok, reason = validate_effect(effect, units=case["frozen_units"], matches=matches, nodes=nodes)
        if ok:
            valid_effects.append(effect)
        else:
            invalid.append({**row, "invalid_reason": reason})
    normalized = normalize_effects(valid_effects, nodes=nodes)
    valid_rows = [{**serialize(e, nodes), "family": list(relation_family(e, nodes=nodes)), "identity": list(relation_identity(e, nodes=nodes))} for e in valid_effects]
    norm_rows = [{**serialize(e, nodes), "family": list(relation_family(e, nodes=nodes)), "identity": list(relation_identity(e, nodes=nodes))} for e in normalized]
    return {
        "sample_id": f"{label}-{ordinal}",
        "status": "OK",
        "raw_effects": raw,
        "valid_effects": valid_rows,
        "normalized_effects": norm_rows,
        "invalid_effects": invalid,
        "raw_effect_count": len(raw),
        "valid_effect_count": len(valid_effects),
        "normalized_effect_count": len(normalized),
        "duplicate_effect_count": len(valid_effects) - len(normalized),
        "relation_families": sorted({tuple(x["family"]) for x in norm_rows}, key=repr),
        "meta": meta,
        "schema_events": events,
    }


def summarize(label, rows):
    ok = [r for r in rows if r["status"] == "OK"]
    raw = sum(r["raw_effect_count"] for r in ok)
    valid = sum(r["valid_effect_count"] for r in ok)
    norm = sum(r["normalized_effect_count"] for r in ok)
    invalid_reasons = Counter(x["invalid_reason"] for r in ok for x in r["invalid_effects"])
    family_sample_counts = Counter()
    support_by_family = defaultdict(Counter)
    for r in ok:
        families = set()
        for e in r["normalized_effects"]:
            family = tuple(e["family"])
            families.add(family)
            support_by_family[family][tuple(sorted(e["support_unit_ids"]))] += 1
        family_sample_counts.update(families)
    sentinel_rows = {}
    for sentinel in HISTORICAL_SENTINELS[label]:
        count = family_sample_counts[sentinel]
        sentinel_rows[repr(sentinel)] = {
            "sample_count": count,
            "sample_rate": count / len(ok) if ok else 0.0,
            "recovered_at_least_once": bool(count),
        }
    stable_support = {}
    for family, counter in support_by_family.items():
        total = sum(counter.values())
        top_sig, top_count = counter.most_common(1)[0]
        stable_support[repr(family)] = {
            "n_effects": total,
            "n_support_signatures": len(counter),
            "mode_signature": list(top_sig),
            "mode_rate": top_count / total,
        }
    return {
        "n_ok": len(ok),
        "n_error": len(rows) - len(ok),
        "raw_effects": raw,
        "valid_effects": valid,
        "normalized_effects": norm,
        "valid_effect_rate": valid / raw if raw else 1.0,
        "duplicate_effects_removed": valid - norm,
        "invalid_reason_counts": dict(invalid_reasons),
        "relation_family_sample_counts": {repr(k): v for k, v in sorted(family_sample_counts.items(), key=lambda x: repr(x[0]))},
        "historical_sentinel_recovery": sentinel_rows,
        "historical_sentinel_fraction_recovered": sum(int(v["recovered_at_least_once"]) for v in sentinel_rows.values()) / len(sentinel_rows),
        "support_binding_by_family": stable_support,
    }


def main():
    selected = selected_cases()
    nodes = build_phase6b_mvp_kernel_nodes()
    results = {}
    for label in CASES:
        case = selected[label]["case"]
        matches = reconstruct_prod_matches(case, nodes)
        rows = []
        for ordinal in range(1, REPEATS + 1):
            try:
                row = run_one(label, ordinal, case, nodes, matches)
            except Exception as exc:
                row = {"sample_id": f"{label}-{ordinal}", "status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:3000]}
            rows.append(row)
            print(json.dumps({
                "label": label, "repeat": ordinal, "status": row["status"],
                "raw": row.get("raw_effect_count"), "valid": row.get("valid_effect_count"),
                "normalized": row.get("normalized_effect_count"), "duplicates": row.get("duplicate_effect_count"),
                "families": row.get("relation_families"), "error": row.get("error"),
            }, ensure_ascii=False), flush=True)
        summary = summarize(label, rows)
        results[label] = {
            "samples": rows,
            "summary": summary,
            "frozen_units_replay_sha256": case["frozen_units_replay_sha256"],
            "frozen_locate": case["locate"]["modal"],
        }
        print(json.dumps({"label": label, "summary": {k: v for k, v in summary.items() if k != "support_binding_by_family"}}, ensure_ascii=False), flush=True)
    out = {
        "run_version": RUN_VERSION,
        "status": "NATIVE_SEMANTICS_SUPPORT_BINDING_PARITY_SHADOW",
        "measurement_sha": git_head(),
        "relation_contract_version": CONTRACT_VERSION,
        "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "cases": list(CASES),
        "repeats_per_case": REPEATS,
        "historical_sentinels": {k: [list(x) for x in v] for k, v in HISTORICAL_SENTINELS.items()},
        "results": results,
        "guardrails": [
            "Exact frozen Auditor worlds, Kernel fixtures and modal Locate are reused; no acquisition/Sensor/Auditor/Locate call occurs.",
            "Historical NATIVE_IMPACT_SYSTEM is the base semantic contract; only explicit support/jurisdiction provenance obligations are appended.",
            "Compatibility cardinal fields remain diagnostic-only; no Attention or authority policy is evaluated.",
            "Unknown identifiers fail closed at effect level and are never rewritten.",
            "Duplicate relation identities are retained raw and deterministically normalized for analysis.",
            "Historical >=0.50 relation-family sentinels are descriptive parity references, not correctness Gold.",
            "No outcome-dependent expansion or prompt editing.",
            "Production defaults remain unchanged; Phase 9A remains paused.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    print("RESULT_SHA256=" + sha256(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
