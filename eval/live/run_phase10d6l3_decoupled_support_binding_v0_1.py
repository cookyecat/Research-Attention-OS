from __future__ import annotations

import hashlib, json, subprocess, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for p in (ROOT, BACKEND):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from pydantic import Field
from app.cognitive.client import chat_json, chat_json_schema
from app.cognitive.schemas import StrictModel
from app.services.cognitive_impact import node_proposition
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import selected_cases
from eval.live.run_phase10d6b_prompt_reconciliation_shadow_v0_1 import reconstruct_prod_matches
from eval.live.run_standing_radar_fit_eval import load_repo_env

load_repo_env()
RUN_VERSION = "phase10d6l3-decoupled-support-binding-v0.1"
PRIMARY_ARTIFACT = ROOT / "eval/live/results/phase10d6l1_minimal_prompt_authority_shadow_v0_1/phase10d6l1_minimal_prompt_authority_shadow_v0.1_20260911T124905Z.json"
PRIMARY_SHA256 = "444fe8bb7e0d7670411983167fade62fd638dd7f7e8ba7599303e45a5c2fd8cf"
OUT_DIR = ROOT / "eval/live/results/phase10d6l3_decoupled_support_binding_v0_1"
CASES = ("A", "D", "X", "N4")
REPEATS = 3

SYSTEM_PROMPT = """You are the Support Binding stage for Research Attention OS.
The semantic relations are already frozen. You must not add, remove, merge, retarget, reinterpret, or change any relation.
For each relation_id, select exact audited unit_id values that materially support that frozen relation. If no supplied unit supports it, return an empty support_unit_ids list.
For OPEN_NEW only, select supplied Kernel location ids that genuinely define its cognitive jurisdiction. If none fits, return an empty jurisdiction_anchor_ids list.
For targeted REINFORCE/CHALLENGE, jurisdiction_anchor_ids should be empty because the existing target already supplies location.
Return exactly one binding for every supplied relation_id and no others. Do not output operation, target, scores, Attention, or replacement relations.
Return JSON only."""

class BindingItem(StrictModel):
    relation_id: str
    support_unit_ids: list[str] = Field(default_factory=list)
    jurisdiction_anchor_ids: list[UUID] = Field(default_factory=list)
    reason: str = ""

class BindingResponse(StrictModel):
    bindings: list[BindingItem] = Field(default_factory=list)

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def forced_chat(messages, **kwargs):
    return chat_json(
        messages,
        timeout=float(kwargs.get("timeout") or 60.0),
        thinking=kwargs.get("thinking"),
        reasoning_effort=kwargs.get("reasoning_effort"),
        temperature=0.1,
    )


def frozen_relations(label: str, sample: dict) -> list[dict]:
    out = []
    for idx, effect in enumerate(sample.get("effects") or [], start=1):
        out.append({
            "relation_id": f"{label}:{sample['sample_id']}:{idx}",
            "operation": effect.get("operation"),
            "target_kernel_node_id": effect.get("target_kernel_node_id"),
            "reason": effect.get("reason") or "",
        })
    return out

def build_user_prompt(*, relations: list[dict], units: list[dict], matches, nodes) -> str:
    by_id = {node.id: node for node in nodes}
    locations = []
    for match in matches:
        node = by_id[match.node_id]
        locations.append({
            "id": str(node.id),
            "type": node.node_type,
            "title": node.title,
            "proposition": node_proposition(node),
            "relevance_type": match.relevance_type,
        })
    unit_rows = [
        {"unit_id": str(u.get("unit_id") or ""), "text": u.get("content") or u.get("text") or u.get("statement") or ""}
        for u in units
    ]
    shape = {"bindings": [{
        "relation_id": relations[0]["relation_id"] if relations else "relation-id",
        "support_unit_ids": [], "jurisdiction_anchor_ids": [], "reason": ""
    }]}
    return (
        "Frozen semantic relations (immutable):\n" + json.dumps(relations, ensure_ascii=False)
        + "\n\nAudited semantic units:\n" + json.dumps(unit_rows, ensure_ascii=False)
        + "\n\nKernel locations:\n" + json.dumps(locations, ensure_ascii=False)
        + "\n\nReturn JSON exactly in this shape:\n" + json.dumps(shape, ensure_ascii=False)
    )

def validate_bindings(*, parsed: BindingResponse, relations: list[dict], units: list[dict], matches) -> tuple[bool, list[str]]:
    errors: list[str] = []
    expected = [r["relation_id"] for r in relations]
    got = [b.relation_id for b in parsed.bindings]
    if len(got) != len(set(got)):
        errors.append("DUPLICATE_RELATION_ID")
    if set(got) != set(expected) or len(got) != len(expected):
        errors.append("RELATION_ID_SET_MISMATCH")
    known_units = {str(u.get("unit_id") or "") for u in units}
    known_anchors = {m.node_id for m in matches}
    relation_by_id = {r["relation_id"]: r for r in relations}
    for b in parsed.bindings:
        if any(uid not in known_units for uid in b.support_unit_ids):
            errors.append(f"UNKNOWN_SUPPORT:{b.relation_id}")
        if any(anchor not in known_anchors for anchor in b.jurisdiction_anchor_ids):
            errors.append(f"UNKNOWN_ANCHOR:{b.relation_id}")
        rel = relation_by_id.get(b.relation_id)
        if rel and rel["operation"] != "OPEN_NEW" and b.jurisdiction_anchor_ids:
            errors.append(f"TARGETED_HAS_JURISDICTION:{b.relation_id}")
    return (not errors), errors


def run_binding_draw(*, relations: list[dict], units: list[dict], matches, nodes) -> dict:
    parsed, meta, events = chat_json_schema(
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": build_user_prompt(relations=relations, units=units, matches=matches, nodes=nodes)}],
        BindingResponse, chat_fn=forced_chat, thinking="disabled", timeout=60.0,
    )
    ok, errors = validate_bindings(parsed=parsed, relations=relations, units=units, matches=matches)
    return {
        "status": "OK" if ok else "INVALID",
        "errors": errors,
        "bindings": [{
            "relation_id": b.relation_id,
            "support_unit_ids": list(b.support_unit_ids),
            "jurisdiction_anchor_ids": [str(x) for x in b.jurisdiction_anchor_ids],
            "reason": b.reason,
        } for b in parsed.bindings],
        "meta": meta,
        "schema_events": events,
    }

EXPECTED_NONEMPTY = {"A": 0, "D": 3, "X": 5, "N4": 6}


def summarize_sample(relations: list[dict], draws: list[dict]) -> dict:
    by_relation = {r["relation_id"]: {"relation": r, "support": Counter(), "anchor": Counter(), "n_present": 0} for r in relations}
    exact_id_draws = 0
    unknown_identifier_errors = 0
    for draw in draws:
        expected = {r["relation_id"] for r in relations}
        got = {b["relation_id"] for b in draw.get("bindings", [])}
        if draw.get("status") == "OK" and got == expected and len(draw.get("bindings", [])) == len(relations):
            exact_id_draws += 1
        unknown_identifier_errors += sum(
            1 for e in draw.get("errors", []) if e.startswith("UNKNOWN_SUPPORT:") or e.startswith("UNKNOWN_ANCHOR:")
        )
        for binding in draw.get("bindings", []):
            slot = by_relation.get(binding["relation_id"])
            if slot is None:
                continue
            slot["n_present"] += 1
            slot["support"][tuple(sorted(binding["support_unit_ids"]))] += 1
            slot["anchor"][tuple(sorted(binding["jurisdiction_anchor_ids"]))] += 1
    relation_rows = {}
    all_support_stable = True
    for relation_id, slot in by_relation.items():
        support_mode, support_count = ((), 0)
        anchor_mode, anchor_count = ((), 0)
        if slot["support"]:
            support_mode, support_count = slot["support"].most_common(1)[0]
        if slot["anchor"]:
            anchor_mode, anchor_count = slot["anchor"].most_common(1)[0]
        support_stable = support_count >= 2
        all_support_stable = all_support_stable and support_stable
        relation_rows[relation_id] = {
            "relation": slot["relation"],
            "n_present": slot["n_present"],
            "support_signature_count": len(slot["support"]),
            "modal_support_signature": list(support_mode),
            "modal_support_count": support_count,
            "modal_support_rate": support_count / REPEATS,
            "support_stable_2_of_3": support_stable,
            "anchor_signature_count": len(slot["anchor"]),
            "modal_anchor_signature": list(anchor_mode),
            "modal_anchor_count": anchor_count,
            "modal_anchor_rate": anchor_count / REPEATS,
        }
    return {
        "n_relations": len(relations),
        "n_draws": len(draws),
        "n_ok_draws": sum(d.get("status") == "OK" for d in draws),
        "exact_relation_id_draws": exact_id_draws,
        "unknown_identifier_errors": unknown_identifier_errors,
        "all_relations_support_stable_2_of_3": all_support_stable,
        "relations": relation_rows,
    }


def main() -> int:
    if sha256(PRIMARY_ARTIFACT) != PRIMARY_SHA256:
        raise RuntimeError("primary artifact SHA256 mismatch")
    primary = json.loads(PRIMARY_ARTIFACT.read_text(encoding="utf-8"))
    selected = selected_cases()
    if tuple(selected) != CASES:
        raise RuntimeError(f"case order mismatch: {tuple(selected)}")
    nodes = build_phase6b_mvp_kernel_nodes()
    results = {}
    total_calls = 0
    for label in CASES:
        case = selected[label]["case"]
        matches = reconstruct_prod_matches(case, nodes)
        p1_samples = primary["results"][label]["arms"]["P1"]
        nonempty = [s for s in p1_samples if s.get("effects")]
        if len(nonempty) != EXPECTED_NONEMPTY[label]:
            raise RuntimeError(f"{label} non-empty P1 sample count drift: {len(nonempty)}")
        sample_rows = []
        for sample in nonempty:
            relations = frozen_relations(label, sample)
            frozen_identity = [(r["relation_id"], r["operation"], r["target_kernel_node_id"]) for r in relations]
            draws = []
            for draw_idx in range(1, REPEATS + 1):
                try:
                    draw = run_binding_draw(relations=relations, units=case["frozen_units"], matches=matches, nodes=nodes)
                except Exception as exc:
                    draw = {"status": "ERROR", "errors": [f"{type(exc).__name__}:{str(exc)[:500]}"], "bindings": []}
                draw["draw"] = draw_idx
                draws.append(draw)
                total_calls += 1
                print(json.dumps({
                    "label": label, "sample": sample["sample_id"], "draw": draw_idx,
                    "status": draw["status"], "errors": draw.get("errors", []),
                    "n_bindings": len(draw.get("bindings", [])),
                }, ensure_ascii=False), flush=True)
            if frozen_identity != [(r["relation_id"], r["operation"], r["target_kernel_node_id"]) for r in relations]:
                raise RuntimeError("frozen relation topology mutated in runner")
            sample_rows.append({
                "sample_id": sample["sample_id"],
                "frozen_relations": relations,
                "draws": draws,
                "summary": summarize_sample(relations, draws),
            })
        results[label] = {
            "expected_nonempty_samples": EXPECTED_NONEMPTY[label],
            "nonempty_samples": sample_rows,
        }
    if total_calls != 42:
        raise RuntimeError(f"call-count drift: {total_calls}")

    samples = [s for c in results.values() for s in c["nonempty_samples"]]
    all_draws = [d for s in samples for d in s["draws"]]
    relation_summaries = [r for s in samples for r in s["summary"]["relations"].values()]
    n_bindings = sum(len(d.get("bindings", [])) for d in all_draws)
    empty_support = sum(not b["support_unit_ids"] for d in all_draws for b in d.get("bindings", []))
    empty_anchor = sum(not b["jurisdiction_anchor_ids"] for d in all_draws for b in d.get("bindings", []))
    integrity_pass = (
        all(d.get("status") == "OK" for d in all_draws)
        and all(s["summary"]["exact_relation_id_draws"] == REPEATS for s in samples)
        and all(s["summary"]["unknown_identifier_errors"] == 0 for s in samples)
    )
    stability_pass = all(r["support_stable_2_of_3"] for r in relation_summaries)
    summary = {
        "n_calls": total_calls,
        "n_ok_calls": sum(d.get("status") == "OK" for d in all_draws),
        "structured_success_rate": sum(d.get("status") == "OK" for d in all_draws) / total_calls,
        "exact_relation_id_preservation": integrity_pass,
        "unknown_identifier_error_count": sum(s["summary"]["unknown_identifier_errors"] for s in samples),
        "n_frozen_relation_instances": len(relation_summaries),
        "n_stable_support_relation_instances": sum(r["support_stable_2_of_3"] for r in relation_summaries),
        "all_support_signatures_stable_2_of_3": stability_pass,
        "empty_support_binding_rate": empty_support / n_bindings if n_bindings else 0.0,
        "empty_anchor_binding_rate": empty_anchor / n_bindings if n_bindings else 0.0,
        "promotion_gate_pass": integrity_pass and stability_pass,
    }
    out = {
        "run_version": RUN_VERSION,
        "status": "DECOUPLED_SUPPORT_BINDING_MEASUREMENT",
        "measurement_sha": git_head(),
        "primary_artifact": str(PRIMARY_ARTIFACT.relative_to(ROOT)),
        "primary_artifact_sha256": PRIMARY_SHA256,
        "binder_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "cases": list(CASES),
        "repeats_per_relation_set": REPEATS,
        "summary": summary,
        "results": results,
        "guardrails": [
            "No Relation Mapping call occurs in this gate; P1 relations are frozen from the closed 10D.6L.1 artifact.",
            "The binder schema has no operation or target field and cannot add/delete/retarget relations.",
            "Empty support/anchor is legal and preferred to invented provenance.",
            "Unknown support/anchor identifiers fail closed.",
            "Flash binding errors are robustness findings, not automatic architecture failures.",
            "No Attention policy or production switch is evaluated; Phase 9A remains paused.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print("SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    print("RESULT_SHA256=" + sha256(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
